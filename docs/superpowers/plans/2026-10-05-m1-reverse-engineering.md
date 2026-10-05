# M1: Reverse Engineering + Round-Trip Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python toolkit and finish the RE work so that every text block in the ROM dumps to `script/*.txt` and reinserts unchanged, giving a ROM byte-identical to the original.

**Architecture:**
- The `lmtools/` package holds small, single-purpose modules: ROM I/O, table codec, graphics dump, IPS, locate helpers, script format, blocks, and the Mesen2 runner.
- `lm.py` is a thin argparse CLI over these modules.
- RE findings live as data (`tbl/jp.tbl`, `data/blocks.json`) and notes (`docs/re/*.md`). Tests pin both.

**Tech Stack:**
- Python 3.12 with pytest 8 and Pillow 11 (both already installed).
- Mesen2, used for both the debugger and the headless `--testrunner` Lua mode. It needs .NET 8, which is already installed.

**Spec:** `docs/superpowers/specs/2026-10-05-little-master-translation-design.md`

**Scope:** this plan covers milestone **M1** only. M2 (font/VWF) through M6 each get their own plan, written once M1's findings exist. They depend on addresses and control codes this plan discovers.

## Global Constraints

- **Base ROM:** `rom/Little Master - Nijiiro no Maseki (Japan).sfc`, LoROM 2MB, SHA1 `75b76715d4a20371e0340dbeee3a51ff6a1dbad3`. Never modify any file in `rom/`.
- **Header checksum:** 0x409D at PC `0x7FDE`, complement 0xBF62 at `0x7FDC` (both verified).
- **Beta2** (`patch/LM3-Beta2.IPS`) is **reference only**. Use it to locate text and pointers. Never copy its code, assets or English text into project outputs.
- **Gitignored, never committed:** `rom/`, `patch/`, `tools/`, `build/`, `test/states/`, any `*.sfc/*.smc/*.ips/*.bps`.
- **Dependencies:** pytest, Pillow, stdlib only. Add no new pip packages.
- **Working directory:** run every command from the repo root `H:\translation\little-master`. Module paths like `tbl/jp.tbl` are relative to it.
- **Commit messages** end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **PC offsets** (file offsets) are written as 6-digit uppercase hex, e.g. `1B2307`. SNES addresses are written as `$36:A307`.

## Review Focus

1. **A byte not in `jp.tbl`** (an unmapped kanji, or junk) must round-trip as a `[XX]` escape. It must not crash or be dropped (Task 2 test `test_unknown_byte_roundtrips`).
2. **Two codes that draw the same glyph** must keep the original code on round-trip (Task 2 test `test_duplicate_value_keeps_original_code`).
3. **Pointers.** Several pointers to one string must stay shared after insert. A pointer into the middle of another string must raise a clear error, not corrupt silently (Task 9 `test_overlap_raises`, Task 11 `test_shared_pointer_preserved`).
4. **Files from a Windows editor** (UTF-8 BOM, CRLF) must parse the same, for both scripts and tables (Task 2 `test_load_bom_crlf`, Task 9 `test_tolerates_bom_crlf`).
5. **Wrong ROM input.** A headered `.smc` (extra 512 bytes) loads after stripping. A different ROM fails with a SHA1 message. Re-running `dump` must never overwrite EN translations (Task 1 `test_headered_rom_loads` / `test_wrong_rom_rejected`, Task 9 `test_save_refuses_to_clobber_translations`).

---

## File Structure

```
lm.py                      CLI: info gfx betadiff findptr findbytes freespace scan boot dump coverage roundtrip
pytest.ini
lmtools/__init__.py        (empty)
lmtools/rom.py             load_base, lorom_to_pc, pc_to_lorom, checksum, fix_checksum, expand
lmtools/tbl.py             Table: load, decode, encode
lmtools/gfx.py             tile_planar, glyph_linear, render
lmtools/ips.py             records, apply, regions
lmtools/locate.py          find_bytes, find_pointers, free_runs, scan_strings
lmtools/mesen.py           MESEN path, run(rom, script, out_dir)
lmtools/script.py          Entry, parse, serialize, save
lmtools/blocks.py          Block, load_blocks, pointers, dump_block, spans, insert_block
test/lua/boot.lua          headless boot smoke test
tests/conftest.py          `base` fixture
tests/test_*.py
tbl/jp.tbl                 Japanese decode table (RE output)
data/blocks.json           text block definitions (RE output)
data/beta2_nontext.json    Beta2 regions that aren't text (font/code/gfx)
tests/data/known_strings.json  on-screen-verified strings
docs/re/README.md          index of RE notes
docs/re/beta2-regions.md   generated region map
docs/re/encoding.md, text-engine.md, pointers.md, memory-map.md
script/<block>.txt         dumped script files
```

---

### Task 1: Project scaffold and ROM module

**Files:**
- Create: `pytest.ini`, `lmtools/__init__.py`, `lmtools/rom.py`, `lm.py`, `tests/conftest.py`
- Test: `tests/test_rom.py`

**Interfaces:**
- Produces:
  - `rom.BASE: Path`, `rom.SHA1: str`;
  - `rom.load_base(path=BASE) -> bytearray`;
  - `rom.lorom_to_pc(snes: int) -> int`, `rom.pc_to_lorom(pc: int) -> int` (bank without the $80 bit);
  - `rom.checksum(buf) -> int`, `rom.fix_checksum(buf: bytearray) -> None`;
  - pytest fixture `base -> bytes`;
  - `lm.py` with `build_parser()`. Each command is a `cmd_<name>(args)` function, registered with `sub.add_parser(...).set_defaults(fn=cmd_<name>)`.

- [ ] **Step 1: Write config and failing tests**

`pytest.ini`:
```ini
[pytest]
testpaths = tests
pythonpath = .
markers =
    mesen: needs the Mesen2 emulator in tools/mesen2
```

`lmtools/__init__.py`: empty file.

`tests/conftest.py`:
```python
import pytest
from lmtools import rom


@pytest.fixture(scope="session")
def base():
    return bytes(rom.load_base())
```

`tests/test_rom.py`:
```python
import pytest
from lmtools import rom


def test_base_loads(base):
    assert len(base) == 0x200000
    assert base[0x7FC0:0x7FCD] == b"LITTLE MASTER"


def test_checksum_matches_header(base):
    assert rom.checksum(bytearray(base)) == 0x409D


def test_fix_checksum_after_edit(base):
    b = bytearray(base)
    b[0x100000] ^= 1
    rom.fix_checksum(b)
    c = int.from_bytes(b[0x7FDE:0x7FE0], "little")
    assert c == rom.checksum(b)
    assert int.from_bytes(b[0x7FDC:0x7FDE], "little") ^ c == 0xFFFF


def test_lorom_conversion():
    assert rom.lorom_to_pc(0x008000) == 0
    assert rom.lorom_to_pc(0x368000) == 0x1B0000
    assert rom.lorom_to_pc(0xB68000) == 0x1B0000  # $80+ mirror
    assert rom.pc_to_lorom(0x1B2307) == 0x36A307
    with pytest.raises(ValueError):
        rom.lorom_to_pc(0x361234)


def test_headered_rom_loads(base, tmp_path):
    p = tmp_path / "h.smc"
    p.write_bytes(bytes(512) + base)
    assert rom.load_base(p) == base


def test_wrong_rom_rejected(tmp_path):
    p = tmp_path / "x.sfc"
    p.write_bytes(bytes(0x200000))
    with pytest.raises(ValueError, match="SHA1"):
        rom.load_base(p)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_rom.py -v`
Expected: errors with `ImportError: cannot import name 'rom'` or `ModuleNotFoundError`.

- [ ] **Step 3: Implement `lmtools/rom.py`**

```python
"""Base ROM loading and LoROM address/checksum helpers."""
import hashlib
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "rom" / "Little Master - Nijiiro no Maseki (Japan).sfc"
SHA1 = "75b76715d4a20371e0340dbeee3a51ff6a1dbad3"


def load_base(path=BASE) -> bytearray:
    data = Path(path).read_bytes()
    if len(data) % 0x8000 == 512:  # copier header
        data = data[512:]
    got = hashlib.sha1(data).hexdigest()
    if got != SHA1:
        raise ValueError(f"{path}: SHA1 {got} != expected {SHA1} (need the unheadered Japan ROM)")
    return bytearray(data)


def lorom_to_pc(snes: int) -> int:
    addr = snes & 0xFFFF
    if addr < 0x8000:
        raise ValueError(f"{snes:06X} is not a LoROM ROM address")
    return ((snes >> 16) & 0x7F) * 0x8000 + addr - 0x8000


def pc_to_lorom(pc: int) -> int:
    return (pc // 0x8000) << 16 | 0x8000 | pc % 0x8000


def checksum(buf) -> int:
    # ponytail: plain sum, valid only for power-of-two ROM sizes (2MB/4MB are all we use)
    return (sum(buf) - sum(buf[0x7FDC:0x7FE0]) + 0x1FE) & 0xFFFF


def fix_checksum(buf: bytearray) -> None:
    c = checksum(buf)
    buf[0x7FDC:0x7FE0] = (c ^ 0xFFFF).to_bytes(2, "little") + c.to_bytes(2, "little")
```

