"""Halfwidth font hack: Python model of the glyph composition done in asm/halfwidth.asm."""
import shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).parent
FONT = ROOT / "asm" / "font6x12.bin"


def _glyph(font: bytes, c: int) -> bytes:
    if not 0x20 <= c <= 0x7E:
        c = 0x20
    return font[(c - 0x20) * 12:(c - 0x20) * 12 + 12]


def compose(font: bytes, c1: int, c2: int) -> bytes:
    """12x12 1bpp cell, 2 bytes per row, MSB first: c1 in columns 0-5, c2 in 6-11."""
    out = bytearray()
    for left, right in zip(_glyph(font, c1), _glyph(font, c2)):
        row = (left << 8) | (right << 2)
        out += bytes([row >> 8, row & 0xFF])
    return bytes(out)


BASE = 0x8000F800                      # address - BASE = offset in the EXE file
RANGES = [
    (0x800344FC, 0x80034504),          # hook 1
    (0x80034638, 0x80034640),          # hook 2
    (0x800604A0, 0x80060848),          # font 0x20-0x5F   } zero runs of the SJIS
    (0x8006087C, 0x80060A8C),          # code             } index table: codes no
    (0x8006292C, 0x80062C4C),          # font 0x60-0x7E   } glyph in the font uses
]
ARMIPS = ROOT / "tools" / "armips" / "armips.exe"


def assemble(src: Path, dst: Path) -> None:
    """Check the patch ranges are free in `src`, then assemble asm/halfwidth.asm into `dst`.
    The .asm names its own input, work/orig/SLPS_035.73, which is what `src` must be."""
    exe = src.read_bytes()
    for lo, hi in RANGES[2:]:
        if any(exe[lo - BASE:hi - BASE]):
            raise ValueError(f"patch range {lo:#x}-{hi:#x} is not empty in {src}")
    subprocess.run([ARMIPS, "asm/halfwidth.asm"], cwd=ROOT, check=True)
    shutil.move(ROOT / "work" / "halfwidth.exe", dst)
