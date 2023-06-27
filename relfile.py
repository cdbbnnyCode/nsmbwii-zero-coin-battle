import struct
import os
import shutil
import numpy as np

def read(f, addr, n):
    f.seek(addr)
    return f.read(n)

def read8(f, addr):
    return struct.unpack('>B', read(f, addr, 1))[0]

def read16(f, addr):
    return struct.unpack('>H', read(f, addr, 2))[0]
def read32(f, addr):
    return struct.unpack('>I', read(f, addr, 4))[0]

def write(f, addr, d):
    f.seek(addr)
    f.write(d)

def write8(f, addr, d):
    write(f, addr, struct.pack('>B', d))

def write16(f, addr, d):
    write(f, addr, struct.pack('>I', d))

class RelSection:
    def __init__(self, f=None, addr=0):
        if f is not None:
            h = struct.unpack('>II', read(f, addr, 8))
            self.section_off = h[0] & 0xfffffffc
            self.executable  = (h[0] & 0x1) != 0
            self.length      = h[1]
            if self.section_off != 0:
                self.section = np.frombuffer(read(f, self.section_off, self.length), dtype=np.uint8).copy()
            else:
                self.section = np.zeros(0, dtype=np.uint8)
        else:
            self.section_off = 0
            self.executable = False
            self.length = 0
            self.section = np.zeros(0, dtype=np.uint8)

    def write(self, f, addr):
        # BSS sections need special treatment, so the length field must be
        # manually updated before this function is called
        section_off_packed = self.section_off | (1 if self.executable else 0)
        write(f, addr, struct.pack('>II', section_off_packed, self.length))
        if self.section_off != 0:
            write(f, self.section_off, self.section.tobytes())

class Relocation:
    def __init__(self, f, addr):
        h = struct.unpack('>HBBI', read(f, addr, 8))
        self.offset = h[0]
        self.reltype = h[1]
        self.section = h[2]
        self.addend = h[3]

        valid_reltypes = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 201, 202, 203, 204}
        if self.reltype not in valid_reltypes:
            print("WARN: invalid relocation type %d" % self.reltype)

    def write(self, f, addr):
        write(f, addr, struct.pack('>HBBI', self.offset, self.reltype, self.section, self.addend))

class RelImpInfo:
    def __init__(self, f, addr):
        h = struct.unpack('>II', read(f, addr, 8))
        self.id = h[0]
        self.offset = h[1]
        if self.offset % 8 != 0:
            print("WARN: relocation table not aligned to 8 bytes: %08x" % self.offset)
            self.offset -= self.offset % 8
        self.relocs = []
        i = 0
        while True:
            rel = Relocation(f, self.offset + i)
            i += 8
            self.relocs.append(rel)
            if rel.reltype == 203: # 203 is the "stop" type
                break

    def write(self, f, addr):
        write(f, addr, struct.pack('>II', self.id, self.offset))
        i = 0
        for rel in self.relocs:
            rel.write(f, self.offset + i)
            i += 8

