# Decisions

The user's rulings on scope, style and trade-offs, newest last. Read before asking the user anything; if a later
decision replaces one, mark the old one "replaced by D<n>" instead of deleting it. Binding term spellings live in
`glossary.md`; this file holds the why.

Rows D1-D9 were collected from earlier notes when the repo moved to the template; the options offered then were not
recorded.

| # | Date | Question | Options offered | Decision and reason |
|---|---|---|---|---|
| D1 | 2026-10-03 | Style and honorifics | faithful, localised; keep (-san), drop | Faithful; honorifics kept, hyphenated. |
| D2 | 2026-10-03 | 近親 ("Incest") | keep, rename | Keep: it is the game's own term. |
| D3 | 2026-10-20 | Romanization source for names | official site, Hepburn | Double O official site spellings (glossary.md); Abel and Aragi kept over the site's "Able"/"Arag". |
| D4 | 2026-10-08 | Abbreviations | full names, abbreviate | Full names, no abbreviations. |
| D5 | 2026-10-04 | Graphics text | leave Japanese, redraw | Redraw all picture text; a few unused leftovers stay Japanese (README, known issues). |
| D6 | 2026-10-05 | Stage title card slide-in | keep the slide, freeze | Keep the slide animation (letters overlap briefly). |
| D7 | 2026-10-04 | Movies | leave, subtitle | English subtitles burned into the video; voices untouched. |
| D8 | 2026-10-08 | Release contents | with cue files, patches only | Release zip = xdelta patches + PATCHING.txt, no cue files. |
| D9 | 2026-10-23 | Repo layout | as is, fan-translation-template | Template docs/config; Python modules and tests stay at the root (sibling repos did the same). |
