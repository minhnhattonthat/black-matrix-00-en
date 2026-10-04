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
    (48, 0): "Plan", (48, 32): "Fly", (48, 64): "Boy", (48, 96): "Girl", (48, 128): "Clown",
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
    (48, 0): "One-winged Angel", (48, 48): "Plan", (48, 80): "Fly", (48, 112): "Clown", (48, 144): "Postbox",
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


# ---- circus mini-game instruction pages (TOWN.DAT sub-files 36-42) ----------------------------------
# A page is one frame of a sprite table: every line of text is one or two 16-px strips cut from the sheet.
# English lines are drawn, cut into as many strips as the Japanese line had, packed into the space the
# Japanese strips occupied, and the frame's x positions are rewritten.
#   lines: (rect indices of the line left to right, English, "centre" | "left" | "keep")
#   title: redrawn inside its own rectangle
#   blocks: (rect, first column to clear, lines) for text that keeps its rectangle - bubbles, multi-line blocks
START = "Press START to begin!!"
PANELS = {
    36: dict(table=26, sheet=8, frames=(4,), title=(4, "Flyers"), lines=[
        ((9, 10), "Hand out lots of flyers to passers-by", "centre"),
        ((11, 12), "and promote our Nekintar Kanel Troupe~", "centre"),
        ((13, 14), "But some people take one and toss it,", "centre"),
        ((15,), "so watch out for them~", "centre"),
        ((16,), "Move Cain", "left"),
        ((17, 18), "Hold to hand out, release to stop", "left"),
        ((19,), START, "centre"),
    ], blocks=[(8, 0, [("Beware of", 2, "centre"), ("these people~!!", 15, "centre")])]),
    37: dict(table=22, sheet=8, frames=(4,), title=(4, "Knife Throw"), lines=[
        ((15, 16), "Hit the targets that appear within the", "centre"),
        ((17,), "time limit with your knives~", "centre"),
        ((18,), "But no peeking at them!", "centre"),
        ((19, 20), "Why? ...Because this is a circus!!", "centre"),
        ((22,), START, "centre"),
    ], blocks=[(21, 33, [("target", 0, 33)]),
               (12, 0, [("Press twice", 2, "centre"), ("for this one!", 15, "centre")])]),
    38: dict(table=22, sheet=8, frames=(4, 5), title=(4, "Juggling"), lines=[
        ((16, 17), "Catch the balls I throw!!", "centre"),
        ((18,), "I throw one every so often,", "centre"),
        ((19,), "so press the button shown", "centre"),
        ((20, 21), "mid-screen in time to catch it!!", "centre"),
        ((22,), START, "centre"),
    ], blocks=[(28, 15, [("Red", -3, "right:47"), ("Blue", 11, "right:47"), ("Pink", 25, "right:47"), ("Green", 39, "right:47")]),
               (30, 0, [("ball", 0, 4)]),
               (29, 17, [("Catchphrase", 0, 19)]),
               (12, 0, [("mark:", -2, 27), ("press any", 11, "centre"), ("button!", 25, "centre")])]),
    39: dict(table=22, sheet=8, frames=(3, 4, 6), title=(4, "Tightrope"), lines=[
        ((5, 6), "Cross the rope, deflecting the balls that", "centre"),
        ((7, 8), "fly at you, and pop balloons on the way~", "centre"),
        ((9, 10), "Iron balls come flying too, so watch out~", "centre"),
        ((11, 12), START, "centre"),
        ((13, 14), "Auto-move", "left"),
        ((18,), "… Back", "left"),
        ((20,), "… Balance", "left"),
        ((22,), "… Jump", "left"),
        ((24,), "… Hit", "left"),
        ((36,), "Beware this", "left"),
        ((37,), "balloon!", "left"),
    ], blocks=[(32, 0, [("After popping a", -2, "centre"), ("balloon, don't forget", 12, "centre"), ("to strike a pose!", 24, "centre")])]),
    40: dict(table=22, sheet=8, frames=(), title=(4, "Beast Tamer"), lines=[], blocks=[
        (5, 0, [("Signal the lion to dodge", -3, "centre"), ("the obstacles nicely~", 8, "centre")]),
        (6, 0, [("But there's a short delay before the lion", 2, "centre"), ("responds to a signal, so be careful~", 15, "centre")]),
        (8, 13, [("Left/Right changes the lion's speed", -2, 14), ("Lion jumps; hold for a high jump", 12, 14),
                 ("Slide (only when in a good mood)", 26, 14), (START, 40, 46)]),
        (16, 0, [("Meat restores", 0, "centre")]),
        (17, 0, [("its mood~", 0, "centre")]),
    ]),
    41: dict(table=22, sheet=8, frames=(3,), title=(4, "Trapeze"), lines=[
        ((5, 6), "You're not ready to perform yet,", "centre"),
        ((7, 8), "so learn backstage on the spotlight~", "centre"),
        ((9, 10), "Just lighting us is easy, right!?", "centre"),
        ((12,), "Move the spotlight", "left"),
        ((13,), START, "centre"),
    ], blocks=[(17, 0, [("Light Fly", 2, "centre"), ("up nicely!", 15, "centre")])]),
    42: dict(table=22, sheet=8, frames=(3,), title=(4, "Trapeze"), lines=[
        ((5, 6), "So we finally share the same stage!", "centre"),
        ((7, 8), "Three stunts! Time it right and", "centre"),
        ((9, 10), "leap over to my trapeze quickly~", "centre"),
        ((11,), "Or blood rushes to my head", "centre"),
        ((12,), "and I can't perform!", "centre"),
        ((15,), "Adjust swing speed", "left"),
        ((18,), START, "centre"),
    ], blocks=[(13, 26, [("Cain jumps", 0, 28)]),
               (21, 0, [("Don't keep", 2, "centre"), ("me waiting~", 15, "centre")])]),
}
PANEL_CENTRE = 160
TITLE = dict(fonts=["arialbd.ttf", "ARIALNB.TTF"], outline=1, under=None, drop=False, pick="brightest")


