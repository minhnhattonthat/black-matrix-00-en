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
PROMPT = dict(fonts=["arialbd.ttf", "ARIALNB.TTF"], outline=4, under=None, drop=False, pick="brightest")
TOWN_PROMPT = [
    ((4, 112, 168, 127), "Choose a command", PROMPT, "left"),
    ((0, 128, 88, 152), "FREE TIME", PROMPT, "centre"),
]
# sheets in every town file of TOWN.DAT: name -> entry of the file's first container
TOWN_SHEETS = {"town_menu": 1, "town_prompt": 3}
# sheets inside SYSTEM.DAT: name -> (sub-file, offset of the image blob in it)
SYSTEM_SHEETS = {"system_ui": (1, 0), "save_labels": (80, 0x4DC)}
WORK = {"system_ui": (SYSTEM_UI, 15), "town_menu": (TOWN_MENU, 0), "save_labels": (SAVE_LABELS, 0),
        "town_prompt": (TOWN_PROMPT, 1)}   # labels, preview palette


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
    first = town.parse(dat.unpack((orig / "TOWN.DAT").read_bytes())[4])[0][0][0]
    return {name: first[i] for name, i in TOWN_SHEETS.items()} | {name: system[n][off:] for name, (n, off) in SYSTEM_SHEETS.items()}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, blob in sheets().items():
        labels, palette = WORK[name]
        for label in labels:
            blob = redraw(blob, *label)
        gfx.to_image(blob, palette).save(OUT / f"{name}.png")
        print(OUT / f"{name}.png")


# ---- NPC name plates in the towns ------------------------------------------------------------------
# Each town file has a 256-wide sheet of names (16 px rows) and a sprite table whose last section lists
# rectangles (u, v, w, h bytes). English names are wider, so the names are repacked and the table rewritten.
# Keys are the Japanese name's (v, u) on the sheet; two layouts exist (human towns, the demon village).
HUMAN = {
    (0, 72): "Flower Seller", (0, 136): "Member (Man)", (0, 192): "Member (Woman)",
    (16, 0): "Member (Youth)", (16, 64): "Dahlia", (16, 96): "Waiter", (16, 152): "Swordsman",
    (16, 176): "Middle-aged Man", (16, 200): "One-winged Angel",
    (32, 0): "Syria", (32, 32): "Old Man", (32, 56): "Young Man", (32, 80): "Old Woman",
    (32, 104): "Boyfriend", (32, 160): "Girlfriend", (32, 216): "Priest",
    (48, 0): "Bran", (48, 32): "Fly", (48, 64): "Boy", (48, 96): "Girl", (48, 128): "Clown",
    (48, 160): "Soldier", (48, 184): "Lilis", (48, 216): "Kilota",
    (64, 0): "Johannes", (64, 32): "Valtoss", (64, 88): "Stayen", (64, 144): "Boy", (64, 176): "Exal",
    (64, 216): "Postbox", (80, 0): "Swordsman's Lover", (80, 56): "Old Woman's Son", (80, 112): "Mailbox",
}
# cells that hold another name in some towns: (v, u) -> {signature of the pixels: name}
HUMAN_ALT = {(16, 64): {"fdaebc7b51b4": "Mistress"}, (64, 144): {"cb77bf87ac42": "Abel"}}
DEMON = {
    (0, 72): "Unda", (0, 104): "Chief's Aide", (0, 152): "Watch Captain", (0, 200): "Demon (Girl)",
    (16, 0): "Mistress", (16, 32): "Waitress", (16, 80): "Demon (Swordsman)", (16, 128): "Demon (Older Man)",
    (16, 176): "Watchman", (32, 0): "Demon (Man)", (32, 40): "Demon (Woman)", (32, 80): "Watchwoman",
    (32, 136): "Demon (Boy)", (32, 192): "Demon (Little Girl)",
    (48, 0): "One-winged Angel", (48, 48): "Bran", (48, 80): "Fly", (48, 112): "Clown", (48, 144): "Postbox",
    (48, 176): "Mailbox", (64, 0): "Syria",
}
PLATE_ROWS, PLATE_H, BAR_W = 96, 16, 72        # names live in the top 96 rows; the underline bar is at (0,0)-(72,16)


