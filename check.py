"""One-command check (the pre-commit hook runs this): every fast test, then tl.check over all committed text.
  python -X utf8 check.py
Leaves out test_build.py: it rebuilds both identity discs into build/ (slow, and it overwrites the English
image and work/extracted). Run it by hand before a final build."""
import json, subprocess, sys
from pathlib import Path

import tl

ROOT = Path(__file__).parent
failed = []
for t in sorted(ROOT.glob("test_*.py")):
    if t.name == "test_build.py":
        continue
    if subprocess.run([sys.executable, "-X", "utf8", t.name], cwd=ROOT, capture_output=True).returncode:
        failed.append(t.name)

# Lint the translated text with tl.check, as if every committed entry were a fresh answer file.
problems = []
for js in sorted((ROOT / "script").rglob("*.json")):
    entries = json.loads(js.read_text(encoding="utf-8"))
    src, ans = [], []
    for e in entries:
        if not e.get("en"):
            continue
        col = f'{"a" if e.get("wrap") else "w"}{e["width"]}' if "width" in e else "-"
        src.append(f'{e["id"]}\t{col}\t')
        ans.append(f'{e["id"]}\t{e["en"].replace(chr(10), chr(92) + "n")}')
    # "long" is tl.check's drafting heuristic for unlimited lines; window fit is enforced by script.insert at build.
    problems += [f"{js.relative_to(ROOT)}: {p}" for p in tl.check(src, ans) if not p.startswith("long:")]

print("\n".join([f"FAIL {t}" for t in failed] + problems) or "ok")
sys.exit(1 if failed or problems else 0)
