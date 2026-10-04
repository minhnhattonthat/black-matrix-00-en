"""Redraw the Japanese picture labels in English. Usage: python labels.py
Reads the pristine sheets from work/orig, writes script/GFX/*.png (indexed; build.py pastes them back).
The PNGs are the source of truth after this: hand edits survive until this script is run again."""
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import dat, gfx, town

ROOT = Path(__file__).parent
OUT = ROOT / "script" / "GFX"
FONTS = Path("C:/Windows/Fonts")

# style: fonts widest first, height = cap on the letter height (default: as tall as the Japanese),
# pick = which of a row's indices is the letter colour (the rest is anti-aliasing),
# outline index (ring around the letters), under index (1 px below), drop shadow of the outline
TITLE = dict(fonts=["arialbd.ttf", "ARIALNB.TTF"], outline=None, under=3, drop=False, pick="common")
MENU = dict(fonts=["arialbi.ttf", "ARIALNBI.TTF"], outline=1, under=None, drop=True, pick="brightest")
SMALL = dict(fonts=["arialbd.ttf", "ARIALNB.TTF"], outline=3, under=None, drop=False, pick="brightest")

SAVE = dict(fonts=["ARIALNB.TTF"], height=10, outline=5, under=None, drop=False, pick="brightest")
SLOT = dict(SAVE, outline=4)

# (x0, y0, x1, y1) of the Japanese label, English, style, alignment
SYSTEM_UI = [
    ((48, 96, 96, 112), "SKILL", TITLE, "centre"),
    ((48, 112, 96, 128), "SHOP", TITLE, "centre"),
    ((0, 128, 48, 144), "STATUS", TITLE, "centre"),
    ((48, 128, 96, 144), "EQUIP", TITLE, "centre"),
    ((184, 112, 256, 128), "LEVEL UP", TITLE, "centre"),
    ((184, 65, 216, 80), "LIST", TITLE, "centre"),
]
TOWN_MENU = [
    ((0, 80, 56, 96), "EQUIP", MENU, "left"),
    ((57, 80, 129, 96), "INFO", MENU, "left"),
    ((129, 80, 195, 96), "TOWNSFOLK", MENU, "left"),
    ((0, 96, 56, 112), "SHOP", MENU, "left"),
    ((57, 96, 137, 112), "NOTEBOOK", MENU, "left"),
    ((137, 96, 201, 112), "MINI-GAME", MENU, "left"),
    ((201, 96, 256, 112), "TROUPE", MENU, "left"),
    ((0, 112, 56, 128), "SKIRMISH", MENU, "left"),
    ((57, 112, 148, 128), "TALK TO PARTY", MENU, "left"),
    ((150, 112, 248, 128), "SAVE / LOAD /", MENU, "left"),
    ((150, 128, 216, 143), "CONFIG", MENU, "left"),
    ((212, 0, 248, 13), "LEAVE", SMALL, "left"),
]

SAVE_LABELS = [
    ((0, 32, 39, 47), "SLOT", SLOT, "left"),            # the slot digit beside it is its own sprite
    ((17, 48, 48, 63), "OK", SAVE, "left"),
    ((17, 64, 48, 79), "DEL", SAVE, "left"),
    ((17, 80, 48, 95), "BACK", SAVE, "left"),
]
# sheets inside SYSTEM.DAT: name -> (sub-file, offset of the image blob in it)
SYSTEM_SHEETS = {"system_ui": (1, 0), "save_labels": (80, 0x4DC)}
WORK = {"system_ui": (SYSTEM_UI, 15), "town_menu": (TOWN_MENU, 0), "save_labels": (SAVE_LABELS, 0)}   # labels, preview palette


def mask(text: str, font_file: str, height: int) -> list[list[int]]:
    """Text as 0/1 rows, capitals exactly `height` pixels tall (largest size that is not taller)."""
    best = None
    for size in range(6, 40):
        font = ImageFont.truetype(str(FONTS / font_file), size)
        im = Image.new("1", (400, 60))
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        d.text((10, 10), text, 1, font=font)
        box = im.getbbox()
        if box[3] - box[1] > height:
            break
        best = im.crop(box)
    data = list(best.getdata())
    return [[1 if v else 0 for v in data[y * best.width:(y + 1) * best.width]] for y in range(best.height)]


def redraw(blob: bytes, rect, text: str, style: dict, align: str) -> bytes:
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    old = [[gfx.get(blob, x, y) for x in range(x0, x1)] for y in range(y0, y1)]
    edge = {0, style["outline"], style["under"]}
    face = {}                                    # row -> the letters' colour index on that row (a vertical gradient)
    for y, row in enumerate(old):
        seen = Counter(v for v in row if v not in edge)
        if seen:
            face[y] = seen.most_common(1)[0][0] if style["pick"] == "common" else max(seen)
    top, span = min(face), max(face) - min(face) + 1
    pad = 1 if style["outline"] is not None else 0
    room = w - 2 * pad - (1 if style["drop"] else 0)
    fits = (m for height in range(min(span, style.get("height", span)), 6, -1) for font in style["fonts"]      # full height first, then smaller
            if len((m := mask(text, font, height))[0]) <= room)
    m = next(fits, None)
    if m is None:
        raise ValueError(f"{text!r} does not fit a label {w} px wide")
    left = pad if align == "left" else (w - len(m[0])) // 2
    top += (span - len(m)) // 2
    new = [[0] * w for _ in range(h)]
    on = {(left + x, top + y) for y, row in enumerate(m) for x, v in enumerate(row) if v}

    def put(points, v):
        for x, y in points:
            if 0 <= x < w and 0 <= y < h and (x, y) not in on:
                new[y][x] = v

    if style["outline"] is not None:
        ring = {(x + dx, y + dy) for x, y in on for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        if style["drop"]:
            put({(x + 1, y + 1) for x, y in ring}, style["outline"])
        put(ring, style["outline"])
    if style["under"] is not None:
        put({(x, y + 1) for x, y in on}, style["under"])
    for x, y in on:
        new[y][x] = face.get(y, face[min(face, key=lambda r: abs(r - y))])
    return gfx.paste(blob, x0, y0, new)


def sheets() -> dict[str, bytes]:
    """The pristine sheets that carry Japanese labels."""
    orig = ROOT / "work" / "orig"
    system = dat.unpack((orig / "SYSTEM.DAT").read_bytes())
    menu = town.parse(dat.unpack((orig / "TOWN.DAT").read_bytes())[4])[0][0][0][1]
    return {"town_menu": menu} | {name: system[n][off:] for name, (n, off) in SYSTEM_SHEETS.items()}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, blob in sheets().items():
        labels, palette = WORK[name]
        for label in labels:
            blob = redraw(blob, *label)
        gfx.to_image(blob, palette).save(OUT / f"{name}.png")
        print(OUT / f"{name}.png")
