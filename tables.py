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


BATTLE_MAGIC = b"\x04\x00\x01\x00"
_UNITS = 0x318          # unit table offset in every battle file that has one
_UNIT = 88              # record size
_NAME = 16              # zero-padded name at record start


def _lead(c: int) -> bool:
    return 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC


def battle_names(sub: bytes) -> list[int]:
    """Offsets of unit-name fields; the table ends at the first record without a name."""
    out, off = [], _UNITS
    while off + _NAME <= len(sub) and _lead(sub[off]) and b"\0" in sub[off:off + _NAME]:
        out.append(off)
        off += _UNIT
    return out


def insert_battle(sub: bytes, names: dict[str, str]) -> bytes:
    out = bytearray(sub)
    for off in battle_names(sub):
        jp = decode(_text(sub, off, _NAME))
        if names.get(jp):
            out[off:off + _NAME] = _fit({"id": f"BATTLE/{off:05x} {jp}", "en": names[jp]}, _NAME)
    return bytes(out)


_SJIS_STRING = re.compile(rb"(?:[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]){2,}\0")
_REAL = re.compile(rb"\x82[\x9f-\xf1]|\x83[\x40-\x96]|\x81[\x40-\x49]|[\x88-\x9f\xe0-\xea]")


def extract_overlay(sub4: bytes, prefix: str) -> list[dict]:
    out = []
    for m in _SJIS_STRING.finditer(sub4):
        text = m.group()[:-1]
        if m.start() % 2 == 0 and _REAL.search(text):
            out.append({"id": f"{prefix}/{m.start():05x}", "jp": decode(text), "en": "", "width": len(text)})
    return out


def insert_overlay(sub4: bytes, entries: list[dict]) -> bytes:
    out = bytearray(sub4)
    for e in entries:
        if e["en"]:
            off = int(e["id"].rsplit("/", 1)[1], 16)
            out[off:off + e["width"]] = _fit(e, e["width"])
    return bytes(out)


def battle_name_list(subs: list[bytes]) -> list[str]:
    """Every distinct unit name used by battle files, in first-seen order.
    Bosses and monsters are not all in SYSTEM table 2, so these get their own translations."""
    seen = {}
    for b in subs:
        if b[:4] == BATTLE_MAGIC:
            for off in battle_names(b):
                seen.setdefault(decode(_text(b, off, _NAME)), None)
    return list(seen)
