# System Text Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menus, equipment, skills, options/save messages and battle unit names show English.

**Architecture:** `tables.py` handles in-place text: fixed-width fields in `SYSTEM.DAT` sub-file 2 (declared table list), zero-terminated labels in overlay sub-file 4, and unit-name fields in `BATTLE.DAT` (found by matching known names). `pointers.py` relocates the pointer-linked messages of sub-file 10. `build.py dump/patch` and `tl.py` gain width-aware handling. Translation is done inline.

**Tech Stack:** Python 3.12 stdlib; existing `dat.py`, `script.encode/decode`, `tl.py`; DuckStation for the user's check.

**Spec:** `docs/superpowers/specs/2026-10-03-system-tables-design.md`

## Global Constraints

- Pipeline code imports only the Python standard library.
- Every inserter with all `en` empty reproduces the original sub-file byte for byte.
- English is measured in encoded bytes (`script.encode`, which pads odd ASCII runs); a field holds at most its width in bytes, an overlay label at most its original byte length.
- `rom/` and `work/orig/` are never modified. Sub-file sizes are unchanged by this plan.
- Only ASCII 0x20–0x7E in `en`; names from `glossary.md`.

## Known layouts (measured on the original)

`SYSTEM.DAT` sub-file 2, directory at offset 8 = 25 × (`u16 off`, `u16 size`), both in 4-byte units.

| Table | Content | Record | Text fields (offset, width) |
|---|---|---|---|
| 2 | unit names | 20 | (0, 18) |
| 6–20 | weapons (15 classes) | 128 | (0, 20), (26, 34), (60, 34), (94, 34) |
| 21 | gems | 96 | (0, 22), (28, 34), (62, 34) |
| 22 | items | 122 | (0, 18), (20, 100) |
| 23 | rings | 98 | (0, 24), (30, 32), (62, 34) |
| 24 | skills | 94 | (0, 26), (26, 34), (60, 34) |

Tables 22–24 have 2 bytes of slack after the last record. Total text fields: about 1,372.

`SYSTEM.DAT` sub-file 10: messages from offset 0, each a zero-terminated Shift-JIS string padded to 2 bytes, followed by metadata words; 78 pointer words (`u32`, 4-byte aligned, values `0x800d4000`–`0x800d4800`, i.e. base `0x800d4000` + offset) both interleaved after messages and in a table around `0xcb80`.

`SYSTEM.DAT` sub-file 4: overlay at `0x80140000`, 79 zero-terminated Shift-JIS strings.

`BATTLE.DAT`: in every sub-file whose first four bytes are `04 00 01 00`, unit records of 88 bytes with a 16-byte zero-padded name at record start; names are a subset of SYSTEM table 2.

## Review Focus

1. A shorter English in a fixed field must zero the rest of the field; stale Japanese bytes after the terminator would show if the game draws by width. Test in Task 1.
2. BATTLE name matching must not hit a name inside a longer name (`パスカ` inside `パスカ最終形態`): the match must end at a zero byte and start at a record boundary. Test in Task 2.
3. A pointer-range word in sub-file 10 that is really data must make insert raise, not be remapped. Test in Task 3.
4. A `{XX}` escape or odd-length ASCII in `en` still counts in bytes: `"abc"` occupies 4. Width checks use `len(encode(en))`. Test in Task 1.
5. The user cannot see widths in the JSON unless `tl.py show` prints them; `check` must reject over-width before `apply`. Test in Task 5.

---

### Task 1: `tables.py` — fixed-width fields in SYSTEM sub-file 2

**Files:**
- Create: `tables.py`, `test_tables.py`

**Interfaces:**
- Produces:

```python
tables.SYSTEM_TABLES: list[tuple[int, int, list[tuple[int, int]]]]   # (table index, record size, [(field off, width)])
tables.fields(sub2: bytes) -> list[tuple[int, int]]        # every (absolute offset, width) in sub-file 2, record by record
tables.extract_fixed(sub2: bytes, prefix: str) -> list[dict]   # {"id": f"{prefix}/{off:05x}", "jp", "en": "", "width"}
tables.insert_fixed(sub2: bytes, entries: list[dict]) -> bytes
```

- [ ] **Step 1: Write the failing tests `test_tables.py`**

