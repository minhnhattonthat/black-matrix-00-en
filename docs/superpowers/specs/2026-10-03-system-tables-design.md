# System Text (menus, items, skills, unit names) — Design

Date: 2026-10-03
Parent spec: `2026-10-02-black-matrix-00-translation-design.md` (phase 4, non-SCENARIO text)
Depends on: `dat.py`, the halfwidth font hack, `glossary.md`.

## Goal

Translate the game's system text: the item/skill/unit database, options and memory-card messages, battle menu labels and objectives, and unit names in battle files. After this, a player sees English in menus, equipment screens, battle UI and save/load, not only in dialogue.

Out of scope: `TOWN.DAT` (Notebook articles and NPC chatter; its own plan), `EVENT.DAT` (graphics only), text drawn as images.

## Findings

| Where | What | Format |
|---|---|---|
| `SYSTEM.DAT` sub-file 2 | 25 tables; tables 2 and 6–24 hold text: unit names, fifteen weapon classes, gems, items, rings, skills. About 1,350 strings. | Table directory at offset 8: 25 × (`u16 offset`, `u16 size`) in 4-byte units. Fixed-size records with zero-padded Shift-JIS fields. Measured: units 20-byte records, name at 0; weapons 128-byte records, name at 0 (20), descriptions at 26 and 60; gems 96-byte, name 0, descriptions 28 and 62; items 118-byte, name 0 (18), description at 20; rings 98-byte, name 0, descriptions 30 and 62; skills 94-byte, name 0 (26), descriptions 26 and 62. Exact widths are pinned by the coverage test. |
| `SYSTEM.DAT` sub-file 10 | About 60 option, load/save and memory-card messages. | Zero-terminated strings packed from offset 0; each followed by 2–4 bytes of metadata; a table of absolute pointers (`0x800d4000` + offset) elsewhere in the sub-file. The file is 61 KB; the text uses about 1 KB. |
| `SYSTEM.DAT` sub-files 4 and 5 | Menu labels (`Config`, `Load`, `Item`, `Unit`, `Ring`, `Skill`), status names, battle prompts, objectives (`Defeat Bale`), skill names. About 100 strings. | Zero-terminated strings inside code overlays loaded at `0x80140000` (sub 4) and `0x80190000` (sub 5), referenced by MIPS `lui`/`addiu` pairs. |
| `BATTLE.DAT`, 433 sub-files of type `04 00 01 00` | Unit names, 16-byte field at the start of each 88-byte unit record, inside the container's unit table. 52 unique names, all present in SYSTEM table 2. | Fixed width. |

With the halfwidth hack, one byte holds one English letter, so a 14-byte name field holds 14 letters.

## Components

### `tables.py` — fixed-width fields

A declarative list of text fields:

```python
TABLES = [  # (archive, sub-file, table offset, record size, record count, [(field offset, width), ...])
    ("SYSTEM.DAT", 2, 0xBEF8, 20, 84, [(0, 14)]),            # unit names
    ("SYSTEM.DAT", 2, 0xCDF0, 60, 44, [(0, 20), (26, 32)]),  # gloves: name, description
    ...
]
```

- `extract()` yields `{"id": "SYSTEM/2/<offset>", "jp", "en": "", "width": N}` for every field whose Japanese is non-empty.
- `insert()` writes `encode(en)` into the field, zero-padded to the width. English longer than the width fails the build naming the id and width. `tl.py check` is given the width per entry so the translator sees the limit before applying.
- A coverage test asserts that no kana run in the sub-file lies outside a declared field, so a forgotten table is caught by the test, not by a Japanese item name in play.
- Battle unit names are not translated separately: `insert` for `BATTLE.DAT` maps each record's Japanese name to its English through the SYSTEM table 2 translations. A battle name with no SYSTEM match fails the build.

### `pointers.py` — sub-file 10

- Pointers appear in two places: a `u32` after each message (a chain to the next message) and a table of 47 near the end of the sub-file (offset `0xcb80` region). All 78 are 4-byte aligned words in `0x800d4000–0x800d4800`.
- `extract()` walks the message region from offset 0 (zero-terminated strings, 2-byte aligned, each followed by its metadata words).
- `insert()` lays the strings out again from offset 0 with their metadata, then remaps every aligned word in the pointer range through the old→new offset map. A word that does not land on a string start fails the build (it would be data, not a pointer). Text may grow until the message region meets the next used data; exceeding that fails the build.

### Overlay labels — sub-files 4 and 5

- Sub-file 5 holds no Shift-JIS text; only sub-file 4 (79 strings) is handled. Only 4 of its strings are reached by a `lui`/`addiu` pair; the rest are referenced through data tables that are not worth mapping, because in-place replacement needs no knowledge of the references.
- `extract()` lists every zero-terminated Shift-JIS string in the overlay.
- `insert()` overwrites in place; English must be at most the original byte length (zero-padded). Longer fails the build.
- If the first translation pass shows that many labels need more room, a second phase relocates long strings into the overlay's zero padding and patches whatever references them. That phase is not designed here.

### Build

`build.patch()` gains: unpack `SYSTEM.DAT` and `BATTLE.DAT` from `work/orig/`, apply the three inserters, repack to `work/extracted/`. `python build.py dump` writes `script/SYSTEM/*.json`. Sub-file sizes do not change (fixed fields, in-place pointers), so archive layout is unchanged; the DAT repack already handles growth if a later phase needs it.

### Translation

About 1,500 short strings. Translated inline in the session (no agents) with `tl.py show/apply/check`, the width shown per entry. Abbreviations that the width forces (e.g. `Lthr Gloves`) go in a glossary table so item names stay consistent between the equipment list and any dialogue that mentions them.

## Testing

- Each inserter: extract then insert with empty `en` is byte-identical for every sub-file it touches.
- Width overflow and missing BATTLE name match raise with the id.
- Coverage: no kana outside declared fields in SYSTEM sub-file 2; every pointer in sub-file 10 is accounted for.
- The patched image boots; the user checks the equipment screen, a skill list, the options menu, a save/load prompt and a battle's unit names.

## Risks

- A field may be shorter than any sensible English (14 bytes for unit names like `見習い神官兵` → `Novice Priest`). Abbreviate; a VWF is out of scope.
- The game may read some fields with a fixed Japanese character count rather than a byte terminator (e.g. drawing exactly 7 cells). Caught in the user's screen check; fix would be per-field padding with spaces instead of zeros.
- Overlay strings may also be referenced through data tables, not only `lui`/`addiu`; such a string would be missed by `extract` and stay Japanese. The coverage test lists unreferenced strings so they are visible.
