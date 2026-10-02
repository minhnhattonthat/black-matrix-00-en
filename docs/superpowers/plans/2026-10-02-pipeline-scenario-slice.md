# Pipeline + SCENARIO.DAT Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One command rebuilds a bootable disc image in which any `SCENARIO.DAT` string can be replaced by a longer one, proven by one English line on screen.

**Architecture:** Stdlib-only Python at repo root. `dat.py` unpacks/repacks archives in memory, `script.py` tokenizes the script bytecode so strings can change length and absolute jump offsets are remapped, `build.py` drives dumpsxiso/mkpsxiso. Tests are plain `test_*.py` files run with `python test_x.py`.

**Tech Stack:** Python 3.12 stdlib; `tools/mkpsxiso-2.30-win64` (dumpsxiso/mkpsxiso); `capstone` (pip, reverse-engineering only, never imported by the pipeline); DuckStation for the manual boot check.

**Spec:** `docs/superpowers/specs/2026-10-02-black-matrix-00-translation-design.md`

## Scope

This plan covers spec phases 1–2 for `SCENARIO.DAT` only. Exploration showed the other archives do not share its text format:

| Archive | Text format seen | Plan |
|---|---|---|
| SCENARIO.DAT | script bytecode, string ops `1050 1081 105b 108a 108f` | this plan |
| TOWN.DAT | different container, strings preceded by `0100` | later plan |
| SYSTEM.DAT | tables (sub-file 2 holds ~1100 strings) | later plan |
| BATTLE.DAT, EVENT.DAT | nested containers, scattered strings | later plan |
| Font hack, translation | depend on this plan's findings | later plans |

Deviations from the spec, both simplifications:

- No `work/unpacked/` directory. Sub-files are handled in memory.
- Script JSON lives at `script/SCENARIO/NNN.json`, one file per sub-file, each entry holding both `jp` and `en`. The spec's separate `jp/` and `en/` trees would duplicate IDs for no gain.

## Global Constraints

- `rom/` is never modified.
- Pipeline code imports only the Python standard library.
- JSON entry shape: `{"id": ..., "jp": ..., "en": ...}`. Empty `en` keeps the Japanese.
- Every extract→insert of unmodified Japanese is byte-identical.
- `rom/`, `work/`, `build/`, `tools/` stay git-ignored.

## Known format facts

**Archive** (`*.DAT`), verified byte-identical round-trip on all five:

- `u32 count`, `u32 11` (sector shift), then `count` × (`u16 sector_offset`, `u16 sector_count`), zero-padded to one 2048-byte sector.
- Sub-files follow contiguously from sector 1. Empty entries carry the running offset and count 0.

**SCENARIO script** (partly known; Task 3 completes it):

- A stream of little-endian u16 words. Not 4-byte aligned.
- String ops `0x1050 0x1081 0x105b 0x108a 0x108f`: the op word, then Shift-JIS bytes, then zero terminator, padded to even length. Every original string has even length and is followed by `00 00`.
- Absolute jump targets are u32 byte offsets from the sub-file start. Seen so far: `0002 0000 <u32>` (conditional jump), `0003 0000 <u32>` (goto), `000a 0000 <u32>` (call), `1082 <u32>` (menu choice target).
- `0001` is a push whose length depends on its second word (`0001 0000 <u32>` immediate; `0001 0003 ...` longer). `0003 <nonzero>` looks like an operator with no operand.
- About 940 strings are preceded by `0000` rather than a known string op. Their owning op is unknown.
- The script's used bytes are followed by zero padding to the sector boundary.

## Review Focus

1. A string holding bytes that are not valid cp932 (control codes, e.g. the `81 f4` seen after some strings) must survive extract→insert unchanged. Test in Task 4.
2. An `en` value with a character cp932 cannot encode must fail the build with the entry's ID, not write a `?`. Test in Task 4.
3. An archive that grows past the u16 sector range, or whose table outgrows one sector, must raise, not wrap. Test in Task 1.
4. A jump whose target is not a token start must raise at insert time, not produce a script that crashes mid-game. Test in Task 4.
5. An odd-length English string (halfwidth, future plan) must still leave the next token on an even offset. Test in Task 4.