class Rel:
    def __init__(self, f):
        h = struct.unpack('>IIIIIIIIIIIIBBBBIII', read(f, 0, 0x40))
        self.id                 = h[0]
        self.next               = h[1]
        self.prev               = h[2]
        num_sections            = h[3]
        self.section_tbl_off    = h[4]
        self.name_off           = h[5]
        self.name_len           = h[6]
        self.version            = h[7]
        self.bss_size           = h[8]
        self.rel_off            = h[9]
        self.imp_off            = h[10]
        imp_size                = h[11]
        self.prolog_section     = h[12]
        self.epilog_section     = h[13]
        self.unresolved_section = h[14]
        self.bss_section        = h[15]
        self.prolog             = h[16]
        self.epilog             = h[17]
        self.unresolved         = h[18]
        self.align = 4
        self.bss_align = 4
        self.fix_size = 4
        if self.version >= 2:
            self.align = struct.unpack('>I', read(f, 0x40, 4))[0]
        if self.version >= 3:
            self.bss_align, self.fix_size = struct.unpack('>II', read(f, 0x44, 8))

        section_addr = self.section_tbl_off
        self.sections = []
        for i in range(num_sections):
            self.sections.append(RelSection(f, section_addr))
            section_addr += 8

        imp_addr = self.imp_off
        self.imps = []
        for i in range(imp_size // 8):
            self.imps.append(RelImpInfo(f, imp_addr))
            imp_addr += 8

    @property
    def num_sections(self):
        return len(self.sections)

    @property
    def imp_size(self):
        return len(self.imps) * 8

    def print_info(self):
        print("REL %d : %d sections" % (self.id, self.num_sections))

        for i in range(self.num_sections):
            s = self.sections[i]
            names = []
            if i == self.prolog_section: names.append('prolog')
            if i == self.epilog_section: names.append('epilog')
            if i == self.unresolved_section: names.append('unresolved')
            if i == self.bss_section: names.append('bss')

            name = ','.join(names)

            print("  section %d (%s): %d bytes @ %08x - %08x (exec=%s)" % \
                   (i, name, s.length, s.section_off, 
                    s.section_off + s.length, s.executable))

        print("Relocation tables @ %08x:" % self.imp_off)
        for imp in self.imps:
            print("  module %d: %d relocations" % (imp.id, len(imp.relocs)))
#             for i in range(16):
#                 if i >= len(imp.relocs):
#                     break
#                 reloc = imp.relocs[i]
#                 print("    off=%04x tp=%02x sec=%d add=%08x" % (reloc.offset, reloc.reltype, reloc.section, reloc.addend))
#             else:
#                 print("    ...")

    def write(self, f):
        write(f, 0, struct.pack('>IIIIIIIIIIIIBBBBIII',
            self.id, self.next, self.prev, self.num_sections, self.section_tbl_off,
            self.name_off, self.name_len, self.version, self.bss_size, self.rel_off,
            self.imp_off, self.imp_size, self.prolog_section, self.epilog_section,
            self.unresolved_section, self.bss_section, self.prolog, self.epilog,
            self.unresolved
        ))
        if self.version >= 2:
            write(f, 0x40, struct.pack('>I', self.align))
        if self.version >= 3:
            write(f, 0x44, struct.pack('>II', self.bss_align, self.fix_size))

        # write sections
        section_addr = self.section_tbl_off
        for s in self.sections:
            s.write(f, section_addr)
            section_addr += 8

        imp_addr = self.imp_off
        for imp in self.imps:
            imp.write(f, imp_addr)
            imp_addr += 8


def bl(pc, addr):
    off = (addr - pc)
    if off & 0x3:
        raise ValueError("branch offset not aligned: %+09x" % off)
    if off > 0x007fffff or off < -0x00800000:
        raise ValueError("branch distance too far: %+09x" % off)
    
    off &= 0x00fffffc
    instr = 0x48000001 # bl instruction without the address filled
    instr |= off
    return np.frombuffer(struct.pack('>I', instr), dtype=np.uint8).copy()

def patch(section, rel_base, addr, data):
    off = addr - rel_base - section.section_off
    print("patching at %08x (rel addr %08x)" % (off, off+section.section_off))
    if off < 0:
        raise ValueError("address %08x is not in this section" % addr)
    if off + len(data) > len(section.section):
        raise ValueError("address %08x is not in this section" % addr)
    
    section.section[off:off+len(data)] = data

def main():
    shutil.copy2('d_basesNP.rel.orig', 'd_basesNP.rel')
    with open('d_basesNP.rel', 'r+b') as f:
        f.seek(0, os.SEEK_END)
        fsize = f.tell()

        rel = Rel(f)
        rel.print_info()

        patch_section_off = rel.imp_off # import data lives immediately after the section data

        # create our patch section
        rel.sections[7].section = np.array([
                    0x3b, 0xa0, 0x00, 0x01, # li r29, 0x1
                    0x4e, 0x80, 0x00, 0x20  # blr
        ], dtype=np.uint8)
        patch_size = len(rel.sections[7].section)
        rel.sections[7].section_off = patch_section_off
        rel.sections[7].length = patch_size
        rel.sections[7].executable = True

        base_addr = 0x8076d770 - rel.sections[1].section_off # the address we know points to the code section

        # where to patch the rel module
        patch_addr = 0x807a53e8

        target = base_addr + rel.sections[7].section_off

        print("adding branch to %08x" % target)
        instr = bl(patch_addr, target)
        
        patch(rel.sections[1], base_addr, patch_addr, instr)

        # move the import table over so that we can fit the patch section before it
        rel.imp_off += patch_size
        for imp in rel.imps:
            # move each relocation table too
            imp.offset += patch_size

        rel.write(f)

if __name__ == "__main__":
    main()
