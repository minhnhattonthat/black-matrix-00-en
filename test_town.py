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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
