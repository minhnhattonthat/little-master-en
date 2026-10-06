# M4 Story Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Translate the whole story script (msg36, msg37, ev03, ev0A, ev22: ~1,540 entries, ~46k JP characters) into faithful, natural English that is lint- and overflow-clean and renders correctly in game.

**Architecture:** No new engine work is planned. The VWF, relocation and inline stubs from M2/M3 carry the text. M4 adds:
- a story glossary and style guide;
- two lint rules (speaker labels, missing translations) and `lm.py show` / `lm.py apply` for the chunked translation loop;
- one runtime guard for full-width dialogue lines.

Then the script is translated block by block, in id order (≈ game order), one chunk per task.

**Tech Stack:** Python 3.12 (`lmtools/`, `lm.py`, pytest), asar 1.91, Mesen2 2.1.1 headless test runner (`tools/mesen2`), save states in `test/states/`.

**Spec:** `docs/superpowers/specs/2026-10-05-little-master-translation-design.md` (milestone M4: "full story script translated, lint and overflow clean").

## Global Constraints

- The base ROM is never modified. Output goes to `build/lm_en.sfc` + `build/lm_en.bps`.
- No Beta2 code, assets or text are copied. Beta2 is a reference map only.
- `glossary.md` is the single source of truth for names and terms. `python lm.py lint` must stay clean after every task.
- Translation style:
  - faithful and natural English;
  - JP 「…」 becomes "…";
  - the speaker label is a line of its own, exactly the glossary name;
  - continuation lines inside a quote keep the JP leading space;
  - ‥‥ / ・・・ become "...";
  - ♪ ♡ ～ ‼ stay as glyphs;
  - `{delay:..}`, `{clear:..}`, `{scroll:..}` and every non-layout code stay where JP has them (lint parity).
- An EN page never has more lines than its JP page shows, and every VWF line is ≤ 216 px.
- Commits are authored by the repo-local identity and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Work happens on branch `m4-work`. Merge to `main` and tag `m4` only after user approval.

## Review Focus

1. **A dialogue line at the full 216 px followed by `{n}`.** The next line must follow directly: no blank line, no extra scroll. The game auto-wraps when the cursor passes the window edge; the M3 briefing showed a full-width line plus `{n}` gives a blank line. Test: Task 3.
2. **A story entry left untranslated.** `python lm.py lint --missing` must list it with block and #id, and M4 acceptance requires the list to be empty for the five story blocks. Test: Task 2.
3. **A speaker label spelled differently from the glossary** ("Reem:", "Moo-moo") → lint error with block and #id. Test: Task 2.
4. **Inline event text (ev03/ev0A/ev22) longer than its slot.** It is relocated through a stub and the event continues. Covered by the existing `test_overlong_inline_text_renders_and_event_continues`; Task 11 re-runs it on the final script.
5. **♪ (and ♡ ～ ‼) inside a VWF line.** It encodes, and is drawn in its own fixed cell without clobbering neighbours. Test: Task 1 (encoding). The existing `test_fixed_char_between_vwf_glyphs_keeps_its_cell` covers drawing.

---

## File Structure

```
glossary.md                     + story names/terms (Task 1)
docs/style.md                   new: story style guide (Task 1)
lmtools/mk_en_tbl.py, tbl/en.tbl  + ♪ = FE (Task 1)
lmtools/lint.py                 + speaker rule, missing() (Task 2)
lmtools/script.py               + apply_tsv(), show() (Task 2)
lm.py                           + show, apply, lint --missing (Task 2)
tests/test_en_tbl.py, test_lint.py, test_script.py, test_vwf_runtime.py
script/msg36.txt msg37.txt ev03.txt ev0A.txt ev22.txt   EN lines (Tasks 4-10)
```

### Task 1: Story glossary, style guide, ♪

**Files:**
- Modify: `glossary.md`, `lmtools/mk_en_tbl.py`, `tbl/en.tbl` (regenerated)
- Create: `docs/style.md`
- Test: `tests/test_en_tbl.py`

**Interfaces:**
- Produces: glossary rows that later tasks and the Task 2 speaker rule rely on (JP name → EN name), and `♪` encodable as byte `FE`.

- [ ] **Step 1: Failing test**

```python
def test_music_note_encodes_like_the_game():
    assert EN.encode("♪") == bytes.fromhex("FE")
```