def _strip(text: str, cheer: bool = False) -> list[list[int]]:
    """Text as a 16-row strip of indices: anti-aliased light letters on a dark (index 1) outline.
    `cheer`: the knife game's shout palette instead - index 1 is the full colour, 8 the faintest, 15 the rim."""
    font = ImageFont.truetype(str(FONTS / "tahoma.ttf"), 11)
    im = Image.new("L", (400, PLATE_H))
    ImageDraw.Draw(im).text((1, 12), text, 255, font=font, anchor="ls")
    w = im.getbbox()[2] + 1
    cov = [[im.getpixel((x, y)) for x in range(w)] for y in range(PLATE_H)]
    rows = [[0] * w for _ in range(PLATE_H)]
    for y in range(PLATE_H):
        for x in range(w):
            if cov[y][x] >= 64:
                rows[y][x] = 8 - round(cov[y][x] * 7 / 255) if cheer else 3 + round(cov[y][x] * 12 / 255)
            elif any(cov[j][i] >= 96 for j in range(max(y - 1, 0), min(y + 2, PLATE_H))
                     for i in range(max(x - 1, 0), min(x + 2, w))):
                rows[y][x] = 15 if cheer else 1
    return rows


def _block(sheet: bytes, rect: tuple, clear_from: int, texts: list, cheer: bool = False) -> bytes:
    """Lines drawn inside one rectangle: (text, top row, "centre" | "right:COL" | left column). Pixels of
    the rectangle left of `clear_from` are kept (a leading "..." that the English reuses)."""
    u, v, w, h = rect
    area = [[gfx.get(sheet, u + x, v + y) if x < clear_from else 0 for x in range(w)] for y in range(h)]
    for text, top, align in texts:
        rows = _strip(text, cheer)
        tw = len(rows[0])
        left = (w - tw) // 2 if align == "centre" else int(align[6:]) - tw if isinstance(align, str) else align
        if left < clear_from or left + tw > w:
            raise ValueError(f"{text!r} ({tw} px) does not fit its {w}-pixel block")
        for y, row in enumerate(rows):
            for x, value in enumerate(row):
                if value and 0 <= top + y < h:
                    area[top + y][left + x] = value
    return gfx.paste(sheet, u, v, area)


