# Voice-fix brief - Little Master: Nijiiro no Maseki

You fix the English story lines of ONE script block that story reviewers flagged. Work only on the block named in your
dispatch; another agent may be fixing a different block at the same time. Do all the work yourself; do not dispatch
subagents. Do not touch git, tools, or any other script file.

## Read first
1. `docs/style.md` - the Voices table (JP markers -> EN devices per character) and the line rules. Match it.
2. `docs/synopsis.md` - who is who, reveals; don't tip a reveal early.
3. The review reports named in your dispatch (`work/qa/story/reports/<block>_NN.md`): Critical and Important findings
   with suggested EN. Suggestions are a starting point, not final: they ignore width.

## What to change
- Every Critical and Important finding for your block. Minors only if the line is already being rewritten.
- Also any other line in your block where the JP has a marker from the Voices table and the EN has no device for it.
  Find them with: `python -X utf8 lm.py show <block> 0 9999` and the JP.
- Change wording only. Keep every control code where it is (`{delay}`, `{scroll}`, `{clear}`, `{p..}`, `{color}`),
  the speaker label line, names exactly as in `glossary.md`, and the meaning. One device per line is enough.
- Never add content the JP lacks (insults, requests, new clauses): a device colours a line, it does not change what
  is said. Bad: よろしくね -> "Be nice to me, will you?!"; 人質がいるのよ -> "...hostage, dummy!". Don't tack the same
  tic ("my boy", "eh?") on every line of a speaker; vary it and skip it where it reads oddly.

## How
1. Write `work/tl/voice/<block>.tsv`: `id<TAB>full EN line` (with every control code, exactly as the script stores
   it; copy the current EN from `script/<block>.txt` and edit it). Use your file-write tool, never a shell heredoc.
2. `python -X utf8 lm.py apply <block> work/tl/voice/<block>.tsv`
3. `python -X utf8 lm.py lint` and fix every line of output that starts with your block name. Lines are at most
   208 px; a page never has more lines than the JP page. Repeat 1-3 until no line of your block is reported.
4. If a line cannot fit without losing the voice or meaning, keep the best version that fits and report it as
   `LONG: id - what was given up`. The controller can add a page through engine work.

## Report (reply with only this)
Lines changed (count), then one line per change: `id - before -> after` (short), then any `LONG:` and `UNSURE:` lines.
