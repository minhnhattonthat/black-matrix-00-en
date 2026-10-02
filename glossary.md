# Glossary and style guide — Black/Matrix 00

## Style

- Faithful to the Japanese; sentence order followed where English allows.
- Honorifics kept, hyphenated: `-san`, `-sama`, `-chan`, `-kun`, `-dono`. `神父様` → `Father`; `お姉ちゃん` → `big sis` / `Name-neesan` only when used as address; `おばちゃん` (Dahlia) → `Auntie`; `坊や` → `kiddo`.
- First-person pronouns (`ボク`, `オレ`, `アタシ`) are all `I`; the voice carries the difference.
- `・・・` and `・・` → `...`; `～` after a vowel → drop or `~` when the drawl matters; `！？` → `!?`; `！！！` → `!!`; `「」` and `『』` → `"`; `＜＞` around proper nouns → dropped, or `"` for titles.
- ASCII 0x20–0x7E only. Fullwidth digits → ASCII digits.
- A window is one utterance: wrap freely across its 1–3 lines; stay inside the Japanese line count where it fits; 30 characters per line, spill (4+ lines) only when meaning needs it.
- Character gender for pronouns: Cain, Johannes, Zion, Exal, Abel, Luca, Aragi, Valtoss, Bale, Terios male; Matia, Lilis, Stayen, Kilota, Syria, Cardia, Dahlia, Fly, Rea female. Correct as the pilot reveals.

## Names

| Japanese | English | notes |
|---|---|---|
| カイン | Cain | protagonist, 16, wingless, memory loss |
| アベル | Abel | black-winged look-alike |
| マティア | Matia | Cain's childhood friend, an Incest |
| ヨハネ | Johannes | Cain's guardian, "irregular" angel |
| メフィスト | Mephisto | Johannes's sick companion on the island |
| ルカ | Luca | demon, Zion's companion |
| ザイオン | Zion | demon |
| エクサル | Exal | Cypherpunk member |
| ステイエン / ステイ | Stayen / Stay | ex-monk soldier |
| キロタ | Kilota | child, calls Stayen "big sis" |
| リリス | Lilis | child |
| ヴァルトス | Valtoss | Cypherpunk leader |
| シリア | Syria | |
| ベイル・ペレンデール | Bale Perendale ? | angel, Church |
| カルディア | Cardia | Stayen's "big sister" in the Church |
| ウンダ | Unda | demon village elder |
| アラギ | Aragi | demon, main antagonist |
| ホワイトフェイス | Whiteface | |
| レッド・ムフロン | Red Mouflon | one of the 十審将 |
| テリオス | Terios | Church |
| クレイス | Kreis ? | Church |
| ルビエル | Rubiel | |
| リプサリス | Rhipsalis | |
| グリシナ | Grisina | |
| ニコ | Nico | island child |
| フリエ神父 | Father Frie ? | island priest |
| クッタ | Kutta | |
| プラン | Plan | |
| フライ | Fly ? | Cypherpunk, odd remarks |
| レア | Rea | Incest girl in the demon village |
| ダリア（・ビアー） | Dahlia (Beer) | tavern owner, "Auntie" |
| ダーナ | Dana | |
| ゼロ | Zero | |
| ソリュウ | Soryu | demon |
| パスカ | Pasca | also "a swarm of Pasca": creatures |
| サイファーパンク | Cypherpunk | resistance organisation |
| エシュロン兵 | Echelon soldier | |
| ボンジュール | Bonjour | name-entry default? (title screen strings) |

## Terms and places

