"""Staff rolls: each movie's Japanese text is erased frame by frame and English drawn on the same scroll track.
script/MOVIE/credits.json: stream -> fade (frames around a page), floor (lowest brightness read as text), size (font),
overlap (033: pages can share frames, they scroll far apart; the others cut halfway to the neighbour),
intro (011: a page zooms in over its first frames and fades dim at its end, outside its row boxes: on those frames all
grey is wiped, to this many pixels past the page's longest row), clamp [first, last, level] (dim grey to black: 011 leaves faint copies of old pages), panels [L x0, L x1, R x0, R x1]
(012: the black panel beside the line is wiped whole), pages [frames [a, b], track [[frame, offset]], rows].
A row: box (Japanese text at offset 0), align (l/r/c, the English keeps that edge), en, bold, jp.
  python -X utf8 credits.py BMM_011 [work/qa/credits/en]   render one stream's frames, to look at without jPSXdec"""
import json, shutil, sys, tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

import movie

ROOT = Path(__file__).parent
SPEC = ROOT / "script" / "MOVIE" / "credits.json"
WHITE = 235
SHADOW = .6


def spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def width(row: dict, size: int) -> int:
    return ImageFont.truetype("arialbd.ttf" if row["bold"] else "arial.ttf", size).getbbox(row["en"])[2]


def tile(row: dict, size: int) -> np.ndarray:
    """Coverage 0..1 of the English line."""
    font = ImageFont.truetype("arialbd.ttf" if row["bold"] else "arial.ttf", size)
    im = Image.new("L", (width(row, size) + 2, size + 4))
    ImageDraw.Draw(im).text((1, 1), row["en"], fill=255, font=font)
    return np.asarray(im).astype(np.float32) / 255


def offset(page: dict, f: int) -> float:
    """Track at frame f, the end slopes carried on past its first and last keys."""
    keys = np.array(page["track"], dtype=float)
    if f <= keys[0, 0]:
        i = 0
    elif f >= keys[-1, 0]:
        i = len(keys) - 2
    else:
        return float(np.interp(f, keys[:, 0], keys[:, 1]))
    (a, ya), (b, yb) = keys[i], keys[i + 1]
    return float(ya + (yb - ya) * (f - a) / (b - a))


def erase(rgb: np.ndarray, boxes: list) -> None:
    """Fill the bright grey pixels of the boxes (x0, y0, x1, y1, floor, saturation limit) from their nearest
    neighbours, in place."""
    lum, sat = rgb.max(2).astype(int), (rgb.max(2).astype(int) - rgb.min(2))
    mask = np.zeros(lum.shape, bool)
    for x0, y0, x1, y1, floor, limit in boxes:
        y0, y1, x0, x1 = max(0, y0), min(240, y1), max(0, x0), min(320, x1)
        if y0 < y1 and x0 < x1:
            mask[y0:y1, x0:x1] |= (lum[y0:y1, x0:x1] > floor) & (sat[y0:y1, x0:x1] < limit)
    fill(rgb, mask)


def fill(rgb: np.ndarray, mask: np.ndarray) -> None:
    if mask.any():
        mask = ndimage.binary_dilation(mask, iterations=2)    # MDEC rings around each stroke
        idx = ndimage.distance_transform_edt(mask, return_distances=False, return_indices=True)
        rgb[mask] = rgb[idx[0][mask], idx[1][mask]]


def wipe(rgb: np.ndarray, right: int) -> None:
    """A page zooming in or fading, its text anywhere left of `right`: grey outside the picture goes black; over the
    picture (bounding box of the coloured pixels) only thin bright strokes go, or the picture would go with them."""
    lum = rgb.max(2).astype(int)
    sat = lum - rgb.min(2)
    cols, rows = np.nonzero((sat > 12).sum(0) > 6)[0], np.nonzero((sat > 12).sum(1) > 6)[0]
    inside = np.zeros(lum.shape, bool)
    if cols.size and rows.size:
        inside[max(0, rows[0] - 4):rows[-1] + 5, max(0, cols[0] - 4):cols[-1] + 5] = True   # dark edges have no colour
    area = np.zeros(lum.shape, bool)
    area[:, :right] = True
    rgb[area & ~inside & (sat < 48)] = 0
    fill(rgb, area & inside & (sat < 48) & (lum - ndimage.grey_opening(lum, size=5) > 40))


