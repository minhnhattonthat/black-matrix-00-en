# Black/Matrix 00 (PSX, SLPS-03573) Disc 1 — English Translation Design

Date: 2026-10-02

## Goal

Produce a playable English-patched `bin/cue` of *Black/Matrix 00 (Japan) (Disc 1)*, plus an xdelta patch against the original image.

Decisions made with the user:

- Target language: English. Personal use.
- Claude produces the translation; the user spot-checks.
- English renders through a halfwidth (8px, 1-byte ASCII) font hack in the executable.
- Done = all text in English: dialogue, menus, items, skills, battle text, EXE strings.

Out of scope: Japanese baked into images (TIM textures, logos), FMV, voice, Disc 2. Disc 2 should later reuse the same pipeline.

## Findings from exploration

- Disc holds 47 files. Text lives in `SCENARIO.DAT` (~620KB of text), `TOWN.DAT` (~530KB), `BATTLE.DAT`, `SYSTEM.DAT`, `EVENT.DAT`, and a few strings in `SLPS_035.73`.
- `.DAT` archive header: u32 file count, u32 sector shift (`0x0b` = 2048-byte sectors), then a table of u16 pairs (sector offset, sector count) per sub-file.
- Dialogue is uncompressed Shift-JIS embedded in script bytecode. Each line is opcode `50 10`, the string, then `00 00`, padded to 16-bit alignment. Observed in `SCENARIO.DAT`; other files are unconfirmed.
- `tools/mkpsxiso-2.30-win64/dumpsxiso.exe` dumps the disc cleanly and writes a rebuild XML.
- Python 3.12 and git are installed. Perl is not, so abcde/Atlas is not used.

## Approach

A custom Python pipeline (stdlib only), one command to rebuild. Rejected: abcde/Atlas + quickbms (needs Perl, weak on bytecode-embedded strings) and in-place hex patching (English would have to fit the Japanese byte length).

One new download: `armips`, for the ASM patches. Testing and debugging use DuckStation.

## Layout

```
rom/            original bin/cue (never modified, git-ignored)
tools/          third-party tools
work/extracted/ disc dump from dumpsxiso (git-ignored)
work/unpacked/  DAT sub-files (git-ignored)
script/jp/      extracted Japanese, JSON per sub-file
script/en/      English, same structure
glossary.md     names, terms, items, skills
asm/            armips sources for the font hack
build/          patched bin/cue and xdelta (git-ignored)
```

## Components

Each is one Python file with one job.

- `dat.py` — unpack and repack `.DAT` archives. Repack recomputes the offset/size table so sub-files may grow.
  Check: unpack then repack is byte-identical to the original.
- `script.py` — walk a sub-file's bytecode, extract every string with a stable ID (archive, sub-file index, offset), and reinsert strings of a different length, fixing any intra-script offsets that the growth moves.
  Check: extract then reinsert of the Japanese is byte-identical.
- `exe.py` — extract and insert strings in `SLPS_035.73`. Strings stay in their original slots when they fit; otherwise they move to free space and their pointers are updated.
- `build.py` — run insert, repack, armips, then `mkpsxiso` to produce `build/` output and the xdelta.

JSON entry shape: `{"id": ..., "jp": ..., "en": ...}`. An empty `en` means the Japanese is kept, so partial builds always work.

## Font hack

Locate the text draw routine in `SLPS_035.73` with the DuckStation debugger. Add a path for 1-byte ASCII: 8px advance, glyphs from an 8x16 font embedded in the executable. Adjust line-width and wrap constants to match.

Fixed-width halfwidth only. A variable-width font is a later upgrade if the result looks poor.

## Translation

1. Build `glossary.md` first: character names, places, terms, items, skills.
2. Translate each sub-file's JSON in scene order, with the glossary and neighbouring lines as context.
3. The insert step wraps lines to the window width and reports any that overflow the window's line count.

## Phases

Each phase ends with something testable.

1. `dat.py` and `script.py` round-trip byte-identical on all five archives; the rebuilt image boots in DuckStation. This phase includes confirming or reverse-engineering the text format of `EVENT`, `BATTLE`, `SYSTEM`, and `TOWN`.
2. One fullwidth English string, longer than its original, appears in-game. This validates growth and repacking before any ASM work.
3. Font hack: the same string renders in halfwidth.
4. Glossary, then translation in this order: SYSTEM and menus, EXE strings, SCENARIO, TOWN, BATTLE, EVENT.
5. Playtest, fix overflows, produce the xdelta patch.

## Risks and fallbacks

- Script jump offsets may break when strings grow. The round-trip check and phase 2 catch this. Fallback: relocate grown strings to the end of the sub-file, or pad.
- `EVENT`, `BATTLE`, and `SYSTEM` may store text under other opcodes or in fixed-width tables. Phase 1 covers this per file; fixed-width tables keep their slot size.
- The draw routine may share state with a kanji glyph cache. Fallback: fullwidth English on the affected screens.
- An existing PSX patch could not be confirmed; web results conflate this game with the GBA *Black Matrix Zero*. The project assumes none exists.
