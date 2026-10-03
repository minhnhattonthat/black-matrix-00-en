"""Build driver. Usage: python build.py [extract|dump]"""
import json, shutil, subprocess, sys
from pathlib import Path

import dat, exe, halfwidth, movie, pointers, script, tables, town

ROOT = Path(__file__).parent
ROM = ROOT / "rom" / "Black-Matrix 00 (Japan) (Disc 1).bin"
MKPSXISO = ROOT / "tools" / "mkpsxiso-2.30-win64"
EXTRACTED = ROOT / "work" / "extracted"   # tree mkpsxiso builds from; DATs get overwritten
ORIG = ROOT / "work" / "orig"             # pristine copies of files we patch
BUILD = ROOT / "build"
ARCHIVES = ["SCENARIO.DAT", "TOWN.DAT", "EVENT.DAT", "SYSTEM.DAT", "BATTLE.DAT"]


ROM2 = ROOT / "rom" / "Black-Matrix 00 (Japan) (Disc 2).bin"
DISC2 = ROOT / "work" / "d2"               # Disc 2 tree: same archives and EXE (named SLPS_035.74), other XA/STR
EXE2 = "SLPS_035.74"


def extract():
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    subprocess.run([MKPSXISO / "dumpsxiso.exe", "-x", EXTRACTED,
                    "-s", EXTRACTED / "layout.xml", ROM], check=True)
    if ROM2.exists():
        DISC2.mkdir(parents=True, exist_ok=True)
        subprocess.run([MKPSXISO / "dumpsxiso.exe", "-x", DISC2, "-s", DISC2 / "layout.xml", ROM2], check=True)
    ORIG.mkdir(exist_ok=True)
    for name in ARCHIVES + ["SLPS_035.73"]:
        shutil.copy2(EXTRACTED / name, ORIG / name)
    shutil.copytree(EXTRACTED / "MOVIE", ORIG / "MOVIE", dirs_exist_ok=True)


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
    sysdir = SCRIPT / "SYSTEM"
    sysdir.mkdir(exist_ok=True)
    system = dat.unpack((ORIG / "SYSTEM.DAT").read_bytes())
    battle = dat.unpack((ORIG / "BATTLE.DAT").read_bytes())
    for name, entries in (("tables", tables.extract_fixed(system[2], "SYSTEM/2")),
                          ("messages", pointers.extract(system[10], "SYSTEM/10")),
                          ("overlay", tables.extract_overlay(system[4], "SYSTEM/4")),
                          ("battle", [{"id": f"BATTLE/{i:03d}", "jp": jp, "en": "", "width": 16}
                                      for i, jp in enumerate(tables.battle_name_list(battle))])):
        path = sysdir / f"{name}.json"
        if not path.exists():
            path.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")

    towndir = SCRIPT / "TOWN"
    towndir.mkdir(exist_ok=True)
    nb, ui = town.extract(dat.unpack((ORIG / "TOWN.DAT").read_bytes())[4])   # every copy is identical
    for name, entries in (("notebook", nb), ("town", ui)):
        path = towndir / f"{name}.json"
        if not path.exists():
            path.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")

    exedir = SCRIPT / "EXE"
    exedir.mkdir(exist_ok=True)
    if not (exedir / "strings.json").exists():
        entries = exe.extract((ORIG / "SLPS_035.73").read_bytes())
        (exedir / "strings.json").write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")


def _system_json(name):
    return json.loads((SCRIPT / "SYSTEM" / f"{name}.json").read_text(encoding="utf-8"))


def patch_system():
    system = dat.unpack((ORIG / "SYSTEM.DAT").read_bytes())
    fixed = _system_json("tables")
    system[2] = tables.insert_fixed(system[2], fixed)
    system[10] = pointers.insert(system[10], _system_json("messages"))
    system[4] = tables.insert_overlay(system[4], _system_json("overlay"))
    (EXTRACTED / "SYSTEM.DAT").write_bytes(dat.pack(system))
    # battle names: their own list first, then the unit table (SYSTEM table 2) fills any gap
    unit_lo, unit_hi = tables._directory(system[2])[2]
    names = {e["jp"]: e["en"] for e in fixed
             if e["en"] and unit_lo <= int(e["id"].rsplit("/", 1)[1], 16) < unit_lo + unit_hi}
    names.update({e["jp"]: e["en"] for e in _system_json("battle") if e["en"]})
    battle = dat.unpack((ORIG / "BATTLE.DAT").read_bytes())
    battle = [tables.insert_battle(b, names) if b[:4] == tables.BATTLE_MAGIC else b for b in battle]
    (EXTRACTED / "BATTLE.DAT").write_bytes(dat.pack(battle))


def patch_town():
    nb = json.loads((SCRIPT / "TOWN" / "notebook.json").read_text(encoding="utf-8"))
    ui = json.loads((SCRIPT / "TOWN" / "town.json").read_text(encoding="utf-8"))
    subs = dat.unpack((ORIG / "TOWN.DAT").read_bytes())
    grown = 0
    for i, b in enumerate(subs):
        if b and town.has_text(b):
            subs[i] = town.insert(b, nb, ui)
            grown = max(grown, len(subs[i]) - len(b))
    print(f"TOWN: largest sub-file growth {grown} bytes")
    (EXTRACTED / "TOWN.DAT").write_bytes(dat.pack(subs))


def patch_movies():
    """Subtitled streams from the cache (rendered on a miss); movies without English cues are the originals."""
    for src in sorted((ORIG / "MOVIE").glob("*.STR")):
        cue_file = SCRIPT / "MOVIE" / f"{src.stem}.json"
        cues = json.loads(cue_file.read_text(encoding="utf-8")) if cue_file.exists() else []
        shutil.copyfile(movie.cached(src, cues) if any(c["en"] for c in cues) else src,
                        EXTRACTED / "MOVIE" / src.name)


def patch():
    patch_system()
    patch_town()
    patch_movies()
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
    strings = json.loads((SCRIPT / "EXE" / "strings.json").read_text(encoding="utf-8"))
    patched = exe.insert((EXTRACTED / "SLPS_035.73").read_bytes(), strings)
    (EXTRACTED / "SLPS_035.73").write_bytes(patched)


def make_iso(tree: Path = EXTRACTED, name: str = "bm00-en") -> Path:
    BUILD.mkdir(exist_ok=True)
    out = BUILD / f"{name}.bin"
    # cwd is the dump dir: layout.xml refers to its files by relative path
    subprocess.run([MKPSXISO / "mkpsxiso.exe", "-y", "-o", out,
                    "-c", BUILD / f"{name}.cue", "layout.xml"],
                   cwd=tree, check=True)
    return out


def make_iso2() -> Path:
    """Disc 2 carries the same archives and executable as Disc 1: reuse whatever is in EXTRACTED."""
    for name in ARCHIVES:
        shutil.copy2(EXTRACTED / name, DISC2 / name)
    shutil.copy2(EXTRACTED / "SLPS_035.73", DISC2 / EXE2)
    return make_iso(DISC2, "bm00-en-disc2")


if __name__ == "__main__":
    if sys.argv[1:] == ["extract"]:
        extract()
    elif sys.argv[1:] == ["dump"]:
        dump()
    elif not sys.argv[1:]:
        patch()
        print(make_iso())
        if (DISC2 / "layout.xml").exists():
            print(make_iso2())
    else:
        sys.exit("usage: python build.py [extract|dump]")
