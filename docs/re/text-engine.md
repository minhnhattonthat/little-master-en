# Text engine

All addresses are SNES addresses in bank `$00` unless noted. Disassemble with `python lm.py dis <addr> --m16 --x16`.

## Pipeline

1. **Pointer lookup.** `$01:EE5B` reads the 24-bit table-of-tables at PC `010040` (`$36:8000`, `$36:8200`, `$37:8000`, `$37:8200`), then a 16-bit string pointer from that table (e.g. PC `1B0000`). The text pointer lives in DP `$14-$16`.
2. **Preprocessor** (`$00:B680-$00:BBB8`). Walks the source text and writes a render buffer at WRAM `$0400`:
   - `00`: end (`JMP $BBB8`).
   - `01-08 xx`: kanji. Writes `D0 <slot>` into the buffer and stores glyph index `(lead-1)<<8 | xx` in the slot table at `$0700 + 2*slot`, where slot = `$0A18 + $0A1A`.
   - `09-FE` (not `FF`): copied as-is.
   - `FF xx`: a control code.
     - `xx` in `00-7F` or `F1-FF`: 3 bytes `FF xx yy` copied for the renderer.
     - `xx` in `80-9C`: dispatch table `$B701` (4 bytes per entry, `JMP` + `NOP`). These run in the preprocessor: variables, numbers, names.
     - `xx` in `C0-F0`: conditional jump (`$BB33`). Arguments are a 3-byte text address. If the condition holds, `[$14]` is set to that address. **These embed text addresses, so relocating strings must rewrite them.**
3. **Renderer** (`$00:BE4F` loop). Reads the `$0400` buffer:
   - `00`: end (`$BF5E`).
   - `90`: newline (`$BF01`). Advances `$09FE` by 2 rows, scrolling via `$C27F` when it reaches `$09FA`.
   - `D0 n`: draws kanji slot n as tiles `$180 + 2n` and `+1` (two 8-px columns).
   - `CE`: no-op (skipped).
   - `FF xx yy`: renderer control (`$BF7D`, see below).
   - Anything else: `JSR $C156` draws **tile = char code** at the tilemap cursor. Each char is 8px wide and 16px tall (two tilemap rows). The column counter is `$09FC`.
   - Auto-wrap: when `$09FC-1 >= $09F8`, a newline is forced unless the next char is `91 。`, `93 」`, `94 、` or `A0 ー` (kinsoku: these hang past the edge).
   - After each char, if text speed `$0A0A` != 0, `JSR $C1B4` delays that many frames.

## Box geometry (RAM)

| Var | Meaning | Intro window (frame 900) |
|---|---|---|
| `$09F0` | origin column | 2 |
| `$09F2` | origin row | `$13` (19) |
| `$09F4` | width (cols) | `$1C` (28) |
| `$09F6` | height (rows) | 8 (= 4 text lines of 16 px) |
| `$09F8` | wrap column | `$1D` |
| `$09FA` | last row | `$1B` |
| `$09FC`/`$09FE` | cursor col/row | |
| `$0A02` | tilemap attribute (palette/priority) | `$2000` |
| `$0A0A` | text speed (frames/char) | 5 |

So the intro box holds **28 half-width chars x 4 lines**. With a fixed 8-px English font that is 28 Latin chars per line. A VWF would need dynamic tiles, the same mechanism kanji already use (`D0` slots → tiles `$180+`). This is the hook for M2.

## Control codes

Source format `FF xx [args]`. Table names are in `tbl/jp.tbl`. Argument counts come from the preprocessor.

### Renderer controls (3 bytes: `FF xx yy`)

