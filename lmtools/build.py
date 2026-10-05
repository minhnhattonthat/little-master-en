"""Build: base -> expand -> asar -> script (EN, JP fallback) -> checksum -> build/lm_en.sfc + .bps."""
import subprocess
from pathlib import Path

from . import bps, rom
from .blocks import insert_block, load_blocks
from .font import fixed_tiles, parse_font, vwf_blobs
from .relocate import Alloc, relocate_block
from .script import parse
from .tbl import Table

ROOT = Path(__file__).resolve().parent.parent
ASAR = ROOT / "tools" / "asar" / "asar.exe"
MAIN_ASM = ROOT / "src" / "asm" / "main.asm"


def _tool(path, name):
    if not path.exists():
        raise FileNotFoundError(f"{name} not found at {path} (download it into tools/{name}/)")
    return str(path)


FIXED_FONT = 0x170000     # single-byte 8x16 font: tile = char code, 16 bytes per tile
VWF_GLYPHS = 0x200000     # $C0:8000 (vwf.asm vwf_glyphs)
VWF_WIDTHS = 0x200600     # $C0:8600 (vwf.asm vwf_widths)


def write_fonts(work):
    """Fixed English a-z over tiles $61-$7A (the game font already has UI-styled A-Z, digits and symbols that
    status screens use as graphics), VWF glyphs + widths into bank $C0."""
    fixed = fixed_tiles(parse_font((ROOT / "src/font/fixed.txt").read_text(encoding="utf-8")))
    for c in range(0x61, 0x7B):
        work[FIXED_FONT + c * 16:FIXED_FONT + c * 16 + 16] = fixed[(c - 0x20) * 16:(c - 0x1F) * 16]
    glyphs, widths = vwf_blobs(parse_font((ROOT / "src/font/vwf.txt").read_text(encoding="utf-8")))
    work[VWF_GLYPHS:VWF_GLYPHS + len(glyphs)] = glyphs
    work[VWF_WIDTHS:VWF_WIDTHS + len(widths)] = widths


def build(out_dir="build", source="en") -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    asar = _tool(ASAR, "asar")
    base = rom.load_base()
    padded_base = rom.expand(bytearray(base))
    work_file = out_dir / "_work.sfc"
    work_file.write_bytes(padded_base)
    r = subprocess.run([asar, "--no-title-check", "--fix-checksum=off", str(MAIN_ASM), str(work_file)],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"asar failed:\n{r.stdout}{r.stderr}")
    work = bytearray(work_file.read_bytes())
    work_file.unlink()
    write_fonts(work)
    jp, en = Table.load(ROOT / "tbl/jp.tbl"), Table.load(ROOT / "tbl/en.tbl")
    alloc = Alloc()
    for b in load_blocks(ROOT / "data/blocks.json"):
        entries = parse((ROOT / f"script/{b.name}.txt").read_text(encoding="utf-8"))
        if b.type == "ptr16":
            relocate_block(work, padded_base, b, entries, jp, source, en, alloc)
        else:
            insert_block(work, b, entries, jp, source, en_tbl=en, base=padded_base, alloc=alloc)
    rom.fix_checksum(work)
    sfc = out_dir / "lm_en.sfc"
    sfc.write_bytes(work)
    (out_dir / "lm_en.bps").write_bytes(bps.create(bytes(base), bytes(work)))
    return sfc
