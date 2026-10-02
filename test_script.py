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
            e["en"] = e["jp"] + "　　　"     # 6 bytes: flips u32 alignment
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


def test_too_wide_lists_lines_past_the_window():
    entries = [{"id": "a", "jp": "", "en": "x" * 30}, {"id": "b", "jp": "", "en": "x" * 31},
               {"id": "c", "jp": "", "en": ""}]
    assert script.too_wide(entries) == ["b"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
