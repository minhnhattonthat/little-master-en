# Little Master: Nijiiro no Maseki (SNES) English translation

Skill: translate-retro-game (Claude Code: plugin, enabled in .claude/settings.json; other agents: `<SKILL_DIR>/SKILL.md`; `$SKILL` = the directory holding its SKILL.md, default `~/.claude/plugins/marketplaces/retro-translation/skills/translate-retro-game`). Read it before ROM, text or QA work.

## Commands (repo root; `python lm.py -h` lists all)
- Build:   `python -X utf8 lm.py build` -> build/lm_en.sfc + .bps (lints first; `--no-lint` skips; refuses a dump not matching `rom.sha1`)
- Check:   `python -X utf8 lm.py lint && python -X utf8 -m pytest -q -x -m "not mesen"` (~80 s; the pre-commit hook runs this)
- Gate:    `python -X utf8 lm.py test` (lint, round-trip, build, full pytest; slow, run before a release)
- Smoke:   `python -X utf8 lm.py boot build/lm_en.sfc` -> build/shots/boot.png (or `$SKILL/scripts/emu.py ... --smoke`)
- Release: `python -X utf8 lm.py release --version 1.0-rcN` -> dist/LittleMaster_EN_v1.0-rcN.zip (bps + README). Never publish without the user.
- Text:    `lm.py show BLOCK LO HI`, `lm.py apply BLOCK file.tsv` (id<TAB>EN), `lm.py roundtrip`, `lm.py coverage`
- RE:      `lm.py dis ADDR`, `findptr`, `findbytes`, `freespace`, `vramfind`, `gfx`, `gfxexport`
- Clean:   `python -X utf8 tools/clean.py` (published projects: lists rebuildable/downloadable files; `--yes` deletes)
- Scratchpad scripts can `import lmtools`: PYTHONPATH is set in .claude/settings.json.

## Paths
- Original ROM: `rom/Little Master - Nijiiro no Maseki (Japan).sfc` (gitignored; SHA-1 in `rom.sha1`, checked by `lmtools/rom.py` and `tools/check_rom.py`). Emulator: Mesen2 2.1.1 in `tools/mesen2/Mesen.exe` (gitignored), driven by `lmtools/mesen.py`. Other third-party tools in `tools/*/` (asar, ...; gitignored).
- Text: `script/*.txt` (19 blocks, 3723 entries), defined in `data/blocks.json`. Window widths for lint: `data/windows.json`. Graphics inserts: `data/graphics.json`.
- Tables: `tbl/jp.tbl`, `tbl/en.tbl`. VWF: `src/asm/vwf.asm`, `src/font/vwf.txt`. Fonts and their licences: `docs/fonts.md`.
- Glossary (names, byte limits): `glossary.md`. Line rules, voices: `docs/style.md`. RE notes index: `docs/re/README.md`. Spec/plans: `docs/superpowers/`.
- Savestates: `work/states/*.mss` (gitignored; tests need them). Lua: `tools/lua/*.lua`; throwaway probes `tools/lua/_*` (gitignored).
- Playtest guide + bug log: `docs/playtest.md`.

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts here read and analyse, never `.replace()` and write back.
- The user's decisions, with the options and reasons: `docs/decisions.md`. Read it before asking the user anything; add each new ruling there the same session.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update `docs/status.md` and the bug log in `docs/playtest.md`.
- Names exactly as in `glossary.md`. Western order (Reem Likeburn). Honorifics dropped (プーちゃん -> Poo).
- 勇者軍 "the Heroes", 魔物軍 "the Monsters", カラード "Calard" (not "Colored"), Jasvan (map art JUSVAN left as drawn).
- Full names, no abbreviations; prefer engine work (VWF, wider box, relocation) to cutting meaning.

## Gotchas
- Copied names stop at a space or 00: write `Skull_Pirate` (drawn as a space). Byte limits: unit 8, weapon/armor/accessory 10, monster 11.
- VWF line <= 208 px (at 213+ the game auto-wraps and the next {n} adds a blank line). Never more lines per page than JP.
- Message tables are 16-bit: each pool stays in its bank. `{goto}`/`{jXX}` carry 24-bit addresses the inserter remaps.
- Mesen fills SRAM randomly per ROM file, so timing drifts: tests wait on game state, not fixed frames.
- Savestates carry old code/VRAM: cold boot after asm/font/gfx changes. The title subtitle relies on the bank $40 mirror: check once in bsnes/Snes9x.
- tools/ subdirectories are gitignored (third-party downloads): put reusable helpers in `lmtools/`, `tools/*.py` or `tools/lua/`.

## Status
`docs/status.md`: done, next, open bugs. Update it at the end of every session.
