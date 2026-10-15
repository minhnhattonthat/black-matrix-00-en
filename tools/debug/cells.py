"""Static overflow check: per text class, compare each English line's width in 12-px cells (two ASCII letters per
cell with the halfwidth font) against the widest Japanese line of the same class (one cell per full-width char).
An English line no wider than the widest original of its class cannot overflow a box the original fit in; the
lines listed here are the only candidates for an in-game overflow check.
  python -X utf8 tools/debug/cells.py            # exit 1 if any English line exceeds its class's Japanese maximum
Dialogue is measured after build wrapping (script.wrap, 30 chars); the Notebook after its own 32-char wrap."""
import collections, glob, json, math, os, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import script  # noqa: E402


def jp_cells(s):
    return sum(1 if unicodedata.east_asian_width(c) in "WF" else 0.5 for c in s)


def en_cells(s):
    return math.ceil(len(s) / 2)


def main():
    classes = collections.defaultdict(lambda: {"jp": 0, "en": []})
    for path in sorted(glob.glob(os.path.join(ROOT, "script", "**", "*.json"), recursive=True)):
        kind = os.path.basename(os.path.dirname(path))
        if kind == "MOVIE":
            continue  # subtitles are burned into video, no box
        for e in json.load(open(path, encoding="utf-8")):
            if not e.get("en"):
                continue
            key = (kind if kind != "SYSTEM" else os.path.basename(path)[:-5], e.get("width"))
            c = classes[key]
            for jp in e["jp"] if isinstance(e["jp"], list) else [e["jp"]]:
                c["jp"] = max(c["jp"], max(jp_cells(l) for l in jp.split("\n")))
            if kind == "SCENARIO" and isinstance(e["jp"], list):
                lines = script.wrap(e["en"])
            elif e.get("wrap"):
                lines = script.wrap(e["en"], e["width"])
            else:
                lines = e["en"].split("\n")
            c["en"] += [(en_cells(l), e["id"], l) for l in lines]
    bad = 0
    for key, c in sorted(classes.items(), key=str):
        over = sorted((x for x in c["en"] if x[0] > c["jp"]), reverse=True)
        print(f"{key[0]}/{key[1]}: jp max {c['jp']:g} cells, en max {max(x[0] for x in c['en'])} cells, "
              f"{len(over)} English lines wider than any Japanese")
        for cells, id_, line in over[:5]:
            print(f"    {cells} {id_} {line!r}")
        bad += len(over)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
