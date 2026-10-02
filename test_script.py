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