def _plate(text: str) -> list[list[int]]:
    """A name as a 16-row strip of colour indices: white-to-cream letters with a dark outline."""
    font = ImageFont.truetype(str(FONTS / "tahoma.ttf"), 11)     # hinted for small sizes: stays legible in 1 bit
    im = Image.new("1", (300, PLATE_H))
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    d.text((1, 11), text, 1, font=font, anchor="ls")
    w = im.getbbox()[2] + 1
    on = {(x, y) for y in range(PLATE_H) for x in range(w) if im.getpixel((x, y))}
    rows = [[0] * w for _ in range(PLATE_H)]
    for x, y in on:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if 0 <= x + dx < w and 0 <= y + dy < PLATE_H:
                    rows[y + dy][x + dx] = 1
    for x, y in on:
        rows[y][x] = 0xB if y <= 7 else 8 if y <= 9 else 0xE
    return rows


def nameplates(sheet: bytes, table: bytes) -> tuple[bytes, bytes]:
    """The name sheet and its sprite table with every referenced name in English."""
    import hashlib, struct
    o2, o3 = struct.unpack_from("<II", table, 8)
    count = struct.unpack_from("<I", table, o3)[0]
    rects = [tuple(table[o3 + 4 + 4 * i:o3 + 8 + 4 * i]) for i in range(count)]
    cells = sorted({(v, u, w) for u, v, w, h in rects
                    if v < PLATE_ROWS and h == PLATE_H and not (v == 0 and u + w <= BAR_W)})
    names = HUMAN if (0, 136, 56) in cells else DEMON
    width = gfx.header(sheet)[1]
    sheet = gfx.paste(sheet, BAR_W, 0, [[0] * (width - BAR_W)] * PLATE_H)
    old = sheet
    sheet = gfx.paste(sheet, 0, PLATE_H, [[0] * width] * (PLATE_ROWS - PLATE_H))
    shelves = [BAR_W] + [0] * (PLATE_ROWS // PLATE_H - 1)          # next free x on each 16-px row
    moved = {}                                                     # (u, v) -> (u, v, w) in English
    for v, u, w in cells:
        text = names[v, u]
        if (v, u) == (48, 0) and w == 24 and names is HUMAN:
            text = "Girl"
        if names is HUMAN and (v, u) in HUMAN_ALT and v:
            pixels = bytes(gfx.get(old, x, y) for y in range(v, v + PLATE_H) for x in range(u, u + w))
            text = HUMAN_ALT[v, u].get(hashlib.sha1(pixels).hexdigest()[:12], text)
        rows = _plate(text)
        row = next((i for i, x in enumerate(shelves) if x + len(rows[0]) <= width), None)
        if row is None:
            raise ValueError(f"name plates do not fit the sheet (at {text!r})")
        sheet = gfx.paste(sheet, shelves[row], row * PLATE_H, rows)
        moved[u, v] = (shelves[row], row * PLATE_H, len(rows[0]))
        shelves[row] += len(rows[0])
    out = bytearray(table)
    grown = {}                                                     # rect index -> extra width
    for i, (u, v, w, h) in enumerate(rects):
        if (u, v) in moved and h == PLATE_H and (v, u, w) in cells:
            out[o3 + 4 + 4 * i:o3 + 8 + 4 * i] = bytes([*moved[u, v], h])
            grown[i] = moved[u, v][2] - w
    frames = struct.unpack_from("<I", table, o2)[0]
    for f in struct.unpack_from(f"<{frames}H", table, o2 + 4):
        parts = struct.unpack_from("<I", table, o2 + f)[0]
        for p in range(o2 + f + 4, o2 + f + 4 + 8 * parts, 8):
            rect, x = table[p + 1], table[p + 2]
            if rect in grown and x >= 0x80:                        # plate right of the NPC: keep its far edge where
                out[p + 2] = max(x - grown[rect], 0)               # the Japanese one ended, so it cannot leave the screen
    return sheet, bytes(out)


# ---- disc-change screen (SYSTEM.DAT sub-file 100) ----------------------------------------------------
# Glowing serif words on a sheet at DISC_SHEET, composed by the sprite table at DISC_TABLE. English puts
# the verb first ("Insert DISC 1"), so the words are redrawn and the five message frames laid out again.
DISC_TABLE, DISC_SHEET = 0x14, 0xA3E8
DISC_WORDS = {5: "Insert", 7: "Checking", 8: "Wrong", 4: ""}        # rect index -> word ("" = the particle, blanked)
DISC_CENTRE, DISC_GAP = 160, -6       # rectangles carry their own halo padding, so they overlap a little


def _glow(text: str) -> list[list[int]]:
    """A word as 32 rows of indices 0-15: serif letters sized and placed like the sheet's own "DISC" (capitals on rows 8-22) with a soft halo."""
    from PIL import ImageChops, ImageFilter
    font = ImageFont.truetype(str(FONTS / "times.ttf"), 23)
    im = Image.new("L", (260, 32))
    ImageDraw.Draw(im).text((5, 23), text, 255, font=font, anchor="ls")
    halo = im.filter(ImageFilter.GaussianBlur(2)).point(lambda v: min(255, v * 2))
    im = ImageChops.lighter(im, halo).crop((0, 0, im.getbbox()[2] + 5, 32))
    data = [round(v / 17) for v in im.getdata()]
    return [data[y * im.width:(y + 1) * im.width] for y in range(32)]


def disc_screen(sub: bytes) -> bytes:
    import struct
    sheet = sub[DISC_SHEET:]
    o2, o3 = (DISC_TABLE + v for v in struct.unpack_from("<II", sub, DISC_TABLE + 8))
    out = bytearray(sub)
    rect = lambda i: out[o3 + 4 + 4 * i:o3 + 8 + 4 * i]
    for i, word in DISC_WORDS.items():
        u, v, w, h = rect(i)
        sheet = gfx.paste(sheet, u, v, [[0] * w] * h)
        if word:
            rows = _glow(word)
            if len(rows[0]) > 144:
                raise ValueError(f"{word!r} is too wide for the disc screen sheet")
            sheet = gfx.paste(sheet, u, v, rows)
            out[o3 + 4 + 4 * i:o3 + 8 + 4 * i] = bytes([u, v, len(rows[0]), 32])
    out[DISC_SHEET:] = sheet
    width = lambda i: rect(i)[2]

    def line(y, *rects):
        """x, y for rects placed left to right as one centred line; a digit hugs its DISC as it did."""
        steps = [65 if a in (0, 2) else width(a) + DISC_GAP for a in rects[:-1]]
        x = DISC_CENTRE - (sum(steps) + width(rects[-1])) // 2
        placed = {}
        for r, step in zip(rects, steps + [0]):
            placed[r] = (x, y)
            x += step
        return placed

    frames = struct.unpack_from(f"<{struct.unpack_from('<I', sub, o2)[0]}H", sub, o2 + 4)
    layouts = {25: line(91, 5) | line(120, 0, 1), 26: line(91, 5) | line(120, 2, 3),
               27: line(94, 7) | line(120, 6),
               28: line(91, 8, 6) | line(118, 5, 0, 1), 29: line(91, 8, 6) | line(118, 5, 2, 3)}
    for f, placed in layouts.items():
        base = o2 + frames[f]
        seen = set()
        for p in range(base + 4, base + 4 + 8 * struct.unpack_from("<I", sub, base)[0], 8):
            r = sub[p + 1]
            if r in placed and (f, r) not in seen:      # frames 28/29 use DISC twice: rect 6 above, 0/2 below
                out[p + 2], out[p + 3] = placed[r]
                seen.add((f, r))
            elif r != 4:
                raise ValueError(f"disc screen frame {f}: unexpected sprite {r}")
    return bytes(out)
