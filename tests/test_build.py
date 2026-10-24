import pytest
from lmtools import bps, build, rom
from lmtools.blocks import dump_block, insert_block, load_blocks
from lmtools.tbl import Table

T = Table.load("tbl/jp.tbl")
HOOKS = [(0x00BE43, 6), (0x00BE6B, 5), (0x00BE70, 5), (0x00BF01, 4), (0x00BF94, 5), (0x01ECE5, 5), (0x00C20E, 5), (0x00B939, 4), (0x01ECCC, 5), (0x00D927, 4)]  # src/asm/vwf.asm org sites


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
    data = bytearray(build.build(tmp_path, "jp").read_bytes())
    exp = rom.expand(rom.load_base())
    data[0x7FDC:0x7FE0] = exp[0x7FDC:0x7FE0]
    data[0x10000:0x10050] = exp[0x10000:0x10050]             # message table list (tables relocated)
    for snes, n in HOOKS:
        pc = rom.lorom_to_pc(snes)
        data[pc:pc + n] = exp[pc:pc + n]
    assert len(data) == 0x400000 and data[:0x200000] == exp[:0x200000]   # JP only: equals the expanded base
    patch = (tmp_path / "lm_en.bps").read_bytes()
    assert bps.apply(bytes(rom.load_base()), patch) == (tmp_path / "lm_en.sfc").read_bytes()


def test_bad_en_char_names_block_and_entry(tmp_path, monkeypatch):
    real_parse = build.parse

    def fake_parse(text):
        es = real_parse(text)
        if es and es[0].meta.get("box") == "dialog":
            es[0].en = "Hi あ{end}"
        return es

    monkeypatch.setattr(build, "parse", fake_parse)
    with pytest.raises(ValueError, match=r"msg36 #0.*unencodable 'あ'"):
        build.build(tmp_path)
    assert not (tmp_path / "lm_en.sfc").exists()


def test_fonts_written(tmp_path):
    data = build.build(tmp_path, "jp").read_bytes()
    assert data[build.VWF_WIDTHS + ord("A") - 0x20] == 6 and data[build.VWF_WIDTHS + ord("i") - 0x20] == 2


def test_build_relocates_message_tables(tmp_path):
    data = build.build(tmp_path, "jp").read_bytes()
    for i in range(20):
        v = int.from_bytes(data[0x10000 + 4 * i:0x10003 + 4 * i], "little")
        assert rom.lorom_to_pc(v) >= 0x208000, f"list entry {i} still at {v:06X}"
    t11 = rom.lorom_to_pc(int.from_bytes(data[0x10000 + 4 * 11:0x10003 + 4 * 11], "little"))
    p = rom.lorom_to_pc(rom.pc_to_lorom(t11) & 0xFF0000 | int.from_bytes(data[t11 + 2 * 67:t11 + 2 * 67 + 2], "little"))
    assert T.decode(data, p)[0] == "「タップンの武器屋さん」{end}"   # place names past entry 59 (issue #1: castle showed a briefing)


def test_failed_build_leaves_no_stale_outputs(tmp_path, monkeypatch):
    build.build(tmp_path, "jp")
    bad = tmp_path / "bad.asm"
    bad.write_text("lorom\nthis is not an instruction\n")
    monkeypatch.setattr(build, "MAIN_ASM", bad)
    with pytest.raises(RuntimeError, match="asar failed"):
        build.build(tmp_path, "jp")
    assert not any((tmp_path / n).exists() for n in ("lm_en.sfc", "lm_en.bps", "_work.sfc"))


def test_underscore_draws_as_a_space(tmp_path):
    data = build.build(tmp_path, "jp").read_bytes()
    i = ord("_") - 0x20
    assert data[build.VWF_GLYPHS + i * 16:build.VWF_GLYPHS + i * 16 + 16] == bytes(16)
    assert data[build.VWF_WIDTHS + i] == 4


def test_en_build_keeps_the_game_font(tmp_path, base):
    """UI icons and gauges draw font tiles with other palettes, so the single-byte font must stay as shipped."""
    data = build.build(tmp_path, "en").read_bytes()
    assert data[0x170000:0x171000] == base[0x170000:0x171000]
