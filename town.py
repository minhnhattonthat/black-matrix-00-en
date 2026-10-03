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
