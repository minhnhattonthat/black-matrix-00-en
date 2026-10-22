# Reverse-engineering notes

One file per subsystem (text engine, pointers, compression, font, graphics). Mark every finding with how far it is
proven, so a later session doesn't build on a guess:

- **verified** - and how: a decoded known string, a corrupt-and-boot test, a breakpoint hit on the drawing path, a
  passing roundtrip test. Name the test or savestate.
- **guess** - and why it seems likely (byte pattern, another game, an earlier patch's notes). Promote it to verified
  before code depends on it.

Addresses are for the dumps in `rom.sha1` unless a note says otherwise.

| File | Covers | State |
|---|---|---|
| [script-format.md](script-format.md) | SCENARIO.DAT script opcodes, strings, TOWN.DAT text containers | verified (test_script.py, test_town.py roundtrips; in game) |
| [movie-notes.md](movie-notes.md) | MOVIE/*.STR, jPSXdec frame replacement, subtitle pipeline | verified (test_movie.py; Disc 1 movies seen in game) |
| module docstrings: `dat.py`, `tables.py`, `pointers.py`, `exe.py`, `gfx.py`, `lz.py`, `labels.py`, `asm/*.asm` | archives, SYSTEM tables and code overlays, EXE strings, picture format, LZ packing, picture text sites, font hack | verified by their test_*.py roundtrips and in-game checks |
