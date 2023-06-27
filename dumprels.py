import struct
import os

first_rel_ptr = 0x800030c8 # location of the first REL pointer in the main OS data

def main():
    with open('mem1.raw', 'rb') as f:

        def read(addr, n):
            f.seek(addr - 0x80000000)
            return f.read(n)

        def read8(addr):
            return struct.unpack('>B', read(addr, 1))[0]

        def read16(addr):
            return struct.unpack('>H', read(addr, 2))[0]

        def read32(addr):
            return struct.unpack('>I', read(addr, 4))[0]

        class RelSectionInfo:
            def __init__(self, addr):
                h = struct.unpack('>II', read(addr, 8))
                self.section_off = h[0] & 0xfffffffc
                self.executable  = (h[0] & 0x1) != 0
                self.length      = h[1]

        class RelImpInfo:
            def __init__(self, addr):
                h = struct.unpack('>II', read(addr, 8))
                self.id = h[0]
                self.offset = h[1]

        class Rel:
            def __init__(self, addr):
                h = struct.unpack('>IIIIIIIIIIIIBBBBIII', read(addr, 0x40))
                self.addr               = addr
                self.id                 = h[0]
                self.next               = h[1]
                self.prev               = h[2]
                self.num_sections       = h[3]
                self.section_tbl_off    = h[4]
                self.name_off           = h[5]
                self.name_len           = h[6]
                self.version            = h[7]
                self.bss_size           = h[8]
                self.rel_off            = h[9]
                self.imp_off            = h[10]
                self.imp_size           = h[11]
                self.prolog_section     = h[12]
                self.epilog_section     = h[13]
                self.unresolved_section = h[14]
                self.bss_section        = h[15]
                self.prolog             = h[16]
                self.epilog             = h[17]
                self.unresolved         = h[18]

                section_addr = self.section_tbl_off
                self.sections = []
                for i in range(self.num_sections):
                    self.sections.append(RelSectionInfo(section_addr))
                    section_addr += 8

                imp_addr = self.imp_off
                self.imps = []
                for i in range(self.imp_size // 8):
                    self.imps.append(RelImpInfo(imp_addr))
                    imp_addr += 8

                if self.name_off != 0:
                    self.name = read(self.name_off, self.name_len).decode('ascii')
                else:
                    self.name = "_%02d.rel" % self.id

                print("REL %d @ %08x : %d sections" % (self.id, self.addr, self.num_sections))
                if self.name_off != 0:
                    print("  Name: %s" % self.name)

                for i in range(self.num_sections):
                    s = self.sections[i]
                    name = "unknown"
                    if   i == self.prolog_section: name     = 'prolog'
                    elif i == self.epilog_section: name     = 'epilog'
                    elif i == self.unresolved_section: name = 'unresolved'
                    elif i == self.bss_section:        name = 'bss'

                    print("  section %d (%s): %d bytes @ %08x - %08x (exec=%s)" % \
                           (i, name, s.length, s.section_off, 
                            s.section_off + s.length, s.executable))

            def dump_sections(self, path):
                with open(path + '/offsets.txt', 'w') as of:
                    for i, s in enumerate(self.sections):
                        name = "unknown"
                        if   i == self.prolog_section: name     = 'prolog'
                        elif i == self.epilog_section: name     = 'epilog'
                        elif i == self.unresolved_section: name = 'unresolved'
                        elif i == self.bss_section:        name = 'bss'
                        if s.executable:
                            name += ',X'
                        loc = s.section_off
                        size = s.length
                        of.write("%d (%s): loc=%08x size=%08x\n" % (i, name, loc, size))

                for i,s in enumerate(self.sections):
                    if s.section_off != 0:
                        with open(path + ('/%02d.bin' % i), 'wb') as of:
                            loc = s.section_off
                            of.write(read(loc, s.length))

        rel_off = read32(first_rel_ptr)
        rels = []
        while True:
            rel = Rel(rel_off)
            path = 'rel_%02d' % rel.id
            try:
                os.mkdir(path)
            except OSError as e:
                pass

            rel.dump_sections(path)
            rels.append(rel)
            rel_off = rel.next
            if rel_off == 0:
                break

if __name__ == "__main__":
    main()