| Code | Name | Behaviour |
|---|---|---|
| `FF 00-7F yy` | `{pXX:YY}` | set cursor: column = `xx & 1F` (`$09FC`); row from `yy` (`yy < 80`: row = `yy & 1F`, else adjust `$09FE` by `yy & 3F`) |
| `FF F1 yy` | `{cF1:YY}` | `yy=1`: clear `$0A1E`; else `$0A1F = (yy-1)*4 + $21`. Purpose not pinned (wrap/flag) |
| `FF F2 yy` | `{delay:YY}` | wait `yy` frames (`$C1B4`) |
| `FF FA yy` | `{cFA:YY}` | `INC $0A16`, then end of text |
| `FF FB yy` | `{color:YY}` | `$0A03 = yy*8 + $20` (tilemap palette bits) |
| `FF FC yy` | `{cFC:YY}` | `$0A12 = yy`, row arithmetic via `$C2A9` (layout helper, not pinned) |
| `FF FD yy` | `{speed:YY}` | text speed `$0A0A = yy` (`FF` = use the config value at `$7E:EA84`) |
| `FF FE yy` | `{scroll:YY}` | scroll the window one line (`$C27F`) |
| `FF FF yy` | `{clear:YY}` | clear the window and reset the cursor to the origin (`$01:ECE1`) |
| `FF F0, F3-F9` | – | unused by the renderer (ignored) |

### Preprocessor controls (`FF 80-9C`, dispatch `$B701`)

Helpers: `$BB65` reads 1 arg byte; `$BB71` reads a 3-byte pointer and adds var `$0A08`; `$BB91` reads a raw 3-byte pointer; `$BBA7` reads 2 bytes.

| Code | Args | Handler | Behaviour (as far as read) |
|---|---|---|---|
| 80 | 1 | B78D | var `$0A08` = imm |
| 81 | 3 | B79C | var = byte at [ptr] |
| 82 | 1 | B7AE | var *= imm (hardware multiply) |
| 83 | 3 | B7CB | prints a value from [ptr] via `$BCD6` |
| 84 | 3 | B7DD | prints a number (byte) |
| 85 | 3 | B810 | prints a number (compares with 100) |
| 86 | 3 | B94A | prints a single digit (clamped to 9) |
| 87 | 3 | B961 | copies a name from [ptr] until `00`/space (**variable-length insert**) |
| 88 | 4 | B97B | copies N bytes from [ptr] (arg0 = N) |
| 89 | 2 | B998 | var += imm16 |
| 8A, 8B | 2 | B9AB, B9CF | `$EEA1` lookups |
| 8C, 8D, 8E | 4 | BA38, BA6D, BAA6 | number/char with width or padding arg |
| 8F | 0 | BABA | save var to `$0A14` |
| 90 | 0 | BAC9 | var += `$0A14` |
| 91 | 3 | B85E | number |
| 92 | 3 | BADC | store var to [ptr] |
| 93 | 3 | BAE7 | var += [ptr] |
| 94 | 2 | BAFD | repeat char (arg1) arg0 times |
| 95 | 3 | B88B | number up to 4 digits (compares with 1000) |
| 96, 97 | 3 | BB12, B8E8 | value/name prints |
| 98, 99 | 3 | B8B7, B82D | name lookup via `$C26C` |
| 9A | 3 | B7F2 | `$BD0D` print |
| 9B | 1 | BB2A | `$0A20` = imm |
| 9C | 3 | B904 | `$B90F` print |

### Conditional jumps (`FF C0-F0`, 3-byte text address) → `{jXX:AAAAAA}`

`$BB33`: `n = xx & 3F`. If `n == $30`, jump when var `$0A08` == 0. Otherwise jump when `($54 & 3F) >= n` (the scenario/progress level). The target is a 24-bit SNES address of text.

## Menu/list drawing

Not traced yet: it needs in-game save states on the item menu and in battle, which M3 will capture. Known so far:
- Item records at PC `010052` are 32 bytes: two 10-byte name fields (`20`-padded) followed by stats.
- The single-byte font is the same tile set, so names drawn into menus use tile = char code.
- Many menu labels ("Save", "Attack", "Equip", "YES/NO"...) are already English graphics: kanji glyphs `7B2-7FF`.

