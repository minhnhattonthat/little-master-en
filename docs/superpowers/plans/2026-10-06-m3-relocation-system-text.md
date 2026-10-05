# M3: Relocation, Lint, Glossary, System Text — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:**
- English text can be longer than the Japanese it replaces.
- A lint catches overflow and inconsistency.
- The VWF leftovers from M2 are fixed.
- All system text is translated, fits, and builds cleanly: system and battle messages, scenario summaries, unit/terrain/item descriptions, and unit, item and monster names.

**Architecture:**
- **Relocation**, in `lmtools/relocate.py`, used by `build`:
  - *Message tables:* each message table that appears in the table list at PC `010000` moves, together with the strings it can reach, into the expanded ROM (`$C1:8000+`), and its list entry is patched. Tables that share strings move as one group within one 32 KB bank. Tables not in the list (`112011`) stay in place.
  - *Inline event text that grows:* the old slot keeps its speaker header and gets `{goto:new}`. The relocated copy ends with `{goto:<old terminator>}`, so the event interpreter's resume pointer is unchanged.
- **Lint** (`lmtools/lint.py`, `lm.py lint`): per-line pixel width against the window, line count, control-code parity, glossary consistency, and name byte limits.
- **Translation:** EN lines in `script/*.txt`, with terms fixed in `glossary.md`.

**Tech Stack:** Python 3.12, pytest, Pillow, asar, Mesen2 Lua.

**Spec:** `docs/superpowers/specs/2026-10-05-little-master-translation-design.md`. Facts: `docs/re/*.md`, especially `text-engine.md` → "Dynamic tiles and VWF hooks".

## Global Constraints

- **Base ROM** read-only. Build output goes to `build/`.
- **No Beta2 content.** Translation is original work, faithful and in natural English (spec).
- **`en.tbl`:** codes `2A 3B 3C 3E 40` mean `× ∶ ◀ ▶ ©`. `[ ] { }` can't be typed. An empty EN line means "use JP".
- **Commits** end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Run all commands from the repo root.

## Facts this plan relies on (checked 2026-10-06)

- **Message by ID:** `$01:EE4A` reads a 24-bit table address from the list at PC `010000` (entry = 3 bytes + 1 pad, 20 entries). It reads a 16-bit pointer with `LDA [$14],y`, so the strings must be in the table's bank. If the string starts with `FF 7F xx`, it skips 3 bytes (speaker header via `$EC12`). Then `JSL $00:B67C`.
- **Event opcodes:** `$01:FA42` = show message by ID (2-byte arg). `$01:FA4E` = inline text: `$14/$16 = event ptr ($85/$87)`, `JSR $EE6D`, then `STA $85`. **The event resumes at the 16-bit pointer the text engine returns**, in the event's own bank.
- **`{goto:AAAAAA}` (`FF C0`):** always jumps. Its 24-bit target is any SNES address.
- **List entries:**
  - Tables 3/16 and 4/17 are the same tables listed twice. Patch both entries.
  - `112011` (7 ailment messages) is not in the list and nothing references it statically, so it stays in place.
- **Free space:** PC `200000-2009FF` holds the VWF code and data. Text starts at PC `208000` (`$C1:8000`).

## Review Focus

1. **A relocated group larger than 32 KB** → the build fails, naming the group's tables and size. It never splits a 16-bit-pointer group across banks. (Task 2 test.)
2. **Inline EN that is longer, in a slot too small for the 3-byte header + 5-byte goto + `00`** → error naming block and #id. (Task 3 test.)
3. **A jump inside relocated text whose target is outside its group** → error, not a stale address. (Task 2 test.)
4. **Lint on a hand-written line with a `{n}` inside a word, or trailing spaces** → widths are measured per visual line and trailing spaces count. (Task 4 test.)
5. **Glossary term present in JP but EN uses a different spelling** → lint flags it with block and #id. (Task 4 test.)

---

## File Structure

```
lmtools/relocate.py     table groups, allocator, pool relocation, inline stub relocation
lmtools/lint.py         line widths, line counts, control parity, glossary, name limits
lmtools/blocks.py       (modify) inline insert -> relocation hook; error messages
lmtools/build.py        (modify) relocation + lint gate; clean stale outputs
src/asm/vwf.asm         (modify) dirty-flag upload, lazy slot advance, edge clamps
src/font/fixed.txt      (modify) bold a-z
glossary.md             term table (JP | EN | max bytes | notes)
data/windows.json       window widths/lines per box type
tests/test_relocate.py, tests/test_lint.py
```