def panel(sheet: bytes, table: bytes, spec: dict) -> tuple[bytes, bytes]:
    """A mini-game's instruction sheet and sprite table in English."""
    import struct
    o2, o3 = struct.unpack_from("<II", table, 8)
    rect = lambda i: tuple(table[o3 + 4 + 4 * i:o3 + 8 + 4 * i])
    out = bytearray(table)
    lines = [(ids, _strip(text), align) for ids, text, align in spec["lines"]]
    runs = []                                                # [row, start, end): space the old strips used
    for u, v, w, h in sorted((rect(i) for ids, _, _ in lines for i in ids), key=lambda r: (r[1], r[0])):
        sheet = gfx.paste(sheet, u, v, [[0] * w] * h)
        if runs and runs[-1][0] == v and u <= runs[-1][2]:
            runs[-1][2] = max(runs[-1][2], u + w)
        else:
            runs.append([v, u, u + w])
    room = lambda run: run[2] - run[1]
    placed = {}                                              # rect index -> (x offset in its line, strip width)
    for ids, rows, _ in sorted(lines, key=lambda t: (len(t[0]) > 1, -len(t[1][0]))):   # uncuttable lines first
        x, total = 0, len(rows[0])                           # a line may be cut anywhere: its strips meet on screen
        for k, i in enumerate(ids):
            left = total - x
            if not left:
                break
            fits = [run for run in runs if room(run) >= left]
            run = min(fits, key=room) if fits else max(runs, key=room)
            w = min(left, room(run))
            if w == 0 or (k == len(ids) - 1 and w < left):
                raise ValueError(f"instruction page: no room for {left} more pixels (free: {sorted(map(room, runs))})")
            sheet = gfx.paste(sheet, run[1], run[0], [r[x:x + w] for r in rows])
            out[o3 + 4 + 4 * i:o3 + 8 + 4 * i] = bytes([run[1], run[0], w, PLATE_H])
            placed[i] = (x, w)
            run[1] += w
            x += w
    parts = {}                                               # rect index -> where its sprites sit in the frames
    for f in spec["frames"]:
        base = o2 + struct.unpack_from("<H", table, o2 + 4 + 2 * f)[0]
        for p in range(base + 4, base + 4 + 8 * struct.unpack_from("<I", table, base)[0], 8):
            parts.setdefault(table[p + 1], []).append(p)
    for ids, rows, align in lines:
        start = PANEL_CENTRE - len(rows[0]) // 2 if align == "centre" else table[parts[ids[0]][0] + 2]
        for i in ids:
            if i not in placed:                              # the English needed fewer strips: park the spare one
                out[o3 + 4 + 4 * i:o3 + 8 + 4 * i] = bytes(rect(0))        # rect 0 is every table's blank
                continue
            if not 0 <= start + placed[i][0] <= 255:
                raise ValueError("instruction page: line starts off screen")
            for p in parts[i]:
                out[p + 2] = start + placed[i][0]
    i, text = spec["title"]
    u, v, w, h = rect(i)
    sheet = redraw(sheet, (u, v, u + w, v + h), text, TITLE, "left")
    for i, clear_from, texts in spec["blocks"]:
        sheet = _block(sheet, rect(i), clear_from, texts)
    return sheet, bytes(out)


# ---- circus mini-game HUD (entry 7 of TOWN.DAT sub-files 36-42) -------------------------------------
# Labels keep their rectangles. Each is named by a point inside it; the rectangle is the smallest one any
# of the file's sprite tables has around that point (or given outright as x0, y0, x1, y1).
HUD_SHEET = 7
HUD_COMMON = [((120, 24, 192, 40), "RESULTS"), ((213, 24, 240, 40), "END"), ((64, 104, 104, 120), "QUOTA"),
              ((104, 104, 144, 120), "MET!"), ((144, 104, 184, 120), "QUOTA"), ((80, 120, 128, 136), "MISSED"),
              ((192, 104, 248, 120), "EARNED"), ((192, 120, 240, 136), "TIPS!")]   # "EARNED 3050 TIPS!"