- [ ] **Step 4: Create `lm.py`**

```python
"""Little Master translation toolkit. Run from repo root: python lm.py <command> -h"""
import argparse
import sys
from pathlib import Path

from lmtools import rom


def cmd_info(a):
    b = rom.load_base()
    print(f"base ROM ok: {len(b):#x} bytes, checksum {rom.checksum(b):04X}")


def build_parser():
    ap = argparse.ArgumentParser(prog="lm")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(fn=cmd_info)
    return ap


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.fn(args)
```

- [ ] **Step 5: Run the tests and the CLI**

Run: `python -m pytest tests/test_rom.py -v`, then `python lm.py info`.
Expected: 6 passed. The CLI prints `base ROM ok: 0x200000 bytes, checksum 409D`.

- [ ] **Step 6: Commit**

```bash
git add pytest.ini lm.py lmtools tests
git commit -m "Add ROM module and CLI scaffold

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Table codec

**Files:**
- Create: `lmtools/tbl.py`
- Test: `tests/test_tbl.py`

**Interfaces:**
- Produces:
  - `Table(lines: list[str])` and `Table.load(path) -> Table`;
  - `Table.decode(data, pos=0, length=None, maxlen=4096) -> tuple[str, int]` (text, bytes consumed);
  - `Table.encode(text: str) -> bytes`;
  - the attribute `Table.ctrl_enc: dict[str, tuple[bytes, int]]` (control name → code, arg count).
- **Table file format**, one entry per line:
  - `HEX=char` for a character (keys can be multi-byte, e.g. `8142=漢`);
  - `HEX={name}` for a control code with no arguments;
  - `HEX={name:N}` for a control code with N argument bytes;
  - `{end}` is the string terminator;
  - `#` starts a comment line.
- **Decoded text format:**
  - characters as-is;
  - controls as `{name}` or `{name:AABB}` (argument bytes in hex);
  - unmapped bytes as `[XX]`.
- When several codes map to the same character, the first one in the file is canonical. Any later duplicate code decodes as `[XX]`, so the round-trip stays exact.

- [ ] **Step 1: Write failing tests** in `tests/test_tbl.py`

```python
import pytest
from lmtools.tbl import Table

T = Table(["41=A", "42=B", "8142=漢", "43=A", "3D==", "F0={n}", "F5={color:1}", "FF={end}"])


def test_decode_chars_and_end():
    assert T.decode(b"AB\xf0\xff") == ("AB{n}{end}", 4)


def test_decode_stops_at_end():
    assert T.decode(b"\x00A\xffB\xff", 1) == ("A{end}", 2)


def test_multibyte_key_greedy():
    assert T.decode(b"\x81\x42\x42\xff") == ("漢B{end}", 4)


def test_control_with_arg_roundtrips():
    assert T.decode(b"\xf5\x03A\xff") == ("{color:03}A{end}", 4)
    assert T.encode("{color:03}A{end}") == b"\xf5\x03A\xff"


def test_unknown_byte_roundtrips():
    assert T.decode(b"\x99\xff") == ("[99]{end}", 2)
    assert T.encode("[99]{end}") == b"\x99\xff"


def test_duplicate_value_keeps_original_code():
    assert T.decode(b"\x43\xff") == ("[43]{end}", 2)
    assert T.encode("[43]A{end}") == b"\x43\x41\xff"


def test_equals_sign_value():
    assert T.decode(b"\x3d\xff") == ("={end}", 2)


def test_fixed_length_decode():
    assert T.decode(b"AB\x20", 0, 2) == ("AB", 2)


def test_missing_end_raises():
    with pytest.raises(ValueError):
        T.decode(b"AB")


def test_encode_errors():
    with pytest.raises(ValueError, match="unencodable"):
        T.encode("Z")
    with pytest.raises(ValueError, match="arg bytes"):
        T.encode("{color}")
    with pytest.raises(ValueError, match="unknown control"):
        T.encode("{nope}")


def test_load_bom_crlf(tmp_path):
    p = tmp_path / "t.tbl"
    p.write_bytes("\ufeff# c\r\n41=A\r\nFF={end}\r\n".encode("utf-8"))
    assert Table.load(p).decode(b"A\xff") == ("A{end}", 2)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_tbl.py -v`
Expected: fails with `ModuleNotFoundError: No module named 'lmtools.tbl'`.

- [ ] **Step 3: Implement `lmtools/tbl.py`**

```python
"""Thingy-style table codec with control codes, hex escapes and multi-byte keys."""
import re
from pathlib import Path

CTRL = re.compile(r"\{(\w+)(?::(\d+))?\}$")
TOKEN = re.compile(r"\{(\w+)(?::([0-9A-Fa-f]*))?\}|\[([0-9A-Fa-f]{2})\]")


class Table:
    def __init__(self, lines):
        self.dec, self.ctrl, self.enc, self.ctrl_enc = {}, {}, {}, {}
        for n, line in enumerate(lines, 1):
            line = line.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            key, sep, val = line.partition("=")
            if not sep or not val:
                raise ValueError(f"table line {n}: bad entry {line!r}")
            code = bytes.fromhex(key)
            m = CTRL.match(val)
            if m:
                argc = int(m[2] or 0)
                self.ctrl[code] = (m[1], argc)
                self.ctrl_enc.setdefault(m[1], (code, argc))
            else:
                self.dec[code] = val
                self.enc.setdefault(val, code)
        self.keylen = max(map(len, (*self.dec, *self.ctrl)), default=1)
        self.vallen = max(map(len, self.enc), default=1)

    @classmethod
    def load(cls, path):
        return cls(Path(path).read_text(encoding="utf-8-sig").splitlines())

    def decode(self, data, pos=0, length=None, maxlen=4096):
        """length=None: decode through {end}. Else decode exactly `length` bytes. Returns (text, consumed)."""
        start, out = pos, []
        stop = len(data) if length is None else pos + length
        while pos < stop:
            if length is None and pos - start >= maxlen:
                raise ValueError(f"no {{end}} within {maxlen} bytes of {start:#x}")
            for k in range(min(self.keylen, stop - pos), 0, -1):
                code = bytes(data[pos:pos + k])
                if code in self.ctrl:
                    name, argc = self.ctrl[code]
                    args = bytes(data[pos + k:pos + k + argc])
                    pos += k + argc
                    out.append(f"{{{name}:{args.hex().upper()}}}" if argc else f"{{{name}}}")
                    if name == "end" and length is None:
                        return "".join(out), pos - start
                    break
                if self.enc.get(self.dec.get(code)) == code:
                    out.append(self.dec[code])
                    pos += k
                    break
            else:
                out.append(f"[{data[pos]:02X}]")
                pos += 1
        if length is None:
            raise ValueError(f"ran off end of data decoding from {start:#x}")
        return "".join(out), pos - start

    def encode(self, text: str) -> bytes:
        out, i = bytearray(), 0
        while i < len(text):
            m = TOKEN.match(text, i)
            if m:
                if m[3]:
                    out.append(int(m[3], 16))
                else:
                    if m[1] not in self.ctrl_enc:
                        raise ValueError(f"unknown control {{{m[1]}}} at {i} in {text!r}")
                    code, argc = self.ctrl_enc[m[1]]
                    args = bytes.fromhex(m[2] or "")
                    if len(args) != argc:
                        raise ValueError(f"{{{m[1]}}} needs {argc} arg bytes at {i} in {text!r}")
                    out += code + args
                i = m.end()
                continue
            for k in range(min(self.vallen, len(text) - i), 0, -1):
                if text[i:i + k] in self.enc:
                    out += self.enc[text[i:i + k]]
                    i += k
                    break
            else:
                raise ValueError(f"unencodable {text[i]!r} at {i} in {text!r}")
        return bytes(out)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_tbl.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add lmtools/tbl.py tests/test_tbl.py
git commit -m "Add table codec with control codes and hex escapes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Graphics dumper

**Files:**
- Create: `lmtools/gfx.py`
- Modify: `lm.py` (add `cmd_gfx` and register it)
- Test: `tests/test_gfx.py`

**Interfaces:**
- Produces:
  - `tile_planar(data: bytes, bpp: int) -> list[list[int]]` (one 8×8 tile, bpp 1/2/4);
  - `glyph_linear(data: bytes, w: int, h: int) -> list[list[int]]` (row-major 1bpp);
  - `render(rom, offset, count, mode="tile", bpp=1, w=8, h=8, cols=16, scale=3, label=None) -> PIL.Image`.
- CLI: `python lm.py gfx --offset 0x20C3C --count 256 --mode linear --w 16 --h 16 --label 0 --out build/x.png`

- [ ] **Step 1: Write failing tests** in `tests/test_gfx.py`

```python
from lmtools import gfx


