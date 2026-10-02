# Halfwidth Font Hack — Design

Date: 2026-10-02
Parent spec: `2026-10-02-black-matrix-00-translation-design.md` (phase 3)

## Goal

Plain ASCII in a script's `en` field renders in-game as 6×12 pixel letters, two per glyph cell, so a dialogue line holds up to 46 characters instead of 23.

Success: the boot warning reads `Keep the room bright!` in halfwidth letters, every ASCII character 0x20–0x7E is legible, and Japanese text elsewhere is unchanged.

## How the game draws text (from disassembly)

- A line of text is an object with **23 glyph slots**. `0x80013ae4` walks the string two bytes at a time, stops when the first byte of a pair is zero, and stores one glyph id per pair.
- `0x80034384(font_id, char_ptr)` returns the glyph id. It searches a glyph cache keyed by the 16-bit code `(byte0 << 8) | byte1`; on a miss it rasterises the glyph into a free cache cell in VRAM at (960, 0), cells 16×16.
- Miss path, at `0x80034494`: the code is turned into an index through a u16 table in the EXE at `0x8005ff48` (0 means missing, which falls back to `＊`, code `0x8196`). At `0x80034600` the glyph pointer becomes `font_data + 24 × (index − 1)`. From `0x80034638` a loop expands the 1bpp bitmap, most significant bit first, two bytes per row.
- Register `s7` holds the 16-bit code throughout the miss path; `s1` holds the bitmap pointer during expansion.
- The font is in `SYSTEM.DAT` at archive offset `0xa7dc`: magic `BIT`, 12×12, 1bpp, 24 bytes per glyph, 1952 glyphs. It lacks `Ｑ ｂ ｑ ｚ`, which is why fullwidth English is not an option.

## Approach: pair cells

Treat a 2-byte unit whose first byte is below 0x80 as two ASCII characters and draw both into one 12×12 cell. The cache, advance, and draw code are untouched: they only see a 16-bit code and a bitmap.

Rejected: a proportional font through the advance function (keeps the 23-character cap), and adding the missing fullwidth glyphs only (15 characters per window line).

## Components

### ASM patch — `asm/halfwidth.asm` (armips)

Two hooks in the miss path:

1. **At `0x800344fc`** (start of the index lookup). If the first byte is below 0x80, skip the table lookup and continue at `0x80034600` with index − 1 = 0. Otherwise run the two displaced instructions and return. Without this hook an ASCII pair would index outside the table and usually land in the `＊` fallback.
2. **At `0x80034638`** (after the bitmap pointer is set). If `s7 < 0x8000`, compose the cell into a 24-byte scratch buffer and point `s1` at it. Then run the displaced instructions and return.

Composition, per row `y` of 12: `row = (left[y] << 8) | (right[y] << 2)`, stored high byte first, where `left` and `right` are the 6×12 glyphs of the two characters (6 pixels in the top bits of each byte). A character outside 0x20–0x7E draws as a space.

Neither hook site is a branch target from elsewhere except `0x80034600`, which is entered, not replaced.

### Half font — `asm/font6x12.bin`

95 glyphs (0x20–0x7E) × 12 bytes. Built once by `tools_py/make_font.py` from the public-domain X11 `6x12` fixed font and committed, so glyphs can be hand-edited later.

### Where the patch lives in the EXE

The EXE has no free tail: its last bytes are gp-relative variables and memory after it is bss. The SJIS index table, however, has runs of zero entries for codes that no font glyph uses. The patch goes into those runs:

| Address range | Bytes | Use |
|---|---|---|
| `0x800604a0–0x80060848` | 936 | font glyphs 0x20–0x5F (768 bytes) |
| `0x8006292c–0x80062c4c` | 800 | font glyphs 0x60–0x7E (372 bytes) and the 24-byte scratch buffer |
| `0x8006087c–0x80060a8c` | 528 | code |

The cost: a Japanese character from those unused code ranges would get a garbage glyph instead of `＊`. No script string uses them. The build asserts that every range is all zero in the original EXE before patching.

### Encoder — `script.py`

- Each run of ASCII in `en` is padded with one space to an even byte count. Pairs then stay cell-aligned, a mixed Japanese/ASCII line works, and the zero-word terminator rule holds without a pad byte.
- A line longer than 23 cells (46 bytes) fails the build with its ID: the text object has 23 slots and the game does not check.
- A line longer than the window width is a warning listing its ID. The width constant starts at 15 cells and is corrected after the first in-game look.
- `{XX}` escapes are unchanged.

### Build — `build.py`

`patch()` also assembles `asm/halfwidth.asm` against a copy of `work/orig/SLPS_035.73` and writes the result to `work/extracted/SLPS_035.73`. armips is downloaded into `tools/armips/`.

## Testing

- **Encoder**: unit tests for padding, the 23-cell error, and that a padded line still tokenizes.
- **Composition model**: a Python function that mirrors the ASM's row formula, tested against `font6x12.bin` (an `A` on the left and `B` on the right produce the expected 12-pixel rows). This catches bit-order mistakes before the emulator does.
- **Patched EXE**: a test that the assembled EXE differs from the original only at the two hook sites and inside the three declared ranges.
- **In-game (user)**: boot warning in halfwidth English; a line containing every printable ASCII character; a Japanese line still correct; a menu or save screen to see whether other text paths behave.

## Out of scope and known limits

- Fixed 6-pixel pitch, not proportional.
- Each window line remains its own string. Adding lines to a window is a translation-phase problem.
- Whether menu and battle text accept ASCII is confirmed only when those files become extractable. They use the same glyph function, so the hack should apply.
- Unknown until tested: whether the dialogue code inspects characters itself (name substitution, typewriter timing). If it does, the plan gains a task; the design here does not change.
