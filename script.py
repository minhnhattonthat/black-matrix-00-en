"""SCENARIO script bytecode: tokenize, extract strings, reinsert with jump fixups.
Format notes: docs/script-format.md"""
import re
import struct
from dataclasses import dataclass

# Operand signature per opcode, read off the interpreter's handlers:
#   w  u16
#   L  u32 absolute byte offset into the script (a jump), 4-byte aligned
#   S  Shift-JIS string, ends at the first zero u16
#   E  expression, ends at a zero u16
OPS = {
    0x0000: "", 0x0001: "wwE", 0x0002: "LE", 0x0003: "L", 0x0009: "E", 0x000A: "L",
    0x000B: "", 0x000C: "wwwL", 0x000D: "E", 0x000E: "E", 0x000F: "",
    0x1000: "E", 0x1001: "EE", 0x1004: "", 0x1005: "E", 0x1006: "", 0x1008: "",
    0x1009: "", 0x100A: "", 0x1020: "E", 0x1021: "E", 0x1022: "E", 0x1023: "E",
    0x1024: "EEEE", 0x1025: "EEEEE", 0x1026: "E", 0x1028: "EEEEE", 0x1029: "",
    0x102A: "", 0x1040: "E", 0x1041: "", 0x1042: "", 0x1043: "E", 0x1044: "EE",
    0x1045: "", 0x1046: "www", 0x1047: "EE", 0x1048: "EE", 0x1050: "S", 0x1051: "",
    0x1052: "EE", 0x1053: "E", 0x1054: "EEEE", 0x1055: "E", 0x1056: "", 0x1057: "E",
    0x1058: "E", 0x1059: "", 0x105A: "", 0x105B: "SL", 0x105C: "", 0x105D: "",
    0x105E: "", 0x105F: "", 0x1060: "", 0x1061: "L", 0x1062: "L", 0x1063: "E",
    0x1064: "E", 0x1065: "E", 0x1070: "", 0x1071: "EE", 0x1072: "EE", 0x1073: "ES",
    0x1075: "", 0x1080: "", 0x1081: "SL", 0x1082: "L", 0x1083: "", 0x1084: "EEEEE",
    0x1085: "EEE", 0x1086: "EE", 0x1087: "EE", 0x1088: "E", 0x1089: "E",
    0x108A: "SLLE", 0x108B: "", 0x108C: "", 0x108D: "E", 0x108E: "EE", 0x108F: "S",
    0x2002: "E", 0x2003: "", 0x2004: "E", 0x2005: "E", 0x2006: "", 0x2007: "EE",
    0x2008: "E", 0x2009: "E", 0x200A: "E", 0x200B: "E", 0x200C: "E", 0x2010: "EEEE",
    0x2011: "E", 0x2012: "EEE", 0x2013: "EE", 0x2014: "EEEE", 0x2015: "E",
    0x2016: "EE", 0x2017: "EE", 0x2018: "EE", 0x2019: "E", 0x2020: "EE", 0x2021: "E",
    0x2022: "EE", 0x2024: "EE", 0x2028: "EEE", 0x2029: "E", 0x202A: "EE",
    0x202B: "E", 0x202C: "E", 0x202D: "EE", 0x202E: "EEE", 0x202F: "EE", 0x2030: "",
    0x2031: "E", 0x2032: "E", 0x2033: "EE", 0x2034: "EEE", 0x2035: "EE", 0x2036: "E",
    0x2037: "EEE", 0x2038: "EE", 0x2040: "E", 0x2041: "E", 0x2042: "E", 0x2043: "",
    0x2044: "E", 0x2048: "EEEE", 0x2049: "", 0x204A: "", 0x204B: "E", 0x204C: "EEEE",
    0x204D: "", 0x204E: "", 0x204F: "EEE", 0x2050: "", 0x2051: "", 0x2052: "EEEEE",
    0x2053: "", 0x2054: "",
    0x3000: "EEEEE", 0x3001: "", 0x3002: "EE", 0x3003: "", 0x3004: "", 0x3005: "E",
    0x3006: "www", 0x3007: "E", 0x3008: "", 0x3009: "www", 0x300A: "", 0x300C: "",
    0x300D: "", 0x300E: "", 0x300F: "", 0x3010: "", 0x3011: "EE", 0x3012: "EEEE",
    0x3013: "", 0x3014: "", 0x3018: "", 0x3019: "E", 0x301A: "EE", 0x301B: "",
    0x3020: "EEE", 0x3024: "EEEEEE", 0x3028: "EEEE", 0x3029: "EEEE", 0x302A: "E",
    0x302B: "E", 0x302C: "E", 0x302D: "EE", 0x302E: "E", 0x3030: "EE",
    0x3031: "EEE", 0x3032: "EE", 0x3033: "EEEEE", 0x3034: "EEEE", 0x3035: "E",
    0x3036: "EE", 0x3037: "EEE", 0x3038: "wwwE", 0x3039: "wwwE", 0x303A: "wwwE",
    0x303B: "wwwE", 0x303C: "wwwE", 0x303D: "wwwE", 0x303E: "wwwE", 0x3040: "EE",
    0x3041: "EE", 0x3042: "", 0x304C: "www", 0x304D: "www", 0x304E: "www",
    0x304F: "www", **{op: "" for op in range(0x3050, 0x3068)},
}