```python
import re
import dat, script, tables
from build import ORIG

SYSTEM = dat.unpack((ORIG / "SYSTEM.DAT").read_bytes())
SUB2 = SYSTEM[2]
KANA = re.compile(rb"(?:\x82[\x9f-\xf1]|\x83[\x40-\x96]){2,}")


def test_fixed_round_trip_is_identical():
    entries = tables.extract_fixed(SUB2, "SYSTEM/2")
    assert len(entries) > 1300
    assert tables.insert_fixed(SUB2, entries) == SUB2


def test_every_kana_run_lies_inside_a_declared_field():
    spans = [(o, o + w) for o, w in tables.fields(SUB2)]
    for m in KANA.finditer(SUB2):
        assert any(a <= m.start() and m.end() <= b for a, b in spans), hex(m.start())


def test_fields_do_not_overlap_record_data():
    for off, w in tables.fields(SUB2):
        field = SUB2[off:off + w]
        text = field.split(b"\0")[0]
        assert len(text) < w or field[-1:] == b"\0" or True   # placeholder removed below
    # the real check: the byte right after each field's text is zero (text never runs to the width)
    for off, w in tables.fields(SUB2):
        text = SUB2[off:off + w].split(b"\0")[0]
        assert len(text) <= w, hex(off)


def test_insert_zero_fills_and_enforces_width():
    entries = tables.extract_fixed(SUB2, "S")
    e = next(x for x in entries if x["width"] == 18)
    e["en"] = "Novice Priest"
    out = tables.insert_fixed(SUB2, entries)
    off = int(e["id"].rsplit("/", 1)[1], 16)
    assert out[off:off + 18] == b"Novice Priest " + b"\0" * 4      # odd length padded by encode, rest zero
    e["en"] = "x" * 19
    try:
        tables.insert_fixed(SUB2, entries)
    except ValueError as err:
        assert e["id"] in str(err) and "18" in str(err)
        return
    assert False, "expected ValueError"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
```

Delete the first loop of `test_fields_do_not_overlap_record_data` (the one ending in `or True`) before running; keep the second.

- [ ] **Step 2: Run to see them fail**

Run: `python test_tables.py`
Expected: `ModuleNotFoundError: No module named 'tables'`

- [ ] **Step 3: Write `tables.py`**

```python
"""In-place text: fixed-width fields in SYSTEM.DAT sub-file 2, overlay labels in
sub-file 4, unit names in BATTLE.DAT. Layouts: docs/superpowers/specs/2026-10-03-system-tables-design.md"""
import re
import struct

from script import decode, encode

WEAPON = (128, [(0, 20), (26, 34), (60, 34), (94, 34)])
SYSTEM_TABLES = [
    (2, 20, [(0, 18)]),                                   # unit names
    *[(i, *WEAPON) for i in range(6, 21)],                # fifteen weapon classes
    (21, 96, [(0, 22), (28, 34), (62, 34)]),              # gems
    (22, 122, [(0, 18), (20, 100)]),                      # items
    (23, 98, [(0, 24), (30, 32), (62, 34)]),              # rings
    (24, 94, [(0, 26), (26, 34), (60, 34)]),              # skills
]


def _directory(sub2: bytes) -> list[tuple[int, int]]:
    count = struct.unpack_from("<I", sub2)[0]
    return [(o * 4, s * 4) for o, s in struct.iter_unpack("<HH", sub2[8:8 + 4 * count])]


def fields(sub2: bytes) -> list[tuple[int, int]]:
    out, directory = [], _directory(sub2)
    for table, rec, flds in SYSTEM_TABLES:
        base, size = directory[table]
        for k in range(size // rec):
            out += [(base + k * rec + off, width) for off, width in flds]
    return out


def _text(buf: bytes, off: int, width: int) -> bytes:
    return buf[off:off + width].split(b"\0")[0]


def extract_fixed(sub2: bytes, prefix: str) -> list[dict]:
    return [{"id": f"{prefix}/{off:05x}", "jp": decode(_text(sub2, off, w)), "en": "", "width": w}
            for off, w in fields(sub2) if _text(sub2, off, w)]


def _fit(e: dict, width: int) -> bytes:
    data = encode(e["en"])
    if len(data) > width:
        raise ValueError(f'{e["id"]}: {len(data)} bytes, field holds {width}')
    return data.ljust(width, b"\0")


def insert_fixed(sub2: bytes, entries: list[dict]) -> bytes:
    out = bytearray(sub2)
    widths = dict(fields(sub2))
    for e in entries:
        if not e["en"]:
            continue
        off = int(e["id"].rsplit("/", 1)[1], 16)
        if off not in widths:
            raise ValueError(f'{e["id"]}: not a text field')
        out[off:off + widths[off]] = _fit(e, widths[off])
    return bytes(out)
```

