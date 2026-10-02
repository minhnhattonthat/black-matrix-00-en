# Translator brief — item, skill and unit tables

You are translating the equipment/item/skill database of *Black/Matrix 00* (PlayStation) for a fan patch. Read `glossary.md` first (names and terms are binding).

## Input

`work/tl/SYSTEM_tables_a.src.txt` or `_b.src.txt`, one field per line:

```
SYSTEM/2/<offset><TAB>w<WIDTH><TAB>Japanese
```

`wN` is the **byte limit** of that field. One ASCII letter is one byte; the build pads an odd-length ASCII text with one space, so an odd-length string occupies length + 1. Keep every answer at `WIDTH − 1` characters or fewer to be safe (e.g. `w20` → at most 19 characters; `w34` → at most 33; `w18` → at most 17).

Fields come in record order: for weapons a **name** (w20) then up to three **description lines** (w34 each, drawn as separate lines on the equipment screen). For gems/items/rings/skills: a name (w18–w26) then one or two description lines. Unit names (w18) come first in the file.

## Output

`work/tl/SYSTEM_tables_a.txt` (or `_b.txt`): one line per input line, same order, `id<TAB>English`. Every id exactly once. ASCII 0x20–0x7E only; no tabs; no `\n`.

Verify with `python tl.py check SYSTEM/tables_a work/tl/SYSTEM_tables_a.txt` (or `_b`) and fix every reported problem until it prints `ok`. `over width` means the encoded text exceeds the field.

## Style

- Names: Title Case, concise. Prefer the established English of the Japanese katakana (`ロングソード` → `Long Sword`, `ミセリコルデ` → `Misericorde`, `フランシスカ` → `Francisca`). Kanji names get natural English (`憂いの大剣` → `Sorrow Greatsword`). When a name will not fit, drop articles, then abbreviate the type word (`Gloves` → `Glove`, `Greatsword` → `G.Sword`, `Rapier` stays). Keep names unique.
- Stat lines: `ＡＴＫ＋７` → `ATK+7`; `ＡＴＫ＋１３　ＡＧＬ＋３` → `ATK+13  AGL+3` (two spaces); `ＭＡＧ` → `MAG`; a line of only fullwidth spaces plus `射程４` → right-align `Range 4` by padding with spaces to 33 characters (`"                          Range 4"`); a stat line with `射程` at the end → `ATK+5 ... Range 3` with spaces between so `Range N` ends at column 33.
- Description lines: plain, terse, no final period unless the Japanese is a full sentence pair. Keep the game's humor (`つつかれると痛い` → `Hurts when it pokes you`).
- Gems: `０時に力を得る宝石` → `Gains power at 0 o'clock` (hour pattern repeats for 0–23); `紅玉（こうぎょく）` → `Ruby (red jewel)` style parentheticals may be shortened to the English stone name alone if the first line already names it.
- Items: `対象のＨＰを１５回復する` → `Restores 15 HP to a target`; `ＰＰ` stays `PP`.
- Rings: `横を使いし者にのみ許されたリング` → `A ring only for those who use Sideways`; `宿りしは影ならぬ「詩人」` → `Within dwells no shade but "the Poet"`. Keep the quoted titles capitalised.
- Skills: `待機型に依存せず反撃を行う` → `Counterattacks regardless of stance`; stance/term vocabulary: 待機型 `stance`, 自軍フェイズ `your phase`, 好調 `in good form`, 移動 `movement`, 飛行移動 `flight`, 瞬間移動 `teleport`, 地中移動 `burrowing`, ＺＯＣ `ZOC`, 反撃 `counter`.
- Unit names (first ~60 lines, w18): `見習い神官兵` → `Novice Priest`, `見習い僧兵` → `Novice Monk`, `僧兵` → `Monk Soldier`, `中位僧兵` → `Monk Sergeant`, `高位僧兵` → `Monk Captain`, `パンク兵` → `Punk Soldier`, `パンク指揮官` → `Punk Commander`, `神官兵` → `Priest Soldier`, `護法兵` → `Law Guard`, `準護法兵` → `Jr. Law Guard`, `神父` → `Priest`, `司祭` → `Bishop`, `教団騎士` → `Church Knight`, `教団員` → `Church Member`, `天使兵` → `Angel Soldier`, `護法天使兵` → `Law Angel`, `高位天使兵` → `High Angel`, `天兵騎士` → `Angel Knight`, `見習い天使兵` → `Novice Angel`, `守護天使` → `Guardian Angel`, `護法天使長` → `Law Archangel`, `はぐれ悪魔` → `Stray Demon`, `悪魔兵` → `Demon Soldier`, `悪魔兵幹部` → `Demon Officer`, `暗黒術者` → `Dark Mage`, `パスカ` → `Pasca`, `レッドムフロン` → `Red Mouflon`, `エリュトロン` → `Erythron`; character names per the glossary (`ヨハネ` → `Johannes`, `ステイエン` → `Stayen`, `キロタ` → `Kilota`, `リリス` → `Lilis`, `シリア` → `Syria`, `ヴァルトス` → `Valtoss`, `エクサル` → `Exal`, `マティア` → `Matia`).

## Report

Reply with the file written, its line count, `ok` from the checker, and `NEW TERM: jp → en` for any name you coined that may recur (weapon families, rings' titles).
