# Story style guide

Applies to the story script (`msg36`, `msg37`, `ev03`, `ev0A`, `ev22`) and to any prose added later. Names and terms
come from `glossary.md`; this file covers how lines are written. `python lm.py lint` checks widths, lines per page,
control codes, glossary terms and speaker labels.

## Lines and layout

| Rule | JP | EN |
|---|---|---|
| Speaker label on its own line, exactly the glossary name | `リイム{n}「はい」` | `Reem{n}"Yes."` |
| 「…」 becomes "…" | `「やったぞ!」` | `"We did it!"` |
| Continuation lines in a quote keep the leading space | `「ジャスバンで拾ったんだよ。{n} じいさん…」` | `"Found it in Jasvan.{n} Here, old man..."` |
| ‥‥ / ・・・ become "..." | `「ちくしょう‥‥」` | `"Dammit..."` |
| ♪ ♡ ～ ‼ stay as glyphs | `「いっくぞ～♪」` | `"Here I go～♪"` |
| Narration (no speaker) stays unquoted | `ヌイグルミを とりもどした勇者軍は、…` | `With the plush toy back, the Heroes...` |

- Keep every `{delay:..}`, `{clear:..}`, `{scroll:..}` and every non-layout code where JP has it. A JP page (text
  between `{clear}`s) may be re-broken with `{n}`, but never gets more lines than JP shows.
- A VWF line is at most 208 px (lint): at 213+ px the cursor reaches the window edge, the game auto-wraps, and the
  following `{n}` adds a blank line (M4 Task 3 test).
- `、` → comma, `。` → period, `・` between names → space. `!?` and `‼` stay.

## Generic speaker labels (not glossary rows)

| JP | EN |
|---|---|
| 兵士 | Soldier |
| 一同 | All |
| ???? / ?? | unchanged |

## Voices

Each row names the JP markers and the English devices that carry them. A line any character could have said is a
mistake: when the JP has the marker, the EN has the device (one per line is enough; don't stack them).

| Character | Voice | JP markers → EN devices |
|---|---|---|
| Reem | earnest boy hero, polite to elders | ボク, ～だよ/～さ → plain, warm, contractions; "sir" to elders. No slang. |
| Moomoo | rough, hungry, blunt minotaur | オレさま, うめえ/喰いてえ/ねえ/だぜ → "ain't", "gonna", "ya", "grub", "old man"; clipped grammar ("Dunno."); a line-final モー → "Moo." |
| Tamtam | gentle girl with a temper | あたし, ～のよ/～わよ/かしら → "you know", "I wonder...", softeners ("Oh, really..."); when angry, short and sharp |
| Charles | feisty, childish, spoiled | あたし, ～わよ/～のよ, ～モン♡ → pouty "Hmph!", "they're all mine♡", "will you?!"; ♡ kept |
| Lilulu | Charles's shy second self, dreamy, polite | ～です, drawn-out ですぅ/～ぉ, 勇者様 → "Um...", stretched words ("sooo", "pleeease"), "never, ever", "Hero" |
| Professor Radock | rambling old mouse scholar | ワシ, ～じゃ/～ぞい/～のお, くどくど → "eh?", "my boy", "you see", "ho ho", "blah blah"; long-winded |
| Weiss | rough, cocky idealist | 俺, ぜ/ねえ/～さ (べらんめえ) → "ya", "ain't", "Good to have ya", streetwise swagger; curt when serious |
| Lime | shy princess | ‥ pauses, polite → "Um...", trailing "...", soft and formal |
| Dr. Skull | pompous gadgeteer | 我輩, ヒャハ♡ → "I, the great Dr. Skull", grandiose, "Hyaha♡" |
| Sougetsu | polite, menacing | ～ですよ/～ましょう, フフフ → smooth formal English, "do try", "merely", "Heh heh"; never rough |
| Yago | cat, childish tyrant | ボク, ～ニャ/～ニャン/～ニャい → "meow" at the end, "nya" inside words for ～ニャい ("I won't forgi-nyah"); bratty |
| Trump | blustering thug boss | 俺様, てめえら, じゃねえ, ヒャッハッハ → "you punks", "ain't", "Hya ha ha!", threats with swagger ("knock you flat") |
| Peacock | timid lackey | おいら/あっし, ～っス/～んスよ, くだせ～ → "Boss", deference ("Mister Reem"), "y'see", whiny "～" |
| Hauser | courteous pontiff | 余, ～ですな/くだされ → formal and gracious: "I pray", "pray pay it no mind"; no contractions |
| King Richard | royal, kindly | よかろう/～なさい → regal: "It is best that...", "Take them, and go." |
| Borscht, villagers | rural, plain | じさま, ～ねえ/～だな → "granddad", "can't be helped", relaxed contractions |
| Old men (NPCs) | folksy | わし, ～じゃ/～ぞい/～のう → "eh?", "back in my day", "sonny" |
| Women (NPCs) | soft | ～わ/～のよ/かしら → "dear", "I wonder", "oh my" |
| Monsters / grunts | short and comic | ギギ, ～だぜ, katakana speech → keep the noises ("Ghee-ghee!"), robot katakana in CAPS |

## Terms

- シナリオ is "Stage" in tight UI (file select, briefing headers) and "scenario" in prose.
- 勇者軍 "the Heroes", 魔物軍 "the Monsters", 魔石 "Jewel" (capitalized), コハク "amber" (lowercase).