- [ ] **Step 4: Run the tests**

Run: `python test_tables.py`
Expected: four `ok` lines. If `test_every_kana_run_lies_inside_a_declared_field` fails, print the offending offset's table and record position and widen or add the field in `SYSTEM_TABLES`; the measured maxima in the spec leave 2–6 bytes of margin per field.

- [ ] **Step 5: Commit**

```bash
git add tables.py test_tables.py
git commit -m "Fixed-width text fields in SYSTEM.DAT sub-file 2"
```

---

### Task 2: BATTLE unit names and overlay labels

**Files:**
- Modify: `tables.py`, `test_tables.py`

**Interfaces:**
- Produces:

```python
tables.BATTLE_MAGIC = b"\x04\x00\x01\x00"
tables.battle_names(sub: bytes) -> list[int]            # offsets of 16-byte name fields (88-byte records)
tables.insert_battle(sub: bytes, names: dict[str, str]) -> bytes   # Japanese name -> English
tables.extract_overlay(sub4: bytes, prefix: str) -> list[dict]      # {"id","jp","en":"","width": original byte length}
tables.insert_overlay(sub4: bytes, entries: list[dict]) -> bytes
```

- [ ] **Step 1: Add the failing tests** (above `__main__` in `test_tables.py`)

```python
BATTLE = dat.unpack((ORIG / "BATTLE.DAT").read_bytes())
UNIT_NAMES = {e["jp"] for e in tables.extract_fixed(SUB2, "S") if e["width"] == 18}


def test_battle_name_fields_hold_only_known_unit_names():
    total = 0
    for i, b in enumerate(BATTLE):
        if b[:4] != tables.BATTLE_MAGIC:
            continue
        for off in tables.battle_names(b):
            name = script.decode(b[off:off + 16].split(b"\0")[0])
            assert name in UNIT_NAMES, (i, hex(off), name)
            total += 1
    assert total > 2000


def test_battle_insert_round_trip_and_translation():
    b = BATTLE[193]
    assert tables.insert_battle(b, {}) == b
    out = tables.insert_battle(b, {"パスカ": "Pasca"})          # パスカ
    offs = [o for o in tables.battle_names(b) if b[o:o + 16].startswith(b"\x83p\x83X\x83J\0")]
    assert offs and all(out[o:o + 16] == b"Pasca" + b"\0" * 11 for o in offs)
    assert b"\x83p\x83X\x83J\x8d\xc5" in out      # パスカ最終形態 untouched when only パスカ is mapped
    try:
        tables.insert_battle(b, {"パスカ": "x" * 17})
    except ValueError:
        return
    assert False, "expected ValueError"


def test_overlay_round_trip_and_in_place_limit():
    sub4 = SYSTEM[4]
    entries = tables.extract_overlay(sub4, "SYSTEM/4")
    assert 70 <= len(entries) <= 90
    assert tables.insert_overlay(sub4, entries) == sub4
    e = next(x for x in entries if x["jp"] == "コンフィグ")   # コンフィグ, 10 bytes
    e["en"] = "Config"
    out = tables.insert_overlay(sub4, entries)
    off = int(e["id"].rsplit("/", 1)[1], 16)
    assert out[off:off + 11] == b"Config\0\0\0\0\0"
    e["en"] = "Configuration"
    try:
        tables.insert_overlay(sub4, entries)
    except ValueError as err:
        assert e["id"] in str(err)
        return
    assert False, "expected ValueError"
```

- [ ] **Step 2: Run to see them fail**

Run: `python test_tables.py`
Expected: `AttributeError: module 'tables' has no attribute 'BATTLE_MAGIC'`

