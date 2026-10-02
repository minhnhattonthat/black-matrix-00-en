# Halfwidth Font Hack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Plain ASCII in a script's `en` field renders in-game as 6×12 letters, two per glyph cell.

**Architecture:** An armips patch adds two hooks to the game's glyph-cache miss path; a 2-byte unit whose first byte is below 0x80 is drawn as two 6×12 glyphs composed into one 12×12 cell. Patch code and font live in zero runs of the EXE's SJIS index table. `script.encode` pads ASCII runs to even length and `script.insert` enforces the 23-cell line cap.

**Tech Stack:** Python 3.12 stdlib; armips (downloaded to `tools/armips/`); X11 `6x12` fixed font (public domain); DuckStation for the manual check.

**Spec:** `docs/superpowers/specs/2026-10-02-halfwidth-font-design.md`

## Global Constraints

- `rom/` and `work/orig/` are never modified.
- Pipeline code imports only the Python standard library.
- Patch may write only to: hook site 1 `0x800344fc–0x80034504`, hook site 2 `0x80034638–0x80034640`, and the three table ranges `0x800604a0–0x80060848`, `0x8006087c–0x80060a8c`, `0x8006292c–0x80062c4c`.
- The three table ranges must be all zero in the original EXE; the build checks before patching.
- A line is at most 23 cells (46 bytes). Longer fails the build with the entry ID.
- EXE file offset = address − `0x8000F800`.

Deviation from the spec: `make_font.py` sits at the repo root, not in `tools_py/`. One file does not need a directory.

## Review Focus

1. An ASCII character outside 0x20–0x7E inside a pair (for example a `{09}` escape) must draw as a space, not read outside the font. Covered by `test_compose_out_of_range_is_space` (Task 1) and the same clamp in the ASM (Task 3).
2. An odd-length ASCII run in the middle of a Japanese line must not shift the following Japanese characters off their 2-byte grid. Test in Task 2.
3. A 47-byte line must fail with its ID; a 46-byte line must pass. Test in Task 2.
4. An original Japanese string longer than 23 cells would disprove the slot-count reading of the disassembly. Test in Task 2.
5. The assembled EXE must differ from the original only inside the declared ranges. Test in Task 3.

---

### Task 1: Half font and composition model

**Files:**
- Create: `make_font.py`, `halfwidth.py`, `test_halfwidth.py`, `asm/font6x12.bin` (generated, committed)

**Interfaces:**
- Produces:
  - `asm/font6x12.bin`: 95 glyphs (0x20–0x7E) × 12 bytes, one byte per row, 6 pixels in bits 7..2, bits 1..0 zero.
  - `halfwidth.FONT: Path`
  - `halfwidth.compose(font: bytes, c1: int, c2: int) -> bytes` — the 24-byte 12×12 cell the ASM must produce.

- [ ] **Step 1: Download the source font**

Run:
```bash
mkdir -p work && curl -L -o work/6x12.bdf https://gitlab.freedesktop.org/xorg/font/misc-misc/-/raw/master/6x12.bdf && head -3 work/6x12.bdf
```
Expected: first line `STARTFONT 2.1`. If the URL fails, any copy of the X11 misc-fixed `6x12.bdf` will do; it is public domain.

- [ ] **Step 2: Write the failing test `test_halfwidth.py`**

```python
import halfwidth

FONT = halfwidth.FONT.read_bytes()


def rows(cell):
    return ["".join("#" if cell[2 * y + x // 8] & (0x80 >> (x % 8)) else "." for x in range(12))
            for y in range(12)]


def test_font_has_95_glyphs_in_top_six_bits():
    assert len(FONT) == 95 * 12
    assert all(b & 3 == 0 for b in FONT)
    assert not any(FONT[:12])                       # space is blank
    assert any(FONT[(ord("A") - 0x20) * 12:][:12])  # A is not


def test_compose_puts_left_in_columns_0_5_and_right_in_6_11():
    a = rows(halfwidth.compose(FONT, ord("A"), ord(" ")))
    b = rows(halfwidth.compose(FONT, ord(" "), ord("A")))
    assert any("#" in r for r in a)
    assert all(r[6:] == "......" for r in a)
    assert all(r[:6] == "......" for r in b)
    assert [r[:6] for r in a] == [r[6:] for r in b]


def test_compose_out_of_range_is_space():
    blank = halfwidth.compose(FONT, 0x20, 0x20)
    assert halfwidth.compose(FONT, 0x09, 0x7F) == blank == bytes(24)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
```

