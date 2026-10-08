# Black/Matrix 00 (PS1, 2 discs) English translation

Skill: translate-retro-game (H:/translation/.claude/skills/translate-retro-game/SKILL.md). Read it before ROM, text or QA work.

## Commands (run from repo root)
- Extract (once): `python -X utf8 build.py extract` -> work/extracted, work/orig, work/orig2, work/d2
- Build:    `python -X utf8 build.py` -> build/bm00-en.bin/.cue + build/bm00-en-disc2.bin/.cue
- Check:    `python -X utf8 check.py` (~50 s: every test except test_build + tl.check lint of script/**/*.json; the pre-commit hook runs this)
- Identity: `python -X utf8 test_build.py` (slow; overwrites build/ and work/extracted with the original-disc rebuild; run before a final build, then rebuild)
- Smoke:    `python -X utf8 H:/translation/.claude/skills/translate-retro-game/scripts/emu.py build/bm00-en.cue --bios E:/DuckStation/bios/SCPH-5500.bin --out work/qa/smoke --route-str "1500 -;8 start;600 -" --smoke` (PCSX-Redux headless, real speed ~40 s; Start skips the intro FMV to the title)
- Release:  `python -X utf8 release.py` -> dist/ xdelta per disc (re-applied and SHA-checked) + zip with PATCHING.txt. VERSION in release.py. Never publish without the user.
- Translate: `python -X utf8 tl.py show|apply|check NNN [FILE]` (answer files in work/tl/)

## Paths
- Discs: `rom/Black-Matrix 00 (Japan) (Disc 1|2).bin` (gitignored). Tools (gitignored, third-party): tools/pcsx-redux, tools/mkpsxiso-2.30-win64, armips, jpsxdec (Java 8); ffmpeg + xdelta3 on PATH.
- Text: `script/{SCENARIO,SYSTEM,TOWN,EXE,MOVIE}/*.json` (jp beside en); redrawn picture text in script/GFX/*.png. Font/asm hacks: asm/ (halfwidth.asm, savetitle.asm).
- Glossary and rulings: glossary.md; voices: docs/style-reference.md; translator brief: docs/translator-brief*.md; formats: docs/script-format.md, docs/movie-notes.md; design specs and plans: docs/superpowers/.
- Savestates: savestates/ (DuckStation; zstd, RAM at +0x1a62, VRAM at +0x201ddb of the unpacked state).

## Rulings
- Faithful style; honorifics kept (-san, -sama...); "Incest" is the game's term, keep it. Names exactly as in glossary.md (プラン = Plan, not Bran). Full names, no abbreviations.
- ASCII 0x20-0x7E only; 30 chars per window line, 3 lines per window, spill only when meaning needs it. Keep it under ~76 chars to avoid spills.
- Release zip = patches + PATCHING.txt only (no cue files).

## Gotchas
- Close DuckStation before building: mkpsxiso fails with "Cannot open or create output image".
- Cold boot after EXE/asm/font/graphics changes: savestates keep the old program in RAM.
- Town text container is limited to 0x7000 bytes (build.TEXT_BUFFER); the Notebook has ~92 bytes spare, so longer town text must be paid for elsewhere.
- SYSTEM subs 4, 7-10 are code overlays: edit strings in place, never touch their tails.
- Disc 2 DATs and EXE are byte-identical to Disc 1; build copies the patched files. Movies are per disc (work/orig/MOVIE, work/orig2/MOVIE).
- Text is often stored twice (place cards, town copies x28): fix every copy.
- tools/ is gitignored: put reusable helpers at the repo root, or un-ignore a folder for them.

## Status
- v00.9 released (dist/). All text translated on both discs, including picture text and movie subtitles.
- Not yet seen in game: the disc-change screen, the Disc 2 movies (008-010, cards 019-022/029-032), the final stage title card. Movie lines marked "check" in script/MOVIE are unverified.