---

### Task 1: `dat.py` — archive unpack/repack

**Files:**
- Create: `dat.py`, `test_dat.py`, `build.py`

**Interfaces:**
- Produces: `dat.unpack(data: bytes) -> list[bytes]`, `dat.pack(files: list[bytes]) -> bytes`, `build.py extract` (fills `work/extracted/` and `work/orig/`), constants `build.ARCHIVES`, `build.ORIG`, `build.EXTRACTED`.

- [ ] **Step 1: Write `build.py` with the `extract` command**

```python
"""Build driver. Usage: python build.py extract | python build.py"""
import shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent
ROM = ROOT / "rom" / "Black-Matrix 00 (Japan) (Disc 1).bin"
MKPSXISO = ROOT / "tools" / "mkpsxiso-2.30-win64"
EXTRACTED = ROOT / "work" / "extracted"   # tree mkpsxiso builds from; DATs get overwritten
ORIG = ROOT / "work" / "orig"             # pristine copies of files we patch
BUILD = ROOT / "build"
ARCHIVES = ["SCENARIO.DAT", "TOWN.DAT", "EVENT.DAT", "SYSTEM.DAT", "BATTLE.DAT"]


def extract():
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    subprocess.run([MKPSXISO / "dumpsxiso.exe", "-x", EXTRACTED,
                    "-s", EXTRACTED / "layout.xml", ROM], check=True)
    ORIG.mkdir(exist_ok=True)
    for name in ARCHIVES + ["SLPS_035.73"]:
        shutil.copy2(EXTRACTED / name, ORIG / name)


if __name__ == "__main__":
    if sys.argv[1:] == ["extract"]:
        extract()
    else:
        sys.exit("usage: python build.py extract")
```

- [ ] **Step 2: Run extract**

Run: `python build.py extract`
Expected: ends with `ISO image dumped successfully.`; `work/orig/` holds six files.

- [ ] **Step 3: Write the failing test `test_dat.py`**

```python
import dat
from build import ARCHIVES, ORIG


def test_roundtrip_all_archives():
    for name in ARCHIVES:
        data = (ORIG / name).read_bytes()
        assert dat.pack(dat.unpack(data)) == data, name


def test_grown_subfile_shifts_later_offsets():
    files = dat.unpack((ORIG / "SCENARIO.DAT").read_bytes())
    files[0] += b"\x01" * 5000            # grows by 3 sectors
    again = dat.unpack(dat.pack(files))
    assert again[0].rstrip(b"\0") == files[0].rstrip(b"\0")
    assert again[1:] == files[1:]


def test_too_many_files_raises():
    try:
        dat.pack([b""] * 511)             # 8 + 4*511 > 2048
    except ValueError:
        return
    assert False, "expected ValueError"


def test_sector_overflow_raises():
    try:
        dat.pack([bytes(2048 * 40000), bytes(2048 * 40000)])
    except ValueError:
        return
    assert False, "expected ValueError"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
```

- [ ] **Step 4: Run it to see it fail**

Run: `python test_dat.py`
Expected: `ModuleNotFoundError: No module named 'dat'`

- [ ] **Step 5: Write `dat.py`**