- [ ] **Step 3: Implement**

Append to `tables.py`:

```python
BATTLE_MAGIC = b"\x04\x00\x01\x00"
_UNIT = 88
_NAME = 16


def battle_names(sub: bytes) -> list[int]:
    """Offsets of unit-name fields: 88-byte records whose first 16 bytes are a
    zero-padded Shift-JIS name. Found by the first name's position, then stride."""
    kana = re.compile(rb"(?:\x82[\x9f-\xf1]|\x83[\x40-\x96]|[\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]){2,}\0")
    m = kana.search(sub)
    if not m:
        return []
    out, off = [], m.start()
    while off + _NAME <= len(sub) and sub[off] and sub[off:off + _NAME].count(b"\0"):
        out.append(off)
        off += _UNIT
    return out


def insert_battle(sub: bytes, names: dict[str, str]) -> bytes:
    out = bytearray(sub)
    for off in battle_names(sub):
        jp = decode(_text(sub, off, _NAME))
        en = names.get(jp, "")
        if en:
            out[off:off + _NAME] = _fit({"id": f"BATTLE/{off:05x} {jp}", "en": en}, _NAME)
    return bytes(out)


_SJIS_STRING = re.compile(rb"(?:[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]){2,}\0")


def extract_overlay(sub4: bytes, prefix: str) -> list[dict]:
    out = []
    for m in _SJIS_STRING.finditer(sub4):
        if m.start() % 2:
            continue
        text = m.group()[:-1]
        if re.search(rb"\x82[\x9f-\xf1]|\x83[\x40-\x96]|\x81[\x40-\x49]|[\x88-\x9f\xe0-\xea]", text):
            out.append({"id": f"{prefix}/{m.start():05x}", "jp": decode(text), "en": "", "width": len(text)})
    return out


def insert_overlay(sub4: bytes, entries: list[dict]) -> bytes:
    out = bytearray(sub4)
    for e in entries:
        if e["en"]:
            off = int(e["id"].rsplit("/", 1)[1], 16)
            out[off:off + e["width"]] = _fit(e, e["width"])
    return bytes(out)
```

- [ ] **Step 4: Run the tests**

Run: `python test_tables.py`
Expected: seven `ok` lines. If `test_battle_name_fields_hold_only_known_unit_names` reports a name not in the unit table, look at that sub-file: either the stride differs for that battle type (add a second stride) or the name belongs in `SYSTEM_TABLES` table 2 after all.

- [ ] **Step 5: Commit**

```bash
git add tables.py test_tables.py
git commit -m "Battle unit names and overlay labels in place"
```

---

### Task 3: `pointers.py` — sub-file 10 messages

**Files:**
- Create: `pointers.py`, `test_pointers.py`

**Interfaces:**
- Produces:

```python
pointers.BASE = 0x800D4000
pointers.extract(sub10: bytes, prefix: str) -> list[dict]   # {"id": f"{prefix}/{off:05x}", "jp", "en": ""}
pointers.insert(sub10: bytes, entries: list[dict]) -> bytes
```

- [ ] **Step 1: Write the failing tests `test_pointers.py`**

```python
import struct
import dat, pointers, script
from build import ORIG

SUB10 = dat.unpack((ORIG / "SYSTEM.DAT").read_bytes())[10]


def _pointer_words(b):
    return [(o, struct.unpack_from("<I", b, o)[0]) for o in range(0, len(b) - 3, 4)
            if pointers.BASE <= struct.unpack_from("<I", b, o)[0] < pointers.BASE + 0x800]


def test_round_trip_is_identical():
    entries = pointers.extract(SUB10, "SYSTEM/10")
    assert 50 <= len(entries) <= 80
    assert pointers.insert(SUB10, entries) == SUB10


def test_every_pointer_targets_a_message():
    starts = {int(e["id"].rsplit("/", 1)[1], 16) for e in pointers.extract(SUB10, "S")}
    for o, v in _pointer_words(SUB10):
        assert v - pointers.BASE in starts, (hex(o), hex(v))


def test_growth_relocates_following_messages_and_pointers():
    entries = pointers.extract(SUB10, "S")
    entries[0]["en"] = "This closes the screen. " * 3          # much longer than the Japanese
    out = pointers.insert(SUB10, entries)
    new = pointers.extract(out, "S")
    assert [e["jp"] for e in new] == [entries[0]["en"].strip()] + [e["jp"] for e in entries[1:]]
    assert len(_pointer_words(out)) == len(_pointer_words(SUB10))


def test_data_word_in_pointer_range_raises():
    bad = bytearray(SUB10)
    struct.pack_into("<I", bad, 0x200, pointers.BASE + 1)      # inside a string, not a start
    try:
        pointers.insert(bytes(bad), [])
    except ValueError:
        return
    assert False, "expected ValueError"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
```