- [ ] **Step 3: Run it to see it fail**

Run: `python test_halfwidth.py`
Expected: `ModuleNotFoundError: No module named 'halfwidth'`

- [ ] **Step 4: Write `make_font.py`**

```python
"""Build asm/font6x12.bin from the X11 6x12 BDF font: 95 glyphs (0x20-0x7E),
12 bytes each, one byte per row, pixels in bits 7..2.
Usage: python make_font.py work/6x12.bdf"""
import sys
from pathlib import Path

W, H = 6, 12


def parse(bdf: str) -> dict[int, bytes]:
    lines = iter(bdf.splitlines())
    descent, glyphs = 0, {}
    for line in lines:
        if line.startswith("FONT_DESCENT"):
            descent = int(line.split()[1])
        elif line.startswith("ENCODING"):
            code = int(line.split()[1])
        elif line.startswith("BBX"):
            bw, bh, bx, by = map(int, line.split()[1:])
        elif line == "BITMAP":
            cell = bytearray(H)
            top = H - descent - by - bh          # first cell row the bitmap occupies
            for r in range(bh):
                bits = int(next(lines)[:2], 16) >> bx
                if 0 <= top + r < H:
                    cell[top + r] = bits & 0xFC
            glyphs[code] = bytes(cell)
    return glyphs


if __name__ == "__main__":
    glyphs = parse(Path(sys.argv[1]).read_text(encoding="latin-1"))
    out = b"".join(glyphs[c] for c in range(0x20, 0x7F))
    Path(__file__).parent.joinpath("asm").mkdir(exist_ok=True)
    Path(__file__).parent.joinpath("asm", "font6x12.bin").write_bytes(out)
    print(len(out), "bytes")
```

- [ ] **Step 5: Write `halfwidth.py`**

```python
"""Halfwidth font hack: Python model of the glyph composition done in asm/halfwidth.asm."""
from pathlib import Path

ROOT = Path(__file__).parent
FONT = ROOT / "asm" / "font6x12.bin"


def _glyph(font: bytes, c: int) -> bytes:
    if not 0x20 <= c <= 0x7E:
        c = 0x20
    return font[(c - 0x20) * 12:(c - 0x20) * 12 + 12]


def compose(font: bytes, c1: int, c2: int) -> bytes:
    """12x12 1bpp cell, 2 bytes per row, MSB first: c1 in columns 0-5, c2 in 6-11."""
    out = bytearray()
    for left, right in zip(_glyph(font, c1), _glyph(font, c2)):
        row = (left << 8) | (right << 2)
        out += bytes([row >> 8, row & 0xFF])
    return bytes(out)
```

- [ ] **Step 6: Generate the font and run the tests**

Run: `python make_font.py work/6x12.bdf && python test_halfwidth.py`
Expected: `1140 bytes`, then three `ok` lines.

- [ ] **Step 7: Look at the font**

Render every glyph as text and read it:

```bash
python -c "
import halfwidth
f = halfwidth.FONT.read_bytes()
for base in range(0x20, 0x7F, 16):
    cs = [c for c in range(base, min(base + 16, 0x7F))]
    for y in range(12):
        print(' '.join(''.join('#' if f[(c-0x20)*12+y] & (0x80 >> x) else '.' for x in range(6)) for c in cs))
    print()
"
```
Expected: six blocks of recognisable characters, baseline consistent, nothing clipped at the top or bottom. If glyphs sit too high or low, the `top` formula in `parse` is off by the font's descent; fix it there and regenerate.

- [ ] **Step 8: Commit**

```bash
git add make_font.py halfwidth.py test_halfwidth.py asm/font6x12.bin
git commit -m "Add 6x12 half font and composition model"
```

---

### Task 2: Encoder — ASCII padding and line limits

**Files:**
- Modify: `script.py` (`encode`, `insert`), `test_script.py`, `build.py` (`patch`)

**Interfaces:**
- Consumes: `script.encode`, `script.insert`, `script.extract`.
- Produces:
  - `script.MAX_CELLS = 23`, `script.WINDOW_CELLS = 15`
  - `script.encode(text)` pads each ASCII run to even length with a space.
  - `script.insert` raises `ValueError` naming the ID when an `en` line exceeds `MAX_CELLS * 2` bytes.
  - `script.too_wide(entries: list[dict]) -> list[str]` — IDs whose `en` exceeds `WINDOW_CELLS * 2` bytes.

