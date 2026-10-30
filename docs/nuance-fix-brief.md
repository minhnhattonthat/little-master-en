# Nuance-fix brief - Little Master: Nijiiro no Maseki

A blind comparison against another English patch found our lines often lose small pieces of the Japanese that a
careful reader notices. Voice is already fixed; this pass is accuracy at the word level. You review AND fix the
chapters named in your dispatch. Do all the work yourself; do not dispatch subagents. Do not touch git, tools, or
any script file other than through `lm.py apply`. Another agent may be fixing other chapters of the same block.

## Read first
1. `docs/style.md` - line rules and the Voices table. The voice devices already in a line stay (see below).
2. `glossary.md` - names and terms.
3. Your chapter files `work/qa/story/chapters/<chapter>.txt`: every line in story order, `>> block:id | speaker | JP`
   then `EN`. Read the whole chapter: nuance often depends on the line before.

## What counts (fix these)
What the blind judges kept marking us down for, with the JP that triggered it:
- Hedges and evidentials dropped: みたい / ようだ / らしい ("looks like", "seems"), んじゃないかな / かも ("maybe",
  "I think"), はず ("should").
- Connectives dropped or changed: でも, それよりも, だから, やっぱり ("after all"), それに.
- Aspect and attempt: てみる ("try ...ing"), てしまう ("went and ..."), ことにした ("decided to"), tense errors.
- Small content words dropped: しっかり ("closely"), すこし ("a little"), 例の ("that ... we talked about"),
  ずっと ("for ages"), titles (教授 "Professor"), "this village", "the ruins", plural vs singular (あれが = one).
- Register: polite ください / おつかえします / なさる lines must not read casual; a rude line must not read polite.
- Misreadings: おっと is "Hold it / Whoa", not "Oh no"; さきの is "recent / the earlier", not "just now";
  こっちのセリフ is "that's my line"; check every line where the EN could mean something the JP doesn't.
- Additions: words, names, insults or clauses the JP lacks. Remove them unless they are a voice device for the
  speaker's row in style.md.

## What not to do
- Don't rewrite a line that is already accurate. Most lines are fine; expect to change roughly 1 line in 6.
- Keep every voice device that is there ("ain't", "I wonder", "meow", "my boy", stretched vowels). If the fix
  needs room, shorten elsewhere in the line, not the device.
- Don't make English stiff to be literal. The target is what a fluent translator would write with every nuance
  of the JP in it.
- Keep every control code where it is (`{delay}`, `{scroll}`, `{clear}`, `{p..}`, `{color}`), the speaker label
  line, and names exactly as in `glossary.md`.

## How
1. Write `work/tl/nuance/<your tag>.tsv` (tag from your dispatch): `block:id<TAB>full EN line`, with every
   control code exactly as the script stores it. Copy the current EN from `script/<block>.txt` and edit it.
   Use your file-write tool, never a shell heredoc.
2. For each block in your TSV, write its rows (`id<TAB>EN`, id without the block) to
   `work/tl/nuance/<your tag>_<block>.tsv` and run `python -X utf8 lm.py apply <block> work/tl/nuance/<your tag>_<block>.tsv`.
3. `python -X utf8 lm.py lint` and fix every line of output for your ids. Lines are at most 208 px; a page never
   has more lines than the JP page allows. Repeat until none of your ids is reported.
4. If a line can't fit with the nuance, keep the best version that fits and report `LONG: block:id - what was lost`.

## Report (reply with only this)
Lines changed (count), then one line per change: `block:id - JP nuance - before -> after` (short), then any
`LONG:` and `UNSURE:` lines.