HUD = {
    36: [((120, 152), "HANDED OUT"), ((112, 168), "QUOTA"), ((160, 168), ""), ((248, 128), ""),
         ((16, 192), "QUOTA"), ((40, 192), "")],
    37: [((120, 153), "QUOTA"), ((105, 168), "HITS"), ((32, 193), "QUOTA"), ((176, 192), "x")],
    38: [((115, 192), "QUOTA"), ((63, 208), "CAUGHT"), ((130, 209), "QUOTA"), ((63, 225), "DROPPED"),
         ((160, 192), "x"), ((143, 223), "x")],
    39: [((17, 191), "AIM"), ((53, 191), "POSES"), ((72, 184, 104, 200), "PASS"), ((104, 184, 136, 200), "MARK"), ((0, 200, 104, 216), "POSES"),
         ((223, 192), "GOAL"), ((217, 208), "IN!"), ((248, 128), "")],
    40: [((216, 40, 248, 56), "DIST"), ((110, 151), "MISS"), ((135, 151), ""), ((92, 168), "RANK"),
         ],
    41: [((112, 161), "TOTAL"), ((130, 178), ""), ((38, 194), "QUOTA"), ((138, 194), "QUOTA")],
}
HUD[42] = HUD[41]


def _rects(node, page: int) -> tuple[set, set]:
    """Rectangles of the sprite tables under a parsed TOWN node that draw from texture page `page`
    (a sprite's page is the low 3 bits of its last word; entry 5 + page of the file is its sheet):
    (those a frame uses on that page, every other rectangle of such tables - the game also draws
    rectangles by number, without a frame, so the second set holds real labels among strangers)."""
    import struct
    if isinstance(node, tuple):
        found = [_rects(c, page) for c in node[0]]
        return set().union(*(f[0] for f in found)), set().union(*(f[1] for f in found))
    if len(node) < 0x20 or struct.unpack_from("<II", node, 0) != (0, 0x10):
        return set(), set()
    o2, o3 = struct.unpack_from("<II", node, 8)
    if not 0x14 <= o2 < o3 <= len(node) - 4:
        return set(), set()
    count = struct.unpack_from("<I", node, o3)[0]
    frames = struct.unpack_from("<I", node, o2)[0]
    if o3 + 4 + 4 * count > len(node) or o2 + 4 + 2 * frames > o3:
        return set(), set()
    used = set()
    for f in struct.unpack_from(f"<{frames}H", node, o2 + 4):
        parts = struct.unpack_from("<I", node, o2 + f)[0]
        for p in range(o2 + f + 4, min(o2 + f + 4 + 8 * parts, o3), 8):
            if node[p + 1] < count and node[p + 4] & 7 == page and not node[p + 5:p + 8].strip(bytes(1)):
                used.add(tuple(node[o3 + 4 + 4 * node[p + 1]:o3 + 8 + 4 * node[p + 1]]))
    every = {tuple(node[o3 + 4 + 4 * i:o3 + 8 + 4 * i]) for i in range(count)} if used else set()
    return used, every - used


def hud(sheet: bytes, rects: tuple, labels: list, debug: bool = False) -> bytes:
    width, height = gfx.header(sheet)[1], gfx.height(sheet)
    for where, text in labels:
        if len(where) == 4:
            box = where
        else:
            x, y = where
            holds = lambda r: (r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3] and 8 <= r[3] <= 24
                               and r[2] >= (24 if len(text) > 1 else 8)
                               and r[0] + r[2] <= width and r[1] + r[3] <= height)
            around = [r for r in rects[0] if holds(r)] or [r for r in rects[1] if holds(r) and r[3] == 16]
            if not around:
                raise ValueError(f"HUD label {text!r}: no rectangle around {where}")
            u, v, w, h = min(around, key=lambda r: r[2] * r[3])
            box = (u, v, u + w, v + h)
            if debug:
                print(text or 'blank', where, '->', (u, v, w, h))
        old = [gfx.get(sheet, x, y) for y in range(box[1], box[3]) for x in range(box[0], box[2])]
        if not text:
            sheet = gfx.paste(sheet, box[0], box[1], [[0] * (box[2] - box[0])] * (box[3] - box[1]))
            continue
        dark = Counter(v for v in old if 0 < v <= 3)
        if not dark:
            raise ValueError(f"HUD label {text!r}: nothing drawn in {box}")
        style = dict(fonts=["arialbd.ttf", "ARIALNB.TTF"], outline=dark.most_common(1)[0][0], under=None,
                     drop=False, pick="brightest")
        sheet = redraw(sheet, box, text, style, "centre")
    return sheet


