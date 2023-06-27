import sys

def rl(x, n):
    return ((x << n) & 0xffffffff) | \
           ((x >> (32 - n)) & 0xffffffff)

def gen_mask(b, e):
    mask = 0
    if b < e+1:
        for i in range(b, e+1):
            mask |= 1<<(31 - i)
    else:
        mask = 0xffffffff
        if b > e+1:
            for i in range(e+1, b):
                mask &= ~(1 << (31 - i))
    return mask

def get_int(s):
    if s.startswith('0x'):
        return int(s, 16)
    else:
        return int(s)

def rlwinm(x, shift, mb, me):
    if shift > 16:
        op = "(0x%x >>> %d) " % (x, 32-shift)
    else:
        op = "(0x%x <<< %d) " % (x, shift)
    
    mask = gen_mask(mb, me)
    op += "& 0x%08x " % mask
    res = rl(x, shift) & mask
    op += "= 0x%x " % res

    print(op)
    return res

def main():
    x = get_int(sys.argv[1])
    shift = get_int(sys.argv[2])
    mb = get_int(sys.argv[3])
    me = get_int(sys.argv[4])

    rlwinm(x, shift, mb, me)

if __name__ == "__main__":
    main()
