# Fullness-fix brief - Little Master: Nijiiro no Maseki

A blind comparison with another English patch says our lines read compressed: they cut clauses to fit the box,
so they lose fullness and flow. The engine now gives more room (narrower lowercase font, about 12% more per line,
and extra timed pages on demand), so line length is no longer a reason to cut. Rewrite the chapters named in your
dispatch so each line reads like a polished English localization: smooth, complete, natural.

Do all the work yourself; do not dispatch subagents. Do not touch git, tools, or any script file other than through
`lm.py apply`. Other agents may be fixing other chapters of the same block at the same time.

## Read first
1. `docs/style.md` - line rules and the Voices table (voice devices already in a line stay).
2. `glossary.md` - names and terms.
3. Your chapter files `work/qa/story/chapters/<chapter>.txt`: every line in story order, `>> block:id | speaker | JP`
   then `EN`. Read the whole chapter first; flow depends on the lines around.

## What to change
- Lines that cut JP content to fit: a dropped clause, reason, detail, title, softener, or echo of an earlier line.
  Put it all back.
- Lines that are stiff, clipped or telegraphic ("Up early, or we won't make it by noon.") -> full natural sentences.
- Lines that read as a list of facts -> connect them the way the JP does (because, so, but, and then).
- Keep accuracy: nothing the JP lacks (insults, new clauses, names). Keep every voice device and every nuance word
  ("seems", "after all", "try") a previous pass added.
- Leave lines that are already full and natural. Expect to change roughly 1 line in 3.

## Room
- A line is at most 208 px and a page has at most the window's lines (dialog 2, msg 3); `lm.py lint` checks both.
  Re-break pages with `{n}` freely.
- If the full line still doesn't fit its page, add a page: insert `{delay:XX}{clear:00}` at a sentence boundary,
  where XX is the delay the entry's own JP uses before its `{clear:00}` (78 in msg36/msg37; 30 in ev blocks; if the
  JP has no page break, use 78 for msg blocks and 30 for ev blocks), and give the TSV row a third column
  `addpage=N` (N = pages added). Every added `{clear:00}` needs that `{delay:..}` right before it.
- Don't add pages to entries with `{p01:..}`-style cell positioning (narration banners) or to item/menu text.

## How
1. Write `work/tl/full/<your tag>_<block>.tsv`: `id<TAB>full EN line[<TAB>addpage=N]`, with every control code
   exactly as the script stores it. Copy the current EN from `script/<block>.txt` and edit it. Use your file-write
   tool, never a shell heredoc.
2. `python -X utf8 lm.py apply <block> work/tl/full/<your tag>_<block>.tsv`
3. `python -X utf8 lm.py lint` and fix every line of output for your ids. Repeat until none is reported.

## Report (reply with only this)
Lines changed (count), pages added (count), then one line per change: `block:id - what was restored or smoothed`
(short, no full text), then any `UNSURE:` lines.