- [ ] **Step 1: Add the failing tests to `test_script.py`** (above the `__main__` block)

```python
def test_ascii_runs_are_padded_to_even_length():
    assert script.encode("abc") == b"abc "
    assert script.encode("ab") == b"ab"
    assert script.encode("あabcい") == b"\x82\xa0abc \x82\xa2"   # JP stays on its 2-byte grid
    assert script.encode("aあb") == b"a \x82\xa0b "


def test_no_original_string_exceeds_23_cells():
    longest = max(len(t.text) for i, b in SCRIPTS for t in script.tokenize(b) if t.text is not None)
    assert longest <= script.MAX_CELLS * 2, longest


def test_line_over_23_cells_raises_and_23_passes():
    first = script.extract(SCRIPTS[0][1], "S")[0]
    script.insert(SCRIPTS[0][1], [{**first, "en": "x" * 46}])
    assert _insert_raises([{**first, "en": "x" * 47}])


def test_too_wide_lists_lines_past_the_window():
    entries = [{"id": "a", "jp": "", "en": "x" * 30}, {"id": "b", "jp": "", "en": "x" * 31},
               {"id": "c", "jp": "", "en": ""}]
    assert script.too_wide(entries) == ["b"]
```

Also change the existing `test_odd_length_string_keeps_even_alignment`: its last assertion becomes

```python
    assert next(t.text for t in toks if t.text is not None) == b"abc "
```

- [ ] **Step 2: Run to see them fail**

Run: `python test_script.py`
Expected: `AssertionError` in `test_odd_length_string_keeps_even_alignment` (text is still `b"abc"`).

If `test_no_original_string_exceeds_23_cells` fails once the others pass, stop: the 23-slot reading is wrong. Re-read `0x80012e90` (it clears `0x2e` bytes at object+8) and the string-op handlers before continuing.

- [ ] **Step 3: Implement in `script.py`**

Add below `_ESCAPE`:

```python
MAX_CELLS = 23      # glyph slots in the game's text object; it does not bounds-check
WINDOW_CELLS = 15   # cells that fit the dialogue window; tune after an in-game look
_ASCII_RUN = re.compile(r"[\x20-\x7e]+")
```

In `encode`, replace the line `out += part.encode("cp932")` with:

```python
                # two ASCII letters share one glyph cell, so each run must fill whole cells
                part = _ASCII_RUN.sub(lambda m: m.group() + " " * (len(m.group()) % 2), part)
                out += part.encode("cp932")
```

The `{`/`}` check above it must stay ahead of this line.

In `insert`, directly after `data = encode(e["en"])` and its `except` block, add:

```python
                    if len(data) > MAX_CELLS * 2:
                        raise ValueError(f'{e["id"]}: {len(data)} bytes; a line holds {MAX_CELLS * 2}')
```

Add at the end of the file:

```python
def too_wide(entries: list[dict]) -> list[str]:
    """IDs of English lines that fit the text object but overflow the window."""
    return [e["id"] for e in entries if e["en"] and len(encode(e["en"])) > WINDOW_CELLS * 2]
```

- [ ] **Step 4: Print width warnings from the build**

In `build.py`, inside `patch()`, replace the loop body so the entries are loaded once:

```python
    for path in sorted((SCRIPT / "SCENARIO").glob("*.json")):
        i = int(path.stem)
        entries = json.loads(path.read_text(encoding="utf-8"))
        files[i] = script.insert(files[i], entries)
        for wide in script.too_wide(entries):
            print("warning: wider than the window:", wide)
```

- [ ] **Step 5: Run the tests**

Run: `python test_script.py`
Expected: seventeen `ok` lines.

The existing `test_grown_strings_keep_jumps_on_the_same_tokens` appends three fullwidth spaces to every Japanese line. If the 46-byte limit now trips it, change its suffix to one fullwidth space plus nothing else on lines already at 44 bytes or more:

```python
            e["en"] = e["jp"] + ("　　　" if len(script.encode(e["jp"])) <= 40 else "")
```

- [ ] **Step 6: Commit**