- [ ] **Step 2:** `python -m pytest tests/test_en_tbl.py -q -k music`. Expected: FAIL, unencodable '♪'.
- [ ] **Step 3:** In `lmtools/mk_en_tbl.py`, append `"FE=♪"` to the list of game symbols added after ASCII, next to `09=▲`. Then run `python -m lmtools.mk_en_tbl`.
- [ ] **Step 4:** Re-run. Expected: PASS.
- [ ] **Step 5: Glossary rows.** Add these to `glossary.md`. Speakers, under Characters:

  | JP | EN | notes |
  |---|---|---|
  | ライム | Lime | Princess of Rainark |
  | 司会者 | Host | quiz show host |
  | ポトフ | Potofu | |
  | タップン | Tappun | |
  | ミーシャの母 | Misha's mom | speaker label only |
  | ハムス | Hamus | the twins' pet hamster |
  | プーちゃん | Poo | Misha's plush toy |
  | ゲザガイン | Gezagain | black demon dragon of the first game |

  Generic labels are **not** glossary rows (they would cause false hits):
  - 兵士 → Soldier
  - 一同 → All
  - ???? and ?? stay as they are

  Write these generic labels into `docs/style.md` instead.
- [ ] **Step 6:** Write `docs/style.md`. It contains:
  - the style rules from Global Constraints, with a JP→EN example for each;
  - the generic speaker labels;
  - character voice notes:
    - Reem: earnest;
    - Moomoo: rough and casual ("ya", "gonna");
    - Tamtam: polite;
    - Charles: feisty;
    - Lilulu: gentle;
    - Radock: old man ("ho ho");
    - Weiss: gruff;
    - Sougetsu: formal;
    - Yago: grandiose;
    - Trump: blustering;
  - this note: シナリオ is "Stage" in tight UI, "scenario" in prose.
- [ ] **Step 7:** `python -m pytest -q` (all pass), `python lm.py lint` (clean). Commit: `M4: story glossary, style guide, ♪ in en.tbl`.

### Task 2: Tooling for the translation loop

**Files:**
- Modify: `lmtools/lint.py`, `lmtools/script.py`, `lm.py`
- Test: `tests/test_lint.py`, `tests/test_script.py`

**Interfaces:**
- Produces:
  - `script.apply_tsv(path: Path, tsv: str) -> tuple[int, list[int]]`: sets EN for each `id<TAB>EN` line. Returns (number applied, ids not found). Writes LF.
  - `script.show(entries, lo: int, hi: int) -> str`: one line per entry, `id<TAB>meta<TAB>JP`.
  - `lint.missing(root=".", blocks=None) -> list[str]`: `"<block> #<id>"` for every entry with JP text (kana or kanji outside `{}`) and empty EN.
  - CLI:
    - `python lm.py show <block> <lo> <hi>`;
    - `python lm.py apply <block> <tsv-file>`;
    - `python lm.py lint --missing [block...]`.
- Speaker rule in `lint_entry`. For each page (split on `{clear:..}`), if the JP page's first line, with any `{p7F:..}` header removed, exactly equals a glossary JP key and the next JP line starts with 「, then the EN page's first line, with its header removed, must equal that key's EN. Error text: `#<id>: speaker '<JP>' should be '<EN>'`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_lint.py
def test_speaker_label_must_match_glossary():
    g = {"リイム": "Reem"}
    e = Entry(30, 0, {}, "リイム{n}「はい」{end}", "Reem:{n}\"Yes.\"{end}")
    assert lint_entry(e, "wide", WID, W, g) == ["#30: speaker 'リイム' should be 'Reem'"]
    e.en = "Reem{n}\"Yes.\"{end}"
    assert lint_entry(e, "wide", WID, W, g) == []


def test_speaker_rule_checks_every_page():
    g = {"リイム": "Reem"}
    e = Entry(31, 0, {}, "「あ」{clear:00}リイム{n}「い」{end}", "\"A\"{clear:00}Rem{n}\"I\"{end}")
    assert lint_entry(e, "wide", WID, W, g) == ["#31: speaker 'リイム' should be 'Reem'"]


def test_missing_lists_untranslated_text_entries(tmp_path):
    from lmtools.script import save
    (tmp_path / "script").mkdir()
    save(tmp_path / "script" / "b.txt", [Entry(0, 1, {}, "あ{end}", ""), Entry(1, 2, {}, "{end}", ""),
                                         Entry(2, 3, {}, "い{end}", "I{end}")])
    assert lint.missing(tmp_path, ["b"]) == ["b #0"]
