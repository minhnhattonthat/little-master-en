# Decisions

The user's rulings on scope, style and trade-offs, newest last. Read before asking the user anything; if a later
decision replaces one, mark the old one "replaced by D<n>" instead of deleting it. Binding term spellings live in
`glossary.md`; this file holds the why.

Rows D1-D6 were collected from earlier notes (CLAUDE.md, glossary.md, docs/style.md) when the repo moved to the
template; the options offered then were not recorded.

| # | Date | Question | Options offered | Decision and reason |
|---|---|---|---|---|
| D1 | 2026-10-05 | Honorifics and name order | keep (-san), drop; JP or Western order | Honorifics dropped (プーちゃん -> Poo); Western order (Reem Likeburn). |
| D2 | 2026-10-05 | Style | faithful, localised | Faithful, natural English; Japanese names romanized, items/monsters get English equivalents (design spec). |
| D3 | 2026-10-07 | Army and place names | - | 勇者軍 "the Heroes", 魔物軍 "the Monsters", カラード "Calard" (not "Colored"). ジャスバン "Jasvan"; the map art's JUSVAN is left as drawn. |
| D4 | - | Abbreviations | engine work first (default), abbreviate | Full names, no abbreviations; prefer engine work (VWF, wider box, relocation) to cutting meaning. |
| D5 | - | Credits | stay Japanese, translate | Not recorded: ask the user before touching the staff roll. |
| D6 | 2026-10-24 | Repo layout | as is, fan-translation-template | Template docs/config; `lm.py`, `lmtools/` and `tests/` stay; Lua scripts -> `tools/lua/`, savestates -> `work/states/` (as black-matrix-00 did). |
