# Graphics (M5)

## Tools

- `test/lua/vram_dump.lua` (globals `STATE`, `INPUTS`, `AT`, `NAME`) writes `NAME.vram/.cgram/.oam/.ppu/.png`. `.ppu` has mode, chr/map addresses (words), 64-wide/high flags and scroll *at frame end*. Mid-frame register changes (map screen) make this unreliable there.
- `python lm.py vramfind dump.vram --bpp 4` lists runs of VRAM tiles found verbatim in the ROM. Single-tile hits are usually coincidences.
- `python lm.py gfxexport` exports ROM tiles with a CGRAM palette. `lmtools.gfx` has `encode_tiles`, `png_to_tiles`, `tiles_to_png` and `cgram_palette`.

## Chunk-dictionary codec (`lmtools/chunkgfx.py`)

The unpacker is at `$00:AF6B` and writes to `$7E:2000`. The caller then DMAs each 8 KB piece to VRAM.
- Args: A = id, `[$12]` = header table, `$16/$18` = dictionary address/bank.
- Table: 8-byte entries from offset 8: `id, stream offset (from table), first new-chunk index, $0200`. A `0` id ends the table.
- Each op of the stream outputs one 16-byte chunk:

| op | meaning |
|---|---|
| `00` | end |
| `01-3F` | n chunks `dict[next++]` (next starts at the entry's index) |
| `40-7F xx` | chunk `(op&3F)<<8 \| xx`; becomes `last` |
| `80 n` | chunk `last`, n times |
| `81-FF` | chunk `last + (op&7F)` |

Chunk `k` sits at dictionary + `16*k`, with LoROM bank math (`chunk_pc`). Within each bank, `$xx:8000-8FFF` is unreachable when the base is `$xx:9000`.

**Title screen:** mode 4, BG1 = one 256x224 8bpp bitmap with a linear tilemap.
- Table `$23:8000`, dictionary `$23:9000`, ids 8-14 (32 lines each).
- The decoder output equals the VRAM dump (`tests/test_chunkgfx.py`).

**Subtitle** `～虹色の魔石～` → `~ Jewels of Rainbow ~`:
- It sits at y 98-109 in piece id 11.
- `src/gfx/title_subtitle.png` (116x14, at x70/y98) is our own art: Times 12 mapped onto palette 0's grey ramp (`data/graphics.json` `greys`).
- The build decodes piece 11 and patches the box. It stores the piece whole as new chunks at `$C0:E000` (index ED00), so its 10-byte stream fits in place.
- Bank `$23` has only 448 bytes free (`118040-1181FF`). `vwf.asm` asserts that bank `$C0` code stays below `$C0E000`.

## Checked, no change

- **World-map place labels** are already Latin. They use a decorative A-Z font at `174040` (BG tiles 02-1B = A-Z; e.g. `JUSVAN`, `JIRIJIRI`, `NAIEL`). Note that the map spells it *Jusvan*, while the script uses *Jasvan*.
- **UI label glyphs** (kanji `7B2-7FF`) are the game's own English (Scenario, Medal, Caution, Save, …). They read fine.
- **Intro credits**, "LITTLE MASTER / EPISODE III / JEWELS OF RAINBOW", PUSH START and the copyright line are English in the original.

## Open

- `09DB16-09DC93`: 2bpp tiles of small bubbles with glyphs (Beta2 changed it). No save state, A-press run or 12000-frame boot reads it, so the screen is unknown. Deferred to the M6 playthrough: save a state where it shows.
- `EBM1` containers (another codec, 106 of them) aren't decoded. None of the screens seen so far draws Japanese from them.
- Save-state screenshots can't show re-rendered graphics or text, because a state restores the JP VRAM. Graphics checks must reload the screen (the title test boots).
