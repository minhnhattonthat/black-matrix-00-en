# TOWN.DAT text translation — design

Last of the game's text containers. Covers the Notebook articles and the
town UI (prompts, coach tips, shop names). Follows the SCENARIO/SYSTEM
pipeline: JSON per block, `tl.py` for translation, insert at build time.

## Format

`TOWN.DAT` has 43 sub-files (`dat.py`). Sub-files are nested containers:

    u16 count, u16 1, u32 2, then count x (u32 offset, u32 size) in 4-byte words

Offsets are relative to the container start, entries are contiguous, the
first entry starts right after the table. A leaf is any blob that does not
parse as a container.

Town-state files 4..30 and sub 40 carry two text leaves, byte-identical in
every copy (path `(1,2)`/`(1,4)` in 4..30, `(4,2)`/`(4,4)` in 40):

| leaf | role | entries | lines | max bytes/line |
|------|------|---------|-------|----------------|
| A, 19288 B | Notebook articles | 68 | 846 | 32 (16 cells) |
| B, 3692 B | town UI | 48 | ~150 | 28 (14 cells) |

Text leaf layout: u16 offset table (count = first offset / 2), each entry

    (0x0001 [u16 param] <Shift-JIS bytes, even length> 0x0000)* 0x0000

Params (0x07/0x0b/0x0c) appear only on the three yes/no prompts of leaf B.
Empty entries exist (zero length, shared offset). No other text in the file
(subs 0/1 and 34..42 are graphics/data).

## Components

`town.py`

- `parse(blob) -> tree` / `rebuild(tree) -> bytes`: containers recursively,
  leaves as bytes. Rebuild pads each entry to 4 bytes with zeros and writes
  word offsets/sizes. Round trip of every original sub-file is identical.
- `text_entries(leaf) -> list[list[(param|None, bytes)]]` and
  `text_leaf(entries) -> bytes`; raise if the leaf exceeds 65535 bytes.
- `extract(sub) -> (notebook, town)`:
  - `notebook.json`: one entry per article
    `{"id": "TOWN/A/NN", "jp": [lines], "en": ""}`; `en` is text with `\n`
    hard breaks, lines wrapped at 32 bytes with `script.wrap` on insert.
    A line that is only `　` stays as is.
  - `town.json`: one entry per line
    `{"id": "TOWN/B/NN/LL", "jp": "...", "en": "", "width": 28}`;
    no wrapping, over-width raises, params are kept verbatim.
- `insert(sub, notebook, town) -> bytes`: walks the tree, replaces every
  leaf equal to original A or B with the rebuilt leaf, rebuilds containers.
  Unknown ids raise. Lines are produced from `en` when set, else `jp`.

`build.py`: `patch_town()` reads `script/TOWN/*.json`, rewrites every
sub-file of `TOWN.DAT`, called from `patch()`; `dump()` writes the two JSON
files once. `tl.py check`: width is enforced per line (`\n` split).

## Risks

- Growth: English is ~1.3x the bytes, so each town file grows ~6 KB. If the
  game reads town files into a fixed buffer, the overflow corrupts what
  follows. Verified empirically by entering town fresh (save states made
  inside town hide it). Fallback: in-place byte budget per leaf.
- Display width of the Notebook box is inferred from the longest Japanese
  line (16 cells); overflow is caught in play.
- Entry line counts: articles may gain lines (box scrolls, up to 25 lines
  in the original). Leaf B keeps lines 1:1.

## Testing

- Round trip: `rebuild(parse(sub)) == sub` for all 43 sub-files;
  `insert(sub, extract(sub)...) == sub`.
- Growth: longer `en` relayouts parents, offsets/sizes stay consistent,
  the two leaves are found again after insert.
- Width: B over 28 bytes raises; A long line wraps to two lines.
- Params: prompt lines keep their u16 param.
- `test_build`: identity build still byte-identical with TOWN restored.

## Out of scope

EXE strings (a handful; separate task). Graphics.
