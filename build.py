"""Build driver. Usage: python build.py [extract|dump]"""
import json, shutil, subprocess, sys
from pathlib import Path

import dat, halfwidth, script

ROOT = Path(__file__).parent
ROM = ROOT / "rom" / "Black-Matrix 00 (Japan) (Disc 1).bin"
MKPSXISO = ROOT / "tools" / "mkpsxiso-2.30-win64"
EXTRACTED = ROOT / "work" / "extracted"   # tree mkpsxiso builds from; DATs get overwritten
ORIG = ROOT / "work" / "orig"             # pristine copies of files we patch
BUILD = ROOT / "build"
ARCHIVES = ["SCENARIO.DAT", "TOWN.DAT", "EVENT.DAT", "SYSTEM.DAT", "BATTLE.DAT"]


def extract():
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    subprocess.run([MKPSXISO / "dumpsxiso.exe", "-x", EXTRACTED,
                    "-s", EXTRACTED / "layout.xml", ROM], check=True)
    ORIG.mkdir(exist_ok=True)
    for name in ARCHIVES + ["SLPS_035.73"]:
        shutil.copy2(EXTRACTED / name, ORIG / name)


SCRIPT = ROOT / "script"


def dump():
    """Write script/SCENARIO/NNN.json. Never overwrites: translations live there."""
    out = SCRIPT / "SCENARIO"
    out.mkdir(parents=True, exist_ok=True)
    for i, b in enumerate(dat.unpack((ORIG / "SCENARIO.DAT").read_bytes())):
        path = out / f"{i:03d}.json"
        if b and not path.exists():
            entries = script.extract(b, f"SCENARIO/{i:03d}")
            path.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")


def patch():
    files = dat.unpack((ORIG / "SCENARIO.DAT").read_bytes())
    for path in sorted((SCRIPT / "SCENARIO").glob("*.json")):
        i = int(path.stem)
        entries = json.loads(path.read_text(encoding="utf-8"))
        files[i] = script.insert(files[i], entries)
        for wide in script.too_wide(entries):
            print("too wide:", wide)
        for spill in script.spilled(entries):
            print("spilled:", spill)
    (EXTRACTED / "SCENARIO.DAT").write_bytes(dat.pack(files))
    halfwidth.assemble(ORIG / "SLPS_035.73", EXTRACTED / "SLPS_035.73")


def make_iso() -> Path:
    BUILD.mkdir(exist_ok=True)
    out = BUILD / "bm00-en.bin"
    # cwd is the dump dir: layout.xml refers to its files by relative path
    subprocess.run([MKPSXISO / "mkpsxiso.exe", "-y", "-o", out,
                    "-c", BUILD / "bm00-en.cue", "layout.xml"],
                   cwd=EXTRACTED, check=True)
    return out


if __name__ == "__main__":
    if sys.argv[1:] == ["extract"]:
        extract()
    elif sys.argv[1:] == ["dump"]:
        dump()
    elif not sys.argv[1:]:
        patch()
        print(make_iso())
    else:
        sys.exit("usage: python build.py [extract|dump]")
