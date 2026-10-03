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
    leaf = town.text_leaf([([], False), ([(None, script.encode("abc"))], True)])
    assert leaf == bytes([4, 0, 4, 0]) + b"\x01\x00abc \x00\x00\x00\x00" + bytes(2)   # 0-byte entry, then word pad
    assert town.text_entries(leaf) == [([], False), ([(None, b"abc ")], True)]
    padded = town.text_leaf([([(None, b"ab")], True)])             # 10 bytes of content
    assert len(padded) == 12 and town.text_entries(padded) == [([(None, b"ab")], True)]   # 4-byte pad survives
    try:
        town.text_leaf([([(None, b"xx" * 33000)], True)])      # 66000 bytes: u16 offsets overflow
    except ValueError:
        return
    assert False, "expected ValueError"


def test_extract_and_identity_insert():
    nb, ui = town.extract(TOWN[4])
    assert len(nb) == 68 and nb[0]["id"] == "TOWN/A/00" and nb[0]["jp"][0].startswith("『")   # 『
    assert nb[0]["width"] == 32 and nb[0]["wrap"] is True
    assert ui[0] == {"id": "TOWN/B/00/00", "jp": "街を出ますか？", "en": "", "width": 28}
    assert len(ui) > 140 and all(e["jp"] for e in ui)            # blank 　 lines are listed too
    for i in list(range(4, 31)) + [40]:
        assert town.has_text(TOWN[i]) and town.insert(TOWN[i], nb, ui) == TOWN[i]
    assert not town.has_text(TOWN[0])


def test_insert_wraps_articles_relayouts_and_keeps_params():
    nb, ui = town.extract(TOWN[4])
    nb[0]["en"] = ("『The circus is in town!』\nThe Nekinter Kanel troupe has come to this town too, "
                   "and everyone is talking about it so go and see it quickly!\n\nFly")
    ui[0]["en"] = "Leave town?"
    out = town.insert(TOWN[4], nb, ui)
    assert len(out) > len(TOWN[4])
    nb2, ui2 = town.extract(out)
    lines = nb2[0]["jp"]
    assert lines[0] == "『The circus is in town!』" and lines[-1].rstrip() == "Fly" and "　" in lines
    assert all(len(script.encode(l)) <= 32 for l in lines) and len(lines) >= 5
    assert ui2[0]["jp"].rstrip() == "Leave town?"
    children, _ = town.parse(out)
    orig_children, _ = town.parse(TOWN[4])
    assert [town.rebuild(c) for c in children[2:]] == [town.rebuild(c) for c in orig_children[2:]]   # later siblings moved intact
    inner, _ = children[1]
    leaf = next(c for c in inner if isinstance(c, bytes) and town.text_entries(c) and len(town.text_entries(c)) == 48)
    assert town.text_entries(leaf)[0][0][0][0] == 7               # param kept


def test_insert_rejects_unbreakable_article_line():
    nb, ui = town.extract(TOWN[4])
    nb[1]["en"] = "『" + "x" * 31 + "』"                 # 35 bytes, no space to wrap at
    try:
        town.insert(TOWN[4], nb, ui)
    except ValueError as err:
        assert "TOWN/A/01" in str(err) and "32" in str(err)
        return
    assert False, "expected ValueError"


def test_translated_articles_stay_within_the_original_line_count():
    import json
    from build import SCRIPT
    nb = json.loads((SCRIPT / "TOWN" / "notebook.json").read_text(encoding="utf-8"))
    longest = max(len(e["jp"]) for e in nb)                       # 25 in the original: the only known-safe envelope
    too_long = [(e["id"], len(town._article_lines(e))) for e in nb if len(town._article_lines(e)) > longest]
    assert not too_long, too_long


def test_insert_rejects_wide_ui_line_and_unknown_id():
    nb, ui = town.extract(TOWN[4])
    ui[0]["en"] = "x" * 29
    try:
        town.insert(TOWN[4], nb, ui)
    except ValueError as err:
        assert "TOWN/B/00/00" in str(err)
    else:
        assert False
    try:
        town.insert(TOWN[4], nb, [{"id": "TOWN/B/99/00", "en": "x", "width": 28}])
    except ValueError:
        return
    assert False


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
