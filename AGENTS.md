# Black/Matrix 00 (PS1, 2 discs) English translation

Skill: translate-retro-game (Claude Code: plugin, enabled in .claude/settings.json; other agents: `<SKILL_DIR>/SKILL.md`; `$SKILL` = the directory holding its SKILL.md, default `~/.claude/plugins/marketplaces/retro-translation/skills/translate-retro-game`). Read it before ROM, text or QA work.

## Commands (run from repo root)
- Extract (once): `python -X utf8 build.py extract` -> work/extracted, work/orig, work/orig2, work/d2 (checks both discs against `rom.sha1` first)
- Build:    `python -X utf8 build.py` -> build/bm00-en.bin/.cue + build/bm00-en-disc2.bin/.cue
- Check:    `python -X utf8 check.py` (~50 s: every test except test_build + tl.check lint of script/**/*.json; the pre-commit hook runs this)
- Identity: `python -X utf8 test_build.py` (slow; overwrites build/ and work/extracted with the original-disc rebuild; run before a final build, then rebuild)
- Smoke:    `python -X utf8 $SKILL/scripts/emu.py build/bm00-en.cue --out work/qa/smoke --route-str "1500 -;8 start;600 -" --smoke` (PCSX-Redux headless, ~40 s; Start skips the intro FMV to the title). BIOS: tools/bios/scph5500.bin (gitignored; copy of DuckStation's ps-30j.bin from %LOCALAPPDATA%\DuckStation\bios). Without it PCSX-Redux exits 1 with no output.
- Tour:     `python -X utf8 tools/debug/tour.py [10 20-25] [--frames 6000 --jobs 3]` -> work/qa/tour/sNNN/ (frames, sheet.png, log.txt of DAT loads, jp.txt) + report.txt: per scenario, started/ended how, and every Japanese glyph the font cache drew. Exit 1 on any. ~1 min per scene at 3 jobs.
- Warp:     `python -X utf8 $SKILL/scripts/emu.py build/bm00-en.cue --out work/qa/w020 --script tools/debug/warp.lua --var SCENE=20 --frames 6000 --mash 20 --shot-every 60 --sheet --sav work/qa/tour/blank.mcd` (never ask the user to play to a scene). The warp cold-boots, picks NEW GAME and makes the first scenario load fetch SCENE; it ends when the script moves to another scenario. Story state: `tools/debug/ds2inject.py work/states/X.sav work/qa/inject.lua` turns a DuckStation state into the save regions, passed as an extra `--script` before warp.lua (does NOT unlock town hub commands: EQUIP/SHOP are still unreachable cold).
- Widths:   `python -X utf8 tools/debug/cells.py` -> per text class, English lines wider (in 12-px cells) than the widest Japanese of that class: the only overflow candidates. SYSTEM tables are measured in game instead (test_tables.test_english_fits_the_menu_boxes): item/weapon/ring names <= 16 chars (shop/equip list column), description lines <= 32 (bottom box), so its 29 ring names at 15-16 chars are fine. Left: 1 memory-card message.
- Town save: `work/states/ch9-disc2.mcd` (user's Ch9 card, Disc 2). Cold route to the town hub: `emu.py build/bm00-en-disc2.cue --sav work/states/ch9-disc2.mcd --route-str "1500 -;8 start;1500 -;6 start;120 -;6 circle;300 -;6 circle;300 -;6 circle;120 -;6 circle;3300 -" --state-out X.sav`; from the hub (cursor on TALK) left x4 + circle = STATUS, left + circle = SHOP. Circle confirms; a savestate taken during the load hangs on black, and play.py drops `--sav` after its first step (load screen sees no save).
- Release:  `python -X utf8 release.py` -> dist/ xdelta per disc (re-applied and SHA-checked) + zip with PATCHING.txt. VERSION in release.py. Never publish without the user.
- Translate: `python -X utf8 tl.py show|apply|check NNN [FILE]` (answer files in work/tl/)
- Clean:    `python -X utf8 tools/clean.py` (published projects: lists rebuildable/downloadable files; `--yes` deletes)

## Paths
- Original discs: `rom/Black-Matrix 00 (Japan) (Disc 1|2).bin` (gitignored; SHA-1 in `rom.sha1`, checked by `tools/check_rom.py`). Tools (gitignored, third-party): tools/pcsx-redux, tools/mkpsxiso-2.30-win64, armips, jpsxdec (Java 8); ffmpeg + xdelta3 on PATH. Savestates: `work/states/` (DuckStation; zstd, RAM at +0x1a62, VRAM at +0x201ddb of the unpacked state).
- Text: `script/{SCENARIO,SYSTEM,TOWN,EXE,MOVIE}/*.json` (jp beside en); redrawn picture text in script/GFX/*.png. Font/asm hacks: asm/ (halfwidth.asm, savetitle.asm).
- Glossary: `glossary.md`; voices: docs/style-reference.md; translator brief: docs/translator-brief*.md. RE notes index: `docs/re/README.md`. Fonts and their licences: `docs/fonts.md`. Design specs and plans: docs/superpowers/.

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts here read and analyse, never `.replace()` and write back.
- The user's decisions, with the options and reasons: `docs/decisions.md`. Read it before asking the user anything; add each new ruling there the same session.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update `docs/status.md`.
- Faithful style; honorifics kept (-san, -sama...); "Incest" is the game's term, keep it. Names exactly as in glossary.md (プラン = Plan, not Bran). Full names, no abbreviations.
- ASCII 0x20-0x7E only; 30 chars per window line, 3 lines per window, spill only when meaning needs it. Keep it under ~76 chars to avoid spills.
- Release zip = patches + PATCHING.txt only (no cue files).

## Gotchas
- Close DuckStation before building: mkpsxiso fails with "Cannot open or create output image".
- test_build.py leaves the ORIGINAL (Japanese) image in build/: rebuild before any emulator QA, or the tour reports Japanese everywhere (sha1 of the original Disc 1: f205c838...).
- Overflow is not checked at runtime: tl.check lints widths at build time; read the tour's sheet.png per scene for spills.
- Cold boot after EXE/asm/font/graphics changes: savestates keep the old program in RAM.
- Town text container is limited to 0x7000 bytes (build.TEXT_BUFFER); the Notebook has ~92 bytes spare, so longer town text must be paid for elsewhere.
- SYSTEM subs 4, 7-10 are code overlays: edit strings in place, never touch their tails.
- Disc 2 DATs and EXE are byte-identical to Disc 1; build copies the patched files. Movies are per disc (work/orig/MOVIE, work/orig2/MOVIE).
- Text is often stored twice (place cards, town copies x28): fix every copy.
- tools/ subdirectories are gitignored (third-party downloads): put reusable helpers at the repo root, in tools/*.py, or in tools/debug/.

## Status
`docs/status.md`: done, next, open bugs. Update it at the end of every session.
