"""Build: base -> expand -> asar -> script (EN, JP fallback) -> checksum -> build/lm_en.sfc + .bps."""
import json
import subprocess
from pathlib import Path

from . import bps, chunkgfx, rom
from .blocks import insert_block, load_blocks
from .font import parse_font, vwf_blobs
from .relocate import TEXT_START, Alloc, relocate_block
from .script import parse
from .tbl import Table

ROOT = Path(__file__).resolve().parent.parent
ASAR = ROOT / "tools" / "asar" / "asar.exe"
MAIN_ASM = ROOT / "src" / "asm" / "main.asm"


def _tool(path, name):
    if not path.exists():
        raise FileNotFoundError(f"{name} not found at {path} (download it into tools/{name}/)")
    return str(path)


VWF_GLYPHS = 0x200000     # $C0:8000 (vwf.asm vwf_glyphs)
VWF_WIDTHS = 0x200600     # $C0:8600 (vwf.asm vwf_widths)


def _px8(t):
    return [[sum(((t[16 * (p // 2) + 2 * r + (p % 2)] >> (7 - x)) & 1) << p for p in range(8)) for x in range(8)] for r in range(8)]


def _tile8(px):
    out = bytearray(64)
    for r in range(8):
        for x in range(8):
            for p in range(8):
                if px[r][x] >> p & 1:
                    out[16 * (p // 2) + 2 * r + (p % 2)] |= 0x80 >> x
    return bytes(out)


def _patch_bitmap8(piece, e):
    """Overwrite e's PNG box in one 32-line piece of a 256-wide 8bpp linear-tilemap bitmap."""
    from PIL import Image
    im = Image.open(ROOT / e["png"]).convert("RGB")
    greys = {int(v): i for v, i in e["greys"].items()}
    tiles = [_px8(piece[64 * t:64 * t + 64]) for t in range(len(piece) // 64)]
    for y in range(im.height):
        for x in range(im.width):
            rgb = im.getpixel((x, y))
            if rgb[0] != rgb[1] or rgb[1] != rgb[2] or rgb[0] not in greys:
                raise ValueError(f"{e['png']}: pixel ({x},{y}) color {rgb} not in palette")
            X, Y = e["x"] + x, e["y"] - e["piece_y"] + y
            if not (0 <= X < 256 and 0 <= Y < 32):
                raise ValueError(f"{e['png']}: pixel ({x},{y}) lands outside piece {e['id']}")
            tiles[(Y // 8) * 32 + X // 8][Y % 8][X % 8] = greys[rgb[0]]
    return b"".join(_tile8(t) for t in tiles)


def insert_graphics(work, entries=None):
    used = []
    for e in entries or json.loads((ROOT / "data/graphics.json").read_text(encoding="utf-8")):
        cset = {"title": chunkgfx.TITLE}[e["set"]]
        piece = _patch_bitmap8(chunkgfx.decode(work, cset, e["id"]), e)
        at, room = int(e["new_at"], 16), e["new_room"]
        start = (at - chunkgfx.chunk_pc(cset["dict"], 0)) // 16
        assert chunkgfx.chunk_pc(cset["dict"], start) == at
        new, stream, _ = chunkgfx.encode(piece, start)       # all chunks new: stream stays tiny
        if len(new) > room:
            raise ValueError(f"{e['name']}: {len(new)} bytes of new chunks > {room} reserved")
        try:
            reachable = chunkgfx.chunk_pc(cset["dict"], start + len(new) // 16 - 1) == at + len(new) - 16
        except ValueError:
            reachable = False
        end = at + len(new)
        if not reachable or end > TEXT_START or any(a < end and at < b for a, b in used):
            raise ValueError(f"{e['name']}: new chunks {at:06X}-{end:06X} not contiguous/reachable, overlap text or another entry")
        used.append((at, end))
        work[at:at + len(new)] = new
        pos, _ = chunkgfx._entry(work, cset["table"], e["id"])
        if len(stream) > chunkgfx.stream_len(work, pos):
            raise ValueError(f"{e['name']}: stream {len(stream)} bytes > original")
        work[pos:pos + len(stream)] = stream
        chunkgfx.set_entry(work, cset["table"], e["id"], pos, start)


def write_fonts(work):
    """VWF glyphs + widths into bank $C0. The single-byte font stays as shipped: its tiles double as UI graphics, so the
    renderer draws fixed-font a-z with the A-Z tiles instead (src/asm/vwf.asm)."""
    glyphs, widths = vwf_blobs(parse_font((ROOT / "src/font/vwf.txt").read_text(encoding="utf-8")))
    work[VWF_GLYPHS:VWF_GLYPHS + len(glyphs)] = glyphs
    work[VWF_WIDTHS:VWF_WIDTHS + len(widths)] = widths


def build(out_dir="build", source="en") -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    asar = _tool(ASAR, "asar")
    base = rom.load_base()
    padded_base = rom.expand(bytearray(base))
    sfc, patch = out_dir / "lm_en.sfc", out_dir / "lm_en.bps"
    for stale in (sfc, patch):
        stale.unlink(missing_ok=True)
    work_file = out_dir / "_work.sfc"
    work_file.write_bytes(padded_base)
    try:
        r = subprocess.run([asar, "--no-title-check", "--fix-checksum=off", "--symbols=wla",
                            f"--symbols-path={out_dir / 'lm_en.sym'}", str(MAIN_ASM), str(work_file)],
                           capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"asar failed:\n{r.stdout}{r.stderr}")
        work = bytearray(work_file.read_bytes())
    finally:
        work_file.unlink(missing_ok=True)
    write_fonts(work)
    if source == "en":
        insert_graphics(work)
    jp, en = Table.load(ROOT / "tbl/jp.tbl"), Table.load(ROOT / "tbl/en.tbl")
    alloc = Alloc()
    for b in load_blocks(ROOT / "data/blocks.json"):
        entries = parse((ROOT / f"script/{b.name}.txt").read_text(encoding="utf-8"))
        if b.type == "ptr16":
            relocate_block(work, padded_base, b, entries, jp, source, en, alloc)
        else:
            insert_block(work, b, entries, jp, source, en_tbl=en, base=padded_base, alloc=alloc)
    rom.fix_checksum(work)
    sfc.write_bytes(work)
    patch.write_bytes(bps.create(bytes(base), bytes(work)))
    return sfc
