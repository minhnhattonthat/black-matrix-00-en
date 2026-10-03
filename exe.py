"""Strings inside SLPS_035.73, patched in place. Each lives in a fixed slot that code
addresses directly, so nothing moves: English must fit the slot minus its terminator."""
import script
import tables

BASE = 0x8000F800                      # load address minus the 0x800 header

# (address, slot bytes)
SLOTS = [
    (0x80010064, 16),                  # を　個入手した   name + template; cell 1 is overdrawn
    (0x80010074, 16),                  # を　スターした   by a table string (digit, マ, 覚)
    (0x80010084, 12),                  # を　えた
    (0x80010090, 16),                  # Ｇを入手した
    (0x8006B22C, 8), (0x8006B234, 8),  # は　い / いいえ
    (0x8006B23C, 4), (0x8006B240, 4),  # 覚 / マ overlay cells
    *[(0x80011044 + 12 * i, 12) for i in range(6)],   # names used by SYSTEM overlays 7/8
    *[(0x8006B30C + 8 * i, 8) for i in range(7)],     # default names; only the first is referenced
]


def extract(exe: bytes, prefix: str = "EXE") -> list[dict]:
    return [{"id": f"{prefix}/{addr:08x}", "jp": script.decode(tables._text(exe, addr - BASE, slot - 2)),
             "en": "", "width": slot - 2}
            for addr, slot in SLOTS]


def insert(exe: bytes, entries: list[dict]) -> bytes:
    slots = {f"{addr:08x}": (addr - BASE, slot - 2) for addr, slot in SLOTS}
    out = bytearray(exe)
    for e in entries:
        key = e["id"].rsplit("/", 1)[1]
        if key not in slots:
            raise ValueError(f'{e["id"]}: not an EXE string slot')
        if e["en"]:
            off, width = slots[key]
            out[off:off + width] = tables._fit(e, width)
    return bytes(out)
