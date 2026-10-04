"""The game's own image blobs (not TIM), 4-bit kind only: read, draw into, write back.
u32 type, u32 0x10, u32 pixel_off, u32 extra_off; @0x10 u16 clut_w, clut_h, colours;
@pixel_off u16 width in 16-bit words (4 pixels each), u16 height, then raw pixels, low nibble first."""
import struct


def header(blob: bytes) -> tuple[list[int], int, int]:
    """(clut colours, width in pixels, offset of the first pixel byte). The blob may run past the image."""
    kind, ten, off, _ = struct.unpack_from("<4I", blob, 0)
    cw, ch = struct.unpack_from("<HH", blob, 0x10)
    if kind != 0 or ten != 0x10 or off != 0x14 + 2 * cw * ch:
        raise ValueError("not a 4-bit image blob")
    return list(struct.unpack_from(f"<{cw * ch}H", blob, 0x14)), struct.unpack_from("<H", blob, off)[0] * 4, off + 4


def height(blob: bytes) -> int:
    return struct.unpack_from("<H", blob, header(blob)[2] - 2)[0]


def get(blob: bytes, x: int, y: int) -> int:
    _, w, base = header(blob)
    return blob[base + (y * w + x) // 2] >> (4 * (x & 1)) & 15


def paste(blob: bytes, x0: int, y0: int, rows: list[list[int]]) -> bytes:
    """Overwrite a rectangle with colour indices; the blob keeps its size."""
    _, w, base = header(blob)
    out = bytearray(blob)
    for dy, row in enumerate(rows):
        for dx, v in enumerate(row):
            x = x0 + dx
            if not (0 <= x < w and 0 <= v < 16):
                raise ValueError(f"pixel ({x},{y0 + dy})={v} outside the image")
            i = base + ((y0 + dy) * w + x) // 2
            shift = 4 * (x & 1)
            out[i] = out[i] & ~(15 << shift) & 255 | v << shift
    return bytes(out)


def to_image(blob: bytes, palette: int = 0):
    """The whole sheet as an indexed PNG-ready image (pixel value = colour index), shown with one CLUT row."""
    from PIL import Image
    clut, w, base = header(blob)
    h = height(blob)
    im = Image.new("P", (w, h))
    im.putdata([blob[base + i // 2] >> (4 * (i & 1)) & 15 for i in range(w * h)])
    im.putpalette([(c >> s & 31) << 3 for c in clut[palette * 16:palette * 16 + 16] for s in (0, 5, 10)])
    return im


def from_image(blob: bytes, im) -> bytes:
    """The blob with every pixel taken from an indexed image of the same size."""
    _, w, base = header(blob)
    if im.mode != "P" or im.size != (w, height(blob)):
        raise ValueError(f"need an indexed {w}-pixel-wide image of the sheet's own size, got {im.mode} {im.size}")
    data = list(im.getdata())
    return paste(blob, 0, 0, [data[y * w:(y + 1) * w] for y in range(im.size[1])])