---

### Task 1: RE spike — remaining reference types (gate for Task 2)

Answers go into `docs/re/pointers.md` → "Relocation constraints". **Exit criteria:**

- [ ] **Q1. Preprocessor controls with ROM-address args** (`c81`-`c9C` with 3-byte pointer args): do any point into a pool's string range?
  - Write a throwaway scan of all dumped JP lines: decode each control's args as a 24-bit SNES address; flag ones whose PC falls inside any pool's string span. M1's reviewer saw `{c88:124BD202}` → PC `0x1524B`, inside msg02's range.
  - For each hit, decide: (a) bytes are data that must stay at that address, so mark the range `exclude` in `blocks.json` (never moved, never overwritten), or (b) a string, so treat the arg like a jump target and remap it.
  - Record the list.
- [ ] **Q2. What `$00:B67C` returns** (the event resume pointer). Lua on `ordinary_field_message.mss`: exec callback at `$01:FA5C` (`STA $85`), log A and `$85` before and after, and confirm A = PC after the inline text's `00`. Then patch one inline text in a test ROM with `{goto}` there and back, and confirm the event continues (the next message appears, no crash).
- [ ] **Q3. Message ID → table use:** confirm that every list table actually used is reached only through `$01:EE4A`. Exec-count `$01:EE57` (`LDA $028000,x`) during a 3600-frame `mash.lua` run and the 6 states, and log the X values (table indices).
- [ ] Commit the doc with the message `RE: relocation constraints`.

### Task 2: Pool relocation

**Files:** Create `lmtools/relocate.py`, `tests/test_relocate.py`. Modify `lmtools/build.py`.

**Interfaces:**
- `TABLE_LIST = 0x010000`, `TEXT_START = 0x208000`.
- `class Alloc(start=TEXT_START, end=0x400000)`. `take(size) -> pc` places `size` bytes inside one 32 KB bank (moves to the next bank if needed) and raises `ValueError` if `size > 0x8000` or space runs out.
- `list_entries(rom) -> dict[int, list[int]]`: table PC → list entry PCs pointing at it.
- `table_groups(layout, b, tbl) -> list[tuple[list[list[int]], set[int]]]`: groups of `[table_pc, count]` with the entry PCs they reach (pointers + jump targets + cont successors). Tables sharing entries are in the same group.
- `relocate_block(rom, layout, b, entries, tbl, source, en_tbl, alloc) -> None`:
  - groups whose tables are all in the list are written to `alloc` (tables first, then strings in original address order), and their list entries are patched;
  - remaining tables are inserted in place via `insert_block` on a filtered `Block`.

