"""SYSTEM.DAT sub-file 10: option messages, memory-card messages and chapter titles.

Three message runs, each a sequence of zero-terminated Shift-JIS strings (2-byte
aligned) that ends at the first byte that is not a Shift-JIS lead. A record may be
preceded by 4-byte-aligned u32 pointers to other messages and (run 2) followed by a
pointer to itself. All pointers are BASE + offset. Each run is boxed in by other
data, so a string that no longer fits its run is placed in the zero tail of the
sub-file and every pointer to it follows."""
import struct

from script import decode, encode

BASE = 0x800D4000
RUN_STARTS = (0x000, 0x178, 0x6B4)


def _lead(c: int) -> bool:
    return 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC


def _pointer_at(b: bytes, o: int) -> int | None:
    if o % 4 or o + 4 > len(b):
        return None
    v = struct.unpack_from("<I", b, o)[0]
    return v - BASE if BASE <= v < BASE + len(b) else None


def _messages(b: bytes, start: int):
    """Records of a run: (offset of text, text, pre-pointer targets, has self pointer,
    trailing zero bytes); then ("end", offset) where the run stops."""
    p = start
    while True:
        pre = []
        while (t := _pointer_at(b, p)) is not None:
            pre.append(t)
            p += 4
        if p >= len(b) or not _lead(b[p]):
            yield "end", p - 4 * len(pre)
            return
        e = b.find(b"\0\0", p)
        e += e % 2
        text = b[p:e]
        q = e + 2
        aligned = q
        while aligned % 4 and b[aligned:aligned + 2] == b"\0\0":
            aligned += 2
        selfptr = _pointer_at(b, aligned) == p
        if selfptr:
            q = aligned + 4
        z = q
        while b[z:z + 2] == b"\0\0" and z + 2 <= len(b) and not _lead(b[z]) and _pointer_at(b, z) is None:
            z += 2
        yield p, text, pre, selfptr, z - q
        p = z


def _runs(b: bytes):
    for start in RUN_STARTS:
        items = list(_messages(b, start))
        yield start, items[:-1], items[-1][1]


def extract(b: bytes, prefix: str) -> list[dict]:
    return [{"id": f"{prefix}/{off:05x}", "jp": decode(text), "en": ""}
            for _, items, _ in _runs(b) for off, text, _, _, _ in items]


def insert(b: bytes, entries: list[dict]) -> bytes:
    english = {int(e["id"].rsplit("/", 1)[1], 16): e for e in entries if e["en"]}
    out = bytearray(b)
    tail = (len(b.rstrip(b"\0")) + 3) & ~3          # free space starts here
    moved, spans, fixups = {}, [], []                # fixups: (position, original target)

    def record(at, off, text, pre, selfptr, zeros):
        """Bytes of one record laid out at `at`; registers fixups and the move."""
        rec = bytearray()
        for t in pre:
            fixups.append((at + len(rec), t))
            rec += struct.pack("<I", BASE + t)
        moved[off] = at + len(rec)
        rec += text + b"\0" * (len(text) % 2) + b"\0\0"
        if selfptr:
            rec += b"\0" * (-(at + len(rec)) % 4)
            fixups.append((at + len(rec), off))
            rec += struct.pack("<I", BASE + off)
        return rec + b"\0" * zeros

    for start, items, end in _runs(b):
        pos, overflow = start, []
        for off, text, pre, selfptr, zeros in items:
            if off in english:
                try:
                    text = encode(english[off]["en"])
                except ValueError as err:
                    raise ValueError(f'{english[off]["id"]}: {err}') from None
            saved = (dict(moved), list(fixups))
            rec = record(pos, off, text, pre, selfptr, zeros)
            if pos + len(rec) <= end:
                out[pos:pos + len(rec)] = rec
                pos += len(rec)
            else:
                moved.clear(); moved.update(saved[0]); fixups[:] = saved[1]
                overflow.append((off, text, pre, selfptr))
        out[pos:end] = b"\0" * (end - pos)
        spans.append((start, end))
        for off, text, pre, selfptr in overflow:
            rec = record(tail, off, text, pre, selfptr, 0)
            rec += b"\0" * (-len(rec) % 4)
            if tail + len(rec) > len(out):
                raise ValueError(f"no free space left in sub-file 10 for message {off:#x}")
            out[tail:tail + len(rec)] = rec
            tail += len(rec)
    for o in range(0, len(out) - 3, 4):
        if any(lo <= o < hi for lo, hi in spans) or o >= (len(b.rstrip(b"\0")) + 3) & ~3:
            continue
        target = _pointer_at(b, o)
        if target is not None and any(lo <= target < hi for lo, hi in spans):
            fixups.append((o, target))
    for pos, target in fixups:
        if target not in moved:
            raise ValueError(f"pointer at {pos:#x} targets {target:#x}, which is not a message")
        struct.pack_into("<I", out, pos, BASE + moved[target])
    return bytes(out)
