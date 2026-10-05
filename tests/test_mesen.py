import pytest
from lmtools import mesen, rom

pytestmark = [pytest.mark.mesen,
              pytest.mark.skipif(not mesen.MESEN.exists(), reason="Mesen2 not installed")]


def test_base_rom_boots(tmp_path):
    assert mesen.run(rom.BASE, "boot.lua", tmp_path) == 0
    assert (tmp_path / "boot.png").stat().st_size > 0


def test_expanded_rom_boots(tmp_path):
    p = tmp_path / "exp.sfc"
    p.write_bytes(rom.expand(rom.load_base()))
    assert mesen.run(p, "boot.lua", tmp_path) == 0