```python
"""Black/Matrix 00 .DAT archive: u32 count, u32 sector shift (11),
count x (u16 sector offset, u16 sector count), padded to one sector."""
import struct

SECTOR = 2048


def unpack(data: bytes) -> list[bytes]:
    count, shift = struct.unpack_from("<II", data)
    if shift != 11:
        raise ValueError(f"unexpected sector shift {shift}")
    files = []
    for i in range(count):
        off, size = struct.unpack_from("<HH", data, 8 + 4 * i)
        files.append(data[off * SECTOR:(off + size) * SECTOR])
    return files


def pack(files: list[bytes]) -> bytes:
    if 8 + 4 * len(files) > SECTOR:
        raise ValueError(f"{len(files)} entries do not fit the one-sector table")
    header = bytearray(struct.pack("<II", len(files), 11))
    body = bytearray()
    off = 1
    for i, f in enumerate(files):
        size = -(-len(f) // SECTOR)
        if off + size > 0xFFFF:
            raise ValueError(f"entry {i}: archive exceeds the u16 sector range")
        header += struct.pack("<HH", off, size)
        body += f.ljust(size * SECTOR, b"\0")
        off += size
    return bytes(header.ljust(SECTOR, b"\0")) + bytes(body)
```

- [ ] **Step 6: Run the tests**

Run: `python test_dat.py`
Expected: four `ok` lines.

- [ ] **Step 7: Commit**

```bash
git add dat.py test_dat.py build.py
git commit -m "Add DAT archive unpack/repack and disc extract"
```

---

### Task 2: `build.py` — rebuild the disc image

**Files:**
- Modify: `build.py`
- Create: `test_build.py`

**Interfaces:**
- Consumes: `build.EXTRACTED`, `build.BUILD`, `build.MKPSXISO`, `build.ROM`.
- Produces: `build.make_iso() -> Path` (path of the built `.bin`), run by `python build.py`.

- [ ] **Step 1: Write the failing test `test_build.py`**

```python
import hashlib
import build


def sha(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def test_unmodified_rebuild_matches_original():
    out = build.make_iso()
    assert out.stat().st_size == build.ROM.stat().st_size
    assert sha(out) == sha(build.ROM)


if __name__ == "__main__":
    test_unmodified_rebuild_matches_original()
    print("ok")
```

- [ ] **Step 2: Run it to see it fail**

Run: `python test_build.py`
Expected: `AttributeError: module 'build' has no attribute 'make_iso'`

- [ ] **Step 3: Add `make_iso` to `build.py`**

Add above the `__main__` block:

```python
def make_iso() -> Path:
    BUILD.mkdir(exist_ok=True)
    out = BUILD / "bm00-en.bin"
    # cwd is the dump dir: layout.xml refers to its files by relative path
    subprocess.run([MKPSXISO / "mkpsxiso.exe", "-y", "-o", out,
                    "-c", BUILD / "bm00-en.cue", "layout.xml"],
                   cwd=EXTRACTED, check=True)
    return out
```

Replace the `__main__` block with:

```python
if __name__ == "__main__":
    if sys.argv[1:] == ["extract"]:
        extract()
    elif not sys.argv[1:]:
        print(make_iso())
    else:
        sys.exit("usage: python build.py [extract]")
```

- [ ] **Step 4: Run the test**

Run: `python test_build.py`
Expected: `ok`.

If the size matches but the hash differs, compare the two images in 2352-byte sectors and list the differing sector numbers. Differences confined to sectors 0–15 (system area/license) or to EDC/ECC bytes are acceptable: change the assertion to compare only the 2048-byte user data of sectors 16 onward, and note the reason in a comment. Any difference in file data is a real bug in the layout XML.

- [ ] **Step 5: Manual boot check**

Load `build/bm00-en.cue` in DuckStation. Expected: the game reaches the title screen.

- [ ] **Step 6: Commit**

```bash
git add build.py test_build.py
git commit -m "Rebuild disc image with mkpsxiso"
```

---

### Task 3: Reverse-engineer the script VM; `script.tokenize`

This task discovers the one thing this plan cannot pre-write: the length and jump operands of every opcode. The test below is fixed; the opcode table is the deliverable.

**Files:**
- Create: `script.py`, `test_script.py`, `docs/script-format.md`

**Interfaces:**
- Consumes: `dat.unpack`, `build.ORIG`.
- Produces:

```python
@dataclass
class Token:
    off: int                 # byte offset in the original sub-file
    raw: bytes               # the whole token: op, operands, string, terminator, padding
    text: bytes | None       # string payload (no terminator) for string tokens, else None
    jumps: tuple[int, ...]   # offsets within raw of u32 absolute jump operands

script.used_length(b: bytes) -> int      # length without the trailing zero padding, rounded up to even
script.tokenize(b: bytes) -> list[Token] # raises ValueError(f"unknown op {op:#06x} at {off:#x}")
```

- [ ] **Step 1: Write the failing test `test_script.py`**

```python
import struct
import dat, script
from build import ORIG

SCRIPTS = [(i, b) for i, b in enumerate(dat.unpack((ORIG / "SCENARIO.DAT").read_bytes())) if b]


def test_every_script_tokenizes_exactly():
    for i, b in SCRIPTS:
        toks = script.tokenize(b)
        assert b"".join(t.raw for t in toks) == b[:script.used_length(b)], i
        pos = 0
        for t in toks:
            assert t.off == pos, (i, hex(pos))
            pos += len(t.raw)


def test_every_jump_lands_on_a_token():
    for i, b in SCRIPTS:
        toks = script.tokenize(b)
        starts = {t.off for t in toks} | {script.used_length(b)}
        for t in toks:
            for j in t.jumps:
                target = struct.unpack_from("<I", t.raw, j)[0]
                assert target in starts, (i, hex(t.off), hex(target))


def test_every_japanese_run_is_inside_a_string_token():
    import re
    kana = re.compile(rb"(?:\x82[\x9f-\xf1]|\x83[\x40-\x96]){3,}")
    for i, b in SCRIPTS:
        for t in script.tokenize(b):
            if t.text is None:
                assert not kana.search(t.raw), (i, hex(t.off))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
```

The third test is what forces the ~940 `0000`-preceded strings to be explained rather than swallowed as operands.

- [ ] **Step 2: Run it to see it fail**

Run: `python test_script.py`
Expected: `ModuleNotFoundError: No module named 'script'`

- [ ] **Step 3: Write the `script.py` skeleton with the known facts**

```python
"""SCENARIO script bytecode: tokenize, extract strings, reinsert with jump fixups.
Format notes: docs/script-format.md"""
import struct
from dataclasses import dataclass

STRING_OPS = {0x1050, 0x1081, 0x105B, 0x108A, 0x108F}


@dataclass
class Token:
    off: int
    raw: bytes
    text: bytes | None = None
    jumps: tuple[int, ...] = ()


def used_length(b: bytes) -> int:
    return (len(b.rstrip(b"\0")) + 1) & ~1


def _string_end(b: bytes, p: int) -> int:
    """Offset of the terminating zero byte of the Shift-JIS string at p."""
    while b[p]:
        p += 2 if (0x81 <= b[p] <= 0x9F or 0xE0 <= b[p] <= 0xFC) else 1
    return p


def _token_at(b: bytes, p: int) -> Token:
    op, sub = struct.unpack_from("<HH", b, p)
    if op in STRING_OPS:
        end = _string_end(b, p + 2)
        return Token(p, b[p:(end + 2) & ~1], text=b[p + 2:end])
    if op == 0x0002 and sub == 0:
        return Token(p, b[p:p + 8], jumps=(4,))
    if op == 0x0003 and sub == 0:
        return Token(p, b[p:p + 8], jumps=(4,))
    if op == 0x000A and sub == 0:
        return Token(p, b[p:p + 8], jumps=(4,))
    if op == 0x1082:
        return Token(p, b[p:p + 6], jumps=(2,))
    raise ValueError(f"unknown op {op:#06x} at {p:#x}")


def tokenize(b: bytes) -> list[Token]:
    end = used_length(b)
    toks, p = [], 0
    while p < end:
        t = _token_at(b, p)
        toks.append(t)
        p += len(t.raw)
    return toks
```

`(end + 2) & ~1` covers the terminator plus padding: an even-length string is followed by two zero bytes, an odd-length one by one.

