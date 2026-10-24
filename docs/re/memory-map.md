# Memory map, free space, expansion, compression

## ROM

- LoROM, SlowROM (map mode `$20`), 2 MB, SRAM 8 KB (header `$7FD8 = 3`).
- PC `p` ↔ SNES `$BB:AAAA` with `BB = p / $8000`, `AAAA = $8000 + p % $8000` (`lmtools.rom`).

### Free space (original 2 MB)

`python lm.py freespace --min 0x400` finds only three runs of at least 1 KB:

| Range | Bytes | Fill |
|---|---|---|
| `1541A6-154626` | 1152 | `00` |
| `17D100-17D801` | 1793 | `00` |
| `1B0400-1B0801` | 1025 | `00` (between message tables #4 and #6) |

Smaller runs (256-1023 bytes) exist; list them with `--min 0x100`. Caution: a long `00`/`FF` run can be real data (tile graphics). Check that nothing points into it before using it. **Conclusion: English text will not fit in place. Expansion is required.**

### Expansion

`rom.expand()` pads to 4 MB, sets the header ROM-size byte `$7FD7 = $0C` and fixes the checksum.

- New space: PC `200000-3FFFFF`, read at **`$C0:8000-$FF:FFFF`** (also `$40-$7D:8000-FFFF`). Banks `$70-$7D:0000-7FFF` are SRAM.
- `tests/test_mesen.py::test_expanded_rom_boots` passes. A 3600-frame scripted run (`tools/lua/mash.lua`, Start/A mashing into the first dialogue) matches the original's screenshots, except for an animation-phase shift at frame 3000.
- That shift was traced and is **not** caused by expansion:
  - Nothing reads PC `200000+`.
  - The game reads SRAM `$70:0000-0A9F` at boot (`$01:E6E0`, save-data load + checksum), and Mesen fills SRAM with random bytes that differ per ROM file. The resulting timing difference shows up in animations.
  - A 4 MB file with the old size byte `$0B` matches exactly. A 2 MB file with size byte `$0C` drifts at frame 3600.
  - To check in M2: real save/load on the expanded ROM.

## RAM (text engine)

See `text-engine.md`. Key locations:
- DP `$14-$16`: text pointer.
- `$0400`: preprocessed render buffer.
- `$0700`: kanji slot table.
- `$09F0-$0A0A`: window and cursor state.
- `$0A08`: script variable.
- `$7E:9000`: text window tilemap buffer (DMA'd to VRAM, 2 KB).
- `$7E:EA84`: configured text speed.

## Graphics and compression survey

Unique VRAM DMA sources over a 3600-frame run (`tools/lua/_dma.lua`, not committed):

| Source | Size | What |
|---|---|---|
| `$2E:8000` (PC `170000`) | `$1000` | single-byte font (uncompressed in ROM) |
| `$03:8340` (PC `018340`) | `$800` | font part 2 |
| `$2E:A000`, `$2E:F000` | `$1000` | more uncompressed tiles |
| `$7E:9000`, `$7F:B000` | `$800` | tilemap buffers (text window) |
| `$7E:2000` | `$4000`, `$1180`, `$540` | **decompressed graphics** |

ROM graphics come in **`EBM1` containers**: 106 of them, e.g. PC `1200CA`, `15698C`. Header: `"EBM1"`, then bytes that look like width/height/size, then data. They are unpacked into `$7E:2000` before upload. The title logo and scene graphics are most likely here. **Codec not written (M5).** Find the unpacker by putting a write breakpoint on `$7E:2000` during a scene load.

Text is uncompressed: proven by the byte-identical round-trip.
