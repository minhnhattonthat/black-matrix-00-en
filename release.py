"""Make the release files in dist/: one xdelta patch per disc (original image -> English image), each
checked by applying it, plus the player's readme, zipped. Needs xdelta3 on PATH and a
finished `python build.py`. No game data goes into dist/ except the differences inside the patches."""
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import build

VERSION = "00.9"
DIST = build.ROOT / "dist"
DISCS = [(1, build.ROM, build.BUILD / "bm00-en.bin"), (2, build.ROM2, build.BUILD / "bm00-en-disc2.bin")]


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while block := f.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    files = [build.ROOT / "PATCHING.txt"]
    for n, rom, built in DISCS:
        patch = DIST / f"bm00-en-v{VERSION}-disc{n}.xdelta"
        # -B: source window as large as the image, so files that moved on the disc are still matched
        subprocess.run(["xdelta3", "-e", "-9", "-f", "-B", str(rom.stat().st_size), "-s", rom, built, patch], check=True)
        check = DIST / "check.bin"
        subprocess.run(["xdelta3", "-d", "-f", "-B", str(rom.stat().st_size), "-s", rom, patch, check], check=True)
        if sha1(check) != sha1(built):
            sys.exit(f"disc {n}: the patch does not reproduce the built image")
        check.unlink()
        files.append(patch)
        print(f"disc {n}: original sha1 {sha1(rom)}  patch {patch.stat().st_size / 1e6:.1f} MB")
    out = DIST / f"bm00-en-v{VERSION}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:       # the patches are already compressed
        for f in files:
            z.write(f, f.name)
    print(out)


if __name__ == "__main__":
    main()
