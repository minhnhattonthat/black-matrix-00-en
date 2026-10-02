"""SCENARIO script bytecode: tokenize, extract strings, reinsert with jump fixups.
Format notes: docs/script-format.md"""
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
