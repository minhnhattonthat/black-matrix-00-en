import struct
import dat, pointers, script
from build import ORIG

SUB10 = dat.unpack((ORIG / "SYSTEM.DAT").read_bytes())[10]


def _pointer_words(b):
    return [(o, struct.unpack_from("<I", b, o)[0]) for o in range(0, len(b) - 3, 4)
            if pointers.BASE <= struct.unpack_from("<I", b, o)[0] < pointers.BASE + len(b)]


def test_round_trip_is_identical():
    entries = pointers.extract(SUB10, "SYSTEM/10")
    assert 110 <= len(entries) <= 130
    assert pointers.insert(SUB10, entries) == SUB10


def test_every_pointer_into_a_run_targets_a_message():
    runs = list(pointers._runs(SUB10))
    starts = {off for _, items, _ in runs for off, *_ in items}
    spans = [(start, end) for start, _, end in runs]
    checked = 0
    for o, v in _pointer_words(SUB10):
        t = v - pointers.BASE
        if any(lo <= t < hi for lo, hi in spans):
            assert t in starts, (hex(o), hex(v))
            checked += 1
    assert checked > 100            # 78 inline/table pointers plus the chapter titles


def test_growth_within_a_run_relayouts_and_pointers_follow():
    entries = pointers.extract(SUB10, "S")
    entries[0]["en"] = "Closes this screen plus more"      # longer than the Japanese
    entries[1]["en"] = "Vibration"                         # shorter: the run still fits
    out = pointers.insert(SUB10, entries)
    assert len(out) == len(SUB10)
    assert len(_pointer_words(out)) == len(_pointer_words(SUB10))
    targets = {v - pointers.BASE for _, v in _pointer_words(out)}
    for e in entries:
        expected = script.encode(e["en"]) if e["en"] else script.encode(e["jp"])
        assert any(out[t:].startswith(expected + bytes(1)) for t in targets), e["id"]
    assert out[0x178:0xBE0] == SUB10[0x178:0xBE0]         # the other runs are untouched


def test_run_overflow_raises_instead_of_spilling():
    entries = pointers.extract(SUB10, "S")
    entries[0]["en"] = "This closes the screen. " * 3
    try:
        pointers.insert(SUB10, entries)
    except ValueError as err:
        assert "shorten" in str(err)
        return
    assert False, "expected ValueError"


def test_code_references_follow_moved_messages():
    refs = pointers.code_refs(SUB10)
    assert len(refs) >= 50
    starts = {off for _, items, _ in pointers._runs(SUB10) for off, *_ in items}
    assert all(t in starts for _, _, t in refs)
    entries = pointers.extract(SUB10, "S")
    entries[0]["en"] = "Closes this screen plus more"      # shifts every later message in run 1
    entries[1]["en"] = "Vibration"
    out = pointers.insert(SUB10, entries)
    by_off = {int(e["id"].rsplit("/", 1)[1], 16): e for e in entries}
    for lui_at, addiu_at, target in refs:
        e = by_off[target]
        expected = script.encode(e["en"]) if e["en"] else script.encode(e["jp"])
        new_target = next(t for _, a, t in pointers.code_refs(out) if a == addiu_at)
        assert out[new_target:].startswith(expected + bytes(1)), hex(addiu_at)

def test_data_word_in_pointer_range_raises():
    bad = bytearray(SUB10)
    struct.pack_into("<I", bad, 0xC000, pointers.BASE + 1)     # a data word pointing inside a string
    try:
        pointers.insert(bytes(bad), [])
    except ValueError:
        return
    assert False, "expected ValueError"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
