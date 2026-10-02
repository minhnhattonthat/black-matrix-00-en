# SCENARIO Translation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dialogue windows become the translation unit, with automatic wrapping and spill, and the opening of the game is translated as a pilot the user plays.

**Architecture:** `script.extract` groups consecutive `1050` tokens into window entries (`jp` is a list, plus `speaker`); `script.insert` wraps `en` to 30-byte lines, emits them as `1050` tokens and copies the window's following `000a` call between every three lines. A small `tl.py` prints windows for translation and merges a tab-separated answer file back into the JSON. A glossary is approved by the user before translation starts.

**Tech Stack:** Python 3.12 stdlib; existing `dat.py`, `script.py`, `build.py`; DuckStation for the user's playthrough.

**Spec:** `docs/superpowers/specs/2026-10-02-scenario-translation-design.md`

## Global Constraints

- Pipeline code imports only the Python standard library.
- With every `en` empty, `insert` reproduces the original script byte for byte.
- Window line width `WINDOW_CELLS * 2 = 30` bytes; hard line cap `MAX_CELLS * 2 = 46` bytes; both already in `script.py`.
- `en` holds only ASCII 0x20–0x7E, `\n`, and `{XX}` escapes; the encoder already rejects other control characters and halfwidth kana.
- Style: faithful, honorifics kept, per `glossary.md`.
- `rom/` and `work/orig/` are never modified.

## Review Focus

1. An `en` with a trailing or doubled `\n` must not produce empty `1050` lines. Test in Task 2.
2. A jump that targets the second line of a window must make `insert` raise, never silently drop the target. Test in Task 2.
3. A four-line `en` on a window with no following `000a` must fail naming the ID. Test in Task 2.
4. An entry whose `id` points at a `1050` that is not the first line of its window must fail with "no string at", not be applied to the wrong window. Test in Task 2.
5. A `{XX}` escape inside `en` must count toward the 30-byte width (wrapping measures encoded bytes). Test in Task 2.

---

### Task 1: Extract windows

**Files:**
- Modify: `script.py` (`extract`), `test_script.py`

**Interfaces:**
- Produces:
  - `script.DIALOGUE_OP = 0x1050`, `script.WAIT_OP = 0x000A`, `script.SPEAKER_OP = 0x1058`
  - `script.op(t: Token) -> int`
  - `script.extract(b, prefix) -> list[dict]` where a dialogue window is `{"id", "speaker": int|None, "jp": [str, ...], "en": ""}` (plus `"spill": False` when no `000a` follows) and every other string is `{"id", "jp": str, "en": ""}`.

- [ ] **Step 1: Add the failing tests to `test_script.py`** (above the `__main__` block)

```python
def test_extract_groups_dialogue_runs_into_windows():
    windows = [e for i, b in SCRIPTS for e in script.extract(b, f"S/{i:03d}") if isinstance(e["jp"], list)]
    assert len(windows) == 18213
    assert sum(len(w["jp"]) for w in windows) == 32497
    assert max(len(w["jp"]) for w in windows) == 3
    assert sum(1 for w in windows if w.get("spill") is False) == 120


def test_extract_reads_the_speaker_from_the_preceding_1058():
    entries = script.extract(SCRIPTS[12][1], "S")
    w = next(e for e in entries if e["id"].endswith("/005fa"))
    assert w["jp"] == ["大事なものなんだよ！",
                       "どこだ！どこなんだよ～！？"]
    assert w["speaker"] == 0x10
    assert "spill" not in w


def test_extract_keeps_other_strings_as_single_entries():
    for i, b in SCRIPTS:
        toks = script.tokenize(b)
        singles = [t for t in toks if t.text is not None and script.op(t) != script.DIALOGUE_OP]
        entries = [e for e in script.extract(b, "S") if isinstance(e["jp"], str)]
        assert [f"S/{t.off:05x}" for t in singles] == [e["id"] for e in entries], i
```

The expected `jp` is the window at `0x5fa` in script 12 (`大事なものなんだよ！` / `どこだ！どこなんだよ～！？`); its preceding `1058` carries `01 00 10 00`, so the speaker is `0x10`.

- [ ] **Step 2: Run to see them fail**

Run: `python test_script.py`
Expected: `AttributeError` or `AssertionError` in `test_extract_groups_dialogue_runs_into_windows` (no entry has a list `jp`).

