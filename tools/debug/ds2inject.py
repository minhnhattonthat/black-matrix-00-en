"""Turn a DuckStation savestate of Black/Matrix 00 into save-game regions for tools/debug/warp.lua (--script after it):
  python -X utf8 tools/debug/ds2inject.py work/states/savestate4.sav work/qa/inject4.lua [--v16 ADDR --v32 ADDR]
The regions are those the game's load routine (0x80039A30) copies out of a memory-card save: the 0x260 u16 and
0x20 u32 script variables, the party flags around 0x8006F258 and the 16 unit records at 0x8006F458, plus 17 records
at 0x800703d8. The variable arrays live at the addresses warp.lua logs ("vars at V16 V32"); the defaults are the
ones seen on this build. The savestate keeps main RAM at +0x31a62 of its zstd payload (located by the EXE bytes)."""
import argparse, sys
import zstandard

REGIONS = [(0x8006F350, 0x15), (0x8006F298, 0xd), (0x8006F3B0, 0x16), (0x8006F3A0, 0xa), (0x8006B490, 8),
           (0x8006F308, 0x14), (0x8006F2F0, 0x15), (0x8006F380, 0xa), (0x8006F340, 0x10), (0x8006F2E0, 0xb),
           (0x8006F368, 0x11), (0x8006B480, 8), (0x8006F330, 0xa), (0x8006F390, 0xd), (0x8006F320, 0xb),
           (0x8006F408, 0x49), (0x8006F258, 0x1d), (0x8006F2A8, 0x35), (0x8006F458, 0x7c0), (0x800703D8, 17 * 0x65)]


def ram(path):
    d = open(path, "rb").read()
    raw = zstandard.ZstdDecompressor().stream_reader(d[d.find(b"\x28\xb5\x2f\xfd"):]).read()
    exe = open("work/orig/SLPS_035.73", "rb").read()[0x800:0x840]
    i = raw.find(exe)
    if i < 0:
        sys.exit("EXE code not found in the state")
    return raw[i - 0x10000:i - 0x10000 + 0x200000]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("state")
    ap.add_argument("out")
    ap.add_argument("--v16", type=lambda s: int(s, 16), default=0x801C0100)
    ap.add_argument("--v32", type=lambda s: int(s, 16), default=0x801C05C0)
    ap.add_argument("--vars-only", action="store_true", help="script variables only (story flags), no party data")
    ap.add_argument("--range", help="LO-HI (hex): keep only the fixed regions inside this address range")
    a = ap.parse_args()
    r = ram(a.state)
    lo, hi = (int(x, 16) for x in a.range.split("-")) if a.range else (0, 0xFFFFFFFF)
    parts = []
    for addr, size in [] if a.vars_only else [x for x in REGIONS if lo <= x[0] < hi]:
        parts.append(f'  {{0x{addr:08X}, "{r[addr & 0x1FFFFF:(addr & 0x1FFFFF) + size].hex()}"}}')
    for name, addr, size in (("V16", a.v16, 0x260 * 2), ("V32", a.v32, 0x20 * 4)):
        if addr:
            parts.append(f'  {{"{name}", "{r[addr & 0x1FFFFF:(addr & 0x1FFFFF) + size].hex()}"}}')
    open(a.out, "w").write("INJECT = {\n" + ",\n".join(parts) + "\n}\n")
    print(f"{len(parts)} regions -> {a.out}")
