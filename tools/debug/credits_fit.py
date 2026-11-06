"""Fit the staff rolls: frames of a page -> scroll track and Japanese text rows, for script/MOVIE/credits.json.
  python -X utf8 tools/debug/credits_fit.py BMM_011 [--out work/qa/credits/fit]
Needs the decoded frames in work/qa/credits/NNN/ (ffmpeg of the pristine stream). Prints the rows and writes
fit/BMM_011.json and one strip per page (the page's stacked text with its row numbers) to read the text from."""
import argparse, json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).parent.parent.parent
L, R = "l", "r"
# (first, last, [(x0, x1, align)]): frames where the page is at full brightness, and its text columns
PAGES = {
    "BMM_011": [(a, b, [(36, 200, L)]) for a, b in
                [(170, 227), (238, 292), (314, 379), (407, 483), (499, 574), (584, 663), (709, 787), (795, 867),
                 (877, 942), (947, 1002), (1051, 1104), (1109, 1201), (1208, 1300)]],
    "BMM_012": [(a, b, [(32, 180, L)] if a < 322 or 487 <= a < 696 or 1155 <= a < 1268 or 1328 <= a < 1477
                 else [(136, 288, R)]) for a, b in
                [(160, 201), (210, 253), (262, 307), (322, 365), (374, 420), (429, 472), (487, 532), (541, 582),
                 (591, 632), (641, 682), (696, 743), (751, 796), (804, 853), (862, 911), (920, 969), (978, 1027),
                 (1036, 1085), (1091, 1137), (1155, 1200), (1211, 1254), (1268, 1313), (1328, 1371), (1377, 1418),
                 (1423, 1464), (1477, 1518), (1522, 1564), (1569, 1610)]],
    "BMM_033": [(73, 1195, [(0, 159, R), (165, 319, L)]), (1170, 1330, [(40, 280, "c")]),
                (1295, 1425, [(40, 280, "c")])],
}
THRESH = {"BMM_011": 110, "BMM_012": 120, "BMM_033": 150}


def load(num, f):
    a = np.asarray(Image.open(ROOT / "work/qa/credits" / num / f"{f:05d}.png").convert("RGB")).astype(int)
    return a.max(2), a.max(2) - a.min(2)


def text_mask(num, f, cols, th):
    lum, sat = load(num, f)
    m = np.zeros(lum.shape, bool)
    for x0, x1, _ in cols:
        m[:, x0:x1 + 1] = (lum[:, x0:x1 + 1] > th) & (sat[:, x0:x1 + 1] < 40)
    return m


def shift_of(ref, prof, guess, reach=6):
    """Sub-pixel row shift d of prof against ref: prof[y] ~ ref[y - d]; ref may be longer than the screen."""
    best, score = guess, {}
    ints = range(int(guess) - reach, int(guess) + reach + 1)
    for d in ints:
        ys = np.arange(240)
        keep = (ys - d >= 0) & (ys - d < len(ref))
        score[d] = float((prof[ys[keep]] * ref[ys[keep] - d]).sum())
    best = max(score, key=score.get)
    a, b, c = score.get(best - 1, 0), score[best], score.get(best + 1, 0)
    den = a - 2 * b + c
    return best + (0.5 * (a - c) / den if den else 0)


def layer(num, frames, cols, th, offs, top, height):
    acc = np.zeros((height, 320))
    n = np.zeros((height, 320))
    for f in frames:
        m = text_mask(num, f, cols, th)
        d = int(round(offs[f]))
        y0 = -d + top            # screen row 0 in layer rows
        lo, hi = max(0, y0), min(height, y0 + 240)
        if lo < hi:
            acc[lo:hi] += m[lo - y0:hi - y0]
            n[lo:hi] += 1
    return acc / np.maximum(n, 1), n


