import json, tempfile
from pathlib import Path
import tl


def test_apply_merges_en_by_id_and_keeps_the_rest():
    with tempfile.TemporaryDirectory() as d:
        js = Path(d) / "012.json"
        js.write_text(json.dumps([{"id": "S/012/00001", "speaker": 1, "jp": ["a"], "en": ""},
                                  {"id": "S/012/00002", "jp": "b", "en": "old"}]), encoding="utf-8")
        answers = Path(d) / "012.txt"
        answers.write_text("S/012/00001\tFirst line\\nsecond\nS/012/09999\tnope\n", encoding="utf-8")
        unknown = tl.apply(js, answers)
        data = json.loads(js.read_text(encoding="utf-8"))
    assert data[0]["en"] == "First line\nsecond"
    assert data[1]["en"] == "old"
    assert unknown == ["S/012/09999"]


def test_show_lists_only_untranslated_windows_and_strings():
    entries = [{"id": "x/1", "speaker": 3, "jp": ["one", "two"], "en": ""},
               {"id": "x/2", "jp": "menu", "en": ""},
               {"id": "x/3", "jp": ["done"], "en": "Done"}]
    assert tl.lines(entries) == ["x/1\t3\tone / two", "x/2\t-\tmenu"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