def peak(rgb: np.ndarray, box: list) -> float:
    """Brightness of the text in a box: the 96th percentile of its grey pixels."""
    x0, y0, x1, y1 = box
    y0, y1, x0, x1 = max(0, y0), min(240, y1), max(0, x0), min(320, x1)
    if y0 >= y1 or x0 >= x1:
        return 0.
    px = rgb[y0:y1, x0:x1]
    grey = px[(px.max(2).astype(int) - px.min(2)) < 48]
    return float(np.percentile(grey.max(1), 96)) if grey.size else 0.


def draw(rgb: np.ndarray, cov: np.ndarray, x: int, y: float, alpha: float) -> None:
    """Blend a coverage tile at sub-pixel row y, with a dark shadow so it reads over a bright picture."""
    y0 = int(np.floor(y))
    frac = y - y0
    h, w = cov.shape
    soft = np.zeros((h + 2, w + 1), np.float32)
    soft[:h, :w] += cov * (1 - frac)
    soft[1:h + 1, :w] += cov * frac
    ys, xs = slice(max(0, y0), min(240, y0 + h + 2)), slice(max(0, x), min(320, x + w + 1))
    if ys.start >= ys.stop or xs.start >= xs.stop:
        return
    part = soft[ys.start - y0:ys.stop - y0, xs.start - x:xs.stop - x][..., None] * alpha
    shadow = np.zeros(rgb.shape[:2] + (1,), np.float32)
    sy, sx = slice(ys.start + 1, min(240, ys.stop + 1)), slice(xs.start + 1, min(320, xs.stop + 1))
    shadow[sy, sx] = part[:sy.stop - sy.start, :sx.stop - sx.start]
    base = rgb * (1 - SHADOW * shadow)
    base[ys, xs] = base[ys, xs] * (1 - part) + WHITE * part
    rgb[...] = np.clip(base + .5, 0, 255).astype(np.uint8)


def track_row(row: dict, off: float) -> list:
    x0, y0, x1, y1 = row["box"]
    d = int(round(off))
    return [x0 - 1, y0 + d - 1, x1 + 2, y1 + d + 2]