## Dynamic tiles and VWF hooks (M2 spike, 2026-10-06)

- **Slot buffer:** `$7F:B000` holds 128 2bpp tiles (16 bytes each, byte `2r` = top row r in plane 0, byte `2r+1` = row r+8 in plane 1). It is uploaded to VRAM word `$6C00`, which is BG tiles `$180-$1FF`, when the NMI sees `$57 == $FE` (`$00:D927`, which also clears `$57`). Verified by poking a pattern and screenshotting: VRAM tile `$180` changed on the next frame.
- **`$57` is an exclusive NMI command**, not a set of flags (`$00:D51D`):
  - `0` = none.
  - `$FE` = slot tiles (`$D927`).
  - `$FF` = another `$7F` upload (`$D954`).
  - Any other non-zero value = text tilemap `$7E:9000` (`$D8F9`). `$C20E` requests it with `INC $57` followed by an NMI wait (`$00:E3BE` waits on `$4A`).
  - **So a writer must not leave `$FE` pending when the renderer's delay path INCs `$57`.** The VWF requests `$FE` and waits one frame with `JSL $00E3BE`.
- **Reserved slots:** `$0A1A` = slots already taken by window labels drawn as UI glyphs ("Message", "Caution", names...). New kanji go to slot `$0A18 + $0A1A`, i.e. tiles `$180 + 2*slot`.

  | State | `$0A1A` |
  |---|---|
  | field / battle / item | 2 |
  | personal info | 23 |
  | report | 0 |

  The VWF must use tiles from `$180 + 2*$0A1A` only, and must never clear below that.
- **Kanji copy is skipped** when `$0A18 == 0` (`$00:BBC6` → `JMP $BC75`). An all-English message leaves `$7F:B000` to the VWF.
- **Tilemap cursor:** offset = `2*$09FC + 64*(($09FE + $0A00) & 31)` (`$00:C233`).
- **Hook sites** all execute in every saved state (exec counts over 600 frames with A presses):
  - `$00:BE70` char path: 44-1008 runs.
  - `$00:BF01` newline: 1-3.
  - `$00:BF91` cursor set: 8-385 (VWF hooks `$BF94` instead: `$BF8C BEQ $BF94` targets it). These are heavy in menus and status screens.
  - `$01:ECE5` window clear: 2-17.
- **Free RAM:** `$7F:FF00-FF1F` saw no reads or writes in any state (600 frames each with A presses) or in a 3600-frame boot run.
- **Consequences for the VWF design:**
  - (1) Line slots of 32 cells start at tile `$180 + 2*$0A1A`, and there are `(128 - 2*$0A1A) / 32` of them. If that is fewer than the window's visible lines (`$09F6/2`), the window uses the fixed font. This is why personal info uses the fixed font for now.
  - (2) A cursor-set code inside a message switches the rest of that message to the fixed font. Positioned layouts are menus and captions.
  - (3) The per-message renderer start (`$00:BE43`) resets the VWF state.

### Single-byte font tiles double as UI graphics

`{cF1:yy}` (yy != 1) sets `$0A1F`, the tilemap attribute byte: palettes 4-7. Status screens, title bars and gauges draw
single-byte codes under those palettes as graphics (e.g. `ぞ`/`だ` = `$69`/`$6A` are the pink title bars, `ガ`/`ぽ`/`ギ`
the battle gauge; uppercase letters are the boxed stat labels). Codes `$0B-$1A`, `$26` and all of BG3 tiles `$000-$0FF`
are used the same way, so there are no free tiles for a separate lowercase set. The EN build therefore leaves the font as
shipped; the fixed-font char path (`vwf_dispatch` `.fixed`) draws `a-z` with the `A-Z` tiles and `_` as a space, but only
while `$0A1E` is 0 (default palette). In EN text, graphic kana are written as raw bytes (`[69]`); lint rejects lowercase
under a `{cF1}` palette.

