import re
import dat, script, tables
from build import ORIG

SYSTEM = dat.unpack((ORIG / "SYSTEM.DAT").read_bytes())
SUB2 = SYSTEM[2]
KANA = re.compile(rb"(?:\x82[\x9f-\xf1]|\x83[\x40-\x96]){2,}")


def test_fixed_round_trip_is_identical():
    entries = tables.extract_fixed(SUB2, "SYSTEM/2")
    assert len(entries) > 1300
    assert tables.insert_fixed(SUB2, entries) == SUB2


def test_every_kana_run_lies_inside_a_declared_field():
    spans = [(o, o + w) for o, w in tables.fields(SUB2)]
    for m in KANA.finditer(SUB2):
        assert any(a <= m.start() and m.end() <= b for a, b in spans), hex(m.start())


def test_field_text_fits_its_width():
    # some ring descriptions fill all 32 bytes with no terminator, so the game reads by width
    for off, w in tables.fields(SUB2):
        text = SUB2[off:off + w].rstrip(b"\0")
        assert len(text) <= w, hex(off)


def test_fields_hold_only_shift_jis_text():
    # insert zero-fills a field after the English, so a field must hold text only
    for off, w in tables.fields(SUB2):
        text = SUB2[off:off + w].rstrip(b"\0")
        assert all(b == 0 or 0x20 <= b for b in text), hex(off)       # no flag bytes mixed in


def test_insert_zero_fills_and_enforces_width():
    entries = tables.extract_fixed(SUB2, "S")
    e = next(x for x in entries if x["width"] == 18)
    e["en"] = "Novice Priest"
    out = tables.insert_fixed(SUB2, entries)
    off = int(e["id"].rsplit("/", 1)[1], 16)
    assert out[off:off + 18] == b"Novice Priest " + b"\0" * 4      # odd length padded by encode, rest zero
    e["en"] = "x" * 19
    try:
        tables.insert_fixed(SUB2, entries)
    except ValueError as err:
        assert e["id"] in str(err) and "18" in str(err)
        return
    assert False, "expected ValueError"


BATTLE = dat.unpack((ORIG / "BATTLE.DAT").read_bytes())
UNIT_NAMES = {e["jp"] for e in tables.extract_fixed(SUB2, "S") if e["width"] == 18}


def test_battle_names_are_found_in_most_files_and_listed_once():
    total = sum(len(tables.battle_names(b)) for b in BATTLE if b[:4] == tables.BATTLE_MAGIC)
    assert total > 900
    names = tables.battle_name_list(BATTLE)
    assert 60 <= len(names) <= 80 and len(names) == len(set(names))
    assert "グリシナ" in names                      # グリシナ: a boss not in SYSTEM table 2
    assert len(UNIT_NAMES & set(names)) > 40                        # most are shared with the unit table


def test_battle_insert_round_trip_and_translation():
    pasca = {"パスカ": "Pasca"}                                 # パスカ
    b = BATTLE[180]
    assert tables.insert_battle(b, {}) == b
    out = tables.insert_battle(b, pasca)
    offs = [o for o in tables.battle_names(b) if b[o:o + 16].startswith("\u30d1\u30b9\u30ab".encode("cp932") + bytes(1))]
    assert offs and all(out[o:o + 16] == b"Pasca " + bytes(10) for o in offs)   # odd length padded by encode
    final = BATTLE[194]                                                        # holds パスカ最終形態, not パスカ
    assert tables.insert_battle(final, pasca) == final
    try:
        tables.insert_battle(b, {"パスカ": "x" * 17})
    except ValueError:
        return
    assert False, "expected ValueError"


def test_overlay_round_trip_and_in_place_limit():
    sub4 = SYSTEM[4]
    entries = tables.extract_overlay(sub4, "SYSTEM/4")
    assert 100 <= len(entries) <= 130
    assert tables.insert_overlay(sub4, entries) == sub4
    e = next(x for x in entries if x["jp"] == "コンフィグ")   # コンフィグ, 10 bytes
    e["en"] = "Config"
    out = tables.insert_overlay(sub4, entries)
    off = int(e["id"].rsplit("/", 1)[1], 16)
    assert out[off:off + 11] == b"Config\0\0\0\0\0"
    e["en"] = "Configuration"
    try:
        tables.insert_overlay(sub4, entries)
    except ValueError as err:
        assert e["id"] in str(err)
        return
    assert False, "expected ValueError"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
