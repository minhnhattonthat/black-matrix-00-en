"""Translation helper.
  python tl.py show NNN          print untranslated entries of script/SCENARIO/NNN.json
  python tl.py apply NNN FILE    merge "id<TAB>en" lines (\\n = line break) into the JSON
  python tl.py check NNN FILE    lint an answer file against work/tl/NNN.src.txt"""
import json, sys
from pathlib import Path

import script

ROOT = Path(__file__).parent
SCRIPT = ROOT / "script" / "SCENARIO"


def _json_path(num: str) -> Path:
    """'012' -> script/SCENARIO/012.json; 'SYSTEM/tables' -> script/SYSTEM/tables.json"""
    return (ROOT / "script" / f"{num}.json") if "/" in num else (SCRIPT / f"{num}.json")


def lines(entries: list[dict]) -> list[str]:
    out = []
    for e in entries:
        if e["en"]:
            continue
        jp = " / ".join(e["jp"]) if isinstance(e["jp"], list) else e["jp"]
        col = f'w{e["width"]}' if "width" in e else e.get("speaker")   # wN = byte limit of a fixed field, else portrait slot
        out.append(f'{e["id"]}\t{"-" if col is None else col}\t{jp}')
    return out


def apply(js: Path, answers: Path) -> list[str]:
    entries = json.loads(js.read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in entries}
    unknown = []
    for raw in answers.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        id_, _, en = raw.partition("\t")
        if id_ not in by_id:
            unknown.append(id_)
            continue
        if not en.strip():                 # a tab-less line must not blank an existing translation
            unknown.append(f"{id_} (empty)")
            continue
        by_id[id_]["en"] = en.replace("\\n", "\n").strip()
    js.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    return unknown


def check(src_lines: list[str], answer_lines: list[str], limit: int = 85) -> list[str]:
    """Problems in a translator's answer file against the source listing it was made from."""
    wanted = [l.split("\t")[0] for l in src_lines if l.strip()]
    limits = {p[0]: int(p[1]) for p in (l.split("\t") for l in src_lines) if len(p) > 1 and p[1].isdigit()}
    seen, problems = {}, []
    for raw in answer_lines:
        if not raw.strip():
            continue
        id_, _, en = raw.partition("\t")
        if id_ in seen:
            problems.append(f"duplicate id: {id_}")
        seen[id_] = en
        if id_ not in wanted:
            problems.append(f"unknown id: {id_}")
        if not en.strip():
            problems.append(f"empty: {id_}")
        if not en.isascii():
            problems.append(f"non-ascii: {id_}: {en!r}")
        if "\t" in en:
            problems.append(f"tab in text: {id_}")
        if id_ in limits:
            n = len(script.encode(en.replace("\\n", " "))) if en.isascii() else len(en) * 2
            if n > limits[id_]:
                problems.append(f"over width: {id_} ({n} > {limits[id_]})")
        elif len(en.replace("\\n", " ")) > limit or any(len(w) > 30 for w in en.split()):
            problems.append(f"long: {id_} ({len(en)} chars)")
    problems += [f"missing id: {i}" for i in wanted if i not in seen]
    return problems


if __name__ == "__main__":
    cmd, num = sys.argv[1], sys.argv[2]
    js = _json_path(num)
    if cmd == "show":
        sys.stdout.reconfigure(encoding="utf-8")
        print("\n".join(lines(json.loads(js.read_text(encoding="utf-8")))))
    elif cmd == "apply":
        for id_ in apply(js, Path(sys.argv[3])):
            print("unknown id:", id_)
    elif cmd == "check":
        src = (ROOT / "work" / "tl" / f"{num.replace('/', '_')}.src.txt").read_text(encoding="utf-8").splitlines()
        ans = Path(sys.argv[3]).read_text(encoding="utf-8").splitlines()
        sys.stdout.reconfigure(encoding="utf-8")
        print("\n".join(check(src, ans)) or "ok")
    else:
        sys.exit(__doc__)
