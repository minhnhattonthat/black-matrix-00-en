"""Screen tour: warp into scenarios from a cold boot, mash through them, and report Japanese glyphs drawn.
  python -X utf8 tools/debug/tour.py [SCENES..] [--frames 6000] [--jobs 3] [--mash 20] [--shot-every 60]
                                     [--out work/qa/tour] [--cue build/bm00-en.cue]
SCENES are SCENARIO.DAT sub numbers or ranges (10 20-25); default: every sub with a script/SCENARIO JSON.
Each scene gets OUT/sNNN/ with the frames, sheet.png, log.txt (sub-file loads) and jp.txt. OUT/report.txt
lists per scene: started or not, how it ended, and the Japanese characters rasterised (decoded from the glyph
codes). Exit 1 when any scene drew Japanese or failed to start. Scenes run in parallel (--jobs)."""
import argparse, concurrent.futures, glob, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILL = os.environ.get("SKILL", os.path.expanduser("~/.claude/plugins/marketplaces/retro-translation/skills/translate-retro-game"))
SCRIPTS = os.path.join(SKILL, "scripts")
EMU = os.path.join(SCRIPTS, "emu.py")
WARP = os.path.join(ROOT, "tools", "debug", "warp.lua")
sys.path.insert(0, SCRIPTS)
import sheet  # noqa: E402


def scenes(args):
    out = []
    for a in args:
        lo, _, hi = a.partition("-")
        out += range(int(lo), int(hi or lo) + 1)
    return out or [int(os.path.basename(p)[:3]) for p in sorted(glob.glob(os.path.join(ROOT, "script", "SCENARIO", "*.json")))]


def run(scene, a, mcd):
    out = os.path.join(a.out, f"s{scene:03d}")
    cmd = [sys.executable, "-X", "utf8", EMU, a.cue, "--out", out, "--script", WARP, "--var", f"SCENE={scene}",
           "--frames", str(a.frames), "--mash", str(a.mash), "--mash-key", a.mash_key, "--shot-every", str(a.shot_every),
           "--sav", mcd, "--timeout", str(a.timeout)]
    rc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).returncode
    log = open(os.path.join(out, "log.txt"), encoding="utf-8").read() if os.path.exists(os.path.join(out, "log.txt")) else ""
    start = [int(l.split()[0]) for l in log.splitlines() if " running" in l]
    started = bool(start)
    if started:  # full-size sheet of the scene itself (the boot and title are the same in every run)
        sheet.make(out, div=1, changed=0.005, lo=start[0])
    nxt = [l for l in log.splitlines() if " next scenario " in l]
    end = nxt[0].split(" ", 1)[1] if nxt else ("frames up" if started else "never started")
    chars = []
    for line in open(os.path.join(out, "jp.txt"), encoding="utf-8").read().splitlines() if os.path.exists(os.path.join(out, "jp.txt")) else []:
        frame, code = line.split()
        chars.append((int(frame), bytes.fromhex(code).decode("shift_jis", "replace")))
    return scene, rc, started, end, chars


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--frames", type=int, default=6000)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--mash", type=int, default=20)
    ap.add_argument("--mash-key", default="circle", help="dialogue advances on Circle; Cross does nothing there")
    ap.add_argument("--shot-every", type=int, default=60)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--out", default=os.path.join(ROOT, "work", "qa", "tour"))
    ap.add_argument("--cue", default=os.path.join(ROOT, "build", "bm00-en.cue"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    mcd = os.path.join(a.out, "blank.mcd")   # no save: the title menu then has nothing to load
    open(mcd, "wb").write(bytes(128 * 1024))
    bad = 0
    lines = []
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        for scene, rc, started, end, chars in pool.map(lambda s: run(s, a, mcd), scenes(a.scenes)):
            jp = "".join(c for _, c in chars)
            first = f" (first at frame {chars[0][0]})" if chars else ""
            line = f"s{scene:03d} rc={rc} {'ok' if started else 'NOT STARTED'} {end} jp={len(chars)}{first} {jp}"
            print(line, flush=True)
            lines.append(line)
            bad += (not started) or bool(chars) or rc not in (0,)
    open(os.path.join(a.out, "report.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{len(lines)} scenes, {bad} with problems -> {os.path.join(a.out, 'report.txt')}")
    sys.exit(1 if bad else 0)