- [ ] **Step 4: Run the test; it fails on the first unknown op**

Run: `python test_script.py`
Expected: `ValueError: unknown op 0x0001 at 0x0`

- [ ] **Step 5: Find the interpreter in the executable**

Run: `pip install capstone`

`work/orig/SLPS_035.73` is a PS-X EXE: 0x800-byte header, code loaded at `0x80010000` (so file offset = address − 0x80010000 + 0x800). Save this as `re_find.py` in the scratchpad, not the repo:

```python
import struct, sys
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

exe = open(sys.argv[1], "rb").read()
code, base = exe[0x800:], 0x80010000
md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
wanted = {0x1050, 0x1081, 0x105B, 0x1082, 0x1000, 0x0FFF}
for off in range(0, len(code), 4):
    for ins in md.disasm(code[off:off + 4], base + off):
        if ins.mnemonic in ("addiu", "ori", "andi", "slti", "sltiu", "li"):
            imm = ins.op_str.split(",")[-1].strip()
            try:
                if int(imm, 0) & 0xFFFF in wanted:
                    print(f"{ins.address:08x} {ins.mnemonic} {ins.op_str}")
            except ValueError:
                pass
```

Run: `python re_find.py work/orig/SLPS_035.73`

Look for the dispatcher: code that reads a u16 through a script pointer (`lhu`), masks or range-checks it against `0x1000`, shifts left by 2, loads from a table (`lw`), and `jr`s. Disassemble around each hit with the same `md.disasm` call over a wider range. The table it indexes holds one handler address per opcode; dump it with `struct.unpack`.

- [ ] **Step 6: Read each handler for its operand length**

For every handler, record how far it advances the script pointer and whether it stores an operand into the script pointer (a jump). Handlers that call a shared "evaluate expression" routine take their arguments from the push tokens (`0001 ...`) that precede them and have no inline operands. Check the string-op handlers for how the terminator is detected (byte or u16) and how the pointer is realigned afterwards.

Write the result to `docs/script-format.md`: one table row per opcode with columns op, name (your label), total length in bytes, jump operand offsets, notes. Include how `0000`-preceded strings are owned, and whether the terminator test is byte-wise.

- [ ] **Step 7: Extend `_token_at` from the table until the tests pass**

Add one branch (or a `LENGTHS: dict[int, int]` lookup for fixed-length ops) per documented opcode. Do not add a catch-all default length: an unknown op must keep raising.

Run: `python test_script.py`
Expected: three `ok` lines.

- [ ] **Step 8: Commit**

```bash
git add script.py test_script.py docs/script-format.md
git commit -m "Tokenize SCENARIO script bytecode"
```

---

### Task 4: `script.py` — extract and insert strings

**Files:**
- Modify: `script.py`, `test_script.py`

**Interfaces:**
- Consumes: `script.tokenize`, `script.Token`, `script.used_length`.
- Produces:

```python
script.decode(raw: bytes) -> str     # cp932 text; undecodable bytes become {XX}
script.encode(text: str) -> bytes    # inverse; raises ValueError on unencodable characters
script.extract(b: bytes, prefix: str) -> list[dict]   # [{"id": f"{prefix}/{off:05x}", "jp": str, "en": ""}]
script.insert(b: bytes, entries: list[dict]) -> bytes # rebuilt sub-file, sector-padded like the input
```

- [ ] **Step 1: Add the failing tests to `test_script.py`** (above the `__main__` block)

