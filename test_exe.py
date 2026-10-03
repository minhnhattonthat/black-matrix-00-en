import exe
from build import ORIG

EXE = (ORIG / "SLPS_035.73").read_bytes()


def test_extract_lists_every_slot_and_identity_insert():
    entries = exe.extract(EXE)
    assert len(entries) == len(exe.SLOTS) == 21
    by_id = {e["id"]: e for e in entries}
    assert by_id["EXE/80010064"] == {"id": "EXE/80010064", "jp": "を　個入手した", "en": "", "width": 14}
    assert by_id["EXE/8006b30c"]["jp"] == "カイン" and by_id["EXE/8006b30c"]["width"] == 6    # カイン
    assert by_id["EXE/80011080"]["jp"] == "リプサリス" and by_id["EXE/80011080"]["width"] == 10
    assert by_id["EXE/8006b240"]["jp"] == "マ" and by_id["EXE/8006b240"]["width"] == 2               # マ overlay
    assert exe.insert(EXE, entries) == EXE


def test_insert_writes_only_inside_the_slot_and_zero_fills():
    entries = exe.extract(EXE)
    e = next(x for x in entries if x["id"] == "EXE/80010064")
    e["en"] = " x   obtained"
    out = exe.insert(EXE, entries)
    off = 0x80010064 - exe.BASE
    assert out[off:off + 16] == b" x   obtained " + bytes(2)          # odd run padded, terminator kept
    assert out[:off] == EXE[:off] and out[off + 16:] == EXE[off + 16:]


def test_insert_rejects_over_width_and_unknown_id():
    entries = exe.extract(EXE)
    e = next(x for x in entries if x["id"] == "EXE/8006b314")           # ヨハネ: 8-byte slot
    e["en"] = "Johannes"
    try:
        exe.insert(EXE, entries)
    except ValueError as err:
        assert "EXE/8006b314" in str(err)
    else:
        assert False, "expected ValueError"
    try:
        exe.insert(EXE, [{"id": "EXE/80010000", "en": "x", "width": 14}])
    except ValueError:
        return
    assert False, "expected ValueError"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