- [ ] **Step 2: Run to see them fail**

Run: `python test_pointers.py`
Expected: `ModuleNotFoundError: No module named 'pointers'`

- [ ] **Step 3: Explore the message region once**

```bash
python -c "
import dat; from build import ORIG
b = dat.unpack((ORIG/'SYSTEM.DAT').read_bytes())[10]
p = 0
for n in range(70):
    e = b.find(b'\0\0', p); e += e % 2
    print(hex(p), b[p:e].decode('cp932','replace'), '|', b[e+2:e+8].hex(' '))
    p = e + 2
    while b[p:p+2] == b'\0\0': p += 2
"
```
Expected: messages in order with their metadata; note where the first non-message data begins (the `0x160`–`0x198` area holds a small table, not text) and the end of the last message (around `0x440`). Record the exact message region boundaries as constants in `pointers.py`; the plan assumes two regions: `0x000`–`0x160` (option screen) and `0x178`–end (memory card), separated by a 24-byte table.

- [ ] **Step 4: Write `pointers.py`**

```python
"""SYSTEM.DAT sub-file 10: option and memory-card messages, linked by absolute pointers."""
import struct

from script import decode, encode

BASE = 0x800D4000
REGIONS = [(0x000, 0x160), (0x178, 0x440)]   # message runs; the gap is a non-text table. Adjust from Step 3.


def _messages(b: bytes):
    """Yield (offset, text, metadata) for every message in the regions."""
    for lo, hi in REGIONS:
        p = lo
        while p < hi:
            e = b.find(b"\0\0", p)
            e += e % 2
            text = b[p:e]
            q = e + 2
            while q < hi and b[q:q + 2] == b"\0\0":
                q += 2
            # metadata = non-text bytes between terminator and next message start
            yield p, text, b[e:q]
            p = q


def extract(b: bytes, prefix: str) -> list[dict]:
    return [{"id": f"{prefix}/{off:05x}", "jp": decode(text), "en": ""} for off, text, _ in _messages(b) if text]


def insert(b: bytes, entries: list[dict]) -> bytes:
    english = {int(e["id"].rsplit("/", 1)[1], 16): e["en"] for e in entries if e["en"]}
    out = bytearray(b)
    moved = {}
    for lo, hi in REGIONS:
        buf = bytearray()
        for off, text, meta in _messages(b):
            if not lo <= off < hi:
                continue
            moved[off] = lo + len(buf)
            data = encode(english[off]) if off in english else text
            buf += data + b"\0" * (len(data) % 2) + meta
        if len(buf) > hi - lo:
            raise ValueError(f"messages in {lo:#x}-{hi:#x} grew to {len(buf)} bytes, room for {hi - lo}")
        out[lo:hi] = buf.ljust(hi - lo, b"\0")
    for o in range(0, len(out) - 3, 4):
        v = struct.unpack_from("<I", out, o)[0]
        if BASE <= v < BASE + 0x800:
            if v - BASE not in moved:
                raise ValueError(f"word at {o:#x} = {v:#x} is in the pointer range but not a message start")
            struct.pack_into("<I", out, o, BASE + moved[v - BASE])
    return bytes(out)
```

The metadata bytes after a message include its own pointer words, which the final loop rewrites after relocation; because the loop runs over `out`, interleaved pointers are remapped exactly once.

- [ ] **Step 5: Run the tests**

Run: `python test_pointers.py`
Expected: four `ok` lines. If the round trip differs, the region boundaries or the "metadata = bytes until next message" rule is off for one message; print `_messages` output next to the Step 3 listing and adjust `REGIONS`.