```python
def test_decode_encode_keeps_odd_bytes():
    raw = b"\x82\xa0\x81\xf4\x05\x82\xa2{"
    assert script.encode(script.decode(raw)) == raw
    assert "{" not in script.decode(b"\x82\xa0")


def test_encode_rejects_unencodable_text():
    try:
        script.encode("café ☃")
    except ValueError:
        return
    assert False, "expected ValueError"


def test_extract_insert_is_byte_identical():
    for i, b in SCRIPTS:
        assert script.insert(b, script.extract(b, f"SCENARIO/{i:03d}")) == b, i


def test_grown_strings_keep_jumps_on_the_same_tokens():
    for i, b in SCRIPTS:
        entries = script.extract(b, f"SCENARIO/{i:03d}")
        for e in entries:
            e["en"] = e["jp"] + "　　　"     # three fullwidth spaces
        old, new = script.tokenize(b), script.tokenize(script.insert(b, entries))
        assert len(old) == len(new), i
        moved = {o.off: n.off for o, n in zip(old, new)}
        moved[script.used_length(b)] = new[-1].off + len(new[-1].raw)
        for o, n in zip(old, new):
            for j in o.jumps:
                was = struct.unpack_from("<I", o.raw, j)[0]
                now = struct.unpack_from("<I", n.raw, j)[0]
                assert now == moved[was], (i, hex(o.off))


def test_odd_length_string_keeps_even_alignment():
    i, b = SCRIPTS[0]
    entries = script.extract(b, "S")
    entries[0]["en"] = "abc"
    for t in script.tokenize(script.insert(b, entries)):
        assert t.off % 2 == 0


def test_jump_to_non_token_raises():
    i, b = SCRIPTS[0]
    t = next(t for t in script.tokenize(b) if t.jumps)
    bad = bytearray(b)
    struct.pack_into("<I", bad, t.off + t.jumps[0], 1)   # offset 1 is never a token start
    try:
        script.insert(bytes(bad), [])
    except ValueError:
        return
    assert False, "expected ValueError"
```

- [ ] **Step 2: Run to see them fail**

Run: `python test_script.py`
Expected: `AttributeError: module 'script' has no attribute 'encode'` (after the three Task 3 tests print `ok`).

- [ ] **Step 3: Implement in `script.py`**

```python
import re

_ESCAPE = re.compile(r"\{([0-9A-F]{2})\}")


def decode(raw: bytes) -> str:
    out, i = [], 0
    while i < len(raw):
        n = 2 if (0x81 <= raw[i] <= 0x9F or 0xE0 <= raw[i] <= 0xFC) else 1
        chunk = raw[i:i + n]
        try:
            s = chunk.decode("cp932")
            # keep only characters that encode back to the same bytes
            if s in "{}" or s.encode("cp932") != chunk or (n == 1 and raw[i] < 0x20):
                raise UnicodeError
            out.append(s)
        except UnicodeError:
            out.extend(f"{{{c:02X}}}" for c in chunk)
        i += n
    return "".join(out)


def encode(text: str) -> bytes:
    out = bytearray()
    for k, part in enumerate(_ESCAPE.split(text)):
        if k % 2:
            out.append(int(part, 16))
        else:
            try:
                out += part.encode("cp932")
            except UnicodeEncodeError as e:
                raise ValueError(f"cannot encode {part[e.start:e.end]!r} in cp932") from None
    return bytes(out)


def extract(b: bytes, prefix: str) -> list[dict]:
    return [{"id": f"{prefix}/{t.off:05x}", "jp": decode(t.text), "en": ""}
            for t in tokenize(b) if t.text is not None]


def insert(b: bytes, entries: list[dict]) -> bytes:
    english = {int(e["id"].rsplit("/", 1)[1], 16): e for e in entries if e["en"]}
    toks = tokenize(b)
    new_raw = []
    for t in toks:
        e = english.get(t.off)
        if e is None:
            new_raw.append(bytearray(t.raw))
            continue
        try:
            body = encode(e["en"])
        except ValueError as err:
            raise ValueError(f'{e["id"]}: {err}') from None
        # even-length body: two zero bytes, as in the original; odd: one
        raw = t.raw[:2] + body + (b"\0" if len(body) % 2 else b"\0\0")
        new_raw.append(bytearray(raw))
    moved, pos = {}, 0
    for t, raw in zip(toks, new_raw):
        moved[t.off] = pos
        pos += len(raw)
    moved[used_length(b)] = pos
    for t, raw in zip(toks, new_raw):
        for j in t.jumps:
            target = struct.unpack_from("<I", raw, j)[0]
            if target not in moved:
                raise ValueError(f"jump at {t.off:#x} targets {target:#x}, not a token start")
            struct.pack_into("<I", raw, j, moved[target])
    out = b"".join(new_raw)
    return out.ljust(max(len(b), -(-len(out) // 2048) * 2048), b"\0")
```

