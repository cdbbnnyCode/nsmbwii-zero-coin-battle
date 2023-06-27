# Decodes Wii (big-endian) LZ file data

import sys

def lzdec(data, verbose=1):
    # decode the provided bytes object
    # verbose determines how much information is printed
    #  0 = no prints
    #  1 = data header information / general statistics
    #  2 = heavy debug information

    def vprint(level, s):
        if verbose >= level:
            print(s)

    magic = data[0]
    if magic != 0x11:
        raise ValueError("invalid magic: 0x%02x" % magic)

    decoded_length = data[1] | (data[2] << 8) | (data[3] << 16)
    vprint(1, "Decompressed size: %d bytes" % decoded_length)

    out_data = bytearray(decoded_length)

    i = 4
    out_i = 0
    f = 0
    f_sel = 0
    while i < len(data):
        if f_sel == 0:
            f_sel = 0x80
            f = data[i]
            i += 1

        if f & f_sel:
            x = data[i] >> 4
            if x == 0:
                ref_data = (data[i] << 16) | (data[i+1] << 8) | (data[i+2])
                i += 3
                pos = (ref_data & 0xFFF) + 1
                l = ((ref_data >> 12) & 0xFF) + 17
            elif x == 1:
                ref_data = (data[i] << 24) | (data[i+1] << 16) | (data[i+2] << 8) | (data[i+3])
                i += 4
                pos = (ref_data & 0xFFF) + 1
                l = ((ref_data >> 12) & 0xFFFF) + 273
            else:
                ref_data = (data[i] << 8) | (data[i+1])
                i += 2
                pos = (ref_data & 0xFFF) + 1
                l = x + 1

            for j in range(l):
                out_data[out_i + j] = out_data[out_i - pos + j]

            out_i += l
        else:
            out_data[out_i] = data[i]

            out_i += 1
            i += 1
        
        f_sel >>= 1

    if out_i < decoded_length:
        vprint(1, "WARN: decompressed %d bytes but expected %d bytes" % (out_i, decoded_length))
    
    return bytes(out_data)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: %s <LZ file> <out file>" % sys.argv[0])
        sys.exit(0)

    with open(sys.argv[1], 'rb') as f:
        in_data = f.read()
        data = lzdec(in_data)
        with open(sys.argv[2], 'wb') as of:
            of.write(data)
