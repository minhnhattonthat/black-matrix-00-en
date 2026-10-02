# Style reference — SCENARIO translation

Brief for translating the rest of `SCENARIO.DAT`. Read `glossary.md` first; it holds the names and the rules. These are worked examples from the pilot (scripts 051–060), which the user played and approved.

## Mechanics

- A window is one entry; `en` is free text. The build wraps at 30 characters per line and a window holds 3 lines, so keep `en` under about 85 characters. Over that it spills into a second window; avoid unless the meaning needs it.
- Only ASCII. `...` for `・・・`. `!?` for `！？`. Double `!!` at most. `"` for `「」`.
- Honorifics hyphenated: `Johannes-san`, `Valtoss-sama`, `Mephisto-san`. `神父様` → `Father`, `フリエ神父` → `Father Frie`. `お姉ちゃん` → `big sis` when it is address.
- The trailing four strings in every script (`青年 / ボンジュール / カイン / ？？？`) are `Young man / Bonjour / Cain / ???`.
- Battle scripts (like 055) hold defeat barks after the dialogue; short and in character.

## Voices

| Character | Voice | Example |
|---|---|---|
| Cain (ボク) | plain, earnest, a bit sulky | `It's no use, I can't do it.` / `...Lucky you, Matia.` |
| Matia | warm, gently scolding, `Honestly, Cain` | `Honestly! You nap all day, so you can't sleep at night, and then you oversleep!` |
| Johannes | formal, measured, no contractions when calm | `There is no need to dwell on it. Memories fade on their own if you leave them be.` |
| Father Frie | stiff, paternal | `It is better not to involve yourself with irregulars like them.` |
| Aragi | coarse, theatrical, `little lady`, `Kukuku`, `HYAA-HAHAHA` | `Sorry, but I had business with the little lady. Just put her down for a nap, that's all.` |
| Bale | archaic when pronouncing judgment (`thou`), cold otherwise | `Thou of the unclean soul. Hast thou any last words before thou diest?` |
| Luca | brisk, decisive | `We're going after him, Zion!` |
| Zion | terse | `...What a pain.` |

## Paired examples

| JP | EN | why |
|---|---|---|
| もう、驚かせないで | `Honestly, don't scare me like that.` | `もう` as exasperation → `Honestly` for Matia |
| カインったら / ないものねだりね | `Honestly, Cain, you always want what you don't have.` | idiom rendered, not glossed |
| ・・・そうか / 夢は深層心理を暗示するものだ | `...I see. Dreams hint at what lies deep in the mind.` | Johannes: complete sentences |
| だからこそ私は、 / 仮面をつけるのかもしれない | `Perhaps that is why I wear a mask.` | keep the hint, do not explain |
| ヒャーッハッハッハ！ / いいお友達を持ったもんだな | `HYAA-HAHAHA! Some friend you've got there.` | Aragi's laugh is a fixed spelling |
| お前なんかに / マティアは渡さない！！！ | `I won't hand Matia over to the likes of you!!!` | triple `!` kept once for the climax line |
| 貴様、何者だ？ | `Who are you?` | `貴様` carries no English word; hostility is in the scene |
| その指輪は / ＜ペインリング＞！！！ | `That ring is a Pain Ring!!!` | `＜＞` dropped |
| ＜規格外＞の天使 | `irregular angel` | glossary term, lower case |
| 汝、黒き土塊より生まれし | `Thou, born of the black clay,` | archaic register for Bale's formula |
| やられたあああ… (defeat bark) | `They got meeeeeeeeeeeeeeeee!` | keep under 30 characters: a word cannot wrap |
| （カインには荷が重いか・・？） | `(Is it too much for Cain...?)` | parentheses mark thought in battle text |
| 温かい紅茶があると嬉しい | `A cup of hot tea would be most welcome when I do.` | Johannes's understatement kept |

## One correction from the pilot

The first draft of Cain's dream line ran to four lines and spilled. Rewritten from
`It was a strange dream, though. It was pitch dark, I couldn't see anything... and a voice came from somewhere.`
to `A strange one, though. Pitch dark, I couldn't see a thing... then a voice, from somewhere.`
Cut filler, keep the beats.