def windows(stream: dict) -> list:
    """Frames each page owns: its fade on both sides, cut halfway to a neighbour so two pages never overlap."""
    pages, fade = stream["pages"], stream["fade"]
    out = []
    for i, p in enumerate(pages):
        lo, hi = p["frames"][0] - fade, p["frames"][1] + fade
        if i and not stream.get("overlap"):
            lo = max(lo, (pages[i - 1]["frames"][1] + p["frames"][0] + 1) // 2)
        if i + 1 < len(pages) and not stream.get("overlap"):
            hi = min(hi, (p["frames"][1] + pages[i + 1]["frames"][0]) // 2)
        out.append((max(0, lo), hi))
    return out


def rows_alpha(stream: dict, load) -> dict:
    """(page index, row index) -> {frame: opacity}: how bright the Japanese row is on each frame, against its best."""
    out = {}
    for pi, (p, (lo, hi)) in enumerate(zip(stream["pages"], windows(stream))):
        levels = {}
        for f in range(lo, hi + 1):
            im = load(f)
            if im is not None:
                levels[f] = [peak(im, track_row(r, offset(p, f))) for r in p["rows"]]
        for ri in range(len(p["rows"])):
            vals = np.array([levels[f][ri] for f in levels])
            top = np.percentile(vals, 90) if len(vals) else 1
            # a median over 5 frames: one star or stray picture pixel does not flash a whole row
            vals = ndimage.median_filter(vals, size=5, mode="nearest")
            dim = ndimage.uniform_filter1d(np.clip(vals / max(top, 1), 0, 1), size=3, mode="nearest")
            dim = np.where(vals < stream["floor"] * .4, 0, dim)
            out[pi, ri] = dict(zip(levels, dim.tolist())), float(top)
    return out


def render(stream: dict, fdir: Path) -> list:
    """Rewrite the frames of d/f in place; returns the frame numbers changed."""
    def load(f):
        p = fdir / f"{f:05d}.png"
        return np.asarray(Image.open(p).convert("RGB")) if p.exists() else None
    size = stream["size"]
    tiles = {(pi, ri): tile(r, size) for pi, p in enumerate(stream["pages"]) for ri, r in enumerate(p["rows"])}
    alpha = rows_alpha(stream, load)
    spans = windows(stream)
    a0, b0 = spans[0][0], spans[-1][1]
    if "clamp" in stream:
        a0, b0 = min(a0, stream["clamp"][0]), max(b0, stream["clamp"][1])
    changed = []
    for f in range(max(0, a0), b0 + 1):
        src = load(f)
        if src is None:
            break
        rgb = src.copy()
        lum, sat = rgb.max(2).astype(int), rgb.max(2).astype(int) - rgb.min(2)
        if "clamp" in stream and stream["clamp"][0] <= f <= stream["clamp"][1]:
            rgb[(lum < stream["clamp"][2]) & (sat < 16)] = 0
        live = [(pi, p) for pi, (p, (lo, hi)) in enumerate(zip(stream["pages"], spans)) if lo <= f <= hi]
        if "panels" in stream:
            near = min(stream["pages"], key=lambda p: min(abs(f - p["frames"][0]), abs(f - p["frames"][1])))
            x0, x1 = stream["panels"][:2] if near["rows"][0]["align"] == "l" else stream["panels"][2:]
            rgb[:, x0:x1 + 1] = 0
        boxes = []
        for pi, p in live:
            for ri, r in enumerate(p["rows"]):
                dim, top = alpha[pi, ri]
                # a fading row dips under the floor: follow it down, as far as the background allows
                floor = max(30, min(stream["floor"], .55 * dim.get(f, 0) * top))
                # "over": the line crosses a picture, MDEC bleeds the picture's colour into its strokes
                boxes.append(track_row(r, offset(p, f)) + [floor, 96 if r.get("over") else 48])
        if "intro" in stream:
            for pi, p in live:
                if f <= p["frames"][0] or f >= p["frames"][1]:
                    wipe(rgb, max(r["box"][2] for r in p["rows"]) + stream["intro"])
        erase(rgb, boxes)
        for pi, p in live:
            off = offset(p, f)
            for ri, r in enumerate(p["rows"]):
                op = alpha[pi, ri][0].get(f, 0)
                if op > .02:
                    cov = tiles[pi, ri]
                    x0, y0, x1, y1 = r["box"]
                    x = {"l": x0, "r": x1 - cov.shape[1] + 2, "c": (x0 + x1 - cov.shape[1]) // 2 + 1}[r["align"]]
                    # centre the English on the Japanese band
                    draw(rgb, cov, x, y0 + off + (y1 - y0 + 1 - cov.shape[0]) / 2, op)
        Image.fromarray(rgb).save(fdir / f"{f:05d}.png")
        changed.append(f)
    return changed


def patch(src: Path, stream: dict, dst: Path) -> None:
    data = src.read_bytes()
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        movie.decode(data, d)
        dst.write_bytes(movie.replace(src, data, d, render(stream, d / "f")))


def cached(src: Path, stream: dict) -> Path:
    """Patched stream, rendered on a cache miss; the code is in the key, so a change here re-renders."""
    path = movie.cache_path(src, [stream, Path(__file__).read_text(encoding="utf-8")])
    if not path.exists():
        movie.CACHE.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        patch(src, stream, tmp)
        tmp.replace(path)
    return path


if __name__ == "__main__":
    name = sys.argv[1]
    out = ROOT / (sys.argv[2] if len(sys.argv) > 2 else f"work/qa/credits/en/{name[-3:]}")
    src = next(p for p in (ROOT / "work" / d / "MOVIE" / f"{name}.STR" for d in ("orig", "orig2")) if p.exists())
    shutil.rmtree(out, ignore_errors=True)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        movie.decode(src.read_bytes(), d)
        render(spec()[name], d / "f")
        shutil.copytree(d / "f", out)
    print(out)