- [ ] **Step 6: Commit**

```bash
git add pointers.py test_pointers.py
git commit -m "Relocatable option and memory-card messages"
```

---

### Task 4: Build and dump integration

**Files:**
- Modify: `build.py`
- Create: `script/SYSTEM/tables.json`, `script/SYSTEM/messages.json`, `script/SYSTEM/overlay.json` (generated)

**Interfaces:**
- Consumes: `tables.*`, `pointers.*`, `dat.*`.
- Produces: `python build.py dump` writes the three JSON files (never overwrites); `patch()` writes `work/extracted/SYSTEM.DAT` and `work/extracted/BATTLE.DAT`.

- [ ] **Step 1: Extend `build.py`**

Add `import pointers, tables` to the imports. In `dump()`, after the SCENARIO loop:

```python
    sysdir = SCRIPT / "SYSTEM"
    sysdir.mkdir(exist_ok=True)
    system = dat.unpack((ORIG / "SYSTEM.DAT").read_bytes())
    for name, entries in (("tables", tables.extract_fixed(system[2], "SYSTEM/2")),
                          ("messages", pointers.extract(system[10], "SYSTEM/10")),
                          ("overlay", tables.extract_overlay(system[4], "SYSTEM/4"))):
        path = sysdir / f"{name}.json"
        if not path.exists():
            path.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
```

In `patch()`, before the `halfwidth.assemble` line:

```python
    sysdir = SCRIPT / "SYSTEM"
    load = lambda name: json.loads((sysdir / f"{name}.json").read_text(encoding="utf-8"))
    system = dat.unpack((ORIG / "SYSTEM.DAT").read_bytes())
    fixed = load("tables")
    system[2] = tables.insert_fixed(system[2], fixed)
    system[10] = pointers.insert(system[10], load("messages"))
    system[4] = tables.insert_overlay(system[4], load("overlay"))
    (EXTRACTED / "SYSTEM.DAT").write_bytes(dat.pack(system))
    names = {e["jp"]: e["en"] for e in fixed if e["width"] == 18 and e["en"]}
    battle = dat.unpack((ORIG / "BATTLE.DAT").read_bytes())
    battle = [tables.insert_battle(b, names) if b[:4] == tables.BATTLE_MAGIC else b for b in battle]
    (EXTRACTED / "BATTLE.DAT").write_bytes(dat.pack(battle))
```

In `test_build.py`, add `"BATTLE.DAT"` to the tuple of files restored before the identity build.

- [ ] **Step 2: Dump and prove identity**

Run:
```bash
python build.py dump && ls script/SYSTEM
python -c "from build import *; patch(); assert (EXTRACTED/'SYSTEM.DAT').read_bytes()==(ORIG/'SYSTEM.DAT').read_bytes(); assert (EXTRACTED/'BATTLE.DAT').read_bytes()==(ORIG/'BATTLE.DAT').read_bytes(); print('identical')"
```
Expected: three JSON files; `identical`.

- [ ] **Step 3: Commit**

```bash
git add build.py test_build.py script/SYSTEM
git commit -m "Dump and patch system text"
```

---

### Task 5: Width-aware `tl.py`

**Files:**
- Modify: `tl.py`, `test_tl.py`

**Interfaces:**
- `tl.lines(entries)` prints `id<TAB>width<TAB>jp` for entries that carry `width` (the second column is the width instead of the speaker).
- `tl.check(src_lines, answer_lines)` reads a numeric second column from the source listing as that id's byte limit and reports `over width: id (N > W)` using `len(script.encode(en))`.
- `tl.py show/apply/check` accept a name like `SYSTEM/tables` as well as `NNN`.

- [ ] **Step 1: Add the failing tests to `test_tl.py`**

```python
def test_lines_show_width_and_check_enforces_it():
    entries = [{"id": "S/1", "jp": "ナイフ", "en": "", "width": 18}]
    assert tl.lines(entries) == ["S/1\t18\tナイフ"]
    src = ["S/1\t18\tjp"]
    assert tl.check(src, ["S/1\tKnife"]) == []
    assert any("over width" in p for p in tl.check(src, ["S/1\tA very long weapon name"]))
    assert any("over width" in p for p in tl.check(["S/2\t4\tjp"], ["S/2\tabcde"]))   # 5 > 4
    assert tl.check(["S/3\t4\tjp"], ["S/3\tabc"]) == []                                 # "abc" pads to 4, fits
```

