# Black/Matrix 00 — English translation

An unofficial English patch for **Black/Matrix 00** (ブラックマトリクス ゼロゼロ), a Japan-only tactical RPG
for the PlayStation, plus every tool used to make it.

| | |
|---|---|
| Platform | PlayStation, 2 discs |
| Serial | SLPS-03573 (Disc 1), SLPS-03574 (Disc 2) |
| Developer / publisher | Flight-Plan / NEC Interchannel |
| Released | 2004, Japan only |
| Patch version | 00.9 |

## The game

Black/Matrix 00 is a grid-based tactical RPG and a prequel in Flight-Plan's *Black/Matrix* series. You follow
Cain, a wingless sixteen-year-old with no memory, looked after by the angel Johannes, into the conflict between
the Church and the demons it hunts.
Between battles you walk around towns, read the Notebook, shop, and can lose an afternoon in the circus
mini-games. The game was never released outside Japan.

## Download and patch

Get `bm00-en-v00.9.zip` from the [Releases](../../releases) page. It holds one xdelta patch per disc, two cue
sheets and `PATCHING.txt`.

The patch contains no game. You need your own images of both discs, identical to these:

| Disc | Size | SHA-1 | CRC32 |
|---|---|---|---|
| 1 | 680,527,680 | `f205c8382149cef508dbfbc79dd35e344ff35337` | `f7c44a85` |
| 2 | 613,655,616 | `bd2e111a087b2dc5cb041a6b7643e6743da281ef` | `ee1e0369` |

Apply each patch to its disc with [Delta Patcher](https://github.com/marco-calautti/DeltaPatcher), xdelta UI,
or `xdelta3`:

```
xdelta3 -d -s "Disc 1.bin" bm00-en-v00.9-disc1.xdelta "Black-Matrix 00 (English) (Disc 1).bin"
xdelta3 -d -s "Disc 2.bin" bm00-en-v00.9-disc2.xdelta "Black-Matrix 00 (English) (Disc 2).bin"
```

Save the output under exactly those names, keep the two `.cue` files from the zip beside them, and open the
`.cue` in your emulator. Full step-by-step instructions are in [PATCHING.txt](PATCHING.txt).

Notes for playing:

- Start from a cold boot. A save state made with the Japanese game keeps the Japanese program in memory.
- Memory-card saves from the Japanese game load fine; unit names are turned into English on load.

## Status

Everything with text in it has been translated, on both discs.

| Part | State |
|---|---|
| Story dialogue (20,756 lines) | Done |
| Menus, items, skills, units, system messages | Done |
| Towns, shops, the Notebook | Done |
| Picture text: menu titles, save screen, name plates, place cards, battle objectives, stage titles, free-battle screens, circus mini-games | Done |
| Movies | English subtitles burned into the video |
| Voices | Japanese, untouched |

The text font was replaced with a half-width one so English fits the original windows.

### How it was translated

The script was translated by an AI model (Anthropic's Claude) working from a glossary and style guide, and
checked by playing the result — not proofread line by line by a fluent Japanese speaker. Expect the meaning to
be right and the occasional line to be stiff or off. Corrections are welcome: each line sits next to its
Japanese in `script/`.

Style choices: faithful rather than localised; honorifics (-san, -sama …) are kept; the game's own term
"Incest" is kept as it is. Names follow [glossary.md](glossary.md).

### Known issues and things not yet seen in play

- The patch was tested in DuckStation through ordinary play, not through a complete playthrough of every
  scene. Report anything that spills out of a window or reads wrong.
- Not yet seen running: the disc-change screen, the Disc 2 movies, and the final stage's title card.
- Movie subtitles were transcribed by ear (speech recognition, then corrected). Lines marked `"check"` in
  `script/MOVIE/` are uncertain.
- Stage title cards slide in as slices of one line, so the letters overlap for a moment before they settle.
- A few Notebook articles are worded tightly: the game keeps town text in a fixed-size buffer.
- A few unused picture leftovers stay Japanese (spare circus HUD pieces, a placeholder title in the
  "BATTLE nn" files).
- The stage cards' small English subtitles are the game's original art and are unchanged (they spell one
  name "Crace"; the dialogue uses "Kreis").

## Building from source

Windows only as it stands (it draws picture text with the fonts in `C:\Windows\Fonts` and calls Windows tool
builds).

Needed:

- Python 3.12 with Pillow
- `tools/mkpsxiso-2.30-win64/` ([mkpsxiso](https://github.com/Lameguy64/mkpsxiso))
- `tools/armips/armips.exe` ([armips](https://github.com/Kingcom/armips))
- `tools/jpsxdec/jpsxdec_v2.0/jpsxdec.jar` ([jPSXdec](https://github.com/m35/jpsxdec)) and Java
- `ffmpeg` on PATH
- `xdelta3` on PATH (only for `release.py`)
- your disc images in `rom/` as `Black-Matrix 00 (Japan) (Disc 1).bin` and `… (Disc 2).bin`

```
python build.py extract     # once: unpack both discs into work/
python build.py             # build/bm00-en.bin + build/bm00-en-disc2.bin
python release.py           # dist/: xdelta patches, cue sheets, zip (each patch is verified)
```

Close the emulator before building: the image cannot be rewritten while it is open.

### Layout

| Path | What |
|---|---|
| `script/` | All text as JSON (Japanese beside English), the redrawn label sheets, movie cues |
| `glossary.md`, `docs/style-reference.md` | Names, terms, character voices |
| `build.py` | Build driver |
| `dat.py`, `town.py`, `tables.py`, `pointers.py`, `exe.py`, `script.py` | Archive and text formats |
| `gfx.py`, `labels.py`, `lz.py` | The game's picture format, redrawn picture text, its compression |
| `movie.py` | Subtitle burning |
| `asm/` | Half-width font hack, save-title routine, unit renaming |
| `tl.py` | Helper for editing translation files |
| `docs/` | Format notes and the design notes written along the way |
| `test_*.py` | Tests (`python test_gfx.py`, …; most need the unpacked discs) |

## Legal

This is an unofficial fan project, not affiliated with or endorsed by Flight-Plan, NEC Interchannel or any
rights holder. Black/Matrix 00 and everything in it belong to their owners. No disc image is distributed
here; the patch is useless without your own copy of the game. Do not sell the patch or distribute pre-patched
images.