def test_tile_planar_2bpp():
    data = bytes([0x80, 0x80] + [0] * 14)
    px = gfx.tile_planar(data, 2)
    assert px[0][0] == 3 and px[0][1] == 0 and px[1][0] == 0


def test_tile_planar_4bpp_high_planes():
    data = bytes(16) + bytes([0x80, 0x00] + [0] * 14)
    assert gfx.tile_planar(data, 4)[0][0] == 4


def test_glyph_linear_16():
    data = bytes([0x80, 0x01] + [0] * 30)
    px = gfx.glyph_linear(data, 16, 16)
    assert px[0][0] == 1 and px[0][15] == 1 and px[0][1] == 0 and px[1][0] == 0


def test_render_size():
    img = gfx.render(bytes(32 * 20), 0, 20, mode="linear", w=16, h=16, cols=8, scale=2, label=0)
    assert img.size == (8 * (16 * 2 + 2), 3 * (16 * 2 + 2 + 10))
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_gfx.py -v`
Expected: fails with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `lmtools/gfx.py`**

```python
"""Render ROM graphics (SNES planar tiles or linear 1bpp glyphs) to a labelled PNG sheet."""
from PIL import Image, ImageDraw


def tile_planar(data: bytes, bpp: int) -> list[list[int]]:
    rows = []
    for r in range(8):
        planes = [data[r]] if bpp == 1 else [data[2 * r], data[2 * r + 1]]
        if bpp == 4:
            planes += [data[16 + 2 * r], data[17 + 2 * r]]
        rows.append([sum(((p >> (7 - x)) & 1) << i for i, p in enumerate(planes)) for x in range(8)])
    return rows


