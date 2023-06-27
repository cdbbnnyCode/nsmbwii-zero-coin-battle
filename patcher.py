import relfile
import numpy as np
import sys
import json
import struct
import hexdump
import re

def add_section(rel, data, set_exec=True):
    # Add data to the next empty section of the REL file.
    # The IMP data is moved forward to allow space for this section.
    # The data is padded with 0 bytes (if necessary) in order to maintain 4-byte
    # alignment for the IMP table.
    # Inputs:
    #  - rel       The REL file object to modify
    #  - data      The data bytes to add (must be either a numpy array with dtype=uint8 or bytes object)
    #  - set_exec  Whether to set the executable bit on the section
    # Returns a tuple of (num, offset)
    #  - num       The section number that has been allocated
    #  - offset    The location of the section data in the REL file 
    if type(data) == bytes:
        data = np.frombuffer(data, dtype=np.uint8).copy()
    elif type(data) == np.ndarray:
        if data.dtype != np.uint8:
            raise ValueError("invalid array type for data, must be uint8")
    else:
        raise ValueError("invalid type for data")

    # ensure that the rel table is aligned to 8 bytes
    if len(data) % 8 != 0:
        data = np.append(data, np.zeros(8 - (len(data) % 8), dtype=np.uint8))

    found_sectionid = None
    next_sectionid = None
    for i, s in enumerate(rel.sections):
        # try to find the first empty section after all nonzero ones
        if s.length == 0:
            if next_sectionid != i-1:
                found_sectionid = i
            next_sectionid = i

    if next_sectionid is None:
        # could techically move the section table entirely but I don't feel like it right now
        raise IndexError("section table is full")
    
    section = rel.sections[found_sectionid]

    section.section = data
    section.section_off = rel.imp_off # the new section always lands on top of the imp table
    section.length = len(data)
    section.executable = set_exec

    # move the import table
    rel.imp_off += len(data)
    for imp in rel.imps:
        imp.offset += len(data)

    # increase fixSize to make more space
    rel.fix_size += len(data)

    return (found_sectionid, section.section_off)
    
def patch_section(rel, secnum, rel_addr, data):
    # Write data onto the specified section at an address relative to the start of the REL file.
    # The data must be either a bytes object or a numpy array with dtype=uint8
    if type(data) == bytes:
        data = np.frombuffer(data, dtype=np.uint8).copy()

    section = rel.sections[secnum]
    if rel_addr < section.section_off or rel_addr+len(data) > section.section_off+section.length:
        raise ValueError("address out of range for section %d" % section)

    addr = rel_addr - section.section_off
    section.section[addr:addr+len(data)] = data

def branch(off, link=True):
    if off & 0x3:
        raise ValueError("branch offset not aligned: %+09x" % off)
    if off > 0x01ffffff or off < -0x02000000:
        raise ValueError("branch distance too far: %+09x" % off)
    
    off &= 0x03fffffc
    instr = 0x48000000 # b instruction without the address filled
    if link: instr |= 0x1 # enable link bit
    instr |= off
    return np.frombuffer(struct.pack('>I', instr), dtype=np.uint8).copy()

def read_symtab(fname):
    symtab = {}
    with open(fname, 'r') as f:
        # skip the header
        for i in range(3):
            f.readline()

        for line in f:
            fields = re.split(r'\s+', line.strip())
            if len(fields) < 8:
                continue # no name
            value = int(fields[1], 16)
            bind = fields[4]
            name = fields[7]
            
            if bind == 'GLOBAL':
                symtab[name] = value

    return symtab

def main(patchspec):
    # Patch spec format:
    # {
    #   "rel":     path to base REL file,
    #   "output":  path to destination REL file,
    #   "sections": [ new sections to add
    #     {
    #       "ref": name to use to refer to this section in the patches list
    #       "data": data to store in the section as a list of bytes (unless file is specified)
    #       "file": file name to read data from
    #       "exec": (defaults to True) - whether to set the executable bit on this section
    #     }
    #   ]
    #   "patches": [
    #     {
    #       "section": section number or ref,
    #       "addr": address relative to the start of the REL file
    #       "type": either "data", "branch_custom", "branch_section"
    #       "data": ("data" type only) - data to apply as list of bytes
    #       "file": ("data" type only) - file to read (supersedes data if both exist)
    #       "link": ("branch_*" types only) - whether to generate a BL or a B instruction (default to true)
    #       "target": ("branch_*" types only)
    #          - when "branch_custom" is specified, this specifies how many bytes to jump relative to the PC
    #          - when "branch_section" is specified, this specifies how many bytes to jump relative to
    #            the start of the section
    #          - in both cases, this value must be a multiple of 4
    #       "target_section": ("branch_section" only) - section ref or ID to jump into
    #     }
    #   ]
    # }

    print("Loading REL file")
    with open(patchspec['rel'], 'rb') as f:
        rel = relfile.Rel(f)

    print("Applying section data")
    section_refs = {}
    for sec in patchspec['sections']:
        if 'file' in sec:
            with open(sec['file'], 'rb') as f:
                data = f.read()
                print(hexdump.hexdump(data))
        elif 'data' in sec:
            data = np.array(sec['data'], dtype=np.uint8)
        else:
            raise ValueError("no data or file in patch spec section")
        
        executable = sec.get('exec', True)

        num,off = add_section(rel, data, executable)
        print("  New section %d @ %08x with %d bytes of data" % (num, off, len(data)))
        if 'ref' in sec:
            symtab = {}
            if 'symtab' in sec:
                symtab = read_symtab(sec['symtab'])
            section_refs[sec['ref']] = (num,off,symtab)

    print("Applying patches")
    for patch in patchspec['patches']:
        if patch['section'] in section_refs:
            secnum = section_refs[patch['section']][0]
        else:
            secnum = patch['section']

        addr = patch['addr'] 

        tp = patch['type']
        if tp == 'data':
            if 'file' in patch:
                with open(patch['file'], 'rb') as f:
                    data = f.read()
            else:
                data = np.array(patch['data'], dtype=np.uint8)
        else:
            if tp == 'branch_custom':
                offset = patch['target']
            elif tp == 'branch_section':
                if patch['target_section'] in section_refs:
                    target = section_refs[patch['target_section']][1]
                    symtab = section_refs[patch['target_section']][2]
                    if patch['target'] in symtab:
                        patch['target'] = symtab[patch['target']]
                    elif type(patch['target']) != int:
                        raise ValueError("Patch target %s not in symbol table %s" % (patch['target'], symtab))
                else:
                    target = rel.sections[patch['target_section']].section_off

                target += patch['target']
                offset = target - addr
            else:
                raise ValueError("invalid patch type '%s'" % tp)

            link = patch.get('link', True)
            data = branch(offset, link)
            print("  Created branch to %08x (off=%08x)" % (offset+addr, offset))

        print("  Applied patch of %d bytes to %08x" % (len(data), addr))
        patch_section(rel, secnum, addr, data)

    # write out the patched file
    with open(patchspec['output'], 'wb') as f:
        rel.write(f)

    with open(patchspec['output'], 'rb') as f:
        rel = relfile.Rel(f)
        rel.print_info()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: %s <patch spec json>" % sys.argv[0])
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        patchspec = json.load(f)

    main(patchspec)
