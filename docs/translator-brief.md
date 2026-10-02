# Translator brief

You are translating part of the Japanese script of *Black/Matrix 00* (PlayStation, 2000) into English for a fan patch. Work only on the scripts you were assigned.

## Read first

1. `glossary.md` — names, terms, style rules. Binding.
2. `docs/style-reference.md` — character voices and worked examples from the approved pilot.

## Input

For each assigned script `NNN`, read `work/tl/NNN.src.txt`. One entry per line:

```
SCENARIO/NNN/offset<TAB>speaker<TAB>Japanese line 1 / line 2 / line 3
```

- `speaker` is a portrait slot (`0`, `16`, …), not a name. The same number can be a different character in another scene. Use it only to tell who is talking within a scene; work out identity from the text.
- ` / ` separates the lines of one dialogue window. Translate the window as one utterance.
- Lines with speaker `-` are single strings: menu choices, names, labels, battle barks, narration.

## Output

Write `work/tl/NNN.txt` with exactly one line per input line, in the same order:

```
SCENARIO/NNN/offset<TAB>English
```

- Every id from the source file must appear once; copy ids exactly.
- No tabs inside the English. No literal newlines; write `\n` (backslash n) only when a break must fall at a specific place, which is rare.
- ASCII 0x20–0x7E only. No curly quotes, no em dashes (use `--`), no Japanese characters, no fullwidth characters.

## Length

A dialogue window shows 3 lines of 30 characters. Keep each window's English at or under about 85 characters so it wraps into 3 lines; the build splits anything longer into a second window, which breaks the pacing. Single strings (speaker `-`) must stay under 30 characters where the Japanese was short (menu choices, names); narration strings may run to 85 like windows. No single word may exceed 30 characters.

Count before you write a long line. Japanese is denser than English: a full 3-line Japanese window usually needs cutting, not padding.

## Style, in brief

- Faithful: keep the information and the order of ideas; adapt idiom, not meaning.
- Honorifics kept and hyphenated (`Johannes-san`, `Valtoss-sama`, `Lilis-chan`). `神父様` → `Father`. `おばちゃん` (the tavern owner Dahlia) → `Auntie`. `坊や` → `kiddo`. `お兄さん`/`お姉ちゃん` as address → `mister` / `big sis` when no name fits.
- `・・・` → `...`; `！？` → `!?`; cap exclamation marks at `!!` except one climax line per scene; `「」` → `"`; `＜term＞` → the term with no brackets.
- Laughs: Aragi `HYAA-HAHAHA` / `Kukuku`; others `Heh heh`, `Hee hee`, `Ha ha ha` as fits.
- Screams and barks: short, e.g. `Gaaah!!`, `Eek!!`.
- The last four strings of nearly every script are `青年 / ボンジュール / カイン / ？？？` → `Young man` / `Bonjour` / `Cain` / `???`.
- Battle-script defeat barks (after the dialogue) are short and in character.
- When the Japanese is a bare `・・・・・・`, output `......`.
- When a line is only an interjection (`うん`, `え？`, `！？`) translate it as such (`Yeah.`, `Huh?`, `!?`).

## Consistency

Use the glossary spelling for every name and term. If you meet a name or term that is not in the glossary, choose a romanisation, use it consistently, and list it at the end of your report as `NEW TERM: Japanese → English (script NNN)` so it can be added.

## Report

When done, reply with: the list of files written, the entry count per file, any NEW TERM lines, and any line where you were unsure of the meaning (`UNSURE: id — note`). Nothing else.
