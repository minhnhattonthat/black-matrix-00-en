"""Build driver. Usage: python build.py extract | python build.py"""
import shutil, subprocess, sys
from pathlib import Path

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
    elif not sys.argv[1:]:
        print(make_iso())
    else:
        sys.exit("usage: python build.py [extract]")
