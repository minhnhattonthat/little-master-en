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
