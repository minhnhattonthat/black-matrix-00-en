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


def test_growth_keeps_every_message_reachable_through_a_pointer():
    entries = pointers.extract(SUB10, "S")
    entries[0]["en"] = "This closes the screen. " * 3           # far longer: pushes later messages to the tail
    entries[1]["en"] = "Vibration"
    out = pointers.insert(SUB10, entries)
    assert len(out) == len(SUB10)
    assert len(_pointer_words(out)) == len(_pointer_words(SUB10))
    targets = {v - pointers.BASE for _, v in _pointer_words(out)}
    for e in entries:
        expected = script.encode(e["en"]) if e["en"] else script.encode(e["jp"])
        assert any(out[t:].startswith(expected + bytes(1)) for t in targets), e["id"]


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
