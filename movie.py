"""FMV subtitles: cue JSON -> ASS -> frames burned by ffmpeg -> replaced in the STR by jPSXdec.
  python movie.py transcribe BMM_001 ...   write script/MOVIE/<name>.json from Whisper (never overwrites)"""
import hashlib, json, shutil, struct, subprocess, sys, tempfile, textwrap
from pathlib import Path

ROOT = Path(__file__).parent
JAR = ROOT / "tools" / "jpsxdec" / "jpsxdec_v2.0" / "jpsxdec.jar"
FRAME_BASE = 0                         # jPSXdec's frame="N" is 0-based, like ffmpeg's output (docs/movie-notes.md)
CACHE = ROOT / "work" / "movie" / "cache"

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
    """Merged frame ranges covered by translated cues (floor of start, ceiling of end), clamped to the stream."""
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


def frame_count(data: bytes) -> int:
    n = 0
    for i in range(0, len(data), SECTOR):
        s = data[i:i + SECTOR]
        if not s[2] & 4 and s[8:10] == bytes([0x60, 0x01]):
            n = max(n, struct.unpack_from("<I", s, 16)[0])
    return n


def patch(src: Path, cues: list, dst: Path) -> None:
    """Copy of the stream with the cues burned in. Only frames inside cue ranges are re-encoded."""
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
        # cwd = temp dir: the subtitles filter then needs no drive-letter escaping, and
        # jPSXdec resolves the stream and the PNGs relative to it
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "psxstr", "-i", "in.bin",
                        "-vf", "subtitles=cues.ass", "-start_number", "0", "f/%05d.png"], cwd=d, check=True)
        xml = ['<?xml version="1.0"?>', '<str-replace version="0.3">']
        xml += [f'  <replace frame="{n + FRAME_BASE}">f/{n:05d}.png</replace>' for r in ranges for n in r]
        (d / "replace.xml").write_text("\n".join(xml + ["</str-replace>"]), encoding="utf-8")
        shutil.copyfile(src, d / "movie.STR")
        for args in (["-f", "movie.STR", "-x", "movie.idx"],
                     ["-x", "movie.idx", "-i", "0", "-replaceframes", "replace.xml"]):
            run = subprocess.run(["java", "-jar", str(JAR), *args], cwd=d, capture_output=True, text=True)
            if run.returncode:
                raise RuntimeError(f"{src.name}: jPSXdec failed\n{run.stdout[-2000:]}{run.stderr[-2000:]}")
        out = (d / "movie.STR").read_bytes()
    if len(out) != len(data):
        raise ValueError(f"{src.name}: size changed {len(data)} -> {len(out)}")
    if out == data:                                # jPSXdec exits 0 when no frame number matched
        raise RuntimeError(f"{src.name}: jPSXdec replaced nothing; the stream would ship without subtitles")
    dst.write_bytes(out)


def cache_path(src: Path, cues: list) -> Path:
    h = hashlib.sha1(src.read_bytes())
    h.update(json.dumps(cues, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    h.update(HEADER.encode())                      # a style change re-renders everything
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


def transcribe(name: str) -> list:
    """Whisper segments of <name>.STR (Disc 1 copy, else Disc 2) as untranslated cues."""
    from faster_whisper import WhisperModel
    src = next(p for p in (ROOT / "work" / d / "MOVIE" / f"{name}.STR" for d in ("orig", "orig2")) if p.exists())
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "in.bin").write_bytes(wrap(src.read_bytes()))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "psxstr", "-i", "in.bin", "-vn",
                        "-ar", "16000", "-ac", "1", "a.wav"], cwd=d, check=True)
        model = WhisperModel("large-v3", device="cpu", compute_type="int8")   # cuBLAS/cuDNN are not installed here
        import wave
        import numpy as np
        with wave.open(str(d / "a.wav")) as w:           # samples, not a path: skips faster-whisper's PyAV loader
            audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        # no VAD filter: it drops speech under music (it hid half of BMM_005)
        segments, _ = model.transcribe(audio, language="ja", vad_filter=False, beam_size=8, word_timestamps=True,
                                       condition_on_previous_text=False)
        words = [(w.start, w.end, w.word) for s in segments for w in s.words]
    num = name.split("_")[1]
    return [{"id": f"MOVIE/{num}/{i:02d}", "start": round(a, 2), "end": round(b, 2), "jp": t, "en": ""}
            for i, (a, b, t) in enumerate(phrases(words))]


def phrases(words: list, gap: float = 0.6) -> list:
    """(start, end, text) runs of words: Whisper segments can span a minute of music, so cut at pauses."""
    out = []
    for a, b, t in words:
        if out and a - out[-1][1] <= gap:
            out[-1][1] = b
            out[-1][2] += t
        else:
            out.append([a, b, t])
    return [(a, b, t.strip()) for a, b, t in out if t.strip()]


if __name__ == "__main__":
    if sys.argv[1:2] != ["transcribe"]:
        sys.exit(__doc__)
    for name in sys.argv[2:]:
        out = ROOT / "script" / "MOVIE" / f"{name}.json"
        if out.exists():
            print("exists, skipped:", out)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(transcribe(name), ensure_ascii=False, indent=1), encoding="utf-8")
        print(out)