- [ ] **Step 1: Failing tests** (synthetic ROM, like `tests/test_blocks.py`'s `synth`):

```python
import pytest
from lmtools.blocks import Block, dump_block, pointers
from lmtools.relocate import Alloc, relocate_block, table_groups
from lmtools.rom import lorom_to_pc, pc_to_lorom
from lmtools.tbl import Table

T = Table(["41=A", "42=B", "43=C", "FFC0={goto:3}", "FF={end}"])


def synth():
    """Bank 0. List at PC 0x0000 (2 entries -> tables at 0x40, 0x60). Table 0x40: 2 ptrs, table 0x60: 1 ptr (shares "B").
    Table 0x80 (not in list): 1 ptr. Strings at 0x100."""
    rom = bytearray(0x10000)
    rom[0x100:0x109] = b"AA\xffB\xffCC\xff\xff"            # "AA" 0x100, "B" 0x103, "CC" 0x105
    def ptrs(at, pcs):
        for i, pc in enumerate(pcs):
            rom[at + 2 * i:at + 2 * i + 2] = (0x8000 | pc).to_bytes(2, "little")
    ptrs(0x40, [0x100, 0x103]); ptrs(0x60, [0x103]); ptrs(0x80, [0x105])
    for i, t in enumerate([0x40, 0x60]):
        rom[i * 4:i * 4 + 3] = pc_to_lorom(t).to_bytes(3, "little")
    return rom


B = Block(name="p", type="ptr16", tables=[[0x40, 2], [0x60, 1], [0x80, 1]], bank=0)


def test_groups_join_tables_sharing_strings():
    groups = table_groups(synth(), B, T)
    assert sorted(sorted(t for t, _ in g) for g, _ in groups) == [[0x40, 0x60], [0x80]]


def test_relocates_listed_group_and_patches_list(monkeypatch):
    import lmtools.relocate as r
    monkeypatch.setattr(r, "TABLE_LIST", 0x0000); monkeypatch.setattr(r, "LIST_LEN", 2)
    rom = synth(); base = bytes(rom)
    es = dump_block(rom, B, T)
    es[0].en, es[1].en, es[2].en = "AAAAAAAA{end}", "BBBB{end}", "C{end}"
    relocate_block(rom, base, B, es, T, "en", T, Alloc(0x8000, 0x10000))
    new_t = lorom_to_pc(int.from_bytes(rom[0:3], "little"))
    assert new_t >= 0x8000                                            # table 0x40 moved
    p0 = lorom_to_pc(int.from_bytes(rom[new_t:new_t + 2], "little"))
    assert bytes(rom[p0:p0 + 9]) == b"AAAAAAAA\xff"
    t60 = lorom_to_pc(int.from_bytes(rom[4:7], "little"))
    assert lorom_to_pc(int.from_bytes(rom[t60:t60 + 2], "little")) == lorom_to_pc(int.from_bytes(rom[new_t + 2:new_t + 4], "little"))
    assert rom[0x105:0x107] == b"C\xff"                               # unlisted table: in place
    assert pointers(rom, Block(name="u", type="ptr16", tables=[[0x80, 1]], bank=0)) == [0x105]


def test_group_too_big_for_a_bank():
    with pytest.raises(ValueError, match="> 32 KB"):
        Alloc(0, 0x10000).take(0x8001)


def test_jump_out_of_group_is_an_error(monkeypatch):
    import lmtools.relocate as r
    monkeypatch.setattr(r, "TABLE_LIST", 0x0000); monkeypatch.setattr(r, "LIST_LEN", 2)
    rom = synth(); base = bytes(rom)
    es = dump_block(rom, B, T)
    for e in es: e.en = e.jp
    es[0].en = "A{goto:058100}"                                       # jumps to "CC" (only table 0x80's)
    with pytest.raises(ValueError, match="outside its group"):
        relocate_block(rom, base, B, es, T, "en", T, Alloc(0x8000, 0x10000))
```

Run `python -m pytest tests/test_relocate.py -q`. Expected: ImportError.

- [ ] **Step 2: Implement `lmtools/relocate.py`.**

```python
"""Move listed message tables (+ the strings they reach) into the expanded ROM; inline text overflow stubs."""
from .blocks import Block, JUMP, REMAP, TERMINATED, _check_entries, _enc, _pick, insert_block, jump_targets, \
    pointers, pool_strings
from .rom import lorom_to_pc, pc_to_lorom

TABLE_LIST, LIST_LEN = 0x010000, 20
TEXT_START = 0x208000


class Alloc:
    def __init__(self, start=TEXT_START, end=0x400000):
        self.pos, self.end = start, end

    def take(self, size):
        if size > 0x8000:
            raise ValueError(f"{size} bytes > 32 KB: a 16-bit-pointer group must fit one bank")
        if self.pos % 0x8000 + size > 0x8000:
            self.pos = (self.pos // 0x8000 + 1) * 0x8000
        if self.pos + size > self.end:
            raise ValueError("expanded ROM text space exhausted")
        pc, self.pos = self.pos, self.pos + size
        return pc


def list_entries(rom):
    out = {}
    for i in range(LIST_LEN):
        at = TABLE_LIST + 4 * i
        out.setdefault(lorom_to_pc(int.from_bytes(rom[at:at + 3], "little")), []).append(at)
    return out


def _reach(layout, b, tbl, table):
    """Entry PCs reachable from one table: its pointers, jump targets and cont successors, closed."""
    strings = pool_strings(layout, b, tbl)
    order = [pc for pc, *_ in strings]
    info = {pc: (text, cont) for pc, text, _, cont in strings}
    todo = set(pointers(layout, Block(name=b.name, type=b.type, tables=[table], bank=b.bank)))
    seen = set()
    while todo:
        pc = todo.pop()
        if pc in seen or pc not in info:
            continue
        seen.add(pc)
        text, cont = info[pc]
        todo |= {t for t in jump_targets(text, len(layout)) if t in info}
        if cont:
            todo.add(order[order.index(pc) + 1])
    return seen


def table_groups(layout, b, tbl):
    groups = []
    for t in b.tables:
        reach = _reach(layout, b, tbl, t)
        merged = [g for g in groups if g[1] & reach]
        for g in merged:
            groups.remove(g)
        groups.append(([t] + [x for g in merged for x in g[0]], reach.union(*(g[1] for g in merged))))
    return groups


def relocate_block(rom, layout, b, entries, tbl, source, en_tbl, alloc):
    listed = list_entries(layout)
    by_pc = {e.ptr: e for e in entries}
    _check_entries(b, entries, [pc for pc, *_ in pool_strings(layout, b, tbl)])
    keep = []
    for tables, reach in table_groups(layout, b, tbl):
        if not all(t in listed for t, _ in tables):
            keep += tables
            continue
        group = sorted(reach)
        chosen = {pc: _pick(by_pc[pc], source, tbl, en_tbl) for pc in group}
        for pc, (text, _) in chosen.items():
            e = by_pc[pc]
            if ("cont" in e.meta) == bool(TERMINATED.search(text)):
                raise ValueError(f"{b.name} #{e.id}: " + ("cont entry must not end with {end}/{goto}"
                                                         if "cont" in e.meta else "must end with {end} or {goto}"))
        data = {pc: _enc(b, by_pc[pc], t, text) for pc, (text, t) in chosen.items()}
        size = sum(n * 2 for _, n in tables) + sum(map(len, data.values()))
        base = alloc.take(size)
        new, pos = {}, base + sum(n * 2 for _, n in tables)
        for pc in group:
            new[pc], pos = pos, pos + len(data[pc])

        def remap(m, e=None):
            target = lorom_to_pc(int.from_bytes(bytes.fromhex(m[2]), "little"))
            if target not in new:
                raise ValueError(f"{b.name}: jump to {target:06X} outside its group")
            v = pc_to_lorom(new[target]) | int.from_bytes(bytes.fromhex(m[2]), "little") & 0x800000
            return f"{{{m[1]}:{v.to_bytes(3, 'little').hex().upper()}}}"

        for pc in group:
            text, t = chosen[pc]
            blob = _enc(b, by_pc[pc], t, REMAP.sub(remap, text)) if JUMP.search(text) else data[pc]
            rom[new[pc]:new[pc] + len(blob)] = blob
        at = base
        for t, n in tables:
            for i in range(n):
                old = lorom_to_pc(b.bank << 16 | int.from_bytes(layout[t + 2 * i:t + 2 * i + 2], "little"))
                rom[at + 2 * i:at + 2 * i + 2] = (pc_to_lorom(new[old]) & 0xFFFF).to_bytes(2, "little")
            for le in listed[t]:
                rom[le:le + 3] = pc_to_lorom(at).to_bytes(3, "little")
            at += 2 * n
    if keep:
        kb = Block(name=b.name, type=b.type, tables=keep, bank=b.bank, box=b.box, exclude=b.exclude)
        kept = {pc for pc, *_ in pool_strings(layout, kb, tbl)}
        insert_block(rom, kb, [by_pc[pc] for pc in sorted(kept)], tbl, source, en_tbl, base=layout)
```

**Note:** in `table_groups`, `JUMP` uppercase-only matching is a known M1 minor. Make `JUMP`/`REMAP` in `blocks.py` case-insensitive (`[0-9A-Fa-f]`) as part of this step and add the case to a test.

- [ ] **Step 3: Wire into `build.build`.** Create one `Alloc()` per build. For `ptr16` blocks call `relocate_block(...)` instead of `insert_block(...)`. Pass the same `alloc` to Task 3's inline relocation. Run all tests.
  - `test_empty_en_falls_back_to_jp` still uses `insert_block` and stays valid.
  - Add `test_build_relocates_message_tables`: build with `source="jp"`, then assert the list entries at `010000` now point at PC `>= 0x208000` for tables 1, 3-10 and 13-19, and that `lm.py boot` passes.
- [ ] **Step 4: Runtime check:** `tests/test_vwf.py` and `tests/test_vwf_runtime.py` still pass (the states call messages by ID, so they now use relocated tables).
- [ ] **Step 5: Commit** with the message `Relocate listed message tables into the expanded ROM`.

### Task 3: Inline text overflow stubs

**Interfaces:** `relocate.inline_stub(rom, layout, b, e, data, tbl, alloc) -> bytes`. It is called by `insert_block`'s inline path when `len(data) > slot` (instead of raising), given `alloc`.
- **Old slot:** the header (`FF 7F xx` if the JP starts with `{p7F:..}`), then `FF C0` + 3-byte address of the new copy, then `{nop}` padding, then the original `00`. The `00` stays at the same PC.
- **New copy:** the EN body without its header and without the final `{end}`, then `FF C0` + 3-byte address of the old slot's `00`.
- **Error** if the slot is smaller than `header + 5 + 1`.

- [ ] **Step 1: Failing tests** (`tests/test_relocate.py`):

```python
def test_inline_overflow_goes_out_and_back():
    t = Table(["41=A", "FF7F={p7F:1}", "FFC0={goto:3}", "CE={nop}", "00={end}"])
    rom = bytearray(0x10000)
    rom[0x10:0x1B] = b"\x10\xff\x7f\x02AAAAAA\x00"         # slot: header + 6 chars + end (10 bytes)
    blk = Block(name="ev", type="inline", ranges=[[0, 0x100]])
    es = dump_block(rom, blk, t)
    es[0].en = "{p7F:02}" + "A" * 20 + "{end}"
    insert_block(rom, blk, es, t, "en", alloc=Alloc(0x8000, 0x10000))
    assert rom[0x11:0x14] == b"\xff\x7f\x02" and rom[0x14:0x16] == b"\xff\xc0" and rom[0x1A] == 0x00
    new = lorom_to_pc(int.from_bytes(rom[0x16:0x19], "little"))
    assert rom[new:new + 20] == b"A" * 20 and rom[new + 20:new + 22] == b"\xff\xc0"
    assert lorom_to_pc(int.from_bytes(rom[new + 22:new + 25], "little")) == 0x1A


def test_inline_slot_too_small_for_stub():
    t = Table(["41=A", "FF7F={p7F:1}", "FFC0={goto:3}", "CE={nop}", "00={end}"])
    rom = bytearray(b"\x10\xff\x7f\x02A\x00" + bytes(0x100))
    blk = Block(name="ev", type="inline", ranges=[[0, 6]])
    es = dump_block(rom, blk, t)
    es[0].en = "{p7F:02}AAAAAAA{end}"
    with pytest.raises(ValueError, match="ev #0: slot too small"):
        insert_block(rom, blk, es, t, "en", alloc=Alloc(0x8000, 0x10000))
```

- [ ] **Step 2: Implement.** Add an `alloc=None` parameter to `insert_block`; `build` passes the build's `Alloc`. With no `alloc`, keep the current "too long; needs relocation" error.
- [ ] **Step 3: In-game check.** Give the field-state Peacock line a long EN version (2 full lines) in a monkeypatched build (as `test_vwf_runtime` does). Run `ordinary_field_message` + A. Assert the text renders (screenshot differs from JP) **and** that 600 frames later the event continues: the next message box appears (window RAM `$09FE` changes, or the screenshot changes again). This uses the Q2 findings.
- [ ] **Step 4: Commit** with the message `Relocate overlong inline event text via goto stubs`.

### Task 4: Lint

**Files:** `lmtools/lint.py`, `data/windows.json`, `glossary.md` (skeleton), `tests/test_lint.py`, `lm.py lint`.

**Interfaces:**
- `data/windows.json`: `{"dialog": {"px": 216, "lines": 2}, "msg": {"px": 216, "lines": 3}, "screen": {"px": null}, "name8": {"bytes": 8}, "name10": {"bytes": 10}, "name11": {"bytes": 11}}`.
  - `px` = window inner width (28 cells = 224 px minus an 8 px margin).
  - `null` = positioned or fixed-font text: no pixel check, but the cell rule below applies.
  - An entry may override with meta `win=<key>`.
- `lint_entry(e, block_box, widths, windows, glossary) -> list[str]` and `lint_all() -> list[str]`, giving messages like `msg02 #0044: line 2 is 231 px > 216`.
- **Rules:**
  1. **VWF lines** (no `{pXX:..}` in the line and no kanji): each `{n}`/`{clear}`/`{scroll}`-separated line's width is ≤ `px`. Width = the sum of VWF widths; tags count as 0, except insertions (`{c87..}`/`{c98..}` names count as 8 x 8 px, `{c84..}`/`{c85..}`/`{c95..}` numbers as 3-4 x 6 px).
  2. **Lines per page:** the count of `{n}` between page breaks (`{clear}`, `{scroll}`, `{wait}`-like controls) is < `lines`.
  3. **Fixed or positioned lines:** each positioned segment's EN char count (cells) is ≤ the JP segment's cells (kanji = 2, others 1), so layouts that were drawn to fit still fit.
  4. **Control parity:** the multiset of control tags (excluding `{n}`, `{delay}`, `{speed}`, `{nop}`) is the same in JP and EN.
  5. **Glossary:** for each glossary JP term present in `e.jp` with non-empty EN, the EN contains the glossary EN term.
  6. **Fixed names:** EN bytes ≤ `bytes`.

- [ ] **Step 1: Failing tests** for each rule, including Review Focus 4 (trailing spaces count; width measured per `{n}` line) and 5 (glossary spelling). Example:

```python
from lmtools.lint import lint_entry
from lmtools.script import Entry

W = {"dialog": {"px": 40, "lines": 2}}
WID = {c: 6 for c in map(chr, range(32, 127))}


def test_width_per_visual_line_counts_trailing_spaces():
    e = Entry(1, 0, {}, "あ{end}", "AAAAAA{n}AAAAA  {end}")
    assert lint_entry(e, "dialog", WID, W, {}) == ["#1: line 2 is 42 px > 40"]


def test_glossary_spelling():
    e = Entry(2, 0, {}, "リイムが来た{end}", "Rime came.{end}")
    assert lint_entry(e, "dialog", WID, {"dialog": {"px": 999, "lines": 9}}, {"リイム": "Reem"}) == \
        ["#2: glossary: リイム should be 'Reem'"]


def test_control_parity():
    e = Entry(3, 0, {}, "{c85:600E00}ポイント{end}", "points{end}")
    assert "control" in lint_entry(e, "dialog", WID, {"dialog": {"px": 999, "lines": 9}}, {})[0]
```

- [ ] **Step 2: Implement** `lint.py`. The VWF widths come from `font.parse_font("src/font/vwf.txt")`.
- [ ] **Step 3: Wire it in.** `lm.py lint` prints all messages and exits 1 if there are any. `build` runs lint for blocks with EN and fails on errors, unless `--no-lint` is given (dev).
- [ ] **Step 4:** run lint on the M2 test lines. Expected: clean, or fix the lines.
- [ ] **Step 5: Commit** with the message `Add lint: widths, line counts, control parity, glossary, name limits`.

### Task 5: VWF/build leftovers from M2

All asm changes need a test first: Lua runtime or static, in `tests/test_vwf_runtime.py` / `tests/test_hooks.py`.

- [ ] **Step 1: Upload batching.**
  - Replace the per-glyph `$57=$FE` + `JSL $00E3BE` with a dirty flag.
  - Hook `$00:C20E` (`PHP / SEP #$20 / INC $57`). If dirty: `$57=$FE`, `JSL $00E3BE`, clear dirty. Then replay.
  - Test (Lua): frames to fully draw the item-caution EN line at speed 0 drop to ≤ 2 frames after the first glyph (measure before and after); the field line still types correctly (screenshot sequence).
- [ ] **Step 2: Lazy slot advance.**
  - `vwf_start` only marks "slot needed". The first VWF glyph of a message advances and clears the slot.
  - Test: a message `{n}{end}` followed by a 3-line message in the battle window keeps all 3 lines visible.
- [ ] **Step 3: Edge cases.**
  - `.adv` writes the next cell's tilemap only when the new `px` is not 0.
  - Clamp spill and parking at column 31 (no write past cell 31 of the slot).
  - Static test plus a Lua test with a width-8 glyph ending at `$09F8`.
- [ ] **Step 4: Build hygiene.**
  - `build` deletes `lm_en.sfc`/`.bps` first and uses `try/finally` for `_work.sfc`.
  - `font.parse_font` errors include the line number and reject names outside `$20-$7E`.
  - Error messages always name the block.
  - Tests for each.
- [ ] **Step 5: Bold a-z** in `src/font/fixed.txt` (2 px stems, matching the game's UI capitals). Preview PNG next to the game's capitals (render tiles from base PC `170410+`). Check the report/personal screens after a fresh font load (Task 8).
- [ ] **Step 6: Commit** each sub-step separately.

### Task 6: Glossary

**Files:** `glossary.md`.

- [ ] **Step 1: Extract candidate terms.**
  - All `unit_names`, `monsters`, `accessories` and weapon/armor names.
  - Katakana runs of 3 or more characters and kanji compounds that recur in msg02/06/22/36/37.
  - Character and place names: リイム, ライクバーン, ヴァイス, ピーコック, ジャスバン, ライナーク, マテドラル, パズタ…
- [ ] **Step 2: Write `glossary.md`** as a table `| JP | EN | max bytes | notes |`.
  - Faithful and natural: romanize names, and use the game's own English where its graphics already show it (e.g. "Little Master", "Scenario", "Medal", "Report").
  - Fix the character and place names first. Record the byte limits from the record blocks.
  - **The name-copy control `c87` stops at a space**, so names copied that way (monsters, units) must use no spaces (e.g. `Mouseman`) or `_` drawn as a space glyph. Decide this in the glossary.
- [ ] **Step 3: Get user review** of the character, place and army names. Present the table; this is the one taste decision that touches everything.
- [ ] **Step 4: Commit** with the message `Add glossary`.

### Task 7: Translate names (fixed records)

- [ ] For `unit_names` (8 bytes), `unit_weapon0-3`/`unit_armor0-3` (10), `accessories` (10) and `monsters` (11): fill EN per the glossary. Copy identical JP across the 4 weapon/armor tables (write a throwaway helper that copies EN by JP text).
- [ ] `python lm.py lint` is clean, `python lm.py build` succeeds.
- [ ] Commit with the message `Translate unit, item and monster names`.

### Task 8: Translate system text (msg02, msg22, msg06)

Work in chunks of about 100 entries. Each chunk: translate EN lines, run lint, build, commit (`Translate <block> #a-#b`).

- [ ] **msg02** (299 entries: battle/system messages, status layouts).
  - Positioned layouts keep every control and position; only the text between them changes, within the JP cell budget.
  - Debug/test screens (`MEMORY CHECK…`, `BG1…`): leave EN empty (JP fallback) and note them.
- [ ] **msg22** (147): scenario summaries (relocated, free length within window lines), clear conditions, the 7 ailment messages (in place, so within the JP byte total).
- [ ] **msg06** (608): unit/terrain/item descriptions.
  - Descriptions are drawn in the personal-info window: fixed font, 29 cells x 3 lines. The lint's `win=` override should be set to that window for this block in `data/windows.json` once measured.
- [ ] **Screen check:**
  - Run `test/lua/state_shot.lua` on all 6 states with A presses (`PRESS_A_AT={10, 60, 110, 160}`) and B to open and close menus, so the game reloads fonts.
  - Read every screenshot. Fix clipping and overflow, and check status screens for broken icons.
  - Record findings in `docs/re/text-engine.md`.

### Task 9: M3 acceptance

- [ ] `python -m pytest -q` passes; `python lm.py lint` is clean; `python lm.py build` succeeds; `python lm.py boot build/lm_en.sfc` passes.
- [ ] Give the user 20 random translated lines (JP | EN) plus the screen-check screenshots for review. Apply their tone fixes across the blocks.
- [ ] Cross-check `lm_en.bps` with a standard BPS patcher (Floating IPS / beat). Apply it to a clean ROM and compare with `build/lm_en.sfc`. If no Windows patcher is available offline, note it for M6.
- [ ] Commit, then `git tag m3`.

---

## Out of scope

- The main story script (`msg36`, `msg37`, `ev03`, `ev0A`, `ev22`): **M4**.
- Graphics and the title screen (`EBM1`): **M5**.
- Personal-info VWF (window labels use 23 slots): revisit in M5 if the fixed font reads poorly.
