# Text locations and pointers

Source of truth: `data/blocks.json`. `python lm.py dump` writes one `script/<block>.txt` per block.

## Message system

Message ID = 16-bit: high byte = table number, low byte = entry. `$01:EE4A` reads the table address from the **table list at PC `010000`** (`$02:8000`, 20 entries of 4 bytes: 24-bit SNES address + pad), then `LDA [table],y` with y = entry*2 gives a 16-bit string pointer in the same bank. If a string starts with `FF 7F xx`, `$EC12` is called with `xx` (speaker/window header) and the text starts 3 bytes later. Then `JSL $00:B67C` (preprocessor) runs.

| # | Table PC | Bank | Count | Block |
|---|---|---|---|---|
| 0 | `0130E0` | `$02` | 200 | `msg02`: system/battle messages and status-screen layout scripts |
| 1 | `030200` | `$06` | 256 | `msg06` |
| 2 | `111EE3` | `$22` | 59 | `msg22`: scenario summaries (end with `{goto:00B222}`) |
| 3, 16 | `1B0000` | `$36` | 256 | `msg36` (same table listed twice) |
| 4, 17 | `1B0200` | `$36` | 256 | `msg36` |
| 5 | `030000` | `$06` | 256 | `msg06` |
| 6-10 | `1B0800`, `1B0A00`, `1B0C00`, `1B0E00`, `1B1000` | `$36` | 53 each | `msg36`: five variant tables over one shared pool (`1B1200-1B1758`) |
| 11 | `111F59` | `$22` | 72 | `msg22`: place names, indexed by `$7E:EA82`; 60-63 are raw `003C-003F` (copied as is), 64-71 castle rooms/shops |
| 12 | `111FE9` | `$22` | 27 | `msg22`: 0-16 spell texts, 17-19 raw `0011-0013` (copied as is), 20-26 status-ailment messages (`0C14`-`0C1A`, "Caution" window) |
| 13 | `030400` | `$06` | 128 | `msg06` |
| 14 | `030600` | `$06` | 256 | `msg06` (shares 1 string with #1) |
| 15 | `030800` | `$06` | 96 | `msg06` |
| 18 | `1B8000` | `$37` | 256 | `msg37` |
| 19 | `1B8200` | `$37` | 232 | `msg37` (232 = up to the first string at `1B83D0`) |

Counts stop where the next table or the pool's first string begins.

### Pools and entries

A pointer block is a **string pool** with one or more pointer tables. Its entries are the unique strings in address order:
- pointer targets;
- plus jump targets: `{goto:...}` / `{jXX:...}` addresses in the same 32 KB LoROM bank.

When an entry point falls inside another string, the string is cut there and flagged `cont=1`: it falls through into the next entry, so the two must stay adjacent. This covers branch targets inside `msg02`/`msg22` screen scripts and pointers to a shared terminator. The dumper refuses a cut that would split a token.

`FF C0` is an unconditional goto (`$54 & 3F >= 0` always holds), so decoding stops after `{goto:...}` as well as after `{end}`.

**Relocation note (M2):** jump controls carry 24-bit text addresses. Moving strings must rewrite those as well as the pointer tables.

## Inline event text (`type: inline`)

Event bytecode shows text with opcode `10` followed directly by the text. The text always begins with an `FF` control: `FF 7F xx` (speaker header), a position `FF 0x yy` (captions/credits), `{color}`, `{speed}` or `{clear:00}`. It runs to `00`. There is no pointer, so a slot's length is fixed: in-place insertion pads short text with `CE` (`{nop}`, which the renderer skips). Longer text needs relocation via goto (M2).

| Block | Range | Entries |
|---|---|---|
| `ev03` | `018000-01FFFF` (bank `$03`, map events) | 134 |
| `ev0A` | `050000-057FFF` (bank `$0A`, events, scenario captions) | 419 |
| `ev22` | `113943-117FFF` (bank `$22`, events, staff credits, captions) | 111 |

Validity filter: clean decode, ends in `{end}`, and it either starts with a speaker header or starts with a position/colour/speed/`{clear:00}` code and has at least 2 real characters and no `{gXX}` decorative tokens. Garbage `10 FF` matches in bank `$03` (`01A1F0`, `01CD18`...) are rejected.

## Fixed-width records (`type: fixed`)

| Block | Start | Count | Stride | Name bytes | Pad |
|---|---|---|---|---|---|
| `unit_weapon0-3` | `010052`, `010852`, `011052`, `011852` | 53 | 32 | 10 | `20` |
| `unit_armor0-3` | `01005C`, `01085C`, `01105C`, `01185C` | 53 | 32 | 10 | `20` |
| `unit_names` | `012050` | 146 | 8 | 8 | `20` |
| `accessories` | `0124E0` | 128 | 24 | 10 | `CE` |
| `monsters` | `05BF64` | 180 | 40 | 12 (max 11 used + `00`) | `00` |

The four unit tables (weapon/armor names, per scenario?) are identical except records 28, 33, 34, 41, 42 and 47.

## Coverage

- `tests/test_coverage.py`: every region Beta2 changed overlaps a block or is listed in `data/beta2_nontext.json` (header, code hook, fonts, graphics).
- `python lm.py coverage --min 6`: lists decodable strings outside all blocks. Almost all hits are code or graphics decoding as kana (the single-byte range is nearly full). Reviewed hits:

### False positives / not translatable

- `0ADC6A`, `1438B1`: ordered runs of character codes (`52 53 54 ... 60 61 ...`) inside data next to an `EBM1` graphics header. These are font mapping data, not text.
- `1B6A41-1B6A5F`: an orphan tail ("…るとは思わなかったニャ」…「コソコソ嗅ぎまわるのは…」") right after `msg36`'s pool. Nothing points to it (unused leftover), so it is left untouched.
- Everything else in the scan: code/graphics bytes.

## Not yet handled

- Menu/battle drawing code (see `text-engine.md`).
- Graphic text: English UI label glyphs `7B2-7FF` already exist. The title screen etc. belong to M5.

## Relocation constraints (M3 spike, 2026-10-06)

- **Control args with ROM addresses:**
  - No `c8x`/`c9x` arg points into a pool's string spans.
  - ROM pointers go to fixed name records (`c87:05BF64` monsters; `c88` copies from `010052`/`01005C`/`0124C8`/`0124E0`).
  - Some point to data sitting in the **gaps** of msg02 (`0151DE`, `0151E9`, `015221`, `01524B`) and of msg22 (`113566`, `113570`).
  - Relocation leaves original bytes in place, and in-place packing only reuses string spans, so these stay valid. Never widen a pool's free space beyond its string spans.
- **Inline event text** (opcode `10`, handler `$01:FA4E`):
  - The text engine returns A = the 16-bit address right after the text's `00`.
  - `$01:FA5C STA $85` resumes the event there, in the same bank. Verified on 4 consecutive texts in bank `$0A` (e.g. `$0A:895B` → returned `$898F` = start + 52).
  - So a relocated inline text must finish on its original `00`: old slot `FF 7F xx` (if any) + `{goto:new}` + `{nop}`… + original `00`; new copy = body + `{goto:<old 00>}`.
- **Message table list `010000`** is read only by `$01:EE57`/`$01:EE5D` (`LDA $028000,x` / `$028002,x`). The other byte match (`$1A:E691`) is data.
  - At runtime (7200 frames of Start/A), tables 0 and 11 were looked up through it.
  - Patching a list entry (24-bit) moves a table; its strings must share the table's bank (16-bit pointers).