- [ ] **Step 3: Implement**

Add below the `OPS` table in `script.py`:

```python
DIALOGUE_OP = 0x1050   # one window line; 1-3 in a row make a window
WAIT_OP = 0x000A       # call that shows the window and waits; copied when a window spills
SPEAKER_OP = 0x1058    # 1058 <imm>: speaker / portrait id, context for translators


def op(t: "Token") -> int:
    return struct.unpack_from("<H", t.raw)[0]


def _window_end(toks: list, k: int) -> int:
    while k < len(toks) and op(toks[k]) == DIALOGUE_OP:
        k += 1
    return k
```

Replace `extract`:

```python
def extract(b: bytes, prefix: str) -> list[dict]:
    toks, out, speaker, k = tokenize(b), [], None, 0
    while k < len(toks):
        t = toks[k]
        if op(t) == SPEAKER_OP:
            speaker = struct.unpack_from("<H", t.raw, 4)[0] if t.raw[2:4] == b"\x01\x00" else None
        if op(t) == DIALOGUE_OP:
            end = _window_end(toks, k)
            e = {"id": f"{prefix}/{t.off:05x}", "speaker": speaker,
                 "jp": [decode(x.text) for x in toks[k:end]], "en": ""}
            if not (end < len(toks) and op(toks[end]) == WAIT_OP):
                e["spill"] = False
            out.append(e)
            k = end
            continue
        if t.text is not None:
            out.append({"id": f"{prefix}/{t.off:05x}", "jp": decode(t.text), "en": ""})
        k += 1
    return out
```

- [ ] **Step 4: Run the tests**

Run: `python test_script.py`
Expected: the three new tests pass. `test_extract_insert_is_byte_identical`, `test_grown_strings_keep_jumps_on_the_same_tokens`, `test_odd_length_string_keeps_even_alignment` and the `_insert_raises` tests now fail or error, because `insert` does not understand list `jp` yet. That is Task 2's RED. Do not commit a red suite: continue straight into Task 2 and commit both together.

---

### Task 2: Insert windows with wrap and spill

**Files:**
- Modify: `script.py` (`insert`, new `wrap`, `spilled`, `too_wide`), `test_script.py`

**Interfaces:**
- Consumes: Task 1's entry shapes, `encode`, `MAX_CELLS`, `WINDOW_CELLS`.
- Produces:
  - `script.wrap(text: str, width: int = 30) -> list[str]` — splits on `\n`, then greedily at spaces so each line's encoded length is at most `width`; a single word longer than `width` stays on its own line; blank lines are dropped.
  - `script.insert(b, entries) -> bytes` — handles both entry shapes.
  - `script.spilled(entries) -> list[str]` — IDs of windows wrapping to more than three lines.
  - `script.too_wide(entries) -> list[str]` — IDs with any line over `WINDOW_CELLS * 2` bytes after wrapping.

- [ ] **Step 1: Replace the old `too_wide` test and add the new tests** in `test_script.py`

Delete `test_too_wide_lists_lines_past_the_window`. In `test_grown_strings_keep_jumps_on_the_same_tokens` replace the line that sets `e["en"]` with:

```python
            jp = "\n".join(e["jp"]) if isinstance(e["jp"], list) else e["jp"]
            e["en"] = jp + "　　　"     # 6 bytes: flips u32 alignment, never spills
```

Add above the `__main__` block:

```python
def _window(entries):
    return next(e for e in entries if isinstance(e["jp"], list) and "spill" not in e)


def test_wrap_breaks_at_spaces_within_30_bytes():
    assert script.wrap("Keep the room bright when you play!") == ["Keep the room bright when", "you play!"]
    assert script.wrap("one\ntwo three") == ["one", "two three"]
    assert script.wrap("a\n\nb\n") == ["a", "b"]                     # no blank lines
    assert script.wrap("x" * 31) == ["x" * 31]                         # long word stays whole
    assert script.wrap("ab {41}" + "c" * 25) == ["ab", "{41}" + "c" * 25]   # escape is one byte


def test_window_en_replaces_all_its_lines():
    i, b = SCRIPTS[12]
    entries = script.extract(b, "S")
    w = _window(entries)
    assert len(w["jp"]) >= 2
    w["en"] = "Hello"
    toks = script.tokenize(script.insert(b, entries))
    texts = [t.text for t in toks if t.text is not None]
    assert b"Hello " in texts
    before = len([t for t in script.tokenize(b) if t.text is not None])
    assert len(texts) == before - len(w["jp"]) + 1


def test_four_lines_spill_into_a_second_window():
    i, b = SCRIPTS[12]
    entries = script.extract(b, "S")
    w = _window(entries)
    w["en"] = "\n".join(["line one", "line two", "line three", "line four"])
    toks = script.tokenize(script.insert(b, entries))
    k = next(n for n, t in enumerate(toks) if t.text == b"line one")
    assert [script.op(t) for t in toks[k:k + 6]] == [0x1050] * 3 + [0x000A] + [0x1050, 0x000A]
    assert toks[k + 3].raw == toks[k + 5].raw                           # the copied wait call
    assert script.spilled(entries) == [w["id"]]


def test_spill_false_window_rejects_four_lines():
    i, b = next((i, b) for i, b in SCRIPTS
                if any(e.get("spill") is False for e in script.extract(b, "S")))
    entries = script.extract(b, "S")
    w = next(e for e in entries if e.get("spill") is False)
    w["en"] = "a\nb\nc\nd"
    try:
        script.insert(b, entries)
    except ValueError as err:
        assert w["id"] in str(err)
        return
    assert False, "expected ValueError"


def test_id_of_a_second_window_line_is_rejected():
    i, b = SCRIPTS[12]
    entries = script.extract(b, "S")
    w = _window(entries)
    toks = script.tokenize(b)
    k = next(n for n, t in enumerate(toks) if f"S/{t.off:05x}" == w["id"])
    bad = {"id": f"S/{toks[k + 1].off:05x}", "jp": "", "en": "x"}
    try:
        script.insert(b, entries + [bad])
    except ValueError as err:
        assert "no string at" in str(err)
        return
    assert False, "expected ValueError"


def test_jump_into_a_window_raises():
    i, b = SCRIPTS[12]
    toks = script.tokenize(b)
    w = _window(script.extract(b, "S"))
    k = next(n for n, t in enumerate(toks) if f"S/{t.off:05x}" == w["id"])
    j = next(t for t in toks if t.jumps)
    bad = bytearray(b)
    struct.pack_into("<I", bad, j.off + j.jumps[0], toks[k + 1].off)
    entries = script.extract(bytes(bad), "S")
    _window(entries)["en"] = "x"
    try:
        script.insert(bytes(bad), entries)
    except ValueError:
        return
    assert False, "expected ValueError"


def test_too_wide_reports_lines_over_the_window():
    i, b = SCRIPTS[12]
    entries = script.extract(b, "S")
    w = _window(entries)
    w["en"] = "x" * 31
    assert script.too_wide(entries) == [w["id"]]
    w["en"] = "x" * 30
    assert script.too_wide(entries) == []
```

- [ ] **Step 2: Run to see them fail**

Run: `python test_script.py`
Expected: `AttributeError: module 'script' has no attribute 'wrap'`.

- [ ] **Step 3: Implement `wrap`, `insert`, `spilled`, `too_wide`**

Replace `insert` and `too_wide` in `script.py` with:

