import tempfile
from pathlib import Path

import halfwidth
from build import ORIG

FONT = halfwidth.FONT.read_bytes()


def rows(cell):
    return ["".join("#" if cell[2 * y + x // 8] & (0x80 >> (x % 8)) else "." for x in range(12))
            for y in range(12)]


def test_font_has_95_glyphs_in_top_six_bits():
    assert len(FONT) == 95 * 12
    assert all(b & 3 == 0 for b in FONT)
    assert not any(FONT[:12])                       # space is blank
    assert any(FONT[(ord("A") - 0x20) * 12:][:12])  # A is not


def test_compose_puts_left_in_columns_0_5_and_right_in_6_11():
    a = rows(halfwidth.compose(FONT, ord("A"), ord(" ")))
    b = rows(halfwidth.compose(FONT, ord(" "), ord("A")))
    assert any("#" in r for r in a)
    assert all(r[6:] == "......" for r in a)
    assert all(r[:6] == "......" for r in b)
    assert [r[:6] for r in a] == [r[6:] for r in b]


def test_compose_out_of_range_is_space():
    blank = halfwidth.compose(FONT, 0x20, 0x20)
    assert halfwidth.compose(FONT, 0x09, 0x7F) == blank == bytes(24)


EXE = ORIG / "SLPS_035.73"
BASE = 0x8000F800


def _patched():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "patched.exe"
        halfwidth.assemble(EXE, out)
        return out.read_bytes()


def test_table_ranges_are_zero_in_the_original():
    exe = EXE.read_bytes()
    for lo, hi in halfwidth.FREE:
        assert not any(exe[lo - BASE:hi - BASE]), hex(lo)


def test_patch_touches_only_declared_ranges():
    a, b = EXE.read_bytes(), _patched()
    assert len(a) == len(b)
    changed = [i + BASE for i in range(len(a)) if a[i] != b[i]]
    assert changed, "patch changed nothing"
    stray = [hex(x) for x in changed if not any(lo <= x < hi for lo, hi in halfwidth.RANGES)]
    assert not stray, stray[:8]


def test_justify_spread_is_disabled():
    # 0x80013598: andi v1, v1, 0x80 (text object flag "spread glyphs across the field")
    import struct
    b = _patched()
    for site in (0x80013598, 0x80013800):        # both copies of the test (0xe00 branch, menu branch)
        word = struct.unpack_from("<I", b, site - BASE)[0]
        assert word == 0x30630000, hex(site)     # andi $v1, $v1, 0 -> the branch below always skips the spread


def test_patched_exe_contains_the_font():
    b = _patched()
    assert b[0x800604A0 - BASE:][:768] == FONT[:768]
    assert b[0x8006292C - BASE:][:372] == FONT[768:]


def _reads_loaded_register(load: int, nxt: int) -> bool:
    """R3000 load delay: the instruction after a load still sees the old register value."""
    if not 0x20 <= load >> 26 <= 0x26:
        return False
    rt = load >> 16 & 31
    op, rs, rt2 = nxt >> 26, nxt >> 21 & 31, nxt >> 16 & 31
    if op in (2, 3) or nxt == 0:                     # j, jal, nop read nothing
        return False
    reads_rt = op in (0, 4, 5) or 0x28 <= op <= 0x2E  # R-type, beq/bne, stores
    return rt == rs or (reads_rt and rt == rt2)


def _load_delay_hazards(word, addrs) -> list[str]:
    """Addresses in `addrs` holding a load whose register is read by the next instruction
    executed: the following one, or the target when the load sits in a delay slot."""
    bad = []
    for a in addrs:
        w = word(a)
        if _reads_loaded_register(w, word(a + 4)):
            bad.append(hex(a))
        op = w >> 26
        if op in (2, 3):                                         # j, jal
            target = (w & 0x3FFFFFF) << 2 | 0x80000000
        elif op in (1, 4, 5, 6, 7):                              # conditional branches
            target = a + 4 + (((w & 0xFFFF) ^ 0x8000) - 0x8000 << 2)
        elif op == 0 and w & 0x3F in (8, 9):                     # jr, jalr: target unknown,
            if 0x20 <= word(a + 4) >> 26 <= 0x26:                #   so allow no load in the slot
                bad.append(hex(a + 4))
            continue
        else:
            continue
        if _reads_loaded_register(word(a + 4), word(target)):
            bad.append(hex(a + 4))
    return bad


def test_hazard_scan_sees_a_load_in_a_delay_slot_read_at_the_target():
    mem = {0x80060000: 0x08000000 | 0x80060010 >> 2 & 0x3FFFFFF,   # j 0x80060010
           0x80060004: 0x90A20000,                                 # lbu v0, 0(a1)
           0x80060008: 0, 0x8006000C: 0,
           0x80060010: 0x2C580080,                                 # sltiu t8, v0, 0x80
           0x80060014: 0}
    assert _load_delay_hazards(mem.__getitem__, [0x80060000]) == ["0x80060004"]


def test_patch_never_reads_a_register_in_its_load_delay_slot():
    import struct
    b = _patched()
    word = lambda addr: struct.unpack_from("<I", b, addr - BASE)[0]
    lo, hi = halfwidth.RANGES[5]                      # the code area
    addrs = [site for site, _ in halfwidth.RANGES[:2]] + list(range(lo, hi - 4, 4))
    assert not _load_delay_hazards(word, addrs)


def test_unit_names_are_fixed_after_set_name_and_after_load():
    import struct
    b = _patched()
    word = lambda addr: struct.unpack_from("<I", b, addr - BASE)[0]
    assert word(0x8003CDA0) >> 26 == 2 and word(0x80039CC4) >> 26 == 3      # j / jal into the patch
    one = (word(0x8003CDA0) & 0x3FFFFFF) << 2 | 0x80000000
    lo, hi = halfwidth.RANGES[6]
    assert lo <= one < hi
    table = b.find(bytes.fromhex("834a8343") + b"Cain", lo - BASE, hi - BASE)
    assert table > 0 and b[table + 16:table + 20] == bytes.fromhex("83888366".replace("66", "6e")) and b[table + 20:table + 28] == b"Johannes"
    assert not _load_delay_hazards(word, list(range(one, one + 0x90, 4)))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
