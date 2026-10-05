# Text encoding

Source of truth: `tbl/jp.tbl`. Verified by `tests/test_jp_table.py` (strings seen on screen + item names).

## How it was found

- `test/lua/trace_reads.lua` (Mesen2 headless) logged ROM reads with the reading PC during the intro.
- Kanji glyph reads come from `$00:BC0F` (32 bytes each, PC `020000+`). The string bytes are read by the preprocessor at `$00:B68D` from `$36:9759` (PC `1B1759`), reached via the pointer table at PC `1B0000` (see `pointers.md`).
- Single-byte codes were mapped by overwriting the intro string with code runs and screenshotting the result (`build/probe/*`, helper script kept out of repo).
- Control codes and their argument counts come from disassembling the preprocessor (`python lm.py dis 00B680`); see `text-engine.md`.

## Fonts

| Font | PC | Format | Glyphs |
|---|---|---|---|
| Kanji, 16x16 | `020000-02FFFF` | 1bpp, 32 bytes/glyph: left 8px column (16 bytes) then right column; **rows interlaced** (stored row r = screen row r//2 + 8*(r%2)). `python lm.py gfx --mode kanji16` | `000-7B1` = 1970 kanji; `7B2-7FF` = English UI label graphics ("Save", "Attack", "Equip", "YES/NO"...) |
| Single-byte, 8x16 | `170000` (4 KB, DMA'd by `$00:DFB5`) plus `018340` (2 KB) | 2bpp tiles, char = 2 tiles | codes `09-FE` |

The kanji font order is *roughly* JIS level-1 (by reading), with exceptions placed among them (聴 026, 秩 028, 猶 1DE, 逢 3BF, 互 44F) and out-of-order extras at `7A2-7B1` (琥珀蒼々維跳踏糧嗅僅褒讐繋託緒雰). That's why automatic JIS alignment drifted: the glyphs were transcribed by hand from sheets, then checked against decoded dialogue.

## Code ranges

| Bytes | Meaning |
|---|---|
| `00` | end of string |
| `01-08 xx` | kanji, glyph = (lead-1)*256 + xx |
| `09-FE` | single-byte char (except `D0`, an engine-internal "kanji slot" marker written into the RAM buffer; never in source text) |
| `90` | newline `{n}` (passed through to the renderer) |
| `FF xx ...` | control code; argument counts in `text-engine.md` |

Single-byte layout: `20` space, `21-3F` ASCII punctuation and digits (`2A`=×, `3C`=◀, `3E`=▶), `40`=©, `41-5A` A-Z, `5B-5F` ゃゅょっぇ, `60-78` voiced/semi-voiced hiragana, `79-8F` voiced/semi-voiced katakana (no ヂヅ), `91-9F` 。「」、・を + small katakana, `A0`=ー, `A1-CD` hiragana あ…ん, `CF`=§, `D1-FD` katakana ア…ン, `FE`=♪. `19`=ヲ, `1A`=ヴ, `1B`=‼, `1C`=‥, `1D`=～, `1F`=♡.

Unmapped (unidentified or decorative, decode as `[XX]`): `09-18`, `1E`, `24`, `3B`, `CE`. `10-17` render as fragments of decorative glyphs. If any of them appear in the script, `test_no_unknown_bytes_in_script` will flag them.

Space and padding: `20`. Fixed-width name fields (items at `010052`) are padded with `20`.
