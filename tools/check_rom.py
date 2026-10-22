"""check_rom.py: refuse to build from a dump that isn't the one listed in rom.sha1.

A wrong revision or an already-patched copy otherwise builds fine and breaks at random offsets in game.
Call check() at the top of build.py; run it alone to check a fresh dump. Exit 1 on a missing or wrong file."""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(listing=ROOT / "rom.sha1"):
    for line in listing.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        want, name = line.split(None, 1)
        path = ROOT / name.strip().lstrip("*")
        if not path.is_file():
            sys.exit(f"missing {name.strip()}: copy your dump there (see README)")
        with open(path, "rb") as f:
            got = hashlib.file_digest(f, "sha1").hexdigest()
        if got != want.lower():
            sys.exit(f"{name.strip()}: SHA-1 {got}, expected {want}. Wrong revision, a header, or already patched?")


if __name__ == "__main__":
    check()
    print("rom ok")