```python
def wrap(text: str, width: int = WINDOW_CELLS * 2) -> list[str]:
    """Lines of at most `width` encoded bytes, broken at spaces and at \\n. A word
    longer than `width` stays whole (insert's 46-byte cap still applies to it)."""
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in filter(None, para.split(" ")):
            if cur and len(encode(cur + " " + word)) > width:
                lines.append(cur)
                cur = word
            else:
                cur = f"{cur} {word}" if cur else word
        if cur:
            lines.append(cur)
    return lines


def _offset(entry: dict) -> int:
    return int(entry["id"].rsplit("/", 1)[1], 16)


def _line_bytes(e: dict, text: str) -> bytes:
    try:
        data = encode(text)
    except ValueError as err:
        raise ValueError(f'{e["id"]}: {err}') from None
    if len(data) > MAX_CELLS * 2:
        raise ValueError(f'{e["id"]}: {len(data)} bytes; a line holds {MAX_CELLS * 2}')
    padded = data + b"\0" * (len(data) % 2)
    if any(padded[i:i + 2] == b"\0\0" for i in range(0, len(padded), 2)):
        raise ValueError(f'{e["id"]}: a zero word inside the text would end the string early')
    return data


def insert(b: bytes, entries: list[dict]) -> bytes:
    """Rebuild the script with each entry's non-empty `en` in place of its string or window."""
    english = {_offset(e): e for e in entries if e["en"]}
    toks = tokenize(b)
    out, moved, fixups = bytearray(), {}, []

    def emit(t: Token, text: bytes | None = None):
        for kind, data in t.parts:
            if kind == "s":
                if text is not None:
                    data = text
                # the game ends a string at a zero u16, so complete an odd last word first
                out.extend(data + b"\0" * (len(data) % 2) + b"\0\0")
            elif kind in "uj":
                if len(out) % 4:
                    out.extend(b"\0\0")
                if kind == "j":
                    fixups.append((len(out), struct.unpack("<I", data)[0], t.off))
                out.extend(data)
            else:
                out.extend(data)

    k = 0
    while k < len(toks):
        t = toks[k]
        moved[t.off] = len(out)
        e = english.pop(t.off, None) if t.text is not None else None
        if e is None or op(t) != DIALOGUE_OP:
            emit(t, _line_bytes(e, e["en"]) if e else None)
            k += 1
            continue
        end = _window_end(toks, k)
        wait = toks[end] if end < len(toks) and op(toks[end]) == WAIT_OP else None
        lines = wrap(e["en"])
        if wait is None and len(lines) > 3:
            raise ValueError(f'{e["id"]}: {len(lines)} lines, and no wait call follows to spill into')
        for n, line in enumerate(lines):
            if n and n % 3 == 0:
                emit(wait)
            emit(t, _line_bytes(e, line))
        k = end                      # lines 2-3 of the window are consumed; jumps to them fail below
    if english:
        ids = ", ".join(e["id"] for e in english.values())
        raise ValueError(f"no string at: {ids}")
    moved[used_length(b)] = len(out)
    for pos, target, off in fixups:
        if target not in moved:
            raise ValueError(f"jump at {off:#x} targets {target:#x}, not a token start")
        struct.pack_into("<I", out, pos, moved[target])
    if len(out) >= 0x20000:
        raise ValueError(f"script is {len(out):#x} bytes; the program counter covers 0x20000")
    return bytes(out).ljust(max(len(b), -(-len(out) // 2048) * 2048), b"\0")


def spilled(entries: list[dict]) -> list[str]:
    """IDs of windows whose English wraps to more than three lines (shown as two windows)."""
    return [e["id"] for e in entries if e["en"] and isinstance(e["jp"], list) and len(wrap(e["en"])) > 3]


def too_wide(entries: list[dict]) -> list[str]:
    """IDs with a line wider than the dialogue window after wrapping."""
    limit = WINDOW_CELLS * 2
    return [e["id"] for e in entries if e["en"]
            and any(len(encode(line)) > limit for line in wrap(e["en"]))]
```

- [ ] **Step 4: Run the whole script suite**

Run: `python test_script.py`
Expected: every test `ok` (27 lines). If `test_extract_insert_is_byte_identical` fails, `emit` is not reproducing a part exactly; diff the first differing offset against `tokenize` output.

- [ ] **Step 5: Commit Tasks 1 and 2 together**

```bash
git add script.py test_script.py
git commit -m "Group dialogue into windows; wrap and spill English on insert"
```

---

### Task 3: Build integration, migration, translation helper

**Files:**
- Modify: `build.py` (`patch`)
- Create: `tl.py`, `test_tl.py`
- Regenerate: `script/SCENARIO/*.json`

**Interfaces:**
- Consumes: `script.extract`, `script.insert`, `script.spilled`, `script.too_wide`.
- Produces:
  - `python build.py` prints `spilled: <id>` and `too wide: <id>` lines.
  - `python tl.py show NNN` prints one window per line: `id<TAB>speaker<TAB>jp lines joined by " / "`, only entries with empty `en`.
  - `python tl.py apply NNN FILE` merges `id<TAB>en` lines from FILE into `script/SCENARIO/NNN.json` (`\n` written as the two characters `\n`), reports unknown IDs, never touches other entries.

- [ ] **Step 1: Update `patch()` in `build.py`**