If Task 3 found that string tokens can carry operands between the op word and the text, replace `t.raw[:2]` with the token's real prefix (`t.raw[:t.raw.index(t.text)]` when the text is non-empty) and record that in `docs/script-format.md`.

- [ ] **Step 4: Run the tests**

Run: `python test_script.py`
Expected: nine `ok` lines.

- [ ] **Step 5: Commit**

```bash
git add script.py test_script.py
git commit -m "Extract and reinsert script strings with jump fixups"
```

---

### Task 5: Wire into the build; English line on screen

**Files:**
- Modify: `build.py`
- Create: `script/SCENARIO/*.json` (generated)

**Interfaces:**
- Consumes: `dat.unpack`, `dat.pack`, `script.extract`, `script.insert`, `build.make_iso`.
- Produces: `python build.py dump` (writes JSON), `python build.py` (inserts JSON, rebuilds image).

- [ ] **Step 1: Add `dump` and `patch` to `build.py`**

Add the imports `import json, dat, script` and, above `make_iso`:

```python
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


def patch():
    files = dat.unpack((ORIG / "SCENARIO.DAT").read_bytes())
    for path in sorted((SCRIPT / "SCENARIO").glob("*.json")):
        i = int(path.stem)
        files[i] = script.insert(files[i], json.loads(path.read_text(encoding="utf-8")))
    (EXTRACTED / "SCENARIO.DAT").write_bytes(dat.pack(files))
```

Replace the `__main__` block with:

```python
if __name__ == "__main__":
    if sys.argv[1:] == ["extract"]:
        extract()
    elif sys.argv[1:] == ["dump"]:
        dump()
    elif not sys.argv[1:]:
        patch()
        print(make_iso())
    else:
        sys.exit("usage: python build.py [extract|dump]")
```

- [ ] **Step 2: Dump and check the untranslated build is still identical**

Run: `python build.py dump`
Expected: `script/SCENARIO/` holds 382 JSON files.

With no `en` filled in, `patch` must reproduce the original archive:

Run: `python -c "from build import *; patch(); assert (EXTRACTED/'SCENARIO.DAT').read_bytes()==(ORIG/'SCENARIO.DAT').read_bytes(); print('identical')"`
Expected: `identical`

- [ ] **Step 3: Translate the boot-time health warning**

The first text shown after boot is a warning in `script/SCENARIO/000.json`, with one variant per character (lines containing `部屋を明るくして`, "keep the room bright"). In every entry of that file whose `jp` contains `部屋を明るくして`, set:

```json
"en": "Ｋｅｅｐ　ｔｈｅ　ｒｏｏｍ　ｂｒｉｇｈｔ　ｗｈｅｎ　ｙｏｕ　ｐｌａｙ！"
```

The text is fullwidth on purpose: the stock font has no halfwidth path yet. It is longer than the original, so it exercises growth and jump remapping. It may run past the window edge; that is expected and is the font plan's problem.

- [ ] **Step 4: Build**

Run: `python build.py`
Expected: prints `...\build\bm00-en.bin`.

- [ ] **Step 5: Manual check in DuckStation**

Load `build/bm00-en.cue`. Expected: the warning screen shows the English line, the game continues to the title screen, and a new game plays through the opening scene without hanging. A hang or garbage here means a jump operand was missed in Task 3: return to that task's table.

- [ ] **Step 6: Commit**

```bash
git add build.py script
git commit -m "Insert translated SCENARIO strings into the build"
```
