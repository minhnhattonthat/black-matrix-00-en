import json, tempfile
from pathlib import Path
import tl


def test_apply_merges_en_by_id_and_keeps_the_rest():
    with tempfile.TemporaryDirectory() as d:
        js = Path(d) / "012.json"
        js.write_text(json.dumps([{"id": "S/012/00001", "speaker": 1, "jp": ["a"], "en": ""},
                                  {"id": "S/012/00002", "jp": "b", "en": "old"}]), encoding="utf-8")
        answers = Path(d) / "012.txt"
        answers.write_text("S/012/00001\tFirst line\\nsecond\nS/012/09999\tnope\nS/012/00002\t   Range 4 \n", encoding="utf-8")
        unknown = tl.apply(js, answers)
        data = json.loads(js.read_text(encoding="utf-8"))
    assert data[0]["en"] == "First line\nsecond"
    assert data[1]["en"] == "   Range 4"                 # leading spaces are alignment; only the tail is trimmed
    assert unknown == ["S/012/09999"]


def test_apply_skips_tabless_lines_instead_of_blanking():
    with tempfile.TemporaryDirectory() as d:
        js = Path(d) / "a.json"
        js.write_text(json.dumps([{"id": "S/1", "jp": "x", "en": "keep me"}]), encoding="utf-8")
        answers = Path(d) / "a.txt"
        answers.write_text("S/1\n", encoding="utf-8")
        unknown = tl.apply(js, answers)
        data = json.loads(js.read_text(encoding="utf-8"))
    assert data[0]["en"] == "keep me"
    assert unknown == ["S/1 (empty)"]
    assert any("empty" in p for p in tl.check(["S/1\t0\tx"], ["S/1"]))


def test_lines_show_width_and_check_enforces_it():
    entries = [{"id": "S/1", "jp": "ナイフ", "en": "", "width": 18}]
    assert tl.lines(entries) == ["S/1\tw18\tナイフ"]
    src = ["S/1\tw18\tjp"]
    assert tl.check(src, ["S/1\tKnife"]) == []
    assert any("over width" in p for p in tl.check(src, ["S/1\tA very long weapon name"]))
    assert any("over width" in p for p in tl.check(["S/2\tw4\tjp"], ["S/2\tabcde"]))   # 5 > 4
    assert tl.check(["S/3\tw4\tjp"], ["S/3\tabc"]) == []                                 # "abc" pads to 4, fits


def test_show_lists_only_untranslated_windows_and_strings():
    entries = [{"id": "x/1", "speaker": 3, "jp": ["one", "two"], "en": ""},
               {"id": "x/2", "jp": "menu", "en": ""},
               {"id": "x/3", "jp": ["done"], "en": "Done"},
               {"id": "x/4", "jp": "　", "en": "", "width": 28}]        # a blank-line placeholder: nothing to translate
    assert tl.lines(entries) == ["x/1\t3\tone / two", "x/2\t-\tmenu"]


def test_check_reports_missing_extra_nonascii_and_long_lines():
    src = ["x/1\t0\tone / two", "x/2\t-\tmenu", "x/3\t0\tthree"]
    answers = ["x/1\tHello " + "w" * 85, "x/2\tcafé", "x/9\tstray", "x/2\tdup"]
    problems = tl.check(src, answers)
    assert any("missing" in p and "x/3" in p for p in problems)
    assert any("unknown" in p and "x/9" in p for p in problems)
    assert any("duplicate" in p and "x/2" in p for p in problems)
    assert any("non-ascii" in p and "x/2" in p for p in problems)
    assert any("long" in p and "x/1" in p for p in problems)
    assert tl.check(src, ["x/1\tHi", "x/2\tMenu", "x/3\tThree"]) == []


def test_wrap_entries_check_per_wrapped_line():
    entries = [{"id": "T/1", "jp": ["a"], "en": "", "width": 32, "wrap": True}]
    assert tl.lines(entries) == ["T/1\ta32\ta"]
    src = ["T/1\ta32\ta"]
    assert tl.check(src, ["T/1\t" + ("word " * 30).strip()]) == []            # wraps fine
    assert tl.check(src, ["T/1\t『Title』\\nbody"]) == []              # 『』 allowed in titles
    assert any("over width" in p for p in tl.check(src, ["T/1\t" + "x" * 33]))  # unbreakable word


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
