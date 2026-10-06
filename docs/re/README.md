# Reverse-engineering notes (M1)

| Doc | Summary |
|---|---|
| [encoding.md](encoding.md) | Fonts (16x16 interlaced kanji at `020000`, 8x16 single-byte at `170000`), code ranges, how `tbl/jp.tbl` was built |
| [text-engine.md](text-engine.md) | Preprocessor `$00:B680` → `$0400` buffer → renderer `$00:BE4F`; control codes and argument counts; window RAM |
| [pointers.md](pointers.md) | Message table list at `010000` (20 tables, shared pools), inline event text (opcode `10`), fixed name records, coverage |
| [graphics.md](graphics.md) | M5: title codec, subtitle insert, graphics checked |
| [memory-map.md](memory-map.md) | Free space (≈4 KB), 4 MB expansion, RAM, `EBM1` compressed graphics |
| [beta2-regions.md](beta2-regions.md) | Generated map of what Beta2 changed (reference only) |

## Tooling

- **Mesen2 2.1.1** in `tools/mesen2/`, run headless with `--testrunner` (`lmtools/mesen.py`).
  - It needs a `settings.json` next to the exe (portable mode, which skips the first-run wizard) with `Debug.ScriptWindow.AllowIoOsAccess = true`, or Lua `io` is nil. `mesen.run` writes this file if it's missing.
  - Lua API as verified: `emu.addEventCallback(fn, emu.eventType.endFrame|inputPolled)`, `emu.addMemoryCallback(fn, emu.callbackType.read|write, start, end, emu.cpuType.snes, emu.memType.snesPrgRom|snesWorkRam|snesMemory|...)`, `emu.takeScreenshot()`, `emu.getScreenBuffer()`, `emu.read(addr, memType)`, `emu.setInput({start=true}, 0)` (inside `inputPolled`), `emu.getState()["cpu.k"/"cpu.pc"]`, `emu.stop(code)`.
  - Mesen fills SRAM with random bytes per ROM file, so runs of *different* ROMs can drift in animation timing (see memory-map.md).
- **Committed Lua:** `test/lua/boot.lua` (smoke test), `mash.lua` (3600-frame Start/A run with screenshots), `trace_reads.lua` (ROM reads with PC). Throwaway helpers are `test/lua/_*.lua` (gitignored).
- `python lm.py <cmd>`:
  - `info`: check the base ROM.
  - `gfx`: render a font or tiles to PNG (`--mode tile|linear|kanji16`).
  - `betadiff`: regenerate `beta2-regions.md`.
  - `findbytes`, `findptr`: search for byte strings and pointers.
  - `freespace`: list unused runs.
  - `scan`, `coverage`: list decodable strings (`coverage` excludes known blocks).
  - `dis`: disassemble 65816 (`--m16 --x16`).
  - `dump`: write `script/*.txt`; refuses to overwrite EN translations without `--force`.
  - `roundtrip`: reinsert JP and compare.
  - `boot`: headless smoke test.
- Tests: `python -m pytest`. They need the ROM; Mesen and Beta2 tests skip if those are absent.

## Script size

19 blocks, **3723 entries, ~81,500 JP characters** (tags excluded).
- Dialogue/events: `msg36` 18.3k, `msg37` 12.6k, `ev0A` 8.8k, `ev03` 4.4k, `ev22` 2.4k.
- System/help: `msg06` 19.9k, `msg02` 5.4k, `msg22` 4.6k.
- Names: units 146, accessories 128, monsters 180, per-unit weapon/armor 4x53x2.

## Facts M2 needs

- **Font/rendering:** text is tilemap-based. Single-byte char = tile code (8x16, two tilemap rows), 8 px per char. Kanji are drawn dynamically into tiles `$180 + 2*slot` (`D0 slot` in the `$0400` buffer, glyph index in `$0700`). **That dynamic-tile path is the natural place for a VWF.**
- **Box geometry:** intro window 28 cols x 4 lines (`$09F0-$09FA`). Auto-wrap at `$09F8`, with kinsoku hang for `。」、ー`. Other windows not yet measured.
- **Control codes:** `text-engine.md`.
  - Renderer: `{pXX:YY}` cursor, `{delay}`, `{speed}`, `{color}`, `{scroll}`, `{clear}`.
  - Preprocessor `FF 80-9C`: vars, number and name inserts. `87`/`88` insert names (variable width).
  - `{goto}` / `{jXX}` embed **24-bit text addresses**, which relocation must rewrite (the inserter already remaps them within a block).
- **Pointers:**
  - Message tables are 16-bit, so each pool must stay in its bank. To move text to the expanded ROM, either patch the table-list entries at `010000` (24-bit, so a table can point at a new bank, with strings in that same bank) or hook `$01:EE4A`.
  - Inline event text (opcode `10`) has no pointer. Longer English needs `{goto:newaddr}` in the old slot plus a check of how the event interpreter finds the end of the text.
  - The scenario summaries already end with `{goto}`, which shows the engine follows gotos.
- **Free space:** none worth using in 2 MB; expand to 4 MB (`$C0-$FF:8000-FFFF`).
- **Graphics:** `EBM1` containers decompress to `$7E:2000`. Menu labels are already English glyphs (kanji `7B2-7FF`, tokens `{uiXX}`).
- **Not yet traced:** menu/battle text drawing and field widths. These need in-game save states, which M2/M3 should capture with `mash.lua`-style input scripts.