# circus menu (sub-file 34) and equipment shop (35): entry 5 = texture page 0
CIRCUS = {
    34: [((168, 0, 216, 16), "TIPS"), ((168, 16, 256, 32), "SHOWS LEFT:"), ((0, 56, 88, 80), "END SHOW"),
         ((0, 80, 88, 120), "SELECT ACT"), ((64, 160, 120, 192), "PRACTICE"), ((64, 192, 120, 224), "PERFORM")],
    35: [((168, 0, 216, 16), "TIPS"), ((233, 0, 256, 16), "EXIT"), ((168, 16, 256, 56), "BUY GEAR")],
}
# shouts in the knife game (sub-file 38, entry 6): rectangle -> English; two-piece shouts read left to right
CHEERS = {
    (104, 128, 48, 16): "Let's go!", (96, 144, 56, 16): "Phew...", (24, 160, 56, 16): "Yay!", (80, 160, 48, 16): "On it!",
    (24, 176, 32, 16): "Nice!", (56, 176, 40, 16): "Did it!", (96, 176, 56, 16): "Easy!",
    (24, 192, 56, 16): "Thanks!", (80, 192, 64, 16): "Now for the", (96, 208, 56, 16): "real show!",
    (0, 208, 48, 16): "Superb!!", (48, 208, 48, 16): "Ta-da!!",
    (0, 224, 56, 16): "Applause!", (56, 224, 24, 16): "Ah,", (80, 224, 64, 16): "I blew it...",
    (0, 240, 56, 16): "Close...", (56, 240, 48, 16): "Not done", (104, 240, 40, 16): "yet!",
}


def cheers(sheet: bytes) -> bytes:
    for rect, text in CHEERS.items():
        sheet = _block(sheet, rect, 0, [(text, 0, 1)], cheer=True)
    return sheet


CIRCUS_FILES = range(34, 43)


def circus(index: int, tree) -> None:
    """Every English picture of one circus sub-file, written into its parsed tree."""
    ch = tree[0]
    if index in PANELS:
        spec = PANELS[index]
        ch[spec["sheet"]], ch[spec["table"]] = panel(ch[spec["sheet"]], ch[spec["table"]], spec)
    if index in HUD:
        ch[HUD_SHEET] = hud(ch[HUD_SHEET], _rects(tree, HUD_SHEET - 5), HUD_COMMON + HUD[index])
    if index in CIRCUS:
        ch[5] = hud(ch[5], (set(), set()), CIRCUS[index])
    if index == 38:
        ch[6] = cheers(ch[6])


# ---- place-name cards (EVENT.DAT, one 160x24 picture per sub-file) and battle objective banners -----
CARDS = {
    10: "Cain's House", 11: "Johannes's Underground Lab", 12: "Outside the Ruins", 13: "Island Church",
    14: "Altar Room", 15: "Prodevon Church", 16: "City of Verona", 17: "Nekintar Kanel Troupe", 18: "Dahlia Beer",
    20: "Diribel Church", 21: "Back Alley", 22: "Spectral Catacombs", 23: "Church Prison", 24: "Church of Rigor",
    25: "Chapel", 26: "Skies over Rigor", 27: "Incest Holding Cell", 28: "Edge of Town",
    30: "Demons' Underground Passage", 31: "Hunting Ground of Lament", 32: "Ramstein Cathedral",
    33: "Inside the Cathedral", 34: "Leniam Plaza", 35: "Fetus Church", 36: "Inside the Church",
    37: "Abandoned Church Facility", 38: "Former Test Facility", 39: "Tribunal Generals' Trial",
    40: "Mephisto's Prison", 41: "Kibotos Island", 42: "God Core's Prison", 43: "Kanel Troupe Stage",
    44: "Underground World", 45: "Elder's Mansion", 46: "Saint Helena Street", 47: "Pasca Temple",
    48: "San Bartelmi Church", 49: "San Bartelmi Underground", 50: "God Core Control Room",
    51: "God Core Test Facility", 52: "Kalhin Settlement", 53: "Demon Army Facility", 54: "Cypherpunk Facility",
    55: "Cryo-Sentence Prison", 56: "Graveyard", 57: "Johannes's Laboratory", 58: "World Tree of Kibotos",
    59: "Atop the World Tree", 60: "Greyhen Chamber", 61: "God Core Tree-Womb Device", 63: "Ruins",
    64: "Site of the Ruins",
}
CARDS[19], CARDS[29] = CARDS[16], CARDS[18]      # the same pictures stored twice
# BATTLE.DAT sub-file -> (English, alignment): victory conditions on the left, defeat conditions on the right
BANNERS = {
    4: ("Annihilate the enemy", "left"), 5: ("Defeat the target", "left"), 6: ("Protect Luca", "left"),
    7: ("Defeat Aragi", "left"), 8: ("Defeat Bale", "left"), 9: ("Withstand the onslaught", "left"),
    10: ("Attack the strange demon", "left"), 11: ("Destroy the core", "left"),
    20: ("All allies defeated", "right"), 21: ("Main unit incapacitated", "right"),
}


