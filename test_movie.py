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


import struct, tempfile
from pathlib import Path
from build import ORIG

SRC = ORIG / "MOVIE" / "BMM_003.STR"               # 14 s, 210 frames


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
    assert len(changed) >= 10                           # the line is really burned across the cue


def test_cache_key_follows_cues():
    c1 = [{"id": "x", "start": 2.0, "end": 3.0, "jp": "", "en": "One"}]
    c2 = [{"id": "x", "start": 2.0, "end": 3.0, "jp": "", "en": "Two"}]
    assert movie.cache_path(SRC, c1) != movie.cache_path(SRC, c2)
    assert movie.cache_path(SRC, c1) == movie.cache_path(SRC, list(c1))


def test_phrases_cut_at_pauses():
    words = [(1.0, 1.2, "a"), (1.3, 1.5, "b"), (9.0, 9.4, "c"), (9.5, 9.9, "d "), (20.0, 20.1, " ")]
    assert movie.phrases(words) == [(1.0, 1.5, "ab"), (9.0, 9.9, "cd")]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
