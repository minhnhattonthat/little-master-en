import pytest
from lmtools import bps, build, rom
from lmtools.blocks import dump_block, insert_block, load_blocks
from lmtools.tbl import Table

T = Table.load("tbl/jp.tbl")
FONT = slice(0x170200, 0x1707F0)                            # fixed tiles $20-$7E (written from Task 3 on)


def test_empty_en_falls_back_to_jp(base):
    b = next(x for x in load_blocks() if x.name == "msg36")
    out = bytearray(base)
    insert_block(out, b, dump_block(base, b, T), T, "en")   # all EN empty
    assert out == base


def test_layout_read_from_base_not_target(base):
    b = next(x for x in load_blocks() if x.name == "ev22")
    target = bytearray(base)
    target[0x113A9B:0x113AA0] = bytes(5)                    # disturb bytes near the block
    insert_block(target, b, dump_block(base, b, T), T, "jp", base=base)
    assert target[0x113AA0:] == base[0x113AA0:]


def test_missing_tool_message(monkeypatch, tmp_path):
    monkeypatch.setattr(build, "ASAR", tmp_path / "nope.exe")
    with pytest.raises(FileNotFoundError, match="asar.*tools/asar"):
        build.build(tmp_path)


def test_build_without_translation_is_expanded_base(tmp_path):
    data = bytearray(build.build(tmp_path).read_bytes())
    exp = rom.expand(rom.load_base())
    data[FONT] = exp[FONT]
    data[0x7FDC:0x7FE0] = exp[0x7FDC:0x7FE0]
    assert len(data) == 0x400000 and data[:0x200000] == exp[:0x200000]   # no EN yet
    patch = (tmp_path / "lm_en.bps").read_bytes()
    assert bps.apply(bytes(rom.load_base()), patch) == (tmp_path / "lm_en.sfc").read_bytes()