```bash
git add script.py test_script.py build.py
git commit -m "Pad ASCII runs to whole cells and enforce the 23-cell line cap"
```

---

### Task 3: ASM patch and build integration

**Files:**
- Create: `asm/halfwidth.asm`, `tools/armips/armips.exe` (downloaded, git-ignored)
- Modify: `halfwidth.py`, `test_halfwidth.py`, `build.py`, `test_build.py`

**Interfaces:**
- Consumes: `build.ORIG`, `build.EXTRACTED`, `asm/font6x12.bin`.
- Produces:
  - `halfwidth.RANGES: list[tuple[int, int]]` — the five address ranges the patch may touch.
  - `halfwidth.assemble(src: Path, dst: Path) -> None` — checks the table ranges are zero in `src`, then runs armips to write `dst`.

- [ ] **Step 1: Get armips**

Download the Windows build of armips v0.11.0 from `https://github.com/Kingcom/armips/releases` and place `armips.exe` at `tools/armips/armips.exe`.

Run: `tools/armips/armips.exe`
Expected: a usage message beginning `armips assembler`.

- [ ] **Step 2: Add the failing tests to `test_halfwidth.py`** (above the `__main__` block)

```python
import tempfile
from pathlib import Path
from build import ORIG

EXE = ORIG / "SLPS_035.73"
BASE = 0x8000F800


def test_table_ranges_are_zero_in_the_original():
    exe = EXE.read_bytes()
    for lo, hi in halfwidth.RANGES[2:]:
        assert not any(exe[lo - BASE:hi - BASE]), hex(lo)


def test_patch_touches_only_declared_ranges():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "patched.exe"
        halfwidth.assemble(EXE, out)
        a, b = EXE.read_bytes(), out.read_bytes()
    assert len(a) == len(b)
    changed = [i + BASE for i in range(len(a)) if a[i] != b[i]]
    assert changed, "patch changed nothing"
    stray = [hex(x) for x in changed if not any(lo <= x < hi for lo, hi in halfwidth.RANGES)]
    assert not stray, stray[:8]


def test_patched_exe_contains_the_font():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "patched.exe"
        halfwidth.assemble(EXE, out)
        b = out.read_bytes()
    assert b[0x800604A0 - BASE:][:768] == FONT[:768]
    assert b[0x8006292C - BASE:][:372] == FONT[768:]
```

- [ ] **Step 3: Run to see them fail**

Run: `python test_halfwidth.py`
Expected: `AttributeError: module 'halfwidth' has no attribute 'RANGES'`

- [ ] **Step 4: Write `asm/halfwidth.asm`**

