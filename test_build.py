import hashlib, shutil
import build


def sha(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def test_unmodified_rebuild_matches_original():
    for name in ("SCENARIO.DAT", "SYSTEM.DAT", "BATTLE.DAT", "TOWN.DAT", "SLPS_035.73"):   # undo any patch
        shutil.copy2(build.ORIG / name, build.EXTRACTED / name)
    shutil.copytree(build.ORIG / "MOVIE", build.EXTRACTED / "MOVIE", dirs_exist_ok=True)
    out = build.make_iso()
    assert out.stat().st_size == build.ROM.stat().st_size
    assert sha(out) == sha(build.ROM)


def test_disc2_shares_disc1_files_and_rebuilds_identically():
    if not build.ROM2.exists():
        return
    for name in build.ARCHIVES + ["SLPS_035.73"]:          # test 1 left the originals in EXTRACTED
        shutil.copy2(build.ORIG / name, build.EXTRACTED / name)
    shutil.copytree(build.ORIG2 / "MOVIE", build.DISC2 / "MOVIE", dirs_exist_ok=True)   # undo subtitled movies
    out = build.make_iso2()
    assert sha(out) == sha(build.ROM2)                     # so Disc 1's originals ARE Disc 2's files


if __name__ == "__main__":
    test_unmodified_rebuild_matches_original()
    test_disc2_shares_disc1_files_and_rebuilds_identically()
    print("ok")