def bands(profile, gap=2, min_h=4):
    out, cur = [], None
    for y, v in enumerate(profile):
        if v:
            if cur and y - cur[1] <= gap:
                cur[1] = y
            else:
                if cur:
                    out.append(cur)
                cur = [y, y]
    if cur:
        out.append(cur)
    return [c for c in out if c[1] - c[0] + 1 >= min_h]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stream")
    ap.add_argument("--out", default="work/qa/credits/fit")
    args = ap.parse_args()
    num = args.stream[-3:]
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    pages = []
    for pi, (a, b, cols) in enumerate(PAGES[args.stream]):
        th = THRESH[args.stream]
        offs = straight(num, a, b, cols, th, walk(num, a, b, cols, th))
        lo, hi = min(offs.values()), max(offs.values())
        top = int(np.ceil(hi)) + 4
        h = 240 + top - int(np.floor(lo)) + 4
        frames = sorted(offs)
        lay, n = layer(num, frames, cols, th, offs, top, h)
        im = Image.fromarray((np.clip(lay, 0, 1) * 255).astype("uint8")).convert("RGB")
        dr = ImageDraw.Draw(im)
        rows = []
        for x0, x1, align in cols:
            # tracks are sharp: text stays in the stack, a picture passing behind it does not
            hit = lay[:, x0:x1 + 1] > (.4 if args.stream == "BMM_033" else .8)  # 033 moves in sub-pixels
            for y0, y1 in bands(hit.sum(1)):
                xs = np.nonzero(hit[y0:y1 + 1].any(0))[0] + x0
                rows.append(dict(box=[int(xs[0]), y0 - top, int(xs[-1]), y1 - top], align=align))
        rows.sort(key=lambda r: (r["box"][1], r["box"][0]))
        for i, r in enumerate(rows):
            x0, y0, x1, y1 = r["box"]
            dr.rectangle([x0 - 1, y0 + top - 1, x1 + 1, y1 + top + 1], outline=(255, 0, 0))
            dr.text((0 if x0 > 20 else 300, y0 + top), str(i), fill=(255, 255, 0))
        im.save(out / f"{args.stream}-p{pi:02d}.png")
        keys = sorted(set(frames[:: max(1, len(frames) // 40)] + frames[-1:]))
        pages.append(dict(frames=[a, b], track=[[int(f), round(float(offs[f]), 1)] for f in keys], rows=rows))
        print(args.stream, pi, a, b, f"track {offs[a]:.1f}..{offs[b]:.1f}", f"rows {len(rows)}")
    (out / f"{args.stream}.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")


def straight(num, a, b, cols, th, offs):
    """A page that scrolls at one speed: the line through the walked track, refined on the sharpness of the stack."""
    fs = np.array(sorted(offs))
    ys = np.array([offs[f] for f in fs])
    core = slice(len(fs) // 5, -len(fs) // 5 or None)      # the walk can lose a nearly empty screen at the ends
    v, c = np.polyfit(fs[core], ys[core], 1)
    if len(fs) < 400 and np.std(ys - (v * fs + c)) > 2.5:  # eases to a stop: keep the walked track, smoothed
        return {f: float(y) for f, y in zip(fs, np.convolve(np.pad(ys, 4, "edge"), np.ones(9) / 9, "valid"))}
    masks = {f: text_mask(num, f, cols, th) for f in fs[:: max(1, len(fs) // 80)]}
    pad = int(abs(v) * (b - a)) + 60
    def score(v2, c2):
        acc = np.zeros((240 + 2 * pad, 320))
        for f, m in masks.items():
            d = pad - int(round(v2 * (f - (a + b) / 2) + c2))
            acc[d:d + 240] += m
        return float((acc ** 2).sum())
    centre = v * (a + b) / 2 + c
    span = (b - a) / 2 or 1
    grid = [(v + dv / span, centre + dc) for dv in np.arange(-24, 24.01, .5) for dc in np.arange(-6, 6.01, .5)]
    v2, c2 = max(grid, key=lambda g: score(*g))
    return {int(f): float(v2 * (f - (a + b) / 2) + c2) for f in fs}


def walk(num, a, b, cols, th):
    """Row shift of each frame against the middle frame of the page, frame-to-frame so a long roll stays locked."""
    mid = (a + b) // 2
    offs = {mid: 0.0}
    for rng in (range(mid + 1, b + 1), range(mid - 1, a - 1, -1)):
        prev = text_mask(num, mid, cols, th).sum(1).astype(float)
        base, last = 0.0, 0.0
        ref_at = mid
        for f in rng:
            prof = text_mask(num, f, cols, th).sum(1).astype(float)
            # rolling reference, refreshed every 10 frames: drift stays small, overlap stays large
            d = shift_of(prev, prof, last - base, reach=5)
            offs[f] = base + d
            last = offs[f]
            if abs(f - ref_at) >= 10:
                prev, base, ref_at = prof, last, f
    return offs


if __name__ == "__main__":
    main()