Replace the `too_wide` loop body with:

```python
        for wide in script.too_wide(entries):
            print("too wide:", wide)
        for spill in script.spilled(entries):
            print("spilled:", spill)
```

- [ ] **Step 2: Regenerate the JSON and check identity**

```bash
rm -rf script/SCENARIO && python build.py dump && ls script/SCENARIO | wc -l
python -c "from build import *; patch(); assert (EXTRACTED/'SCENARIO.DAT').read_bytes()==(ORIG/'SCENARIO.DAT').read_bytes(); print('identical')"
```
Expected: `382`, then `identical`. (The halfwidth test lines in `000.json` are gone on purpose; the boot warning is translated in Task 5.)

- [ ] **Step 3: Write the failing test `test_tl.py`**

```python
import json, tempfile
from pathlib import Path
import tl


def test_apply_merges_en_by_id_and_keeps_the_rest():
    with tempfile.TemporaryDirectory() as d:
        js = Path(d) / "012.json"
        js.write_text(json.dumps([{"id": "S/012/00001", "speaker": 1, "jp": ["a"], "en": ""},
                                  {"id": "S/012/00002", "jp": "b", "en": "old"}]), encoding="utf-8")
        answers = Path(d) / "012.txt"
        answers.write_text("S/012/00001\tFirst line\\nsecond\nS/012/09999\tnope\n", encoding="utf-8")
        unknown = tl.apply(js, answers)
        data = json.loads(js.read_text(encoding="utf-8"))
    assert data[0]["en"] == "First line\nsecond"
    assert data[1]["en"] == "old"
    assert unknown == ["S/012/09999"]


def test_show_lists_only_untranslated_windows_and_strings():
    entries = [{"id": "x/1", "speaker": 3, "jp": ["one", "two"], "en": ""},
               {"id": "x/2", "jp": "menu", "en": ""},
               {"id": "x/3", "jp": ["done"], "en": "Done"}]
    assert tl.lines(entries) == ["x/1\t3\tone / two", "x/2\t-\tmenu"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
```

- [ ] **Step 4: Run to see it fail**

Run: `python test_tl.py`
Expected: `ModuleNotFoundError: No module named 'tl'`

- [ ] **Step 5: Write `tl.py`**

```python
"""Translation helper.
  python tl.py show NNN          print untranslated entries of script/SCENARIO/NNN.json
  python tl.py apply NNN FILE    merge "id<TAB>en" lines (\\n = line break) into the JSON"""
import json, sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "script" / "SCENARIO"


def lines(entries: list[dict]) -> list[str]:
    out = []
    for e in entries:
        if e["en"]:
            continue
        jp = " / ".join(e["jp"]) if isinstance(e["jp"], list) else e["jp"]
        out.append(f'{e["id"]}\t{e.get("speaker", "-") if e.get("speaker") is not None else "-"}\t{jp}')
    return out


def apply(js: Path, answers: Path) -> list[str]:
    entries = json.loads(js.read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in entries}
    unknown = []
    for raw in answers.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        id_, _, en = raw.partition("\t")
        if id_ not in by_id:
            unknown.append(id_)
            continue
        by_id[id_]["en"] = en.replace("\\n", "\n").strip()
    js.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    return unknown


if __name__ == "__main__":
    cmd, num = sys.argv[1], sys.argv[2]
    js = SCRIPT / f"{num}.json"
    if cmd == "show":
        sys.stdout.reconfigure(encoding="utf-8")
        print("\n".join(lines(json.loads(js.read_text(encoding="utf-8")))))
    elif cmd == "apply":
        for id_ in apply(js, Path(sys.argv[3])):
            print("unknown id:", id_)
    else:
        sys.exit(__doc__)
```

- [ ] **Step 6: Run the tests and commit**

Run: `python test_tl.py && python test_script.py | tail -1`
Expected: two `ok` lines, then the last script test `ok`.

```bash
git add build.py tl.py test_tl.py script
git commit -m "Window-shaped script JSON, build warnings, translation helper"
```

---

### Task 4: Glossary (user gate)

**Files:**
- Create: `glossary.md`

- [ ] **Step 1: Count katakana terms and speaker ids**

