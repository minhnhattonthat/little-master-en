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

| Character | Voice |
|---|---|
| Reem | earnest, polite to elders |
| Moomoo | rough and casual ("ya", "gonna", "old man") |
| Tamtam | polite, gentle |
| Charles | feisty, quick |
| Lilulu | gentle, a little dreamy |
| Professor Radock | old man ("ho ho", "my boy") |
| Weiss | gruff, curt |
| Sougetsu | formal, measured |
| Yago | grandiose |
| Trump | blustering |
| Monsters / grunts | short and comic |

## Terms

- シナリオ is "Stage" in tight UI (file select, briefing headers) and "scenario" in prose.
- 勇者軍 "the Heroes", 魔物軍 "the Monsters", 魔石 "Jewel" (capitalized), コハク "amber" (lowercase).
