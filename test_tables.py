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
        text = SUB2[off:off + w].split(b"\0")[0]
        assert len(text) <= w, hex(off)


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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