def glyph_linear(data: bytes, w: int, h: int) -> list[list[int]]:
    bpr = (w + 7) // 8
    return [[(data[y * bpr + x // 8] >> (7 - x % 8)) & 1 for x in range(w)] for y in range(h)]


def render(rom, offset, count, mode="tile", bpp=1, w=8, h=8, cols=16, scale=3, label=None):
    if mode == "tile":
        w = h = 8
        size, maxv = 8 * bpp, (1 << bpp) - 1
    else:
        size, maxv = (w + 7) // 8 * h, 1
    lab = 10 if label is not None else 0
    cw, ch = w * scale + 2, h * scale + 2 + lab
    img = Image.new("L", (cols * cw, (count + cols - 1) // cols * ch), 128)
    d = ImageDraw.Draw(img)
    for i in range(count):
        data = bytes(rom[offset + i * size:offset + (i + 1) * size])
        if len(data) < size:
            break
        px = tile_planar(data, bpp) if mode == "tile" else glyph_linear(data, w, h)
        ox, oy = i % cols * cw + 1, i // cols * ch + 1 + lab
        for y, row in enumerate(px):
            for x, v in enumerate(row):
                d.rectangle([ox + x * scale, oy + y * scale, ox + (x + 1) * scale - 1, oy + (y + 1) * scale - 1],
                            fill=255 - v * 255 // maxv)
        if lab:
            d.text((ox, oy - lab), f"{label + i:X}", fill=0)
    return img
```

- [ ] **Step 4: Add the CLI command to `lm.py`**

Add the import `from lmtools import gfx` and this function above `build_parser`:
```python
def cmd_gfx(a):
    img = gfx.render(rom.load_base(), int(a.offset, 0), a.count, a.mode, a.bpp, a.w, a.h, a.cols, a.scale,
                     None if a.label is None else int(a.label, 0))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(a.out)
    print(f"wrote {a.out}")
```
Register it inside `build_parser`:
```python
    p = sub.add_parser("gfx", help="render ROM graphics to PNG")
    p.add_argument("--offset", required=True)
    p.add_argument("--count", type=int, default=256)
    p.add_argument("--mode", choices=["tile", "linear"], default="tile")
    p.add_argument("--bpp", type=int, choices=[1, 2, 4], default=1)
    p.add_argument("--w", type=int, default=8)
    p.add_argument("--h", type=int, default=8)
    p.add_argument("--cols", type=int, default=16)
    p.add_argument("--scale", type=int, default=3)
    p.add_argument("--label", help="label first glyph with this number (hex ok)")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_gfx)
```

- [ ] **Step 5: Run the tests and a smoke run**

Run: `python -m pytest tests/test_gfx.py -v`, then `python lm.py gfx --offset 0x20C3C --count 64 --mode linear --w 16 --h 16 --label 0 --out build/smoke.png`
Expected: 4 passed. Open `build/smoke.png` with the Read tool: a labelled grid of glyphs should appear. Readable kanji confirm a 1bpp 16×16 font; noise means the format is different, which Task 7 investigates.

- [ ] **Step 6: Commit**

```bash
git add lmtools/gfx.py lm.py tests/test_gfx.py
git commit -m "Add graphics sheet dumper

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: IPS reader and Beta2 region map

**Files:**
- Create: `lmtools/ips.py`, generated `docs/re/beta2-regions.md`
- Modify: `lm.py` (add `cmd_betadiff`)
- Test: `tests/test_ips.py`

**Interfaces:**
- Produces:
  - `ips.records(patch: bytes) -> list[tuple[int, bytes]]`;
  - `ips.apply(rom, patch) -> bytearray`;
  - `ips.regions(recs, gap=0x40) -> list[tuple[int, int]]` (start, end exclusive, merged when the gap ≤ `gap`).

- [ ] **Step 1: Write failing tests** in `tests/test_ips.py`

```python
import pytest
from lmtools import ips

PATCH = b"PATCH" + b"\x00\x00\x02\x00\x02AB" + b"\x00\x00\x10\x00\x00\x00\x03Z" + b"\x00\x00\x30\x00\x01Q" + b"EOF"


def test_records_with_rle():
    assert ips.records(PATCH) == [(2, b"AB"), (0x10, b"ZZZ"), (0x30, b"Q")]


def test_apply_extends_rom():
    out = ips.apply(bytes(0x20), PATCH)
    assert len(out) == 0x31 and out[2:4] == b"AB" and out[0x10:0x13] == b"ZZZ" and out[0x30] == ord("Q")


def test_regions_merge_by_gap():
    assert ips.regions(ips.records(PATCH), gap=0x08) == [(2, 4), (0x10, 0x13), (0x30, 0x31)]
    assert ips.regions(ips.records(PATCH), gap=0x20) == [(2, 0x31)]


def test_bad_patch():
    with pytest.raises(ValueError):
        ips.records(b"NOPE")
    with pytest.raises(ValueError):
        ips.records(b"PATCH\x00\x00")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_ips.py -v`
Expected: fails with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `lmtools/ips.py`**

```python
"""Read/apply IPS patches (used to map what Beta2 changed; Beta2 is reference only)."""


def records(patch: bytes) -> list[tuple[int, bytes]]:
    if patch[:5] != b"PATCH":
        raise ValueError("not an IPS patch")
    i, out = 5, []
    while patch[i:i + 3] != b"EOF":
        if i + 5 > len(patch):
            raise ValueError("truncated IPS patch")
        off, n = int.from_bytes(patch[i:i + 3], "big"), int.from_bytes(patch[i + 3:i + 5], "big")
        i += 5
        if n == 0:
            out.append((off, patch[i + 2:i + 3] * int.from_bytes(patch[i:i + 2], "big")))
            i += 3
        else:
            out.append((off, patch[i:i + n]))
            i += n
    return out


def apply(rom, patch: bytes) -> bytearray:
    out = bytearray(rom)
    for off, data in records(patch):
        if off + len(data) > len(out):
            out += bytes(off + len(data) - len(out))
        out[off:off + len(data)] = data
    return out


def regions(recs, gap=0x40) -> list[tuple[int, int]]:
    reg = []
    for off, data in sorted(recs):
        end = off + len(data)
        if reg and off <= reg[-1][1] + gap:
            reg[-1][1] = max(reg[-1][1], end)
        else:
            reg.append([off, end])
    return [tuple(r) for r in reg]
```

- [ ] **Step 4: Add `cmd_betadiff` to `lm.py`**

Add the import `from lmtools import ips` and:
```python
BETA2 = Path("patch/LM3-Beta2.IPS")


def cmd_betadiff(a):
    base = rom.load_base()
    patched = ips.apply(base, BETA2.read_bytes())
    lines = ["# Beta2 changed regions (generated by `python lm.py betadiff`)", "",
             "Reference only. ASCII preview is of Beta2's bytes.", "",
             "| start | end | size | preview |", "|---|---|---|---|"]
    for s, e in ips.regions(ips.records(BETA2.read_bytes())):
        prev = "".join(chr(c) if 32 <= c < 127 and chr(c) not in "|`" else "." for c in patched[s:s + 24])
        lines.append(f"| {s:06X} | {e:06X} | {e - s} | `{prev}` |")
    Path("docs/re").mkdir(parents=True, exist_ok=True)
    Path("docs/re/beta2-regions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote docs/re/beta2-regions.md ({len(lines) - 6} regions)")
```
Register: `sub.add_parser("betadiff", help="map regions Beta2 changed").set_defaults(fn=cmd_betadiff)`

- [ ] **Step 5: Run the tests and generate the map**

Run: `python -m pytest tests/test_ips.py -v`, then `python lm.py betadiff`
Expected: 4 passed. The command reports about 150 regions. The table should include `020C3C | 02F68F` and `1B2307`-area rows.

- [ ] **Step 6: Commit**

```bash
git add lmtools/ips.py lm.py tests/test_ips.py docs/re/beta2-regions.md
git commit -m "Add IPS reader and Beta2 region map

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Locate helpers (bytes, pointers, free space, string scan)

**Files:**
- Create: `lmtools/locate.py`
- Modify: `lm.py` (add `cmd_findbytes`, `cmd_findptr`, `cmd_freespace`, `cmd_scan`)
- Test: `tests/test_locate.py`

**Interfaces:**
- Consumes: `rom.pc_to_lorom`, `Table.decode`, `Table.ctrl_enc["end"]`
- Produces:
  - `find_bytes(rom, needle: bytes) -> list[int]` (overlapping matches);
  - `find_pointers(rom, pc) -> list[tuple[int, int]]` (offset, width 2 or 3);
  - `free_runs(rom, min_len=0x100) -> list[tuple[int, int, int]]` (start, length, fill byte);
  - `scan_strings(rom, tbl, min_chars=4, exclude=()) -> list[tuple[int, str]]`.

- [ ] **Step 1: Write failing tests** in `tests/test_locate.py`

```python
from lmtools import locate
from lmtools.tbl import Table


def test_find_bytes_overlapping():
    assert locate.find_bytes(b"aaaa", b"aa") == [0, 1, 2]


def test_find_pointers_16_and_24():
    rom = bytearray(0x100)
    rom[0x10:0x12] = (0xA307).to_bytes(2, "little")
    rom[0x20:0x23] = (0x36A307).to_bytes(3, "little")
    rom[0x30:0x33] = (0xB6A307).to_bytes(3, "little")
    hits = locate.find_pointers(rom, 0x1B2307)
    assert (0x10, 2) in hits and (0x20, 3) in hits and (0x30, 3) in hits


def test_free_runs():
    rom = b"\x01" * 8 + b"\xff" * 0x200 + b"\x02" + b"\x00" * 0x50
    assert locate.free_runs(rom, 0x100) == [(8, 0x200, 0xFF)]


def test_scan_strings():
    t = Table(["41=A", "42=B", "FF={end}"])
    rom = b"AAAAB\xff\x99\x99\xffAB\xffBBBB\xff"
    assert locate.scan_strings(rom, t, min_chars=4) == [(0, "AAAAB{end}"), (12, "BBBB{end}")]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_locate.py -v`
Expected: fails with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `lmtools/locate.py`**

```python
"""Helpers for finding text, pointers and free space in the ROM."""
import re

from .rom import pc_to_lorom

TAG = re.compile(r"\{[^}]*\}")


def find_bytes(rom, needle: bytes) -> list[int]:
    return [m.start() for m in re.finditer(b"(?=" + re.escape(needle) + b")", rom)]


def find_pointers(rom, pc) -> list[tuple[int, int]]:
    v = pc_to_lorom(pc)
    hits = [(o, 2) for o in find_bytes(rom, (v & 0xFFFF).to_bytes(2, "little"))]
    for hi in (0, 0x800000):
        hits += [(o, 3) for o in find_bytes(rom, (v | hi).to_bytes(3, "little"))]
    return sorted(set(hits))


def free_runs(rom, min_len=0x100) -> list[tuple[int, int, int]]:
    pat = rb"\x00{%d,}|\xff{%d,}" % (min_len, min_len)
    return [(m.start(), len(m[0]), m[0][0]) for m in re.finditer(pat, rom)]


def scan_strings(rom, tbl, min_chars=4, exclude=()) -> list[tuple[int, str]]:
    """Heuristic: strings start at 0 or right after an {end} code; keep fully-decodable ones."""
    end = tbl.ctrl_enc["end"][0]
    out = []
    for s in [0] + [m.start() + len(end) for m in re.finditer(re.escape(end), rom)]:
        if any(a <= s < b for a, b in exclude):
            continue
        try:
            text, _ = tbl.decode(rom, s, maxlen=256)
        except ValueError:
            continue
        if "[" not in text and len(TAG.sub("", text)) >= min_chars:
            out.append((s, text))
    return out
```

- [ ] **Step 4: Add the CLI commands to `lm.py`**

Add the imports `from lmtools import locate` and `from lmtools.tbl import Table`, then:
```python
def cmd_findbytes(a):
    for o in locate.find_bytes(rom.load_base(), bytes.fromhex(a.hex)):
        print(f"{o:06X}  ${rom.pc_to_lorom(o):06X}")


def cmd_findptr(a):
    b = rom.load_base()
    for o, w in locate.find_pointers(b, int(a.pc, 16)):
        print(f"{o:06X} w{w}  context: {bytes(b[max(o - 4, 0):o + 8]).hex(' ')}")


def cmd_freespace(a):
    for s, n, f in locate.free_runs(rom.load_base(), int(a.min, 0)):
        print(f"{s:06X}-{s + n:06X}  {n:6d} bytes of {f:02X}")


def cmd_scan(a):
    for s, text in locate.scan_strings(rom.load_base(), Table.load("tbl/jp.tbl"), a.min):
        print(f"{s:06X}  {text}")
```
Register:
```python
    p = sub.add_parser("findbytes"); p.add_argument("hex"); p.set_defaults(fn=cmd_findbytes)
    p = sub.add_parser("findptr", help="find pointers to a PC offset (hex)"); p.add_argument("pc"); p.set_defaults(fn=cmd_findptr)
    p = sub.add_parser("freespace"); p.add_argument("--min", default="0x100"); p.set_defaults(fn=cmd_freespace)
    p = sub.add_parser("scan", help="heuristic text scan using tbl/jp.tbl"); p.add_argument("--min", type=int, default=4); p.set_defaults(fn=cmd_scan)
```

- [ ] **Step 5: Run the tests and a smoke run**

Run: `python -m pytest tests/test_locate.py -v`, then `python lm.py findptr 1B2307` and `python lm.py freespace`
Expected: 4 passed. Both commands print lists; nothing has to match a particular result yet.

- [ ] **Step 6: Commit**

```bash
git add lmtools/locate.py lm.py tests/test_locate.py
git commit -m "Add byte/pointer/free-space/string locate helpers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Mesen2 install and headless harness

**Files:**
- Create: `lmtools/mesen.py`, `test/lua/boot.lua`
- Modify: `lm.py` (add `cmd_boot`)
- Test: `tests/test_mesen.py`

**Interfaces:**
- Produces:
  - `mesen.MESEN: Path` (`tools/mesen2/Mesen.exe`);
  - `mesen.run(rom_path, script: str, out_dir, timeout=120) -> int` (the exit code). `script` is a filename under `test/lua/`. The runner prepends a line defining the Lua global `OUT_DIR`.

- [ ] **Step 1: Download Mesen2**

From https://github.com/SourMesen/Mesen2/releases, download the latest Windows x64 zip (it needs .NET 8, which is installed). Unzip it so that `tools/mesen2/Mesen.exe` exists. Run it once in GUI mode so it creates its settings, then close it.

- [ ] **Step 2: Check the Lua API names**

Open Mesen2's Lua API reference (https://www.mesen.ca/docs/ → Debugging → Script Window → API reference, or the in-app Help in the Script Window). Confirm these names and signatures:
- `emu.addEventCallback(fn, emu.eventType.endFrame)`;
- `emu.takeScreenshot()`, which returns PNG bytes;
- `emu.getScreenBuffer()`, which returns an ARGB int array;
- `emu.stop(exitCode)`;
- the `--testrunner` command-line switch.

If any name differs, use the documented name in Step 4 and note it in `docs/re/README.md` under "Tooling".

- [ ] **Step 3: Write the failing test** in `tests/test_mesen.py`

```python
import pytest
from lmtools import mesen, rom

pytestmark = [pytest.mark.mesen,
              pytest.mark.skipif(not mesen.MESEN.exists(), reason="Mesen2 not installed")]


def test_base_rom_boots(tmp_path):
    assert mesen.run(rom.BASE, "boot.lua", tmp_path) == 0
    assert (tmp_path / "boot.png").stat().st_size > 0
```

Run: `python -m pytest tests/test_mesen.py -v`
Expected: fails with `ModuleNotFoundError: lmtools.mesen`. Skipped is **not** acceptable on this machine.

- [ ] **Step 4: Implement the harness**

`lmtools/mesen.py`:
```python
"""Run Mesen2 headless with a Lua script from test/lua/."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MESEN = ROOT / "tools" / "mesen2" / "Mesen.exe"


def run(rom_path, script: str, out_dir, timeout=120) -> int:
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    lua = out_dir / "_run.lua"
    lua.write_text(f"OUT_DIR = [[{out_dir}]]\n" + (ROOT / "test" / "lua" / script).read_text(encoding="utf-8"),
                   encoding="utf-8")
    return subprocess.run([str(MESEN), "--testrunner", str(Path(rom_path).resolve()), str(lua)],
                          timeout=timeout).returncode
```

`test/lua/boot.lua`:
```lua
-- Boot smoke test: run 900 frames (~15 s), save a screenshot, fail if the screen is black.
local frame = 0
emu.addEventCallback(function()
  frame = frame + 1
  if frame == 900 then
    local f = io.open(OUT_DIR .. "/boot.png", "wb")
    f:write(emu.takeScreenshot())
    f:close()
    local buf, lit = emu.getScreenBuffer(), 0
    for i = 1, #buf, 97 do
      if (buf[i] & 0xFFFFFF) ~= 0 then lit = lit + 1 end
    end
    emu.stop(lit > 0 and 0 or 1)
  end
end, emu.eventType.endFrame)
```

Add `cmd_boot` to `lm.py` (with the import `from lmtools import mesen`):
```python
def cmd_boot(a):
    code = mesen.run(a.rom or rom.BASE, "boot.lua", "build/shots")
    print("boot OK, see build/shots/boot.png" if code == 0 else f"boot FAILED (exit {code})")
    sys.exit(code)
```
Register: `p = sub.add_parser("boot"); p.add_argument("rom", nargs="?"); p.set_defaults(fn=cmd_boot)`

- [ ] **Step 5: Run the test**

Run: `python -m pytest tests/test_mesen.py -v`
Expected: 1 passed. Check `boot.png` with the Read tool; it should show the title screen or intro. If `io.open` returns nil, enable "Allow access to I/O and OS functions" in Mesen2's Script Window settings and re-run. If the screen is still black at frame 900, raise the frame count until the title screen appears.

- [ ] **Step 6: Commit**

```bash
git add lmtools/mesen.py test/lua/boot.lua lm.py tests/test_mesen.py
git commit -m "Add Mesen2 headless boot harness

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: RE — fonts and character encoding → `tbl/jp.tbl`

Investigative task. The deliverables are data plus notes, pinned by tests.

**Files:**
- Create: `tbl/jp.tbl`, `docs/re/encoding.md`, `tests/data/known_strings.json`, `tests/test_jp_table.py`
- Local only, gitignored: save states in `test/states/`

**Interfaces:**
- Produces:
  - `tbl/jp.tbl`, which has every character code in the game. Control codes are added in Task 8; for now include `{end}` once its byte is known.
  - `tests/data/known_strings.json`: `[{"pc": "HEX", "length": N | null, "text": "..."}]`. `length` is used for fixed-length fields; `null` means the string is terminated by `{end}`.

- [ ] **Step 1: Capture reference screens**

1. In the Mesen2 GUI, play from New Game to the first dialogue box.
2. Save state to `test/states/first_text.mss`. Also save states on the item menu (`items.mss`) and in a battle with a message showing (`battle.mss`).
3. Screenshot each one to `build/shots/ref_*.png`.

- [ ] **Step 2: Find the glyph format and the font's ROM location**

1. On `first_text`, open Debug → Tile Viewer. Find the text tiles and note their bpp and glyph size (8×8, 12×12 or 16×16).
2. Open Debug → Event Viewer or the debugger, and set a breakpoint on VRAM writes to that tile address. Advance one character, then follow the source back to the ROM read (DMA source register, or the CPU loop's `LDA [ptr],Y`).
3. Record the font base PC offset and the glyph-address formula (e.g. `glyph = base + (code - 0x20) * 32`). That gives the code → glyph mapping.
4. Repeat for every font. Expect a kana or small font for single-byte codes and the 1bpp kanji font near `020C3C` for multi-byte codes.

- [ ] **Step 3: Dump the labelled font sheets**

For each font, run `python lm.py gfx` with the found offset, mode and size. Pass `--label <first code>` so each glyph is labelled with the code that selects it, per the formula from Step 2. Example:
`python lm.py gfx --offset 0x20C3C --count 512 --mode linear --w 16 --h 16 --label 0x8000 --out build/font_kanji.png`
Check each sheet with the Read tool.

- [ ] **Step 4: Transcribe `tbl/jp.tbl`**

1. Write one line per code, in the format `CODE=字`.
2. Use full-width characters as the original shows them; the space code is `　` or ` `, whichever matches the glyph.
3. Mark doubtful glyphs with a comment on the line above, e.g. `# ? 8123 could be 剣/険, context: weapon names`. Resolve them in Step 6 using in-game context.
4. Begin the file with the header `# Little Master JP table. Format: HEX=char, HEX={ctrl} or {ctrl:N}. See docs/re/encoding.md`.

- [ ] **Step 5: Write the known strings and the test**

Fill `tests/data/known_strings.json` with at least 6 strings read off the reference screenshots:
- item 0's name at `010052` (length 10). Beta2 calls it "Club", so it is expected to decode to `こんぼう`; trust the item-menu screenshot if it differs;
- the first dialogue line (found with `python lm.py findbytes` on its encoded bytes);
- a battle message;
- a line that contains kanji;
- a menu label.

`tests/test_jp_table.py`:
```python
import json
from pathlib import Path

from lmtools.tbl import Table

T = Table.load("tbl/jp.tbl")


def test_known_strings(base):
    for s in json.loads(Path("tests/data/known_strings.json").read_text(encoding="utf-8")):
        text, _ = T.decode(base, int(s["pc"], 16), s["length"])
        assert text.rstrip() == s["text"], s["pc"]


def test_table_has_end():
    assert "end" in T.ctrl_enc
```

Run: `python -m pytest tests/test_jp_table.py -v`
Expected: PASS. A failure points to the wrong code in `jp.tbl`; fix the table, not the test data.

- [ ] **Step 6: Write `docs/re/encoding.md`**

Cover:
- each font's PC offset, format, glyph size and count;
- the code → glyph formula;
- the single-byte vs multi-byte code ranges, and how the engine tells them apart;
- the space and padding bytes;
- any doubtful glyphs that remain, and how each was resolved.

- [ ] **Step 7: Commit**

```bash
git add tbl/jp.tbl docs/re/encoding.md tests/data/known_strings.json tests/test_jp_table.py
git commit -m "RE: font locations and JP character table

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: RE — text engine and control codes

**Files:**
- Create: `docs/re/text-engine.md`
- Modify: `tbl/jp.tbl` (add control codes), `tests/data/known_strings.json` (add strings that contain controls)

**Interfaces:**
- Produces: control code entries in `jp.tbl` (`HEX={name}` / `HEX={name:N}`), named in lowercase:
  - `end`, `n` (newline), `wait`, `page`, `name:1`, `choice`, `color:1`, and so on;
  - any code whose meaning is unknown is named `c<HEX>`, e.g. `{cF3:2}`.
- Later plans (M2 VWF) rely on the doc's sections: "Print loop", "Box geometry", "Control codes", "Menu/list drawing".

- [ ] **Step 1: Trace the dialogue print loop**

1. Load `first_text.mss`. Set a CPU read breakpoint on the SNES address of the first dialogue string (`rom.pc_to_lorom(pc)`).
2. Find the loop that fetches each byte, and the compare/branch that splits characters from control codes (e.g. `CMP #$F0 : BCS ctrl`).
3. Find the control dispatch (a jump table indexed by the code). For each entry, read the handler and record how many argument bytes it consumes and what it does.

- [ ] **Step 2: Record box geometry and rendering**

Record:
- how text reaches the screen: glyph tiles copied into a VRAM buffer, or tilemap entries pointing at fixed font tiles;
- the box origin and its size in tiles;
- the characters per line and lines per box;
- the RAM variables (cursor X/Y, text pointer).

- [ ] **Step 3: Trace menu/list drawing**

Repeat Steps 1–2 for the item menu (`items.mss`) and for battle messages (`battle.mss`). Note whether they share the dialogue routine. Record each name field's width in characters.

- [ ] **Step 4: Update `jp.tbl` and the known strings**

1. Add every control code to `jp.tbl`.
2. Add at least 3 known strings that contain controls (newline, wait, name insertion) to `tests/data/known_strings.json`.
3. Run `python -m pytest tests/test_jp_table.py -v`. Expected: PASS.

- [ ] **Step 5: Write `docs/re/text-engine.md`**

Sections: Print loop (routine addresses), Box geometry, Control codes (a table: code, args, behavior, handler address), Menu/list drawing, RAM variables.

- [ ] **Step 6: Commit**

```bash
git add docs/re/text-engine.md tbl/jp.tbl tests/data/known_strings.json
git commit -m "RE: text engine and control codes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Script format, block definitions, dumper

**Files:**
- Create: `lmtools/script.py`, `lmtools/blocks.py`
- Modify: `lm.py` (add `cmd_dump`)
- Test: `tests/test_script.py`, `tests/test_blocks.py`

**Interfaces:**
- Consumes: `Table.decode`, `rom.lorom_to_pc`, `rom.pc_to_lorom`
- Produces:
  - `script.Entry(id: int, ptr: int, meta: dict[str, str] = {}, jp: str = "", en: str = "")`;
  - `script.parse(text) -> list[Entry]`, `script.serialize(entries) -> str`;
  - `script.save(path, entries, force=False)`, which raises `FileExistsError` if the existing file has any EN text and `force` is false;
  - `blocks.Block` (fields below), `blocks.load_blocks(path="data/blocks.json") -> list[Block]`;
  - `blocks.pointers(rom, b) -> list[int]` (PC offsets);
  - `blocks.dump_block(rom, b, tbl) -> list[Entry]`;
  - `blocks.spans(rom, b, tbl) -> list[tuple[int, int]]` (the pointer table span first, then the string spans).
- **Script file format:**
  ```
  #id 0012 ptr=1B2307 box=dialog
  JP: ...decoded text...{end}
  EN: 
  ```
  - A header with `same=<id>` means the entry shares that id's string. Its JP and EN lines stay empty.
  - `ptr` is the original PC offset.
- **`data/blocks.json`** is a list of objects. Hex strings are allowed for numbers, and a `note` key is ignored:
  - `{"name","type":"ptr16","table","count","bank","box"}`: 2-byte pointers, strings in SNES bank `bank`;
  - `{"name","type":"ptr24","table","count","box"}`: 3-byte pointers;
  - `{"name","type":"fixed","start","count","stride","length","pad","box"}`: fixed-width fields with no terminator, padded with `pad`.

- [ ] **Step 1: Write failing tests**

`tests/test_script.py`:
```python
import pytest
from lmtools.script import Entry, parse, save, serialize


def test_format_roundtrip():
    es = [Entry(0, 0x1B2307, {"box": "dialog"}, " あ い{end}", "Hi.{end}"), Entry(1, 0x1B2307, {"same": "0"})]
    assert parse(serialize(es)) == es


def test_tolerates_bom_crlf():
    e = [Entry(3, 0x10, {}, "あ", "")]
    assert parse("\ufeff" + serialize(e).replace("\n", "\r\n")) == e


def test_stripped_trailing_space_on_empty_en():
    assert parse("#id 0001 ptr=000010\nJP: あ\nEN:\n")[0].en == ""


def test_bad_line_reports_line_number():
    with pytest.raises(ValueError, match="line 2"):
        parse("#id 0000 ptr=000010\nhello\n")


def test_save_refuses_to_clobber_translations(tmp_path):
    p = tmp_path / "s.txt"
    save(p, [Entry(0, 0, {}, "あ", "A")])
    with pytest.raises(FileExistsError):
        save(p, [Entry(0, 0, {}, "あ", "")])
    save(p, [Entry(0, 0, {}, "い", "")], force=True)
    assert parse(p.read_text(encoding="utf-8"))[0].jp == "い"
```

`tests/test_blocks.py`:
```python
import pytest
from lmtools.blocks import Block, dump_block, spans
from lmtools.tbl import Table

T = Table(["41=A", "42=B", "20= ", "FF={end}"])


def synth():
    """Bank-0 LoROM image: ptr table at PC 0 -> strings at PC 0x100."""
    rom = bytearray(0x200)
    rom[0x100:0x106] = b"AB\xffB\xff\xff"  # #0 "AB", #1 "B", #2 shares #0
    for i, pc in enumerate([0x100, 0x103, 0x100]):
        rom[i * 2:i * 2 + 2] = (0x8000 | pc).to_bytes(2, "little")
    return rom


B = Block(name="t", type="ptr16", table=0, count=3, bank=0)


def test_dump_ptr16_with_shared():
    es = dump_block(synth(), B, T)
    assert [(e.id, e.ptr, e.jp, e.meta) for e in es] == [
        (0, 0x100, "AB{end}", {}), (1, 0x103, "B{end}", {}), (2, 0x100, "", {"same": "0"})]


def test_spans():
    assert sorted(spans(synth(), B, T)) == [(0, 6), (0x100, 0x103), (0x103, 0x105)]


def test_overlap_raises():
    rom = synth()
    rom[2:4] = (0x8101).to_bytes(2, "little")  # #1 points into the middle of #0
    with pytest.raises(ValueError, match="overlaps"):
        dump_block(rom, B, T)


def test_dump_fixed_strips_pad():
    rom = bytearray(b"AB  BA  ")
    es = dump_block(rom, Block(name="f", type="fixed", start=0, count=2, stride=4, length=4, pad=0x20), T)
    assert [(e.ptr, e.jp) for e in es] == [(0, "AB"), (4, "BA")]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_script.py tests/test_blocks.py -v`
Expected: fails with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `lmtools/script.py`**

```python
"""Script file format: one entry per string, JP original + EN translation."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Entry:
    id: int
    ptr: int
    meta: dict = field(default_factory=dict)
    jp: str = ""
    en: str = ""


def serialize(entries) -> str:
    out = []
    for e in entries:
        out += [f"#id {e.id:04d} ptr={e.ptr:06X}" + "".join(f" {k}={v}" for k, v in e.meta.items()),
                f"JP: {e.jp}", f"EN: {e.en}", ""]
    return "\n".join(out)


def parse(text: str) -> list[Entry]:
    entries = []
    for n, line in enumerate(text.lstrip("\ufeff").splitlines(), 1):
        if line.startswith("#id "):
            num, *kv = line[4:].split()
            e = Entry(int(num), 0)
            for item in kv:
                k, _, v = item.partition("=")
                if k == "ptr":
                    e.ptr = int(v, 16)
                else:
                    e.meta[k] = v
            entries.append(e)
        elif line[:3] in ("JP:", "EN:") and entries:
            setattr(entries[-1], line[:2].lower(), line[4:])
        elif line.strip():
            raise ValueError(f"line {n}: unexpected {line!r}")
    return entries


def save(path, entries, force=False):
    path = Path(path)
    if path.exists() and not force and any(e.en for e in parse(path.read_text(encoding="utf-8"))):
        raise FileExistsError(f"{path} has EN translations; refusing to overwrite (use --force)")
    path.write_text(serialize(entries), encoding="utf-8")
```

- [ ] **Step 4: Implement `lmtools/blocks.py` (dump half; insert comes in Task 11)**

```python
"""Text block definitions (data/blocks.json) and dumping."""
import json
from dataclasses import dataclass
from pathlib import Path

from .rom import lorom_to_pc, pc_to_lorom
from .script import Entry


@dataclass
class Block:
    name: str
    type: str          # "ptr16" | "ptr24" | "fixed"
    table: int = 0     # ptr*: PC offset of pointer table
    count: int = 0
    bank: int = 0      # ptr16: SNES bank holding the strings
    start: int = 0     # fixed: PC offset of record 0's field
    stride: int = 0
    length: int = 0
    pad: int = 0x20
    box: str = ""


def load_blocks(path="data/blocks.json") -> list[Block]:
    out = []
    for raw in json.loads(Path(path).read_text(encoding="utf-8")):
        raw.pop("note", None)
        out.append(Block(**{k: int(v, 0) if isinstance(v, str) and k not in ("name", "type", "box") else v
                            for k, v in raw.items()}))
    return out


def _width(b):
    return 2 if b.type == "ptr16" else 3


def pointers(rom, b) -> list[int]:
    w, out = _width(b), []
    for i in range(b.count):
        v = int.from_bytes(rom[b.table + i * w:b.table + (i + 1) * w], "little")
        out.append(lorom_to_pc(b.bank << 16 | v if w == 2 else v))
    return out


def _meta(b):
    return {"box": b.box} if b.box else {}


def dump_block(rom, b, tbl) -> list[Entry]:
    if b.type == "fixed":
        out = []
        for i in range(b.count):
            off = b.start + i * b.stride
            raw = bytes(rom[off:off + b.length]).rstrip(bytes([b.pad]))
            out.append(Entry(i, off, _meta(b), tbl.decode(raw, 0, len(raw))[0]))
        return out
    seen, out, sp = {}, [], []
    for i, pc in enumerate(pointers(rom, b)):
        if pc in seen:
            out.append(Entry(i, pc, {**_meta(b), "same": str(seen[pc])}))
            continue
        text, n = tbl.decode(rom, pc)
        seen[pc] = i
        sp.append((pc, pc + n, i))
        out.append(Entry(i, pc, _meta(b), text))
    sp.sort()
    for (s0, e0, i0), (s1, _, i1) in zip(sp, sp[1:]):
        if s1 < e0:
            raise ValueError(f"{b.name}: string {i1} at {s1:06X} overlaps string {i0} at {s0:06X}")
    return out


def spans(rom, b, tbl) -> list[tuple[int, int]]:
    if b.type == "fixed":
        return [(b.start + i * b.stride, b.start + i * b.stride + b.length) for i in range(b.count)]
    out = [(b.table, b.table + b.count * _width(b))]
    for pc in sorted(set(pointers(rom, b))):
        out.append((pc, pc + tbl.decode(rom, pc)[1]))
    return out
```

- [ ] **Step 5: Add `cmd_dump` to `lm.py`**

Add the import `from lmtools import blocks, script` and:
```python
def cmd_dump(a):
    base, t = rom.load_base(), Table.load("tbl/jp.tbl")
    Path("script").mkdir(exist_ok=True)
    for b in blocks.load_blocks():
        if a.only and b.name != a.only:
            continue
        es = blocks.dump_block(base, b, t)
        script.save(Path(f"script/{b.name}.txt"), es, a.force)
        print(f"script/{b.name}.txt: {len(es)} entries")
```
Register: `p = sub.add_parser("dump"); p.add_argument("--only"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_dump)`

- [ ] **Step 6: Run the tests**

Run: `python -m pytest tests/test_script.py tests/test_blocks.py -v`
Expected: 9 passed.

- [ ] **Step 7: Commit**

```bash
git add lmtools/script.py lmtools/blocks.py lm.py tests/test_script.py tests/test_blocks.py
git commit -m "Add script format, block definitions and dumper

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: RE — pointer tables → `data/blocks.json`, full coverage

**Files:**
- Create: `data/blocks.json`, `data/beta2_nontext.json`, `docs/re/pointers.md`, `script/*.txt` (generated), `tests/test_coverage.py`
- Modify: `lm.py` (add `cmd_coverage`)

**Interfaces:**
- Consumes: `blocks.load_blocks`, `blocks.spans`, `blocks.dump_block`, `ips.records`, `ips.regions`, `locate.find_pointers`, `locate.scan_strings`
- Produces: a complete `data/blocks.json` covering every text block. It is the input to the inserter and to the M3/M4 translation work.
- **`data/beta2_nontext.json`** format: `[{"start": "020C3C", "end": "02F68F", "what": "font/code area, not text"}]`.

- [ ] **Step 1: Write the coverage test**

`tests/test_coverage.py`:
```python
import json
from pathlib import Path

import pytest
from lmtools import ips
from lmtools.blocks import dump_block, load_blocks, spans
from lmtools.script import parse
from lmtools.tbl import Table

BETA2 = Path("patch/LM3-Beta2.IPS")


def test_blocks_dump(base):
    t = Table.load("tbl/jp.tbl")
    for b in load_blocks():
        assert dump_block(base, b, t), b.name


@pytest.mark.skipif(not BETA2.exists(), reason="Beta2 reference patch not present")
def test_beta2_regions_covered(base):
    t = Table.load("tbl/jp.tbl")
    known = [s for b in load_blocks() for s in spans(base, b, t)]
    known += [(int(r["start"], 16), int(r["end"], 16))
              for r in json.loads(Path("data/beta2_nontext.json").read_text(encoding="utf-8"))]
    missing = [(s, e) for s, e in ips.regions(ips.records(BETA2.read_bytes()))
               if not any(a < e and s < z for a, z in known)]
    assert not missing, " ".join(f"{s:06X}-{e:06X}" for s, e in missing)


def test_no_unknown_bytes_in_script():
    for p in Path("script").glob("*.txt"):
        for e in parse(p.read_text(encoding="utf-8")):
            assert "[" not in e.jp, f"{p.name} #{e.id}: {e.jp}"
```

- [ ] **Step 2: Add `cmd_coverage` (a helper that lists uncovered text)**

```python
def cmd_coverage(a):
    base, t = rom.load_base(), Table.load("tbl/jp.tbl")
    known = [s for b in blocks.load_blocks() for s in blocks.spans(base, b, t)]
    for s, text in locate.scan_strings(base, t, a.min, exclude=known):
        print(f"{s:06X}  {text[:60]}")
```
Register: `p = sub.add_parser("coverage", help="list decodable strings not in any block"); p.add_argument("--min", type=int, default=4); p.set_defaults(fn=cmd_coverage)`

- [ ] **Step 3: Find the pointer tables**

Start `data/blocks.json` as `[]`. For each text area, using `docs/re/beta2-regions.md` as a checklist and starting from the text-heavy rows (`010052…`, `032C04…`, `1B1200…`, `050000…`, `112000…`, `05BF64…`):
1. Find the start of a string: the byte after the previous `{end}`. Use `python lm.py scan` output for the area.
2. Run `python lm.py findptr <pc>`. A real table shows as a run of increasing pointers in the context bytes. Walk backwards and forwards to find the table's first entry and its count.
3. For fixed-width records (item names at `010052`, 32-byte stride), record `start`, `stride`, `length` and `pad`. Each field of a record gets its own block, e.g. `items_name` and `items_desc`.
4. Add the block to `data/blocks.json`, run `python lm.py dump --only <name>`, and read the resulting file to confirm the strings look complete.

Regions Beta2 changed that are font, code or graphics (e.g. `020C3C-02F68F`, `024000` code, `170000` font) go in `data/beta2_nontext.json`, each with a reason.

- [ ] **Step 4: Iterate until everything is covered**

1. Run `python lm.py coverage`, which lists decodable strings that aren't in any block, including text Beta2 never translated.
2. Add blocks for every real one. Junk that only looks like text goes in `docs/re/pointers.md` under "False positives".
3. Repeat until `coverage` prints only listed false positives.

- [ ] **Step 5: Dump all blocks and run the tests**

Run: `python lm.py dump`, then `python -m pytest tests/test_coverage.py -v`
Expected: 3 passed. A failure in `test_no_unknown_bytes_in_script` means `jp.tbl` is missing codes or a block boundary is wrong; go back to Task 7 or 8, or fix the block.

- [ ] **Step 6: Write `docs/re/pointers.md`**

Include:
- one row per block: name, type, table PC, count, string range, which screen uses it;
- how pointers are loaded in code (the routine address, so M2 can relocate the tables);
- the false positives.

- [ ] **Step 7: Commit**

```bash
git add data docs/re/pointers.md script tests/test_coverage.py lm.py
git commit -m "RE: all text pointer tables, full script dump

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: In-place inserter and round-trip proof

**Files:**
- Modify: `lmtools/blocks.py` (add `insert_block`), `lm.py` (add `cmd_roundtrip`)
- Test: `tests/test_blocks.py` (add insert tests), `tests/test_roundtrip.py`

**Interfaces:**
- Consumes: `script.parse`, `Table.encode`, `blocks.spans`, `rom.pc_to_lorom`
- Produces: `blocks.insert_block(rom: bytearray, b: Block, entries: list[Entry], tbl, source="en") -> None`.
  - **In place:** strings are packed in original-address order into the block's original string range, and the pointer table is rewritten.
  - Raises `ValueError` if the text doesn't fit. Shared (`same=`) entries are pointed at their target's new location.
  - For `ptr24`, the original bank's $80 bit is kept.
  - M2 extends this function to relocate strings into expanded banks.

- [ ] **Step 1: Add the failing insert tests** to `tests/test_blocks.py`

```python
from lmtools.blocks import insert_block, pointers


def test_insert_roundtrip_synth():
    rom = synth()
    orig = bytes(rom)
    insert_block(rom, B, dump_block(rom, B, T), T, "jp")
    assert bytes(rom) == orig


def test_shared_pointer_preserved():
    rom = synth()
    es = dump_block(rom, B, T)
    es[0].en, es[1].en = "A{end}", "BA{end}"
    insert_block(rom, B, es, T, "en")
    p = pointers(rom, B)
    assert p[0] == p[2] == 0x100 and p[1] == 0x102
    assert rom[0x100:0x105] == b"A\xffBA\xff"


def test_insert_overflow_raises():
    rom = synth()
    es = dump_block(rom, B, T)
    es[0].en, es[1].en = "ABAB{end}", "B{end}"
    with pytest.raises(ValueError, match="out of space"):
        insert_block(rom, B, es, T, "en")


def test_insert_fixed_pads_and_rejects_long():
    rom = bytearray(b"AB  BA  ")
    fb = Block(name="f", type="fixed", start=0, count=2, stride=4, length=4, pad=0x20)
    es = dump_block(rom, fb, T)
    es[0].en, es[1].en = "B", "AAAA"
    insert_block(rom, fb, es, T, "en")
    assert bytes(rom) == b"B   AAAA"
    es[0].en = "AAAAA"
    with pytest.raises(ValueError, match="bytes >"):
        insert_block(rom, fb, es, T, "en")


def test_empty_text_raises():
    rom = synth()
    with pytest.raises(ValueError, match="empty EN"):
        insert_block(rom, B, dump_block(rom, B, T), T, "en")
```

Run: `python -m pytest tests/test_blocks.py -v`
Expected: the new tests fail with `ImportError: cannot import name 'insert_block'`.

- [ ] **Step 2: Implement `insert_block`** (append to `lmtools/blocks.py`)

```python
def _text(e, source):
    t = e.jp if source == "jp" else e.en
    if not t:
        raise ValueError(f"#{e.id}: empty {source.upper()} text")
    return t


def insert_block(rom, b, entries, tbl, source="en") -> None:
    if b.type == "fixed":
        for e in entries:
            data = tbl.encode(e.jp if source == "jp" else e.en)
            if len(data) > b.length:
                raise ValueError(f"{b.name} #{e.id}: {len(data)} bytes > {b.length}")
            rom[e.ptr:e.ptr + b.length] = data + bytes([b.pad]) * (b.length - len(data))
        return
    old = spans(rom, b, tbl)[1:]
    cur, hi = min(s for s, _ in old), max(z for _, z in old)
    w, new = _width(b), {}
    for e in sorted((e for e in entries if "same" not in e.meta), key=lambda e: e.ptr):
        data = tbl.encode(_text(e, source))
        if cur + len(data) > hi:
            raise ValueError(f"{b.name}: out of space at #{e.id} ({cur + len(data) - hi} bytes over)")
        rom[cur:cur + len(data)] = data
        new[e.id] = cur
        cur += len(data)
    for e in entries:
        pc = new[int(e.meta["same"])] if "same" in e.meta else new[e.id]
        slot = slice(b.table + e.id * w, b.table + (e.id + 1) * w)
        v = pc_to_lorom(pc)
        v = v & 0xFFFF if w == 2 else v | int.from_bytes(rom[slot], "little") & 0x800000
        rom[slot] = v.to_bytes(w, "little")
```

- [ ] **Step 3: Run the block tests**

Run: `python -m pytest tests/test_blocks.py -v`
Expected: 9 passed.

- [ ] **Step 4: Write the real round-trip test and command**

`tests/test_roundtrip.py`:
```python
from pathlib import Path

from lmtools.blocks import insert_block, load_blocks
from lmtools.script import parse
from lmtools.tbl import Table


def test_roundtrip_byte_identical(base):
    t, out = Table.load("tbl/jp.tbl"), bytearray(base)
    for b in load_blocks():
        insert_block(out, b, parse(Path(f"script/{b.name}.txt").read_text(encoding="utf-8")), t, "jp")
    diff = [i for i, (x, y) in enumerate(zip(out, base)) if x != y]
    assert not diff, f"{len(diff)} bytes differ, first at {diff[0]:06X}"
```

Add to `lm.py`:
```python
def cmd_roundtrip(a):
    base, t = rom.load_base(), Table.load("tbl/jp.tbl")
    out = bytearray(base)
    for b in blocks.load_blocks():
        blocks.insert_block(out, b, script.parse(Path(f"script/{b.name}.txt").read_text(encoding="utf-8")), t, "jp")
    Path("build").mkdir(exist_ok=True)
    Path("build/roundtrip.sfc").write_bytes(out)
    diff = [i for i, (x, y) in enumerate(zip(out, base)) if x != y]
    print("IDENTICAL" if not diff else f"{len(diff)} bytes differ: " + " ".join(f"{i:06X}" for i in diff[:20]))
```
Register: `sub.add_parser("roundtrip").set_defaults(fn=cmd_roundtrip)`

- [ ] **Step 5: Run the round-trip**

Run: `python lm.py roundtrip`, then `python -m pytest tests/test_roundtrip.py -v`
Expected: `IDENTICAL`, 1 passed.

If bytes differ, look at the original bytes around the first differing offset. Typical causes:
- a gap of unreferenced data between strings: add a block for it, or split the block at the gap;
- a pointer table entry count that is off by one;
- inconsistent padding in a fixed block.

Fix `data/blocks.json` or `jp.tbl` and re-dump. Never special-case the inserter.

- [ ] **Step 6: Commit**

```bash
git add lmtools/blocks.py lm.py tests/test_blocks.py tests/test_roundtrip.py
git commit -m "Add in-place inserter; JP round-trip is byte-identical

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: ROM expansion, free-space map, compression survey

**Files:**
- Modify: `lmtools/rom.py` (add `expand`), `tests/test_rom.py`, `tests/test_mesen.py`
- Create: `docs/re/memory-map.md`

**Interfaces:**
- Produces: `rom.expand(buf: bytearray, size=0x400000) -> bytearray`. It pads with 0x00, sets header byte `0x7FD7` to log2(size in KB) (0x0C for 4MB), and fixes the checksum. Expanded data is reached at SNES banks `$C0-$FF:8000-FFFF`, since `$70-$7D:0000-7FFF` is SRAM.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rom.py`:
```python
def test_expand_4mb(base):
    b = rom.expand(bytearray(base))
    assert len(b) == 0x400000 and b[0x7FD7] == 0x0C
    assert b[:0x7FD7] == base[:0x7FD7] and b[0x200000:] == bytes(0x200000)
    assert int.from_bytes(b[0x7FDE:0x7FE0], "little") == rom.checksum(b)
```
Add to `tests/test_mesen.py`:
```python
def test_expanded_rom_boots(tmp_path):
    p = tmp_path / "exp.sfc"
    p.write_bytes(rom.expand(rom.load_base()))
    assert mesen.run(p, "boot.lua", tmp_path) == 0
```

Run: `python -m pytest tests/test_rom.py tests/test_mesen.py -v`
Expected: the new tests fail with `AttributeError: module 'lmtools.rom' has no attribute 'expand'`.

- [ ] **Step 2: Implement `expand`** (append to `lmtools/rom.py`)

```python
def expand(buf: bytearray, size=0x400000) -> bytearray:
    if len(buf) > size:
        raise ValueError(f"ROM already {len(buf):#x} bytes > {size:#x}")
    buf += bytes(size - len(buf))
    buf[0x7FD7] = (size // 1024).bit_length() - 1
    fix_checksum(buf)
    return buf
```

- [ ] **Step 3: Run the tests**

Run: `python -m pytest tests/test_rom.py tests/test_mesen.py -v`
Expected: all passed. Also play `expanded` for about a minute in the Mesen2 GUI (load `first_text.mss` won't work across ROMs, so start a new game) to confirm it behaves like the original.

- [ ] **Step 4: Survey compression**

In Mesen2, on the title screen, on `first_text`, and in a battle, open the Event Viewer or put a breakpoint on DMA to VRAM (`$420B` writes). For each graphics upload, check whether the DMA source is ROM (uncompressed) or WRAM (decompressed beforehand). For each WRAM source, find the routine that filled it, and record:
- the routine address;
- the compressed data's PC offset;
- the format family, if recognizable (LZ77/LZSS/RLE).

Text was proven uncompressed by Task 11. **If the title logo or the fonts are compressed, note it for M5/M2. Do not write a codec in this task.**

- [ ] **Step 5: Write `docs/re/memory-map.md`**

Include:
- the output of `python lm.py freespace` (runs of ≥ 256 bytes), with a caution that a long 0xFF run can be real data, verified by checking that nothing points into it;
- the expansion layout: PC `200000-3FFFFF` = `$C0:8000-$FF:FFFF`;
- the compression findings from Step 4;
- the RAM variables from `text-engine.md`, cross-referenced.

- [ ] **Step 6: Commit**

```bash
git add lmtools/rom.py tests/test_rom.py tests/test_mesen.py docs/re/memory-map.md
git commit -m "Add ROM expansion; document free space and compression

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: M1 wrap-up

**Files:**
- Create: `docs/re/README.md`

- [ ] **Step 1: Write `docs/re/README.md`**

Include:
- an index linking `encoding.md`, `text-engine.md`, `pointers.md`, `memory-map.md` and `beta2-regions.md`, each with a one-line summary;
- a "Tooling" section listing the Mesen2 version and any Lua API name differences found in Task 6;
- the `lm.py` command list;
- a "Facts M2 needs" section: font format, box geometry, chars per line, the control code list, the pointer-load routine addresses, and free space.

- [ ] **Step 2: Run the full suite**

Run: `python -m pytest -v`
Expected: every test passes, none skipped (Mesen2 and Beta2 are both present on this machine).

- [ ] **Step 3: Commit and tag**

```bash
git add docs/re/README.md
git commit -m "M1 complete: RE docs index

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git tag m1
```

- [ ] **Step 4: Hand off**

Report to the user:
- the test summary;
- the number of blocks and strings;
- the Japanese character count of the script, which gives a rough size for the translation;
- surprises found (compression, odd controls).

Then propose writing the M2 plan (font + VWF), based on `docs/re/README.md` → "Facts M2 needs".