```

```python
# tests/test_script.py
def test_apply_tsv_sets_en_and_reports_unknown_ids(tmp_path):
    from lmtools.script import apply_tsv
    p = tmp_path / "s.txt"
    save(p, [Entry(0, 0x10, {}, "あ{end}", ""), Entry(1, 0x20, {}, "い{end}", "")])
    assert apply_tsv(p, "1\tI{end}\n7\tX{end}\n") == (1, [7])
    assert parse(p.read_text(encoding="utf-8"))[1].en == "I{end}"
    assert b"\r\n" not in p.read_bytes()
```

- [ ] **Step 2:** `python -m pytest tests/test_lint.py tests/test_script.py -q`. Expected: the 4 new tests FAIL (missing names / speaker rule absent).
- [ ] **Step 3: Implement.**

In `lmtools/script.py`:

```python
def apply_tsv(path, tsv):
    path = Path(path)
    es = parse(path.read_text(encoding="utf-8"))
    tr = {}
    for line in tsv.splitlines():
        if line.strip() and not line.startswith("#"):
            i, en = line.split("\t", 1)
            tr[int(i)] = en
    applied = 0
    for e in es:
        if e.id in tr:
            e.en = tr.pop(e.id)
            applied += 1
    save(path, es, force=True)
    return applied, sorted(tr)
```

Also add `show()`:

```python
def show(entries, lo, hi):
    return "\n".join(f"{e.id}\t{' '.join(f'{k}={v}' for k, v in e.meta.items() if k in ('cont', 'win', 'slack'))}\t{e.jp}"
                     for e in entries if lo <= e.id <= hi)
```

In `lmtools/lint.py`:
- `HEADER` already strips `{p7F:xx}`.
- Add the speaker check after the glossary loop. It needs the raw glossary map, which `lint_entry` already receives.

```python
    for jp_page, en_page in zip(_pages(e.jp), _pages(e.en)):
        first, nxt = HEADER.sub("", jp_page[0]), (jp_page[1] if len(jp_page) > 1 else "")
        if first in glossary and nxt.startswith("「") and HEADER.sub("", en_page[0]) != glossary[first]:
            out.append(f"#{e.id}: speaker '{first}' should be '{glossary[first]}'")
```

```python
def missing(root=".", blocks=None):
    root = Path(root)
    names = blocks or [b.name for b in load_blocks(root / "data/blocks.json")]
    out = []
    for name in names:
        for e in parse((root / f"script/{name}.txt").read_text(encoding="utf-8")):
            if not e.en and re.search(r"[ぁ-んァ-ヶ一-龯]", re.sub(r"\{[^}]*\}", "", e.jp)):
                out.append(f"{name} #{e.id}")
    return out
