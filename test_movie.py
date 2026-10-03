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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
