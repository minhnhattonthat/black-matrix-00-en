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
    out = build.make_iso()
    assert out.stat().st_size == build.ROM.stat().st_size
    assert sha(out) == sha(build.ROM)


if __name__ == "__main__":
    test_unmodified_rebuild_matches_original()
    print("ok")
