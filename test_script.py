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


def test_decode_encode_keeps_odd_bytes():
    raw = bytes.fromhex("82a0 81f4 0506 82a2 7b7d")       # control bytes and braces, in whole cells
    assert script.encode(script.decode(raw)) == raw
    assert "{" not in script.decode(bytes.fromhex("82a0"))


def test_padding_counts_escaped_bytes():
    jp = bytes.fromhex("82a0")
    assert script.encode("a{7B}b" + jp.decode("cp932")) == b"a{b " + jp
    assert script.encode("ab{41}" + jp.decode("cp932")) == b"abA " + jp
    assert len(script.encode("x" * 45 + "{41}")) == 46


def test_encode_rejects_control_and_halfwidth_kana():
    for bad in ("a" + chr(9) + "b", "a" + chr(10) + "b", chr(0xFF71)):
        try:
            script.encode(bad)
        except ValueError:
            continue
        assert False, repr(bad)


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
            jp = "\n".join(e["jp"]) if isinstance(e["jp"], list) else e["jp"]
            e["en"] = jp + "　　　"     # 6 bytes: flips u32 alignment, never spills
        old, new = script.tokenize(b), script.tokenize(script.insert(b, entries))
        assert len(old) == len(new), i
        moved = {o.off: n.off for o, n in zip(old, new)}
        moved[script.used_length(b)] = new[-1].off + len(new[-1].raw)
        for o, n in zip(old, new):
            assert o.raw[:2] == n.raw[:2], (i, hex(o.off))
            for jo, jn in zip(o.jumps, n.jumps):
                was = struct.unpack_from("<I", o.raw, jo)[0]
                now = struct.unpack_from("<I", n.raw, jn)[0]
                assert now == moved[was], (i, hex(o.off))


def test_odd_length_string_keeps_even_alignment():
    i, b = SCRIPTS[0]
    entries = script.extract(b, "S")
    entries[0]["en"] = "abc"
    toks = script.tokenize(script.insert(b, entries))
    assert all(t.off % 2 == 0 for t in toks)
    assert next(t.text for t in toks if t.text is not None) == b"abc "


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


def test_script_past_pc_range_raises():
    i, b = SCRIPTS[0]
    entries = script.extract(b, "S")
    entries[0]["en"] = "　" * 0x10000     # 128KB: beyond the u16 word program counter
    try:
        script.insert(b, entries)
    except ValueError:
        return
    assert False, "expected ValueError"


def _insert_raises(entries):
    try:
        script.insert(SCRIPTS[0][1], entries)
    except ValueError:
        return True
    return False


def test_id_matching_no_string_raises():
    assert _insert_raises([{"id": "SCENARIO/000/00002", "jp": "", "en": "ＡＢ"}])


def test_malformed_escape_raises():
    first = script.extract(SCRIPTS[0][1], "S")[0]
    for bad in ("{0a}", "{5}", "a{b", "a}b"):
        assert _insert_raises([{**first, "en": bad}]), bad


def test_zero_word_inside_string_raises():
    first = script.extract(SCRIPTS[0][1], "S")[0]
    assert _insert_raises([{**first, "en": "ＡＢ{00}{00}ＣＤ"}])


def test_ascii_runs_are_padded_to_even_length():
    assert script.encode("abc") == b"abc "
    assert script.encode("ab") == b"ab"
    assert script.encode("あabcい") == bytes.fromhex("82a0") + b"abc " + bytes.fromhex("82a2")   # JP stays on its 2-byte grid
    assert script.encode("aあb") == b"a " + bytes.fromhex("82a0") + b"b "


def test_no_original_string_exceeds_23_cells():
    longest = max(len(t.text) for i, b in SCRIPTS for t in script.tokenize(b) if t.text is not None)
    assert longest <= script.MAX_CELLS * 2, longest


def test_line_over_23_cells_raises_and_23_passes():
    first = script.extract(SCRIPTS[0][1], "S")[0]
    script.insert(SCRIPTS[0][1], [{**first, "en": "x" * 46}])
    assert _insert_raises([{**first, "en": "x" * 47}])


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


def _window(entries):
    """First spillable window with at least two lines."""
    return next(e for e in entries if isinstance(e["jp"], list) and len(e["jp"]) >= 2 and "spill" not in e)


def test_wrap_breaks_at_spaces_within_30_bytes():
    assert script.wrap("Keep the room bright when you play!") == ["Keep the room bright when you", "play!"]   # 29 chars + pad = 30
    assert script.wrap("one\ntwo three") == ["one", "two three"]
    assert script.wrap("a\n\nb\n") == ["a", "b"]                     # no blank lines
    assert script.wrap("x" * 31) == ["x" * 31]                         # long word stays whole
    assert script.wrap("abc {41}" + "c" * 26) == ["abc", "{41}" + "c" * 26]   # 3+1+27 = 31 bytes: breaks
    assert script.wrap("{41}" + "c" * 29) == ["{41}" + "c" * 29]              # escape is one byte, 30 fits


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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
