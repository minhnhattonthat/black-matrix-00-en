"""Build asm/font6x12.bin from the X11 6x12 BDF font: 95 glyphs (0x20-0x7E),
12 bytes each, one byte per row, pixels in bits 7..2.
Usage: python make_font.py work/6x12.bdf"""
import sys
from pathlib import Path

W, H = 6, 12


def parse(bdf: str) -> dict[int, bytes]:
    lines = iter(bdf.splitlines())
    descent, glyphs = 0, {}
    for line in lines:
        if line.startswith("FONT_DESCENT"):
            descent = int(line.split()[1])
        elif line.startswith("ENCODING"):
            code = int(line.split()[1])
        elif line.startswith("BBX"):
            bw, bh, bx, by = map(int, line.split()[1:])
        elif line == "BITMAP":
            cell = bytearray(H)
            top = H - descent - by - bh          # first cell row the bitmap occupies
            for r in range(bh):
                bits = int(next(lines)[:2], 16) >> bx
                if 0 <= top + r < H:
                    cell[top + r] = bits & 0xFC
            glyphs[code] = bytes(cell)
    return glyphs


if __name__ == "__main__":
    glyphs = parse(Path(sys.argv[1]).read_text(encoding="latin-1"))
    out = b"".join(glyphs[c] for c in range(0x20, 0x7F))
    Path(__file__).parent.joinpath("asm").mkdir(exist_ok=True)
    Path(__file__).parent.joinpath("asm", "font6x12.bin").write_bytes(out)
    print(len(out), "bytes")
