# Little Master – Nijiiro no Maseki: English Translation — Design

Date: 2026-10-05

## Goal

Release-quality English translation patch for *Little Master – Nijiiro no Maseki* (SNES, Japan).
All text translated: script, menus, items/monsters/spells, battle and system messages, graphic text.
Delivered as a BPS patch (IPS optional), playtested start to finish.

## Decisions

| Topic | Decision |
|---|---|
| Base ROM | `rom/Little Master - Nijiiro no Maseki (Japan).sfc`, LoROM 2MB, CRC32 `b916334c`, SHA1 `75b76715d4a20371e0340dbeee3a51ff6a1dbad3` |
| Translator | Claude translates all text; user spot-checks samples per milestone |
| Style | Faithful, natural English. Japanese names romanized; items/monsters get English equivalents |
| Approach | Fresh source-based build from the original ROM. Beta2 patch (`patch/LM3-Beta2.IPS`) used **only as a reference map** (text/pointer locations, menu widths). No Beta2 binary code or assets copied |
| Font | New original font drawn for this project |
| Assembler | asar (downloaded) |
| Emulator / tests | Mesen2 (downloaded), Lua test-runner for automated screenshots/crash checks; user does final playthrough |
| ROM expansion | Allowed (2MB → 3MB or 4MB) |
| VCS | git; ROMs, Beta2 patches, `tools/`, `build/` are gitignored |

## Known facts (from initial exploration)

- Header at `0x7FC0`: `LITTLE MASTER`, LoROM.
- Original text: single-byte kana plus multi-byte kanji codes. 1bpp kanji font around `0x20C3C`.
- Beta2 changed about 860 regions. Notable ones:
  - item/equipment name tables at `0x10052+` (20-byte names + stats);
  - terrain descriptions at `0x32C04+`;
  - main script at `0x1B1200–0x1B6200`;
  - its new font at `0x170000+`;
  - relocated code at `0x24000`.
- Beta2 uses `0x0A xx` dictionary-style codes. Treat that as a hint that the original space is tight.

## Architecture

```
little-master/
  rom/            original ROM (read-only, gitignored)
  patch/          Beta2 reference (gitignored)
  tools/          existing + downloaded tools (gitignored)
  docs/           RE notes: encoding, control codes, pointer tables, RAM map, free space
  tbl/            jp.tbl (decode), en.tbl (encode)
  src/asm/        asar hacks: main.asm includes font loader, VWF, engine changes, expansion
  src/gfx/        English font + redrawn graphic text (PNG)
  script/         one file per text block, JP + EN side by side
  glossary.md     canonical names/terms + max lengths
  build/          output ROM, .bps, screenshots (gitignored)
  lm.py           CLI: dump | insert | build | test
```

### Build (`python lm.py build`)

1. Copy the original ROM and expand it.
2. Apply `src/asm/main.asm` with asar.
3. Encode the script with `en.tbl` and write it to free space. Update the pointer tables.
4. Convert `src/gfx/*.png` with superfamiconv (recompressing if the game needs it) and insert the results.
5. Fix the internal checksum. Write `build/lm_en.sfc` and produce `build/lm_en.bps` with flips.

### Script file format

```
#id 0123  ptr=1B2307  box=dialog
JP: <original line, decoded>
EN: Translated line here.{wait}
```

- Only `EN:` lines are inserted. `JP:` lines are kept for review and context.
- Control codes are written as `{name}` or `{name:arg}` tags. The control-code table in `docs/` defines them.

## Phase 1: Reverse engineering (gates everything else)

1. **Encoding.** Render the font graphics to PNG, then read the glyphs and confirm the mapping against known strings. Output: `tbl/jp.tbl`.
2. **Text engine.** Trace the print routine with the Mesen2 debugger. Document:
   - the control codes: newline, wait, page break, name insertion, choices, colors, and any others;
   - the rendering method: tile-based or tilemap-based;
   - the box sizes.
3. **Pointer tables.** Cover the script, menus, items, monsters, spells, places, battle messages and terrain/status text. Diffing against Beta2 helps find them.
4. **Compression.** Identify any compression used for text or graphics. If there is any, implement a Python codec that round-trips byte-for-byte.
5. **Free space.** Map unused regions. Confirm the expanded ROM boots and plays the same as the original.

**Exit criterion:** dump everything, then reinsert it unchanged. The result must be byte-identical to the original, or functionally identical with relocated pointers, as verified by the screenshot tests.

## Font and display

- **Dialogue:** a VWF that renders into a tile buffer, which is then DMA'd to VRAM. Glyph height (8 or 16px) follows the original engine.
- **Menus and lists:** fixed-width or a narrow VWF, whichever the menu drawing code allows. Widen windows where possible. Where a window can't be widened, the glossary records the maximum name length.
- **Space:** the script goes into the expanded banks. Add DTE or dictionary compression only if bank or pointer limits force it.
- **Graphic text:** the title logo, tile-drawn labels and other in-graphic text are redrawn as PNG. The title keeps the Japanese logo with an English subtitle, or gets a full English logo, depending on space.
- **Overflow:** the inserter measures each line in pixels against its box width. A line that doesn't fit fails the build with its line id. Optional auto-wrap.

## Translation workflow

1. Order:
   1. glossary (characters, places, items, monsters, spells, statuses, story terms);
   2. menus and system text;
   3. story script, in game order;
   4. battle and miscellaneous text.
2. `glossary.md` is the single source of truth for terms.
3. `lm.py lint` flags:
   - glossary terms spelled inconsistently;
   - missing `EN:` lines;
   - control-code mismatches between the JP and EN lines;
   - overflow.
4. For ambiguous lines, check the scene in the emulator (speaker, situation) before translating.
5. The user spot-checks samples at each milestone. Tone fixes are applied across the whole script.

## Testing

`python lm.py test` checks that:
- the build succeeds;
- the round-trip test still passes;
- the lint and overflow checks pass;
- the Mesen2 Lua scenario runs pass. These load save states for key scenes and menus, advance text, screenshot each box to `build/shots/`, and fail on a crash or freeze (PC stuck, or a black screen for N frames).

Save states live in `test/states/` (gitignored if they contain ROM-derived data).

## Milestones

Each milestone ends with a git commit and a test build.

| # | Milestone | Done when |
|---|---|---|
| M1 | RE complete | docs written, jp.tbl complete, round-trip passes |
| M2 | Font + VWF | English test line renders correctly in dialogue and menus |
| M3 | System text | menus, items, monsters, spells, statuses translated and fit |
| M4 | Script | full story script translated, lint and overflow clean |
| M5 | Graphics | all graphic text redrawn and inserted |
| M6 | Release | user playthrough bugs fixed; `.bps` + readme (with base ROM checksum) |

## Risks

- **The text engine is unusual** (compression, hardcoded lengths, text inside code). Mitigation: M1 gates all later work, and its findings are documented before any building starts.
- **Menu windows are too narrow for English.** Mitigation: widen windows in asm, or abbreviate. The glossary records each limit.
- **Mesen2 automation proves fiddly.** Fallback: manual save-state screenshot scripts, with the user testing by hand.

## Out of scope

- Gameplay changes and bug fixes in the original game, unless one blocks the translation.
- Translating into any language other than English.