def _fill(blob: bytes, rows: list, left: int, top: int) -> bytes:
    """The whole picture cleared, then `rows` drawn at (left, top)."""
    width, height = gfx.header(blob)[1], gfx.height(blob)
    if left < 0 or top < 0 or left + len(rows[0]) > width or top + len(rows) > height:
        raise ValueError("text does not fit its picture")
    blob = gfx.paste(blob, 0, 0, [[0] * width] * height)
    return gfx.paste(blob, left, top, rows)


def card(blob: bytes, text: str) -> bytes:
    """A place-name card: white letters with a dark rim, centred, in the largest size that fits."""
    width, height = gfx.header(blob)[1], gfx.height(blob)
    for name, size in [("tahomabd.ttf", n) for n in (15, 14, 13, 12, 11)] + [("tahoma.ttf", 11), ("tahoma.ttf", 10)]:
        font = ImageFont.truetype(str(FONTS / name), size)
        im = Image.new("L", (400, height))
        ImageDraw.Draw(im).text((2, height // 2 + size // 2 - 2), text, 255, font=font, anchor="ls")
        box = im.getbbox()
        if box[2] + 2 <= width:
            break
    else:
        raise ValueError(f"{text!r} is too long for a place-name card")
    w = box[2] + 2
    cov = [[im.getpixel((x, y)) for x in range(w)] for y in range(height)]
    rows = [[0] * w for _ in range(height)]
    for y in range(height):
        for x in range(w):
            if cov[y][x] >= 48:
                rows[y][x] = 3 + round(cov[y][x] * 12 / 255)
            elif any(cov[j][i] >= 96 for j in range(max(y - 1, 0), min(y + 2, height))
                     for i in range(max(x - 1, 0), min(x + 2, w))):
                rows[y][x] = 1
    return _fill(blob, rows, (width - w) // 2, 0)


def banner(blob: bytes, text: str, align: str) -> bytes:
    """A battle objective: glowing italic serif letters, as large as the Japanese where they fit."""
    from PIL import ImageChops, ImageFilter
    width, height = gfx.header(blob)[1], gfx.height(blob)
    for size in range(26 if align == "left" else 18, 11, -1):
        font = ImageFont.truetype(str(FONTS / ("timesbi.ttf" if size >= 20 else "timesi.ttf")), size)   # bold clogs when small
        im = Image.new("L", (500, height))
        ImageDraw.Draw(im).text((6, height // 2 + size // 3), text, 255, font=font, anchor="ls")
        if im.getbbox()[2] + 6 <= width:
            break
    else:
        raise ValueError(f"{text!r} is too long for an objective banner")
    halo = im.filter(ImageFilter.GaussianBlur(1.6)).point(lambda v: min(110, v))     # a dim halo: letter holes stay open
    im = ImageChops.lighter(im, halo).crop((0, 0, im.getbbox()[2] + 6, height))
    data = [round(v / 17) for v in im.getdata()]
    rows = [data[y * im.width:(y + 1) * im.width] for y in range(height)]
    return _fill(blob, rows, 0 if align == "left" else width - im.width, 0)


BATTLE_UI = 0x2C                                   # the battle UI sheet inside BATTLE.DAT sub-file 1
BATTLE_LABELS = [((0, 193, 40, 206), "THINK")]     # shown while the enemy decides its move


# ---- speaker name plates (EVENT.DAT sub-files 190-260) ----------------------------------------------
# Each is a packed file (lz.py) holding a container of two pictures: the bust and an 88x16 name plate.
PLATES = {
    190: "Cain", 191: "Abel", 192: "Matia", 193: "Johannes", 194: "Luca", 195: "Zion", 196: "Exal", 197: "Stayen",
    198: "Kilota", 199: "Lilis", 200: "Valtoss", 201: "Syria", 202: "Bale", 203: "Cardia", 204: "Unda", 205: "Aragi",
    206: "Whiteface", 207: "Red Mouflon", 208: "Terios", 209: "Kreis", 210: "Rubiel", 211: "Rhipsalis",
    212: "Grisina", 214: "Nico", 215: "Father Frie", 216: "Tavern Owner", 217: "Kutta", 218: "Plan", 219: "Fly",
    220: "Incest Girl", 221: "Rea", 223: "Cain", 224: "Syria", 225: "Dahlia", 226: "Matia", 227: "Aragi",
    228: "Luca", 229: "Aragi", 230: "Luca", 231: "Lilis", 232: "Dana", 233: "Zero", 234: "Matia", 235: "Abel",
    236: "Johannes", 239: "Soryu", 240: "Terga", 241: "Pasca", 242: "Eerie Demon", 243: "Mithras",
    244: "Novice Monk", 245: "Priest Soldier", 246: "Monk Soldier", 247: "Punk Soldier", 248: "Priest",
    249: "Resident", 250: "Resident", 251: "Resident", 252: "Angel Soldier", 253: "High Angel", 254: "Demon Soldier",
    255: "Demon Officer", 256: "Embryon", 257: "Elder Armorer", 258: "Young Armorer", 259: "Monk Soldier",
    260: "Echelon Soldier",
}                                                  # 222 is "?????" and stays


def plate(packed: bytes, text: str) -> bytes:
    """A portrait file with its name plate redrawn: bold italic letters, light on a thick dark rim, centred."""
    import struct
    import lz
    data, _ = lz.unpack(packed)
    count = struct.unpack_from("<I", data, 4)[0]
    off, size = (4 + 4 * v for v in struct.unpack_from("<HH", data, 12 + 4 * (count - 1)))
    off -= 4
    blob = data[4 + off:4 + off + size - 4]
    width, height = gfx.header(blob)[1], gfx.height(blob)
    for name, size_pt in [("arialbi.ttf", 13), ("arialbi.ttf", 12), ("ARIALNBI.TTF", 13), ("ARIALNBI.TTF", 12),
                          ("ARIALNBI.TTF", 11), ("ARIALNBI.TTF", 10)]:
        font = ImageFont.truetype(str(FONTS / name), size_pt)
        im = Image.new("L", (300, height))
        ImageDraw.Draw(im).text((3, 11), text, 255, font=font, anchor="ls")
        w = im.getbbox()[2] + 3
        if w <= width:
            break
    else:
        raise ValueError(f"{text!r} is too long for a name plate")
    cov = [[im.getpixel((x, y)) for x in range(w)] for y in range(height)]
    rows = [[0] * w for _ in range(height)]
    for y in range(height):
        for x in range(w):
            if cov[y][x] >= 56:
                rows[y][x] = 3 + round(cov[y][x] * 12 / 255)
            elif any(cov[j][i] >= 96 for j in range(max(y - 2, 0), min(y + 3, height))
                     for i in range(max(x - 2, 0), min(x + 3, w)) if abs(j - y) + abs(i - x) < 4):
                rows[y][x] = 1                    # a 2-pixel rim, corners rounded, like the Japanese plates
    blob = _fill(blob, rows, (width - w) // 2, 0)
    data = data[:4 + off] + blob + data[4 + off + len(blob):]
    return lz.pack(data, packed[:3])
