import struct
import dat, script, town
from build import ORIG

TOWN = dat.unpack((ORIG / "TOWN.DAT").read_bytes())


def test_container_round_trip_is_identical_for_every_sub_file():
    for i, b in enumerate(TOWN):
        if b:
            assert town.rebuild(town.parse(b)) == b, i


def test_parse_finds_the_two_text_leaves_in_sub_4():
    tree = town.parse(TOWN[4])
    children, tail = tree
    assert len(children) == 9 and not any(tail)
    inner, _ = children[1]
    assert len(inner) == 5 and len(inner[2]) == 19288 and len(inner[4]) == 3692


LEAF_A = TOWN[4][78204:78204 + 19288]
LEAF_B = TOWN[4][0x17cd4:0x17cd4 + 3692]


def test_text_leaf_round_trip_and_shape():
    for leaf, n in ((LEAF_A, 68), (LEAF_B, 48)):
        entries = town.text_entries(leaf)
        assert len(entries) == n
        assert town.text_leaf(entries) == leaf
    b = town.text_entries(LEAF_B)
    assert b[0][0][0] == (7, "街を出ますか？".encode("cp932"))   # 街を出ますか？ keeps its param
    assert b[3] == ([], False) and b[1][0][0] == (None, "セーブ".encode("cp932"))  # セーブ
    assert len(b[30][0]) == 16 and b[30][1] is False              # the shop list has no closing 0000
    a = town.text_entries(LEAF_A)
    assert a[56] == ([], True) and a[0][1] is True                # an empty article still has one
    assert town.text_entries(TOWN[4][:0x100]) is None            # a container header is not a text leaf


def test_text_leaf_odd_string_and_size_guard():
    leaf = town.text_leaf([([(None, script.encode("abc"))], True), ([], False)])
    assert leaf == bytes([4, 0, 14, 0]) + b"\x01\x00abc \x00\x00\x00\x00"   # empty entry starts at the end
    assert town.text_entries(leaf) == [([(None, b"abc ")], True), ([], False)]
    try:
        town.text_leaf([([(None, b"xx" * 33000)], True)])      # 66000 bytes: u16 offsets overflow
    except ValueError:
        return
    assert False, "expected ValueError"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