```

In `lm.py`, add the subcommands `show` and `apply`, and `--missing` (with optional block names) on `lint`. They print the result. `lint --missing` exits 1 if the list is non-empty.
- [ ] **Step 4:** Run the tests. Expected: PASS. Then `python lm.py lint` → clean. If the speaker rule flags existing entries (msg36/ev0A test lines), fix those EN lines.
- [ ] **Step 5:** `python -m pytest -q`. Commit: `M4: lint speaker labels and missing EN; lm.py show/apply`.

### Task 3: Guard: full-width dialogue line + `{n}`

**Files:**
- Test: `tests/test_vwf_runtime.py`
- Modify (only if RED): `data/windows.json` (dialog/msg `px`) or `src/asm/vwf.asm`

- [ ] **Step 1: Failing-or-passing test.**

```python
def test_full_width_line_then_newline_has_no_blank_line(tmp_path, monkeypatch):
    from lmtools.font import parse_font
    w = {c: x for c, (x, _) in parse_font(Path("src/font/vwf.txt").read_text(encoding="utf-8")).items()}
    line = ""
    while sum(w[c] for c in line) + w["n"] <= 216:
        line += "n"
    line += "i" * ((216 - sum(w[c] for c in line)) // w["i"])          # pad to exactly 216 px if 'i' divides the rest
    real = build.parse

    def inject(text):
        es = real(text)
        for e in es:
            if "Peacock, run home!" in e.en:
                e.en = e.en.replace("Peacock, run home!", line + "{n}B")
        return es

    monkeypatch.setattr(build, "parse", inject)
    sfc = build.build(tmp_path / "b", "en")
    res = run(sfc, "ordinary_field_message", '''
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 300 then
    local rows = {}
    for r = 0, 31 do
      for c = 0, 31 do
        if (emu.read16(0x9000 + r * 64 + c * 2, emu.memType.snesWorkRam) & 0x3FF) >= 0x180 then rows[#rows+1] = r break end
      end
    end
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(table.concat(rows, " ")); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''', tmp_path / "o")
    rows = sorted({int(r) for r in res.split()} - set())
    assert sum(w[c] for c in line) == 216
    tops = [r for r in rows if r - 1 not in rows]                 # first tile row of each text line
    assert len(tops) >= 2 and tops[1] - tops[0] == 2, rows        # 'B' on the very next text line
```
- [ ] **Step 2:** Run it.
  - If PASS: the engine already handles it. Commit the test as a guard.
  - If FAIL: lower `px` for `dialog` and `msg` in `data/windows.json` to the largest width that passes (try 208), re-run lint, and fix any lines it flags.
- [ ] **Step 3:** `python -m pytest -q`. Commit: `M4: guard full-width dialogue lines`.

### Tasks 4-10: Translation chunks

Every chunk follows the same loop. Each task's deliverable is its id range translated, lint-clean and committed.

1. `python lm.py show <block> <lo> <hi>` and read the range, plus 5 entries before it for context (who is speaking, the scene).
2. Write `id<TAB>EN` lines into a TSV in the scratchpad. Use the Write tool, not a shell heredoc: apostrophes and `\n` break heredocs. Follow `docs/style.md`. Copy every control code from JP in order, except layout codes. Leave graphics-only entries and the ASCII credits (ev22 #0-6) as they are.
3. `python lm.py apply <block> <tsv>`, then `python lm.py lint`. Fix every report: width, lines per page, parity, glossary, speaker.
4. `python lm.py lint --missing <block>` must not list ids inside the chunk.
5. `python lm.py build` succeeds.
6. Commit: `M4: translate <block> <lo>-<hi>`.

| Task | Block | Ids | Size (JP chars) | Notes |
|---|---|---|---|---|
| 4 | msg36 | 0-226 | ~4.6k | 0-129 are unit battle cries (keep them short and onomatopoeic; `{p7F:02}` dialog window); story from 130 |
| 5 | msg36 | 227-399 | ~4.6k | |
| 6 | msg36 | 400-637 | ~9k | Misha / Quiz Village arc (≈600) |
| 7 | msg37 | 0-198 | ~6.3k | cutscenes with speaker labels |
| 8 | msg37 | 199-487 | ~6.3k | |
| 9 | ev03 + ev22 | all | ~6.7k | ev22 #0-6 credits stay ASCII; positioned entries keep their budgets |
| 10 | ev0A | 0-418 | ~8.8k | field events; 29 positioned entries (fixed font, caps) |

### Task 11: Screen sweep

- [ ] **Step 1:** Run every save state with A pressed every 90 frames for 900 frames. Screenshot every 90 frames and build a grid per state (the M3 sweep script pattern). Look at every EN text box for:
  - overflow or garbled cells;
  - stray JP;
  - black boxes;
  - blank lines;
  - text cut by labels.
- [ ] **Step 2:** For each defect, write a failing runtime test that reproduces it (the M3 runtime-test pattern in `tests/test_vwf_runtime.py`), fix it, watch it pass. Re-check the three M3 deferred minors here, since story scenes are where they would surface:
  - (a) the `$57=$FE` upload lost while `$10 ≥ 2`;
  - (b) `!partial` surviving the D0 glyph path;
  - (c) a new slot per message start when two messages share a line.
  Fix one only if the sweep shows it.
- [ ] **Step 3:** `python -m pytest -q`, lint, build. Commit: `M4: screen sweep fixes`.

### Task 12: Acceptance

- [ ] **Step 1:** Pass all of these:
  - `python -m pytest -q`;
  - `python lm.py lint`;
  - `python lm.py lint --missing msg36 msg37 ev03 ev0A ev22` prints nothing;
  - `python lm.py build`;
  - `python lm.py boot build/lm_en.sfc`.
- [ ] **Step 2:** Give the user 25 random story lines (JP | EN, controls stripped) across the five blocks, plus sweep screenshots. Apply their tone fixes across the script.
- [ ] **Step 3:** Cross-check `build/lm_en.bps` with `python-bps-continued` (identical output).
- [ ] **Step 4:** Final whole-branch review, fix pass, then finish the branch. Tag `m4` on `main` after the user chooses merge.

---

## Self-review notes

- **Spec coverage.** M4 "full story script translated, lint and overflow clean" maps to Tasks 4-10 + 12. The spec's lint list says lint flags missing `EN:` lines; that is Task 2. Its in-emulator check for ambiguous lines is Task 11.
- **Out of scope:** graphics and the title (M5), the release readme (M6), and the debug screens in msg02.
