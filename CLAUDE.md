# Little Master: Nijiiro no Maseki (SNES) English translation

Skill: translate-retro-game (H:/translation/.claude/skills/translate-retro-game/SKILL.md). Read it before ROM, text or QA work.

## Commands (repo root; `python lm.py -h` lists all)
- Build:   `python -X utf8 lm.py build` -> build/lm_en.sfc + .bps (lints first; `--no-lint` skips)
- Check:   `python -X utf8 lm.py lint && python -X utf8 -m pytest -q -x -m "not mesen"` (~80 s; the pre-commit hook runs this)
- Gate:    `python -X utf8 lm.py test` (lint, round-trip, build, full pytest; slow, run before a release)
- Smoke:   `python -X utf8 lm.py boot build/lm_en.sfc` -> build/shots/boot.png (or the skill's `emu.py ... --smoke`)
- Release: `python -X utf8 lm.py release --version 1.0-rcN` -> dist/LittleMaster_EN_v1.0-rcN.zip (bps + README). Never publish without the user.
- Text:    `lm.py show BLOCK LO HI`, `lm.py apply BLOCK file.tsv` (id<TAB>EN), `lm.py roundtrip`, `lm.py coverage`
- RE:      `lm.py dis ADDR`, `findptr`, `findbytes`, `freespace`, `vramfind`, `gfx`, `gfxexport`
- Scratchpad scripts can `import lmtools`: PYTHONPATH is set in .claude/settings.json.

## Paths
- ROM: `rom/Little Master - Nijiiro no Maseki (Japan).sfc` (gitignored). Mesen2 2.1.1: `tools/mesen2/Mesen.exe` (tools/ gitignored), driven by `lmtools/mesen.py`.
- Text: `script/*.txt` (19 blocks, 3723 entries), defined in `data/blocks.json`. Window widths for lint: `data/windows.json`. Graphics inserts: `data/graphics.json`.
- Tables: `tbl/jp.tbl`, `tbl/en.tbl`. VWF: `src/asm/vwf.asm`, `src/font/vwf.txt`.
- Rulings: `glossary.md` (names, byte limits), `docs/style.md` (line rules, voices). RE index: `docs/re/README.md`. Spec/plans: `docs/superpowers/`.
- Savestates: `test/states/*.mss` (gitignored; tests need them). Lua: `test/lua/*.lua`; throwaway probes `test/lua/_*` (gitignored).
- Playtest guide + bug log: `docs/playtest.md`.

## Rulings
- Names exactly as in `glossary.md`. Western order (Reem Likeburn). Honorifics dropped (プーちゃん -> Poo). Credits language: not recorded, ask.
- 勇者軍 "the Heroes", 魔物軍 "the Monsters", カラード "Calard" (not "Colored"), Jasvan (map art JUSVAN left as drawn).
- Full names, no abbreviations; prefer engine work (VWF, wider box, relocation) to cutting meaning.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update the Status section.

## Gotchas
- Copied names stop at a space or 00: write `Skull_Pirate` (drawn as a space). Byte limits: unit 8, weapon/armor/accessory 10, monster 11.
- VWF line <= 208 px (at 213+ the game auto-wraps and the next {n} adds a blank line). Never more lines per page than JP.
- Message tables are 16-bit: each pool stays in its bank. `{goto}`/`{jXX}` carry 24-bit addresses the inserter remaps.
- Mesen fills SRAM randomly per ROM file, so timing drifts: tests wait on game state, not fixed frames.
- Savestates carry old code/VRAM: cold boot after asm/font/gfx changes. The title subtitle relies on the bank $40 mirror: check once in bsnes/Snes9x.
- Several files are CRLF in the index (lmtools/blocks.py, font.py, tbl.py, src/asm/vwf.asm, ...): edit with the Edit tool only.

## Status
- Done: M1-M6 (RE, VWF, relocation, story script, graphics, release); latest is dist/ rc4. Playtest B1, B2, C1, C2, C4 fixed; C3 wontfix.
- Next: user playtest per docs/playtest.md. Open: C5, the `09DB16` speech-bubble graphic, not yet seen in game (no state).