```bash
python -c "
import re, json, collections, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
terms, speakers = collections.Counter(), collections.Counter()
for p in sorted(Path('script/SCENARIO').glob('*.json')):
    for e in json.loads(p.read_text(encoding='utf-8')):
        jp = ' '.join(e['jp']) if isinstance(e['jp'], list) else e['jp']
        terms.update(re.findall(r'[ァ-ヺー]{2,}', jp))
        if isinstance(e['jp'], list) and e.get('speaker') is not None:
            speakers[e['speaker']] += 1
Path('work/terms.txt').write_text('\n'.join(f'{n}\t{t}' for t, n in terms.most_common()), encoding='utf-8')
print(len(terms), 'terms;', 'speakers:', sorted(speakers.items()))
"
head -60 work/terms.txt
```
Expected: a few hundred terms; the top of the list is character and place names.

- [ ] **Step 2: Write `glossary.md`**

Sections, in this order:

1. **Style** — the rules from the spec: honorifics kept and hyphenated (`-san`, `-sama`, `-chan`, `-kun`, `-dono`); `・・・` → `...`; `～` → `~` after a vowel or dropped; `！？` → `!?`; `「」` → `"`; ASCII 0x20–0x7E only; a window is one utterance, wrap freely; prefer two lines where the Japanese used two; third person pronouns follow the character's established gender once known.
2. **Names** — a table `Japanese | English | notes` for every term with 20 or more occurrences, plus any term from the pilot scripts (`000`–`020`) that is clearly a name. Propose romanisations; mark uncertain ones `?`.
3. **Terms** — game terms (`ブラックマトリクス`, item and class names) in the same table form.
4. **Speakers** — `id | name | evidence`, filled in during Task 5; start it with the ids from Step 1 and `?` names.

- [ ] **Step 3: User approval**

Show the Names and Terms tables to the user and ask for corrections. Do not start Task 5 until they approve.

- [ ] **Step 4: Commit**

```bash
git add glossary.md
git commit -m "Add glossary and style guide"
```

---

### Task 5: Pilot translation of the opening

**Files:**
- Modify: `script/SCENARIO/000.json` and the opening scripts, `glossary.md` (speaker table)
- Create: `docs/style-reference.md`

- [ ] **Step 1: Translate `000.json`**

```bash
python tl.py show 000 > work/tl/000.src.txt
```
Write `work/tl/000.txt` with one `id<TAB>en` line per entry of `000.src.txt` (every variant of the boot warning, and whatever else is there), then:

```bash
python tl.py apply 000 work/tl/000.txt && python build.py
```
Expected: no `unknown id` lines; the warning windows that wrap to three lines or fewer are not listed as `spilled`.

- [ ] **Step 2: Find and translate the opening**

Scripts whose first four bytes are `02 00 00 00` are story scripts (289 of them); `01 00 03 00` and `0a 00 00 00` are system and menu scripts. Starting from the lowest-numbered story script, `show` it, translate every window and string with the glossary at hand, `apply`, and continue until roughly 400 windows are done. Keep each script's answer file in `work/tl/`. Note every speaker id and the name it must be (the speaker's lines make it obvious) in `glossary.md`'s Speakers table.

```bash
python -c "
import dat; from build import ORIG
subs = dat.unpack((ORIG/'SCENARIO.DAT').read_bytes())
print([i for i, b in enumerate(subs) if b[:4] == bytes.fromhex('02000000')][:12])
"
```

- [ ] **Step 3: Build and hand over**

Run: `python build.py`
Expected: no `too wide` lines; any `spilled` lines are reviewed and tightened unless the text needs them.

Ask the user to play from a new game and report: the last scene with English text and the first Japanese one after it; any line that reads wrong, overflows, or breaks; names that should change.

- [ ] **Step 4: Iterate**

Translate the next scripts the user names (or the next story scripts in order if the opening ran out before English did), fix reported lines, update the glossary, rebuild. Stop after the second round or when the user has played a continuous English opening.

- [ ] **Step 5: Write `docs/style-reference.md`**

Ten to twenty representative windows as `jp` / `en` pairs that show: honorific handling, a spilled window, an exclamation with `!?`, an ellipsis, a name with a title, a menu choice, and one line the user corrected with why. This is the brief for the scale-up plan's translators.

- [ ] **Step 6: Commit**

```bash
git add script glossary.md docs/style-reference.md
git commit -m "Pilot translation of the opening"
```