```
; Halfwidth text for Black/Matrix 00 (SLPS-03573).
; A 2-byte text unit whose first byte is < 0x80 is two ASCII letters drawn
; as 6x12 glyphs into one 12x12 cell. See docs/superpowers/specs/2026-10-02-halfwidth-font-design.md
; Assembled by halfwidth.assemble(); paths are relative to the repo root.

.psx
.open "work/orig/SLPS_035.73", "work/halfwidth.exe", 0x8000F800

; ---- hook 1: glyph cache miss, before the SJIS index lookup ----------------
; original:  lbu v0,0(a1) / lhu v1,0xe(a2)
.org 0x800344FC
    j     hw_lookup
    lbu   v0, 0(a1)            ; delay slot: first displaced instruction

; ---- hook 2: bitmap pointer s1 is set, expansion about to start ------------
; original:  sltu t5,zero,s4 / addiu a2,zero,3
.org 0x80034638
    j     hw_glyph
    sltu  t5, zero, s4         ; delay slot: first displaced instruction

; ---- font, glyphs 0x20-0x5F ------------------------------------------------
.org 0x800604A0
.area 0x80060848 - 0x800604A0
hw_font_lo:
    .incbin "asm/font6x12.bin", 0, 768
.endarea

; ---- font, glyphs 0x60-0x7E, and the scratch cell ---------------------------
.org 0x8006292C
.area 0x80062C4C - 0x8006292C
hw_font_hi:
    .incbin "asm/font6x12.bin", 768, 372
.align 4
hw_cell:
    .fill 24
.endarea

; ---- code ------------------------------------------------------------------
.org 0x8006087C
.area 0x80060A8C - 0x8006087C

hw_lookup:
    sltiu t8, v0, 0x80
    bne   t8, zero, @@ascii
    lhu   v1, 0xE(a2)          ; delay slot: second displaced instruction
    j     0x80034504
    nop
@@ascii:
    mflo  a0                   ; the original does this at 0x80034508
    addu  s6, v1, a0           ;   and this at 0x80034510
    j     0x80034600           ; "index found" path
    li    a0, 0                ; index - 1; the pointer it yields is replaced in hw_glyph

; a0 = character -> v0 = address of its 12 glyph bytes. Clobbers a0, t8, t9.
hw_glyph_ptr:
    addiu a0, a0, -0x20
    sltiu t9, a0, 0x5F
    beq   t9, zero, @@space    ; outside 0x20-0x7E
    sltiu t9, a0, 0x40
    sll   t8, a0, 1
    addu  t8, t8, a0
    beq   t9, zero, @@high
    sll   t8, t8, 2            ; delay slot: t8 = index * 12
    la    v0, hw_font_lo
    jr    ra
    addu  v0, v0, t8
@@high:
    la    v0, hw_font_hi - 0x40 * 12
    jr    ra
    addu  v0, v0, t8
@@space:
    la    v0, hw_font_lo
    jr    ra
    nop

; s7 = 16-bit character code. ra was saved by the function prologue and is
; reloaded before its return, so calling from here is safe.
hw_glyph:
    andi  t8, s7, 0x8000
    bne   t8, zero, @@done     ; Shift-JIS: keep the game's glyph
    nop
    jal   hw_glyph_ptr
    srl   a0, s7, 8            ; delay slot: left character
    move  a3, v0
    jal   hw_glyph_ptr
    andi  a0, s7, 0xFF         ; delay slot: right character
    la    s1, hw_cell
    move  t0, s1
    li    t1, 12
@@row:
    lbu   t2, 0(a3)            ; left:  pixels in bits 7..2
    lbu   t3, 0(v0)            ; right: pixels in bits 7..2
    addiu a3, a3, 1
    addiu v0, v0, 1
    srl   t4, t3, 6
    or    t2, t2, t4
    sb    t2, 0(t0)            ; columns 0-7
    sll   t3, t3, 2
    sb    t3, 1(t0)            ; columns 8-11
    addiu t1, t1, -1
    bne   t1, zero, @@row
    addiu t0, t0, 2
@@done:
    j     0x80034640
    addiu a2, zero, 3          ; delay slot: second displaced instruction

.endarea
.close
```

- [ ] **Step 5: Add `RANGES` and `assemble` to `halfwidth.py`**

Change the imports at the top to:

```python
import shutil, subprocess
from pathlib import Path
```

Add at the end:

```python
BASE = 0x8000F800                      # address - BASE = offset in the EXE file
RANGES = [
    (0x800344FC, 0x80034504),          # hook 1
    (0x80034638, 0x80034640),          # hook 2
    (0x800604A0, 0x80060848),          # font 0x20-0x5F   } zero runs of the SJIS
    (0x8006087C, 0x80060A8C),          # code             } index table: codes no
    (0x8006292C, 0x80062C4C),          # font 0x60-0x7E   } glyph in the font uses
]
ARMIPS = ROOT / "tools" / "armips" / "armips.exe"


def assemble(src: Path, dst: Path) -> None:
    exe = src.read_bytes()
    for lo, hi in RANGES[2:]:
        if any(exe[lo - BASE:hi - BASE]):
            raise ValueError(f"patch range {lo:#x}-{hi:#x} is not empty in {src}")
    # the .asm reads work/orig and writes work/halfwidth.exe
    subprocess.run([ARMIPS, "asm/halfwidth.asm"], cwd=ROOT, check=True)
    shutil.move(ROOT / "work" / "halfwidth.exe", dst)
```

`assemble` takes `src` only to check it: the `.asm` file names its own input, which is the same `work/orig/SLPS_035.73`.

- [ ] **Step 6: Run the tests**

Run: `python test_halfwidth.py`
Expected: six `ok` lines.

If armips rejects a directive, check its readme in `tools/armips/` for the v0.11 spelling (`.incbin "file", start, size`; `.area size` / `.endarea`; `.fill length`) and fix the `.asm`. If `test_patch_touches_only_declared_ranges` reports stray bytes, a `.org` or `.area` is wrong.

- [ ] **Step 7: Check the assembled code against the model**

