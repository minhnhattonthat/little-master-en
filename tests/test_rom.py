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
