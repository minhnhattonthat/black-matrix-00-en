# Movie Subtitles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Burn English subtitles into the Disc 1 FMV streams (`MOVIE/*.STR`) from cue files in `script/MOVIE/`.

**Architecture:** `movie.py` turns cue JSON into an ASS subtitle file, has ffmpeg decode the stream with the subtitles burned in, and has jPSXdec replace only the frames inside cue ranges in a copy of the STR. Patched streams are cached by content hash; `build.patch()` copies cached or original streams into the build tree. Japanese source text comes from faster-whisper transcription, corrected and translated by Claude.

**Tech Stack:** Python 3.12 stdlib, ffmpeg (installed), Java 8 + jPSXdec 2.0 (`tools/jpsxdec/`), faster-whisper (pip, transcription only).

**Spec:** `docs/superpowers/specs/2026-10-04-movie-subtitles-design.md`

## Global Constraints

- Streams are 320x240, 15 fps, 2336-byte sectors; a patched stream keeps its exact size.
- Audio sectors and frames outside cue ranges stay byte-identical.
- Subtitles: bottom-centred, white, dark outline, at most 2 lines of 42 characters; a cue needing 3 lines raises.
- A cue with empty `en` is not burned; a movie with no translated cues is copied unchanged.
- Cue times are seconds from stream start; ids are `MOVIE/NNN/II`.
- The identity build (`test_build.py`) stays byte-identical for both discs.
- `tools/` and `work/` are git-ignored; only `movie.py`, tests, `script/MOVIE/*.json`, docs are committed.
- Commit after each task with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Review Focus

