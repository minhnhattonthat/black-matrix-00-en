# SCENARIO Translation — Design

Date: 2026-10-02
Parent spec: `2026-10-02-black-matrix-00-translation-design.md` (phase 4, `SCENARIO.DAT` part)
Depends on: the pipeline (`dat.py`, `script.py`, `build.py`) and the halfwidth font hack, both merged.

## Goal

Translate the story dialogue in `SCENARIO.DAT` into English, starting with a pilot of the opening that the user plays before the rest is done.

Decisions made with the user:

- Rollout: pilot first (boot warning plus the opening scripts), then scale up under a separate plan.
- Style: faithful, honorifics kept (`-san`, `-sama`, `-chan`, …), sentence structure followed where English allows.
- Claude translates; the user spot-checks in-game.

## Findings

Across the 382 scripts: 35,040 strings, 26,107 unique, 331k characters.

| String op | Count | Role |
|---|---|---|
| `1050` | 32,497 | dialogue line |
| `1073` | 1,625 | string with a leading argument |
| `1081` | 789 | menu choice |
| `105b` | 104 | string plus jump target |
| `108a`, `108f` | 25 | strings with targets / plain string |

- Dialogue windows are runs of 1–3 consecutive `1050` lines: 18,213 runs (8,154 single, 5,834 double, 4,225 triple). No jump targets the middle of a run.
- 18,093 runs are followed by `000a` (call) to one of a handful of addresses: the "show window and wait" routine. The remaining 120 are followed by other ops (`1051`, `105f`, …) and are not spilled.
- A run is normally preceded by `1058 <expr>` (speaker or portrait id; ten distinct values in the first 40 scripts) and `2041 <expr>` (a running counter, probably the voice clip index).
- A window line holds 30 halfwidth characters (15 cells). The hard cap is 46 characters.

## Translation unit: the window

`script.py` gains window grouping on top of tokens.

**JSON entry shape** for a dialogue window:

```json
{"id": "SCENARIO/012/005fa", "speaker": 8, "jp": ["大事なものなんだよ！", "どこだ！どこなんだよ～！？"], "en": ""}
```

- `id` is the offset of the run's first `1050` token.
- `speaker` is the immediate from the nearest preceding `1058` in the same script, or `null`. It is context for the translator only; nothing is written back.
- `jp` is the list of lines, decoded as before.
- `en` is free text. The build wraps it to lines of at most 30 characters at spaces; a `\n` in `en` forces a break. Every line must fit 30 characters after wrapping, or the build fails naming the entry (a single word over 30 characters is the only way to trigger that).
- Empty `en` keeps the Japanese lines unchanged.

Non-dialogue string ops keep the existing single-string entry shape (`jp` is a string). The 120 runs not followed by `000a` are also emitted as windows but with `"spill": false`, and more than three wrapped lines fails the build for them.

**Spill.** When `en` wraps to more than three lines, the build emits the first three as `1050` tokens, then a copy of the following `000a` call token, then the next three lines, and so on. The game shows two windows in sequence. Spilled windows are listed in the build output so the translator can tighten them; they may desync a voice clip from its text.

**Jumps and sizes.** Spilled and grown windows only ever lengthen the token stream between two existing tokens, so the existing jump fixup covers them. The 0x20000 script-size guard stays.

**Identity.** With every `en` empty, insert still reproduces the original bytes. The existing round-trip tests stay green.

## Migration

`python build.py dump` regenerates all 382 JSON files in the new shape. The only translated entries today are the halfwidth test strings in `000.json`; they are dropped. `dump` still refuses to overwrite a file that exists, so migration deletes `script/SCENARIO/` first; the plan does that explicitly.

## Glossary and style guide

`glossary.md` is written before any translation and approved by the user:

1. **Names and terms**: every katakana word of two or more characters, by frequency, with a proposed romanisation. The user corrects or approves the list.
2. **Speaker table**: speaker id → character name, worked out from the pilot scripts.
3. **Style rules**: honorifics kept and hyphenated (`Exsal-san`); `・・・` becomes `...`; `～` becomes `~` or is dropped; `！？` becomes `!?`; only ASCII 0x20–0x7E in `en`; Japanese quotes `「」` become straight double quotes; a window's lines are one utterance, so wrap freely rather than line by line; stay inside two lines where the Japanese used two.

## Pilot

Scope: the boot warning (`000.json`) and the opening story. Which sub-files make up the opening is not recorded anywhere; the pilot finds them by translating `000` and the lowest-numbered story scripts, building, and having the user play until English stops. The user reports the last English scene and the next Japanese one; the plan iterates once or twice.

Target size: 300–500 windows. Claude translates inline in this session, window by window with the surrounding windows as context, not through parallel agents: the pilot exists to settle the style.

Output of the pilot, besides the translated scripts: a corrected glossary, a confirmed speaker table, a style reference with examples, and the list of spilled windows. These are the inputs to the scale-up plan.

## Testing

- `script.py`: grouping yields the 18,213 runs; `speaker` is read from the preceding `1058`; wrapping at 30 with `\n` respected; a 4-line `en` spills with a copied call; a 4-line `en` on a `spill: false` window fails; a 31-character word fails; all-empty `en` is byte-identical; every jump still lands on a token after spilling every window in a script.
- Build: the pilot image boots and the user plays the opening.

## Out of scope

- Menu choices and other non-dialogue strings beyond keeping them translatable as single lines.
- The other archives, the EXE strings, and any text in graphics.
- Proportional font, more than 30 characters per line.
- Voice/text sync for spilled windows.
