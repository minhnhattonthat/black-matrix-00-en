"""Black/Matrix 00 .DAT archive: u32 count, u32 sector shift (11),
count x (u16 sector offset, u16 sector count), padded to one sector."""
import struct

SECTOR = 2048


def unpack(data: bytes) -> list[bytes]:
    count, shift = struct.unpack_from("<II", data)
    if shift != 11:
        raise ValueError(f"unexpected sector shift {shift}")
    files = []
    for i in range(count):
        off, size = struct.unpack_from("<HH", data, 8 + 4 * i)
        files.append(data[off * SECTOR:(off + size) * SECTOR])
    return files


def pack(files: list[bytes]) -> bytes:
    if 8 + 4 * len(files) > SECTOR:
        raise ValueError(f"{len(files)} entries do not fit the one-sector table")
    header = bytearray(struct.pack("<II", len(files), 11))
    body = bytearray()
    off = 1
    for i, f in enumerate(files):
        size = -(-len(f) // SECTOR)
        if off + size > 0xFFFF:
            raise ValueError(f"entry {i}: archive exceeds the u16 sector range")
        header += struct.pack("<HH", off, size)
        body += f.ljust(size * SECTOR, b"\0")
        off += size
    return bytes(header.ljust(SECTOR, b"\0")) + bytes(body)
