# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 9 (released, bug fixing). Last release: v00.13 (dist/), fixing issues #4, #5 (bigbanana23: circus text) and #6
  (n902ix: old names, cut plate, card subtitles, staff rolls).
- **Done:** all text translated on both discs, including picture text and movie subtitles. Repo laid out from
  fan-translation-template (2026-10-23).
- **2026-10-23:** item/weapon/ring names and description lines overflowed the STATUS, EQUIP and SHOP boxes (user
  report, Ch9 card). 42 names shortened to <= 16 chars, 79 description lines to <= 32 (bow/gun/whip "Range N" moved
  one char left); limits measured in game and enforced by test_tables.py. Checked in game: STATUS, ring picker, shop
  Buy list. Not seen: a bow/gun description (Range column) on screen.
- **2026-10-23:** saves from 00.9 kept the old unit names (Zion, Bale, Kreis; names live in the save). The load-time
  name fix (asm/halfwidth.asm) now also maps those spellings; verified by loading the Ch9 card and reading the unit
  records in RAM.
- **2026-10-26:** issue #2 (bigbanana23): the 23 status words that pop up over a unit (Dark, Sleep, Poison,
  barriers...) were still Japanese pictures (BATTLE.DAT sub 1, entry 7; labels.POPUPS). Redrawn in English, using
  the status-window names. Checked in game: Dark landing shows "Dark" (status roll forced with a breakpoint on a
  free-battle-396 state), and a cold boot loads the new table. Other 22 words not seen on screen.
- **2026-10-26:** the status label 毒 (SYSTEM sub 4 0x8e8, one kanji the overlay extractor skips) is now "Poison":
  written in spare bytes after "MAG Down" and its pointer (sub 4 0x3fdec) moved (tables.OVERLAY_MOVED). Verified in
  RAM after a cold boot; the "Poison" popup seen in game. Not seen: a screen drawing the label as text (unit list
  and Ally/Enemy Check show icons only).
- **2026-11-06:** issues #4, #5, #6 (not released yet; closed by the push of the fix commit).
  Checked in game (Ch9 card): 回 gone from SHOWS LEFT; shop tome names clear SOLD OUT (list form "Tome ~Flyer~", full
  name stays in the description); instruction pages Juggling, Beast Tamer, Trapeze; "Middle-aged Man" whole.
  Spare page sprites were parked on "rect 0", which is not blank on every sheet: that drew the stray dots.
  Plate cut: `labels.PLATE_END`, measured on that one plate, cause not traced.
  Offline only (composed from the sheet and table / rendered picture, not seen running): juggling shouts centred, stage
  cards 238/240 "Cutta", free battle 275 subtitle "laboratory" (name dropped), Crace/Glysina script lines.
  `tools/debug/circus.py` opens every act's page cold. Page 41 (spotlight practice) not reached: the route lands on 42.
- **2026-11-06:** rest of #6 (not released). Staff rolls in English (D10, `credits.py`, docs/re/movie-notes.md): 011 seen
  playing through the circus ending (scenario 405); 012 and 033 checked as decoded frames of the built stream only, their
  endings not played. Left Japanese: 011's mirrored katakana logo. Place spellings from the free-battle art (D11);
  "Calhing Village" seen in free battle 396, script lines not seen.
- **2026-11-06:** v00.13 released with the above. Release build, seen in game: instruction pages Flyers, Knife Throw,
  Tightrope; all 25 free-battle cards (scenarios 380-404: place spellings, "laboratory" subtitle). Still not seen: stage
  cards 238/240 "Cutta" (not reached by a warp), juggling shouts, spotlight page, the Crace/Glysina lines themselves,
  endings 012/033.
- **Next:** see the in-game checks below.
- **Disc-change screen:** works (reported by n902ix in issue #1).
- **Not yet seen in game:** the Disc 2 movies (008-010, cards 019-022/029-032), the final
  stage title card. Movie lines marked "check" in script/MOVIE are unverified.
- **Open bugs:** see `gh issue list --label bug`.
- **Waiting on the user:** nothing.
