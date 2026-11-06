"""Instruction page of every circus act, cold boot from the Ch9 card (see AGENTS.md, Town save).

    python -X utf8 tools/debug/circus.py [--rom build/bm00-en-disc2.cue] [--out work/qa/circus] [--frames N] [act ...]

Acts: flyers knife juggling rope lion spot trapeze. Each gets OUT/ACT/ with frames and sheet.png. Acts hang on black
when started from a savestate, so each run is one continuous session from power-on.
"""
import argparse
import concurrent.futures as cf
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = os.environ.get("SKILL", os.path.expanduser("~/.claude/plugins/marketplaces/retro-translation/skills/translate-retro-game"))

# hub cursor on TALK -> MINI GAME; the act grid is 3x2, the first entry of the next menu is Practice
COLD = "1500 -;8 start;1500 -;6 start;120 -;6 circle;300 -;6 circle;300 -;6 circle;120 -;6 circle;3300 -"
TO_LIST = COLD + ";6 right;60 -;6 right;60 -;6 circle;800 -"
ACTS = {
    "flyers": "", "knife": "6 right;30 -;", "juggling": "6 right;30 -;6 right;30 -;",
    "rope": "6 down;30 -;", "lion": "6 down;30 -;6 right;30 -;",
    "spot": "6 down;30 -;6 right;30 -;6 right;30 -;",
    "trapeze": "6 down;30 -;6 right;30 -;6 right;30 -;",
}


def run(act: str, a) -> int:
    perform = "6 down;30 -;" if act == "trapeze" else ""
    route = f"{TO_LIST};{ACTS[act]}6 circle;120 -;{perform}6 circle;{a.frames} -" + (f";{a.then}" if a.then else "")
    out = Path(a.out) / act
    cmd = [sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts" / "emu.py"), a.rom, "--out", str(out),
           "--sav", a.sav, "--route-str", route, "--shot-every", "60", "--sheet"]
    return subprocess.run(cmd, cwd=ROOT, stdout=subprocess.DEVNULL).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("acts", nargs="*", default=[])
    ap.add_argument("--rom", default="build/bm00-en-disc2.cue")
    ap.add_argument("--sav", default="work/states/ch9-disc2.mcd")
    ap.add_argument("--out", default="work/qa/circus")
    ap.add_argument("--frames", type=int, default=1500)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--then", help="route steps after the page, e.g. to play the act")
    a = ap.parse_args()
    acts = a.acts or list(ACTS)
    with cf.ThreadPoolExecutor(a.jobs) as pool:
        codes = list(pool.map(lambda act: run(act, a), acts))
    for act, code in zip(acts, codes):
        print(act, "exit", code)
    return max(codes)


if __name__ == "__main__":
    sys.exit(main())