1. Two cues that overlap or touch must yield one merged frame range, not duplicate frame replacements.
2. A cue ending past the last frame must be clamped to the stream length, not ask jPSXdec for a missing frame.
3. English text containing ASS control characters (`{`, `}`, `\`) must be rejected, not interpreted as override tags.
4. A cue edit must invalidate the cache (hash covers cue content and source stream).
5. A stale `EXTRACTED/MOVIE` file from an earlier patched build must not leak into the identity build.

---

### Task 1: Tools and feasibility probe

**Files:**
- Create: `tools/jpsxdec/` (download, git-ignored), `docs/movie-notes.md`

- [ ] **Step 1:** Download and unpack jPSXdec:
  `curl -L -o work/jpsxdec.zip https://github.com/m35/jpsxdec/releases/download/v2.0/jpsxdec_v2.0.zip && unzip -o work/jpsxdec.zip -d tools/jpsxdec` then locate `jpsxdec.jar` (`find tools/jpsxdec -name jpsxdec.jar`). Run `java -jar <jar> -?` and confirm it prints help.
- [ ] **Step 2:** `pip install faster-whisper`; run `python -c "from faster_whisper import WhisperModel; print('ok')"`.
- [ ] **Step 3:** Probe replace on a copy: copy `work/orig`-equivalent `work/extracted/MOVIE/BMM_003.STR` (14 s) to `work/movie/probe.STR`; `java -jar <jar> -f work/movie/probe.STR -x work/movie/probe.idx` and print the index. Record: does it index a bare 2336-byte stream; the item number of the video; the frame numbering shown (first frame 0 or 1).
- [ ] **Step 4:** Decode frame 30 with ffmpeg from the 2352-wrapped copy, draw a white box on it (`ffmpeg -vf drawbox`), write `work/movie/probe/f30.png`, and an XML:
  ```xml
  <?xml version="1.0"?>
  <str-replace version="0.3">
    <replace frame="30">f30.png</replace>
  </str-replace>
  ```
  Run `java -jar <jar> -x work/movie/probe.idx -i <item> -replaceframes work/movie/probe/replace.xml`. Verify: file size unchanged; decode frame 30 again and see the box; frames 29/31 sectors unchanged; audio sectors unchanged (compare with the script from Task 3's test).
- [ ] **Step 5:** If the bare STR cannot be indexed, repeat on the 2352-wrapped copy and unwrap afterwards. Write the outcome (which form works, item number, frame numbering offset between ffmpeg's 0-based frames and jPSXdec's `frame=` value, jar path) into `docs/movie-notes.md`. Later tasks use these as constants `JAR`, `FRAME_BASE`, `WRAPPED`.
- [ ] **Step 6:** Commit `docs/movie-notes.md`.

### Task 2: Sector wrapping, frame ranges, ASS generation

**Files:**
- Create: `movie.py`, `test_movie.py`

**Interfaces:**
- Produces: `wrap(str_bytes) -> bytes` (2336 -> 2352 sectors), `unwrap(raw) -> bytes`, `frames(cues, total, fps=15) -> list[range]`, `ass(cues) -> str`.

- [ ] **Step 1: Failing tests**

```python
import movie

CUES = [{"id": "MOVIE/001/00", "start": 1.0, "end": 2.5, "jp": "a", "en": "Hello there."},
        {"id": "MOVIE/001/01", "start": 2.4, "end": 3.0, "jp": "b", "en": "Second line."},
        {"id": "MOVIE/001/02", "start": 5.0, "end": 6.0, "jp": "c", "en": ""}]


def test_wrap_round_trip():
    s = bytes(range(256)) * 9 + bytes(32)          # 2336 bytes
    raw = movie.wrap(s * 3)
    assert len(raw) == 3 * 2352 and raw[:12] == bytes([0] + [255] * 10 + [0]) and raw[15] == 2
    assert movie.unwrap(raw) == s * 3


def test_frames_merges_overlaps_skips_untranslated_and_clamps():
    assert movie.frames(CUES, total=600) == [range(15, 45)]          # 1.0s..3.0s merged; cue 2 has no en
    late = [{"id": "x", "start": 39.0, "end": 45.0, "jp": "", "en": "End"}]
    assert movie.frames(late, total=600) == [range(585, 600)]        # clamped to the stream


def test_ass_document():
    doc = movie.ass(CUES)
    assert "PlayResX: 320" in doc and "PlayResY: 240" in doc
    assert "Dialogue: 0,0:00:01.00,0:00:02.50,Default,,0,0,0,,Hello there." in doc
    assert doc.count("Dialogue:") == 2                                # empty en skipped
    long = [{"id": "x", "start": 0, "end": 1, "jp": "", "en": "word " * 12}]
    assert "\\N" in movie.ass(long)                                   # wrapped at 42
    for bad in ("word " * 30, "a {b} c", "back\\slash"):
        try:
            movie.ass([{"id": "x", "start": 0, "end": 1, "jp": "", "en": bad}])
        except ValueError as err:
            assert "x" in str(err)
        else:
            assert False, bad
```

- [ ] **Step 2:** `python test_movie.py` fails: no module `movie`.
- [ ] **Step 3: Implement**

```python
"""FMV subtitles: cue JSON -> ASS -> frames burned by ffmpeg -> replaced by jPSXdec."""
import textwrap

SECTOR, RAW = 2336, 2352
SYNC = bytes([0] + [0xFF] * 10 + [0])
FPS, WIDTH, MAX_LINES = 15, 42, 2


def _bcd(x: int) -> int:
    return (x // 10) << 4 | x % 10


def wrap(data: bytes) -> bytes:
    """2336-byte Form 2 sectors -> 2352-byte raw sectors (what ffmpeg's psxstr demuxer reads)."""
    out = bytearray()
    for i in range(len(data) // SECTOR):
        lba = i + 150
        out += SYNC + bytes([_bcd(lba // 4500), _bcd(lba // 75 % 60), _bcd(lba % 75), 2])
        out += data[i * SECTOR:(i + 1) * SECTOR]
    return bytes(out)


def unwrap(raw: bytes) -> bytes:
    return b"".join(raw[i + 16:i + RAW] for i in range(0, len(raw), RAW))


def frames(cues: list, total: int, fps: int = FPS) -> list:
    """Merged frame ranges covered by translated cues, clamped to the stream."""
    spans = sorted((int(c["start"] * fps), min(total, -int(-c["end"] * fps // 1)))
                   for c in cues if c["en"])
    out = []
    for lo, hi in spans:
        if lo >= hi:
            continue
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [range(lo, hi) for lo, hi in out]


def _time(t: float) -> str:
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 320
PlayResY: 240
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,13,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,1.5,0,2,8,8,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ass(cues: list) -> str:
    lines = []
    for c in cues:
        if not c["en"]:
            continue
        if any(ch in c["en"] for ch in "{}\\"):
            raise ValueError(f'{c["id"]}: ASS control character in text')
        rows = [r for para in c["en"].split("\n") for r in textwrap.wrap(para, WIDTH)]
        if len(rows) > MAX_LINES:
            raise ValueError(f'{c["id"]}: {len(rows)} lines, at most {MAX_LINES}')
        lines.append(f'Dialogue: 0,{_time(c["start"])},{_time(c["end"])},Default,,0,0,0,,' + "\\N".join(rows))
    return HEADER + "\n".join(lines) + "\n"
```

- [ ] **Step 4:** `python test_movie.py` passes (fix the frame-range expectation only if the rounding rule floor(start)/ceil(end) gives a different, still-correct number; the rule is the spec).
- [ ] **Step 5:** Commit `movie.py test_movie.py`.

### Task 3: patch() with cache

**Files:**
- Modify: `movie.py`, `test_movie.py`

**Interfaces:**
- Consumes: `wrap`, `unwrap`, `frames`, `ass`; constants from `docs/movie-notes.md` (`JAR`, `FRAME_BASE`, whether jPSXdec works on the bare or wrapped stream).
- Produces: `frame_count(data) -> int`, `patch(src: Path, cues: list, dst: Path) -> None`, `cached(src: Path, cues: list) -> Path`.

- [ ] **Step 1: Failing tests** (integration; uses the real 14 s stream)

```python
import struct, tempfile
from pathlib import Path
from build import EXTRACTED

SRC = EXTRACTED / "MOVIE" / "BMM_003.STR"


def _sectors(data):
    return [data[i:i + 2336] for i in range(0, len(data), 2336)]


def test_patch_without_cues_is_identity_and_with_cues_touches_only_cue_frames():
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "out.STR"
        movie.patch(SRC, [], out)
        assert out.read_bytes() == SRC.read_bytes()
        cues = [{"id": "MOVIE/003/00", "start": 2.0, "end": 3.0, "jp": "", "en": "Subtitle probe line"}]
        movie.patch(SRC, cues, out)
        a, b = _sectors(SRC.read_bytes()), _sectors(out.read_bytes())
    assert len(a) == len(b)
    changed = set()
    for x, y in zip(a, b):
        if x[2] & 4:                                   # audio sector
            assert x == y
        elif x != y:
            changed.add(struct.unpack_from("<I", x, 16)[0])      # frame number in the STR header (1-based)
    assert changed and all(31 <= f <= 45 for f in changed), sorted(changed)[:5]   # 0-based 30..44


def test_cache_key_follows_cues():
    c1 = [{"id": "x", "start": 2.0, "end": 3.0, "jp": "", "en": "One"}]
    c2 = [{"id": "x", "start": 2.0, "end": 3.0, "jp": "", "en": "Two"}]
    assert movie.cache_path(SRC, c1) != movie.cache_path(SRC, c2)
    assert movie.cache_path(SRC, c1) == movie.cache_path(SRC, list(c1))
```

- [ ] **Step 2:** Run: fails with `AttributeError: patch`.
- [ ] **Step 3: Implement** (adjust the two marked lines to the Task 1 findings)

```python
import hashlib, json, shutil, struct, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).parent
JAR = ROOT / "tools" / "jpsxdec" / "jpsxdec.jar"         # path recorded in docs/movie-notes.md
FRAME_BASE = 1                                            # jPSXdec frame number of ffmpeg's frame 0 (movie-notes.md)
CACHE = ROOT / "work" / "movie" / "cache"


def frame_count(data: bytes) -> int:
    n = 0
    for i in range(0, len(data), SECTOR):
        s = data[i:i + SECTOR]
        if not s[2] & 4 and s[8:10] == b"\x60\x01":
            n = max(n, struct.unpack_from("<I", s, 16)[0])
    return n


def patch(src: Path, cues: list, dst: Path) -> None:
    data = src.read_bytes()
    ranges = frames(cues, frame_count(data))
    if not ranges:
        shutil.copyfile(src, dst)
        return
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "in.bin").write_bytes(wrap(data))
        (d / "cues.ass").write_text(ass(cues), encoding="utf-8")
        (d / "f").mkdir()
        # cwd = temp dir so the subtitles filter gets a path with no drive colon
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "psxstr", "-i", "in.bin",
                        "-vf", "subtitles=cues.ass", "-start_number", "0", "f/%05d.png"], cwd=d, check=True)
        wanted = [n for r in ranges for n in r]
        xml = ['<?xml version="1.0"?>', '<str-replace version="0.3">']
        xml += [f'  <replace frame="{n + FRAME_BASE}">f/{n:05d}.png</replace>' for n in wanted]
        (d / "replace.xml").write_text("\n".join(xml + ["</str-replace>"]), encoding="utf-8")
        work = d / "movie.STR"                           # bare 2336 stream, or in.bin if notes say wrapped
        shutil.copyfile(src, work)
        subprocess.run(["java", "-jar", str(JAR), "-f", work.name, "-x", "movie.idx"], cwd=d, check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["java", "-jar", str(JAR), "-x", "movie.idx", "-i", "0", "-replaceframes", "replace.xml"],
                       cwd=d, check=True, stdout=subprocess.DEVNULL)
        out = work.read_bytes()
    if len(out) != len(data):
        raise ValueError(f"{src.name}: size changed {len(data)} -> {len(out)}")
    dst.write_bytes(out)


def cache_path(src: Path, cues: list) -> Path:
    h = hashlib.sha1(src.read_bytes())
    h.update(json.dumps(cues, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    h.update(HEADER.encode())
    return CACHE / f"{src.stem}-{h.hexdigest()[:16]}.STR"


def cached(src: Path, cues: list) -> Path:
    """Path of the patched stream, building it on a cache miss."""
    path = cache_path(src, cues)
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        patch(src, cues, tmp)
        tmp.replace(path)
    return path
```

- [ ] **Step 4:** Run `python test_movie.py`; all pass. If jPSXdec reports a frame that does not fit, lower the outline/size or shorten the test line; if frame numbers are off by one, fix `FRAME_BASE` per the notes.
- [ ] **Step 5:** Commit.

### Task 4: Transcription and build wiring

**Files:**
- Modify: `movie.py` (CLI `transcribe`), `build.py`, `test_build.py`
- Create: `script/MOVIE/BMM_0NN.json` (one per movie with speech)

**Interfaces:**
- Consumes: `movie.cached(src, cues)`.
- Produces: `build.patch_movies()`; `ORIG/MOVIE/*.STR` pristine copies.

- [ ] **Step 1:** `build.extract()` also copies `EXTRACTED/MOVIE` to `ORIG/MOVIE` (pristine). Do it once by hand now: `cp -r work/extracted/MOVIE work/orig/MOVIE` (current build tree is unpatched for movies).
- [ ] **Step 2:** Transcription CLI in `movie.py`:

```python
def transcribe(name: str) -> list:
    """Whisper segments of ORIG/MOVIE/<name>.STR as untranslated cues."""
    from faster_whisper import WhisperModel
    src = ROOT / "work" / "orig" / "MOVIE" / f"{name}.STR"
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "in.bin").write_bytes(wrap(src.read_bytes()))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "psxstr", "-i", "in.bin", "-vn",
                        "-ar", "16000", "-ac", "1", "a.wav"], cwd=d, check=True)
        model = WhisperModel("large-v3", device="cuda", compute_type="float16")
        segments, _ = model.transcribe(str(d / "a.wav"), language="ja", vad_filter=True)
        num = name.split("_")[1]
        return [{"id": f"MOVIE/{num}/{i:02d}", "start": round(s.start, 2), "end": round(s.end, 2),
                 "jp": s.text.strip(), "en": ""} for i, s in enumerate(segments)]


if __name__ == "__main__":
    import sys
    if sys.argv[1] == "transcribe":
        for name in sys.argv[2:]:
            out = ROOT / "script" / "MOVIE" / f"{name}.json"
            if out.exists():
                print("exists, skipped:", out); continue
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(transcribe(name), ensure_ascii=False, indent=1), encoding="utf-8")
            print(out)
```
  If CUDA is unavailable to ctranslate2, fall back to `device="cpu", compute_type="int8"` (slower, same output shape).
- [ ] **Step 3:** `build.patch_movies()`:

```python
def patch_movies():
    for src in sorted((ORIG / "MOVIE").glob("*.STR")):
        cue_file = SCRIPT / "MOVIE" / f"{src.stem}.json"
        cues = json.loads(cue_file.read_text(encoding="utf-8")) if cue_file.exists() else []
        shutil.copyfile(movie.cached(src, cues) if any(c["en"] for c in cues) else src,
                        EXTRACTED / "MOVIE" / src.name)
```
  Call it from `patch()`; `import movie`. In `test_build.py` restore movies before the identity build: `shutil.copytree(build.ORIG / "MOVIE", build.EXTRACTED / "MOVIE", dirs_exist_ok=True)`. Disc 2's tree (`work/d2/MOVIE`) is not touched by this plan.
- [ ] **Step 4:** Run `python movie.py transcribe BMM_001 BMM_002 BMM_003 BMM_004 BMM_005 BMM_006 BMM_007 BMM_011`; inspect each JSON. Make contact sheets and transcribe the short clips (`BMM_013..018`, `BMM_023..028`, `BMM_035`) too; record per movie in `docs/movie-notes.md`: speech yes/no, on-screen Japanese text.
- [ ] **Step 5:** All suites green (`test_build` identity for both discs). Commit code + raw transcripts.

### Task 5: Pilot (BMM_001) and user checkpoint

- [ ] **Step 1:** Correct the BMM_001 transcript against `glossary.md` and the scenario around the movie (grep `script/SCENARIO` for the lines' vocabulary); add `"check": true` to doubtful lines; translate `en` (2 lines x 42 max; split long cues in time rather than shrinking text).
- [ ] **Step 2:** `python test_build.py` first, then `python build.py`; extract three subtitled frames from the patched stream as PNG and look at them (legibility, position).
- [ ] **Step 3:** Commit. **Stop: ask the user to watch the movie in DuckStation** and report on readability, timing, and transcript accuracy. Apply style changes (font size, outline, margin) in `HEADER` before continuing.

### Task 6: Remaining movies, chapter cards, clips

- [ ] **Step 1:** Translate the other story movies the same way (correct, flag, translate), one commit per movie.
- [ ] **Step 2:** Chapter cards `BMM_013..018`: one cue each covering the time the Japanese title is visible, `en` = translated title (chapter titles already exist in `script/SYSTEM/messages.json`; reuse them verbatim).
- [ ] **Step 3:** Short clips: cues only where Task 4's notes found speech or Japanese text.
- [ ] **Step 4:** `python test_build.py`, then `python build.py`; list every `check` line for the user in the final message.

### Task 7: Docs, memory, review, merge

- [ ] **Step 1:** `docs/movie-notes.md`: final pipeline notes; `glossary.md`: any new terms; memory file: movies done, tools needed.
- [ ] **Step 2:** Fresh whole-branch review (superpowers:requesting-code-review), one fix pass, merge after the user's in-game confirmation.
