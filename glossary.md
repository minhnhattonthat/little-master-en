# Glossary

The single source of truth for names and terms. `python lm.py lint` checks that every EN line whose JP contains a
term (first column) uses the EN form (second column). Keep terms distinctive: a short JP term that also appears
inside unrelated words would cause false lint hits. Columns: JP | EN | max | notes.

**Name conventions**
- **Spaces in names:** names that the game copies into messages (unit names, monster names) stop at the first
  space or `00`. A multi-word copied name is written with `_` (e.g. `Skull_Pirate`). The game draws `_` as a space.
- **Byte limits:** unit names 8 bytes; weapon, armor and accessory names 10; monster names 11.
- **Existing English:** the game's own English graphics already say "Little Master", "Jewels of Rainbow",
  "Scenario", "Turn", "Medal", "Phase", "Report", "Information", "Caution", "Message", "Item List",
  "Unit Information" and "Personal Information". The translation uses the same words.

## Characters

| JP | EN | max | notes |
|---|---|---|---|
| リイム・ライクバーン | Reem Likeburn | | hero, "Knight of Lightning". Alternatives: Rime / Liim, Raikburn |
| リイム | Reem | 8 | |
| モーモー | Moomoo | 8 | minotaur, full name モーモー・ダイナマイツ Moomoo Dynamo (unit list fits 13 cells) |
| タムタム | Tamtam | 8 | priest, full name タムタム・タンバリン Tamtam Tabor (a small drum; 13-cell unit list) |
| シャルル | Charles | 8 | full name シャルル・ブレッド Charles Bread |
| リルル | Lilulu | 8 | |
| ヴァイス | Weiss | 8 | leader of the Skull Bombers. Alternative: Vice. Surname キャンベル Campel (13-cell unit list) |
| ヤゴ | Yago | 8 | |
| 蒼月 | Sougetsu | 8 | also written ソウゲツ in the unit table |
| トランプ | Trump | 8 | Bombers member ("trump card"). Alternative: Joker |
| ラドック教授 | Professor Radock | | |
| ピーコック | Peacock | | Radock's assistant |
| ハウサー | Hauser | | 教王 = Pontiff: "Pontiff Hauser" |
| リチャード | Richard | | |
| ミーシャ | Misha | | |
| ボルシチ | Borscht | | villager |
| ラドック | Radock | | speaker label of Professor Radock |
| ライム | Lime | | Princess of Rainark |
| 司会者 | Host | | quiz show host |
| ポトフ | Potofu | | |
| タップン | Tappun | | |
| ミーシャの母 | Misha's mom | | speaker label |
| ハムス | Hamus | | the twins' pet hamster |
| プーちゃん | Poo | | Misha's plush toy |
| ゲザガイン | Gezagain | | black demon dragon of the first game |

## Places

| JP | EN | max | notes |
|---|---|---|---|
| ジャスバン | Jasvan | | ruins (scenario 1) |
| ライナーク | Rainark | | ライナーク城 Castle Rainark |
| マテドラル | Matedral | | theocracy (宗教国家) |
| パズタ | Pazuta | | パズタ村 Pazuta Village; なげきのパズタ村 Pazuta, Village of Sorrow |
| クルクルの森 | Kurukuru Forest | | |
| ジリジリ砂漠 | Jirijiri Desert | | |
| ハイエスト山脈 | Highest Mountains | | |
| オーサム | Ausam | | snowy town |
| ライモス | Laimos | | ライモス神殿 Laimos Temple |
| ソロモンの塔 | Tower of Solomon | | |
| ガウディ | Gaudi | | 聖ガウディ教会 St. Gaudi Church |
| ロイホー | Roiho | | ロイホー地方 the Roiho region |
| レインボーロード | Rainbow Road | | |

## Factions and key terms

| JP | EN | max | notes |
|---|---|---|---|
| 勇者軍 | Heroes | | the player's side ("the Heroes"). Short form chosen because status layouts give it ~6 cells. Alternative: Hero Army |
| 魔物軍 | Monsters | | the enemy side ("the Monsters"). Alternative: Monster Army |
| 魔獣盗賊団 | Beast Bandits | | |
| スカル・ボンバーズ | Skull Bombers | | also スカルボンバーズ |
| 虹色の魔石 | Rainbow Jewel | | the title is "Jewels of Rainbow" in the game's own credits |
| 魔石 | Jewel | | アカイロの魔石 Red Jewel, オレンジの魔石 Orange Jewel… |
| 雷光の騎士 | Knight of Lightning | | |
| コハク | amber | | コハクつかい amber mage |
| 魔方陣 | magic circle | | |
| 地形効果 | terrain bonus | | |
| ストーリーアイテム | story item | | |
| ポイズン | Poison | | ailments: パラライズ Paralyze, トランス Trance, スロウ Slow, ウイーク Weak, カース Curse, 病気 Sick |
