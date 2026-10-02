"""In-place text: fixed-width fields in SYSTEM.DAT sub-file 2, overlay labels in
sub-file 4, unit names in BATTLE.DAT. Layouts: docs/superpowers/specs/2026-10-03-system-tables-design.md"""
import re
import struct

from script import decode, encode

WEAPON = (128, [(0, 20), (26, 34), (60, 34), (94, 34)])
SYSTEM_TABLES = [
    (2, 20, [(0, 18)]),                                   # unit names
    *[(i, *WEAPON) for i in range(6, 21)],                # fifteen weapon classes
    (21, 96, [(0, 22), (28, 34), (62, 34)]),              # gems
    (22, 122, [(0, 18), (20, 100)]),                      # items
    (23, 98, [(0, 24), (30, 32), (62, 34)]),              # rings
    (24, 94, [(0, 26), (26, 34), (60, 34)]),              # skills
]


def _directory(sub2: bytes) -> list[tuple[int, int]]:
    count = struct.unpack_from("<I", sub2)[0]
    return [(o * 4, s * 4) for o, s in struct.iter_unpack("<HH", sub2[8:8 + 4 * count])]


def fields(sub2: bytes) -> list[tuple[int, int]]:
    out, directory = [], _directory(sub2)
    for table, rec, flds in SYSTEM_TABLES:
        base, size = directory[table]
        for k in range(size // rec):
            out += [(base + k * rec + off, width) for off, width in flds]
    return out


def _text(buf: bytes, off: int, width: int) -> bytes:
    return buf[off:off + width].split(b"\0")[0]


def extract_fixed(sub2: bytes, prefix: str) -> list[dict]:
    return [{"id": f"{prefix}/{off:05x}", "jp": decode(_text(sub2, off, w)), "en": "", "width": w}
            for off, w in fields(sub2) if _text(sub2, off, w)]


def _fit(e: dict, width: int) -> bytes:
    data = encode(e["en"])
    if len(data) > width:
        raise ValueError(f'{e["id"]}: {len(data)} bytes, field holds {width}')
    return data.ljust(width, b"\0")


def insert_fixed(sub2: bytes, entries: list[dict]) -> bytes:
    out = bytearray(sub2)
    widths = dict(fields(sub2))
    for e in entries:
        if not e["en"]:
            continue
        off = int(e["id"].rsplit("/", 1)[1], 16)
        if off not in widths:
            raise ValueError(f'{e["id"]}: not a text field')
        out[off:off + widths[off]] = _fit(e, widths[off])
    return bytes(out)
