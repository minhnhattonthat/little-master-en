"""Build: base -> expand -> asar -> script (EN, JP fallback) -> checksum -> build/lm_en.sfc + .bps."""
import subprocess
from pathlib import Path

from . import bps, rom
from .blocks import insert_block, load_blocks
from .script import parse
from .tbl import Table

ROOT = Path(__file__).resolve().parent.parent
ASAR = ROOT / "tools" / "asar" / "asar.exe"
MAIN_ASM = ROOT / "src" / "asm" / "main.asm"


def _tool(path, name):
    if not path.exists():
        raise FileNotFoundError(f"{name} not found at {path} (download it into tools/{name}/)")
    return str(path)


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
    jp, en = Table.load(ROOT / "tbl/jp.tbl"), Table.load(ROOT / "tbl/en.tbl")
    for b in load_blocks(ROOT / "data/blocks.json"):
        entries = parse((ROOT / f"script/{b.name}.txt").read_text(encoding="utf-8"))
        insert_block(work, b, entries, jp, source, en_tbl=en, base=padded_base)
    rom.fix_checksum(work)
    sfc = out_dir / "lm_en.sfc"
    sfc.write_bytes(work)
    (out_dir / "lm_en.bps").write_bytes(bps.create(bytes(base), bytes(work)))
    return sfc