Disassemble the code range of the patched EXE and read it once against the listing above, looking only at branch targets and delay slots:

```bash
python -c "
import tempfile, halfwidth
from pathlib import Path
from build import ORIG
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
with tempfile.TemporaryDirectory() as d:
    out = Path(d) / 'p.exe'; halfwidth.assemble(ORIG / 'SLPS_035.73', out); b = out.read_bytes()
md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
for lo, n in ((0x800344FC, 8), (0x80034638, 8), (0x8006087C, 240)):
    for i in md.disasm(b[lo - halfwidth.BASE:lo - halfwidth.BASE + n], lo):
        print(f'{i.address:08x} {i.mnemonic} {i.op_str}')
    print()
"
```
Expected: the two hook sites show `j 0x8006087c` and `j <hw_glyph>` with the displaced instruction in each delay slot; `la` expands to `lui`/`addiu` pairs, none of them in a delay slot.

- [ ] **Step 8: Wire into `build.py`**

Add `import halfwidth` to the imports. At the end of `patch()` add:

```python
    halfwidth.assemble(ORIG / "SLPS_035.73", EXTRACTED / "SLPS_035.73")
```

In `test_build.py`, restore the EXE as well so the identity test still describes an unpatched build. Replace the `shutil.copy2` line with:

```python
    for name in ("SCENARIO.DAT", "SLPS_035.73"):          # undo any patch
        shutil.copy2(build.ORIG / name, build.EXTRACTED / name)
```

- [ ] **Step 9: Run the whole suite**

Run: `python test_dat.py && python test_script.py && python test_halfwidth.py && python test_build.py`
Expected: every line `ok`.

- [ ] **Step 10: Commit**

```bash
git add asm/halfwidth.asm halfwidth.py test_halfwidth.py build.py test_build.py
git commit -m "Add halfwidth glyph patch and assemble it in the build"
```

---

### Task 4: English on screen

**Files:**
- Modify: `script/SCENARIO/000.json`

**Interfaces:**
- Consumes: `python build.py`.

- [ ] **Step 1: Set the test lines**

The boot warning is shown by one randomly chosen character; each variant is three or four lines in `script/SCENARIO/000.json`. Set `en` by what the Japanese line contains, in every variant:

| `jp` contains | `en` |
|---|---|
| `部屋を明るく` | `Keep the room bright!` |
| `ゲーム` | `ABCDEFGHIJKLMNOPQRSTUVWXYZ0123` |
| `テレビ` | `abcdefghijklmnopqrstuvwxyz4567` |

```bash
python -c "
import json
from pathlib import Path
p = Path('script/SCENARIO/000.json')
e = json.loads(p.read_text(encoding='utf-8'))
for x in e:
    for key, en in (('部屋を明るく', 'Keep the room bright!'),
                    ('ゲーム', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123'),
                    ('テレビ', 'abcdefghijklmnopqrstuvwxyz4567')):
        if key in x['jp']:
            x['en'] = en
p.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding='utf-8')
print(sum(1 for x in e if x['en']), 'lines set')
"
```
Expected: a count of 20 or more. Lines without a match stay Japanese, which doubles as the check that Japanese still renders.

- [ ] **Step 2: Build**

Run: `python build.py`
Expected: no `warning:` lines (30 bytes is exactly the window constant), then the path of `build\bm00-en.bin`.

- [ ] **Step 3: Manual check in DuckStation (user)**

Load `build/bm00-en.cue`. Report:

1. Do the three English lines appear in small letters, every letter and digit legible?
2. Is any remaining Japanese line in the warning still correct?
3. Does the 30-character line fit the window, and how much room is left?
4. Does the game continue to the title and through the opening as before?

Garbage or `＊` where English should be means hook 1 is not taken; letters in the wrong half or sheared means the row formula or bit order is off; a hang means a displaced instruction is wrong. Each of those points back to Task 3 Step 7.

- [ ] **Step 4: Tune the window constant**

From the answer to question 3, set `script.WINDOW_CELLS` to the number of cells that fit, and adjust `test_too_wide_lists_lines_past_the_window` to the new boundary.

Run: `python test_script.py`
Expected: all `ok`.

- [ ] **Step 5: Commit**

```bash
git add script/SCENARIO/000.json script.py test_script.py
git commit -m "Halfwidth English test lines in the boot warning"
```