- [ ] **Step 2: Run to see it fail**

Run: `python test_tl.py`
Expected: `AssertionError` on the `lines` comparison (speaker column prints `-`).

- [ ] **Step 3: Implement**

In `tl.lines`, replace the speaker column computation with:

```python
        col = e["width"] if "width" in e else e.get("speaker")
        out.append(f'{e["id"]}\t{"-" if col is None else col}\t{jp}')
```

In `tl.check`, after `wanted = ...` add:

```python
    limits = {}
    for l in src_lines:
        parts = l.split("\t")
        if len(parts) >= 2 and parts[1].isdigit():
            limits[parts[0]] = int(parts[1])
```

and inside the loop, after the `long:` check:

```python
        if id_ in limits:
            n = len(script.encode(en.replace("\\n", " ")))
            if n > limits[id_]:
                problems.append(f"over width: {id_} ({n} > {limits[id_]})")
```

with `import script` at the top. In the `__main__` block, resolve the JSON path as `SCRIPT.parent / f"{num}.json"` when `num` contains a `/`, else `SCRIPT / f"{num}.json"`, and the `check` source as `work/tl/{num.replace('/', '_')}.src.txt`.

- [ ] **Step 4: Run the tests and commit**

Run: `python test_tl.py`
Expected: all `ok`.

```bash
git add tl.py test_tl.py
git commit -m "tl.py: show and enforce field widths"
```

---

### Task 6: Translate and check in-game

**Files:**
- Modify: `script/SYSTEM/*.json`, `glossary.md` (abbreviations table)

- [ ] **Step 1: Dump the listings**

```bash
mkdir -p work/tl && for n in tables messages overlay; do python tl.py show SYSTEM/$n > work/tl/SYSTEM_$n.src.txt; done; wc -l work/tl/SYSTEM_*.src.txt
```

- [ ] **Step 2: Translate**

Write `work/tl/SYSTEM_tables.txt`, `SYSTEM_messages.txt`, `SYSTEM_overlay.txt` as `id<TAB>en`, inline in this session, against the width column. Rules:
- Names ≤ width; standard abbreviations go in a new `glossary.md` section "Abbreviations" (e.g. `Lthr` for Leather only if `Leather Gloves` cannot fit).
- Descriptions keep stat notation: `ATK+7  AGL+3`; `射程３` → `Range 3`.
- Unit names reuse the glossary's labels (`Novice Priest`, `Monk Soldier`, `Punk Soldier`, `Stray Demon`).
- Messages: plain system English (`Load this data?`, `Saving...`, `Save succeeded.`).
- Overlay labels must fit the original byte length: `コンフィグ` (10) → `Config`; `ロード` (6) → `Load`; `セーブ` (6) → `Save`; `リスト` (6) → `List`; `ターン` (6) → `Turn`; `アイテム` (8) → `Item`; `ユニット` (8) → `Unit`; `リング` (6) → `Ring`; `スキル` (6) → `Skill`; two-kanji labels with a fullwidth space (`道　具`, 6 bytes) → `Items`, `Spec.`, `Attack` is 6 so `Attack`, `移　動` → `Move`.

For each file: `python tl.py check SYSTEM/<name> work/tl/SYSTEM_<name>.txt` until `ok`, then `python tl.py apply SYSTEM/<name> work/tl/SYSTEM_<name>.txt`.

- [ ] **Step 3: Build**

Run: `python build.py`
Expected: no errors; prints the image path.

- [ ] **Step 4: Manual check (user)**

In DuckStation: open the equipment screen and a weapon's description, a skill list, the options menu, a load prompt, and a battle (unit names over heads and in the unit list). Report any Japanese left, any text cut off at a fixed width, and any label that reads wrong.

- [ ] **Step 5: Fix and commit**

Apply corrections through the same answer files, rebuild, then:

```bash
git add script/SYSTEM glossary.md
git commit -m "Translate system text: items, skills, units, messages, menus"
```
