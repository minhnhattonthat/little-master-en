import pytest
from lmtools.blocks import dump_block, insert_block, load_blocks
from lmtools.tbl import Table

T = Table.load("tbl/jp.tbl")
BLOCKS = {b.name: b for b in load_blocks()}


def test_monster_name_keeps_its_terminator(base):
    b, rom = BLOCKS["monsters"], bytearray(base)
    es = dump_block(rom, b, T)
    for e in es:
        e.en = e.jp
    es[0].en = "A" * 12
    with pytest.raises(ValueError, match="bytes >"):
        insert_block(rom, b, es, T, "en")


def test_msg02_has_no_filler_entry(base):
    assert 0x164D5 not in [e.ptr for e in dump_block(base, BLOCKS["msg02"], T)]