DIALOGUE_OP = 0x1050   # one window line; 1-3 in a row make a window
WAIT_OP = 0x000A       # call that shows the window and waits; copied when a window spills
SPEAKER_OP = 0x1058    # 1058 <imm>: speaker / portrait id, context for translators


def op(t: "Token") -> int:
    return struct.unpack_from("<H", t.raw)[0]


def _window_end(toks: list, k: int) -> int:
    while k < len(toks) and op(toks[k]) == DIALOGUE_OP:
        k += 1
    return k


@dataclass
class Token:
    off: int
    raw: bytes
    text: bytes | None = None
    jumps: tuple[int, ...] = ()
    # ("b", bytes) verbatim | ("s", text) string | ("u", bytes4) aligned u32 | ("j", bytes4) aligned jump
    parts: tuple = ()


def used_length(b: bytes) -> int:
    return (len(b.rstrip(b"\0")) + 1) & ~1


def _u16(b: bytes, p: int) -> int:
    return struct.unpack_from("<H", b, p)[0]


def _token_at(b: bytes, p: int) -> Token:
    op = _u16(b, p)
    if op not in OPS:
        raise ValueError(f"unknown op {op:#06x} at {p:#x}")
    q = p + 2
    parts, jumps, text = [("b", b[p:q])], [], None

    def u32(kind):
        nonlocal q
        q = (q + 3) & ~3
        if kind == "j":
            jumps.append(q - p)
        parts.append((kind, b[q:q + 4]))
        q += 4

    for c in OPS[op]:
        if c == "w":
            parts.append(("b", b[q:q + 2]))
            q += 2
        elif c == "L":
            u32("j")
        elif c == "S":
            end = q
            while _u16(b, end):
                end += 2
            text = b[q:end].rstrip(b"\0")
            parts.append(("s", text))
            q = end + 2
        else:  # E
            while True:
                item = _u16(b, q)
                parts.append(("b", b[q:q + 2]))
                q += 2
                if item == 0:
                    break
                if item in (1, 2, 3):      # imm16, var32 index, var16 index
                    parts.append(("b", b[q:q + 2]))
                    q += 2
                elif item == 4:            # imm32
                    u32("u")
    return Token(p, b[p:q], text, tuple(jumps), tuple(parts))


def tokenize(b: bytes) -> list[Token]:
    end = used_length(b)
    toks, p = [], 0
    while p < end:
        t = _token_at(b, p)
        toks.append(t)
        p += len(t.raw)
    return toks


_ESCAPE = re.compile(r"\{([0-9A-F]{2})\}")
MAX_CELLS = 23      # glyph slots in the game's text object; it does not bounds-check
WINDOW_CELLS = 15   # cells that fit the dialogue window; tune after an in-game look
_UNSUPPORTED = re.compile(r"[\x00-\x1f\x7f｡-ﾟ]")   # control chars, halfwidth kana


def decode(raw: bytes) -> str:
    """cp932 text; bytes that do not survive a decode/encode round trip become {XX}."""
    out, i = [], 0
    while i < len(raw):
        n = 2 if (0x81 <= raw[i] <= 0x9F or 0xE0 <= raw[i] <= 0xFC) else 1
        chunk = raw[i:i + n]
        try:
            s = chunk.decode("cp932")
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
        elif "{" in part or "}" in part:
            raise ValueError(f"malformed escape in {part!r}; write a byte as {{XX}}, uppercase hex")
        else:
            bad = _UNSUPPORTED.search(part)
            if bad:
                raise ValueError(f"unsupported character {bad.group()!r}; write a raw byte as {{XX}}")
            try:
                out += part.encode("cp932")
            except UnicodeEncodeError as e:
                raise ValueError(f"cannot encode {part[e.start:e.end]!r} in cp932") from None
    # Two single-byte characters share one glyph cell, so every run of them must fill
    # whole cells or the Shift-JIS characters after it fall off the 2-byte grid.
    padded, i = bytearray(), 0
    while i < len(out):
        if 0x81 <= out[i] <= 0x9F or 0xE0 <= out[i] <= 0xFC:
            padded += out[i:i + 2]
            i += 2
            continue
        start = i
        while i < len(out) and not (0x81 <= out[i] <= 0x9F or 0xE0 <= out[i] <= 0xFC):
            i += 1
        padded += out[start:i] + b" " * ((i - start) % 2)
    return bytes(padded)


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
        if op(t) != DIALOGUE_OP:
            emit(t, _line_bytes(e, e["en"]) if e else None)
            k += 1
            continue
        end = _window_end(toks, k)
        if e is None:                # untranslated window: copy its lines; only line 1 can own an id
            for x in toks[k:end]:
                moved[x.off] = len(out)
                emit(x)
            k = end
            continue
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

