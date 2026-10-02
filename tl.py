"""Translation helper.
  python tl.py show NNN          print untranslated entries of script/SCENARIO/NNN.json
  python tl.py apply NNN FILE    merge "id<TAB>en" lines (\\n = line break) into the JSON"""
import json, sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "script" / "SCENARIO"


def lines(entries: list[dict]) -> list[str]:
    out = []
    for e in entries:
        if e["en"]:
            continue
        jp = " / ".join(e["jp"]) if isinstance(e["jp"], list) else e["jp"]
        speaker = e.get("speaker")
        out.append(f'{e["id"]}\t{"-" if speaker is None else speaker}\t{jp}')
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
        by_id[id_]["en"] = en.replace("\\n", "\n").strip()
    js.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    return unknown


if __name__ == "__main__":
    cmd, num = sys.argv[1], sys.argv[2]
    js = SCRIPT / f"{num}.json"
    if cmd == "show":
        sys.stdout.reconfigure(encoding="utf-8")
        print("\n".join(lines(json.loads(js.read_text(encoding="utf-8")))))
    elif cmd == "apply":
        for id_ in apply(js, Path(sys.argv[3])):
            print("unknown id:", id_)
    else:
        sys.exit(__doc__)
