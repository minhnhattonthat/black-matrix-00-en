"""Halfwidth font hack: Python model of the glyph composition done in asm/halfwidth.asm."""
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
