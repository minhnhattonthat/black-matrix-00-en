"""The game's LZ packing (decoder at 0x800281AC in the executable), used for portrait files.

Stream: 3 bytes the decoder skips, then groups of a flag byte (bit 0 first) and 8 items:
  flag 1: a literal, stored XORed with the inverted low byte of the output position
  flag 0: a copy - one distance byte (distance - 1, so 1..256) and a 4-bit length - 2 (2..17);
          the length nibbles of two successive copies share one byte, low nibble first, which
          sits just before the first copy's distance byte
The unpacked data starts with its own length in 4-byte words (that word included)."""
import struct


def unpack(src: bytes) -> tuple[bytes, int]:
    """(unpacked data, number of packed bytes read)."""
    out = bytearray()
    p, flags, count, nibbles, half, limit = 3, 0, 0, 0, False, None
    while limit is None or len(out) < limit:
        if count & 7 == 0:
            flags = src[p]
            p += 1
        else:
            flags >>= 1
        count += 1
        if flags & 1:
            out.append(src[p] ^ ~len(out) & 0xFF)
            p += 1
        else:
            if half:
                nibbles >>= 4
            else:
                nibbles = src[p]
                p += 1
            half = not half
            distance = src[p] + 1
            p += 1
            for _ in range((nibbles & 15) + 2):
                out.append(out[-distance])
        if limit is None and len(out) >= 5:
            limit = struct.unpack_from("<I", out, 0)[0] * 4
    return bytes(out[:limit]), p


def pack(data: bytes, head: bytes = bytes(3)) -> bytes:
    """Greedy packer; `head` is the 3 bytes the decoder skips."""
    out = bytearray(head)
    n, pos = len(data), 0
    flag_at = nibble_at = None
    count = 0
    recent = {}                                    # 2-byte pair -> positions where it starts, oldest first

    def note(p):
        if p + 1 < n:
            recent.setdefault(data[p:p + 2], []).append(p)

    while pos < n:
        if count & 7 == 0:
            flag_at = len(out)
            out.append(0)
        best, dist = 0, 0
        starts = recent.get(data[pos:pos + 2], ())
        for q in reversed(starts):
            if pos - q > 256:
                break
            k = 2
            while k < 17 and pos + k < n and data[q + k] == data[pos + k]:
                k += 1
            if k > best:
                best, dist = k, pos - q
                if k == 17:
                    break
        if best >= 2:
            if nibble_at is None:
                nibble_at = len(out)
                out.append(best - 2)
            else:
                out[nibble_at] |= (best - 2) << 4
                nibble_at = None
            out.append(dist - 1)
            for p in range(pos, pos + best):
                note(p)
            pos += best
        else:
            out[flag_at] |= 1 << (count & 7)
            out.append(data[pos] ^ ~pos & 0xFF)
            note(pos)
            pos += 1
        count += 1
    return bytes(out)
