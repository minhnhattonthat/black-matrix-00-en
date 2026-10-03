"""TOWN.DAT: nested containers (word offsets) holding two text leaves per town file.

Container: u16 count, u16 1, u32 2, then count x (u32 offset, u32 size) in 4-byte
words, entries contiguous right after the table. Anything else is a leaf."""
import struct

import script


def _table(b: bytes):
    """(offset, size) byte pairs if b starts with a container header, else None."""
    if len(b) < 8:
        return None
    n, one, ver = struct.unpack_from("<HHI", b, 0)
    if one != 1 or ver != 2 or n == 0 or 8 + 8 * n > len(b):
        return None
    pairs = [(o * 4, s * 4) for o, s in (struct.unpack_from("<II", b, 8 + 8 * i) for i in range(n))]
    pos = 8 + 8 * n
    for o, s in pairs:                       # contiguous, in range
        if o != pos or o + s > len(b):
            return None
        pos += s
    return pairs


def parse(b: bytes):
    """A leaf is bytes; a container is (children, tail), tail = bytes after the last entry."""
    pairs = _table(b)
    if pairs is None:
        return b
    children = [parse(b[o:o + s]) for o, s in pairs]
    end = pairs[-1][0] + pairs[-1][1]
    return children, b[end:]


def rebuild(node) -> bytes:
    if isinstance(node, bytes):
        return node
    children, tail = node
    blobs = [rebuild(c) for c in children]
    blobs = [x + bytes(-len(x) % 4) for x in blobs]
    out = bytearray(struct.pack("<HHI", len(blobs), 1, 2))
    pos = 8 + 8 * len(blobs)
    for x in blobs:
        out += struct.pack("<II", pos // 4, len(x) // 4)
        pos += len(x)
    for x in blobs:
        out += x
    return bytes(out) + tail


def text_entries(leaf: bytes):
    """[(lines, terminated) per entry] or None; lines = [(param, sjis), ...].
    Entry = (0001 [param] str 0000)* [0000]. The closing 0000 is missing on some
    entries (the shop list) and present on some empty ones, so it is kept as a flag."""
    if len(leaf) < 4 or len(leaf) % 2:
        return None
    first = struct.unpack_from("<H", leaf, 0)[0]
    if first < 2 or first % 2 or first > len(leaf):
        return None
    offs = [struct.unpack_from("<H", leaf, 2 * i)[0] for i in range(first // 2)] + [len(leaf)]
    if any(a > b for a, b in zip(offs, offs[1:])):
        return None
    entries = []
    for a, b in zip(offs, offs[1:]):
        e, pos, lines, terminated = leaf[a:b], 0, [], False
        while pos < len(e):
            op = struct.unpack_from("<H", e, pos)[0]
            pos += 2
            if op == 0:
                if pos != len(e):
                    return None
                terminated = True
                break
            if op != 1 or pos + 2 > len(e):
                return None
            param = None
            if e[pos + 1] == 0 and e[pos] < 0x20:      # a string never starts with a control byte
                param, pos = e[pos], pos + 2
            end = pos
            while e[end:end + 2] != b"\0\0":
                end += 2
                if end >= len(e):
                    return None
            lines.append((param, e[pos:end]))
            pos = end + 2
        entries.append((lines, terminated))
    return entries


def text_leaf(entries) -> bytes:
    body, offs, pos = bytearray(), [], 2 * len(entries)
    for lines, terminated in entries:
        offs.append(pos)
        e = bytearray()
        for param, s in lines:
            assert len(s) % 2 == 0 and b"\0\0" not in s
            e += b"\x01\x00" + (struct.pack("<H", param) if param is not None else b"") + s + b"\0\0"
        if terminated:
            e += b"\0\0"
        body += e
        pos += len(e)
    if pos > 0xFFFF:
        raise ValueError(f"text leaf too large: {pos} bytes")
    return b"".join(struct.pack("<H", o) for o in offs) + bytes(body)