| Japanese | English | notes |
|---|---|---|
| インセスト | Incest | humans with a special power; canonical, keep |
| ペインリング | Pain Ring | |
| ペインキラー | Painkiller | the Pain Ring's ultimate power |
| 渇き | the Thirst | black-wing illness |
| 教団 / プロデヴォン教団 | the Church / the Prodevon Church | |
| 僧兵 | monk soldier | |
| 神官兵 / 見習い神官兵 | priest soldier / novice priest soldier | |
| 天使兵 / 高位天使兵 | angel soldier / high angel soldier | |
| 悪魔兵幹部 | demon officer | |
| 十審将 | the Ten Tribunal Generals ? | |
| 構成員 | member (of Cypherpunk) | |
| 黒羽根 / 白羽根 | black-wing / white-wing | as noun for the people |
| 規格外 | irregular | the island's word for Johannes and Mephisto |
| 世界樹 | World Tree | |
| 倒立樹計画 | the Inverted Tree Plan | |
| 大地母神 | the Earth Mother | |
| エンブリオン | Embryon | creatures |
| キボートス島 | Kibotos Island | Cain's home |
| ヴェローナ | Verona | city |
| サンバルテルミ | San Bartelmi ? | great cathedral city |
| ラムシュタイン大聖堂 | Ramstein Cathedral | |
| ラメル教会 / リゴルの教会 / ハルフォルト教会 | Ramel Church / Rigor Church / Halfort Church | |
| グーテンベルグ | Gutenberg | handout in Verona |
| ペレンデール | Perendale | Bale's family name |
| グレイヘン | Greyhen ? | |
| ルオナ | Luona | |
| ボーナスシナリオ | Bonus Scenario | scripts 020–037 |
| 核神機 | ? | portrait label for Matia; decide when met in text |

## Speakers

The `speaker` field in the JSON is the `1058` value before a window. In the opening it is `16` for one side of the conversation and `0` for the other, and the same value is reused by different characters in different scenes, so it is a portrait slot, not an identity. Use it only to tell speakers apart within a scene; identify them from the text.

| id | meaning |
|---|---|
| 0 | default slot; narration and most NPC lines |
| 16 | second slot; the other party in a two-way scene |
| 1, 3, 5, 17, 19, 21, 22 | further slots / reaction lines (`！？`, thoughts) |

## Added during the scale-up

| Japanese | English | notes |
|---|---|---|
| 雑記帳 | the Notebook | tavern message book |
| ＜書＞ | the Book | the Gutenberg handout |
| 構成員・男 / 女 / 若者 | Member (Man) / Member (Woman) / Member (Youth) | speaker labels |
| 片翼の天使 | One-winged Angel | |
| ヒトの管理者 | overseer of Man | Bale's title |
| キシャァ / ギシャァ / キシュルル | KSHAAAAAAA / GSHAAAAAAAA / Kshurururu | Embryon cries |

Corrections: Kilota uses 僕 and is called 坊主 in script 111 — a boy, not a girl (gender list above is wrong on this point).
| ジーナ | Gina | Kutta's "wife" |
| セングラー | Sengler | Pain Ring product from Fly's shop |
| 魔王クッタ / このクッタ様 | Demon King Kutta / the great Kutta | |
| ネキンター・カネル団 | Nekintar Kanel Troupe | circus |
| 大粛正 | the Great Purge | |
| 悪魔討伐隊 | demon-hunting squad | Kreis's unit |
| 機械化僧兵 | mechanized monk soldier | |
| ヒヨコ頭 | chick-head | nickname for Cain's hair |
| 自由行動 | Free Roam | menu label |
| 核神機 | God Core | portrait label "Matia (God Core)"; guess |
| 神の見えざる手 | the Invisible Hand of God | |
| 咎人の証 | the Mark of the Sinner | |
| 適合者 | Compatible One | Pain Ring lore |
| 酒場の女主人 | Tavern Mistress | portrait label |
| パンク兵 | Punk Soldier | Cypherpunk rank-and-file |
| うちの子 | Our Boy | bonus scenario title |
| ファントム・ペイン | Phantom Pain | |
| 白き悪魔 | the White Demon | Cain, to the Church |
| 先祖返り | throwbacks | |
| 天使様 (address) | Lord Angel | |
| 実験施設 | the experimental facility | |
| 補佐官 | aide | |
| 四翼 | four-wing / four-winged | Syria's epithet |
| 翼なき者 | the wingless | |
| シリアお姉ちゃん | Syria-neesan | |
| ボーナスシナリオ titles | `Bonus Scenario NN\nSubtitle` | two lines |

Fly uses 僕 in script 031: gender ambiguous, keep pronoun-free.
