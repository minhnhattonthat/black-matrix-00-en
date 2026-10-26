# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 9 (released, bug fixing). Last release: v00.12 (dist/), fixing issue #2 (bigbanana23: status words over units,
  Poison label).
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
- **Next:** see the in-game checks below.
- **Disc-change screen:** works (reported by n902ix in issue #1).
- **Not yet seen in game:** the Disc 2 movies (008-010, cards 019-022/029-032), the final
  stage title card. Movie lines marked "check" in script/MOVIE are unverified.
- **Open bugs:** none filed (`gh issue list --label bug`).
- **Waiting on the user:** nothing.
