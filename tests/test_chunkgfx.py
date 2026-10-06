import os
from pathlib import Path

import pytest
from lmtools import chunkgfx, mesen, rom

pytestmark = pytest.mark.skipif(not mesen.MESEN.exists(), reason="needs Mesen2")

TITLE_IDS = range(8, 15)          # seven 8 KB pieces -> VRAM $0000-$DFFF (BG1 8bpp bitmap)


@pytest.fixture(scope="module")
def title_vram(tmp_path_factory):
    out = tmp_path_factory.mktemp("title")
    hdr = 'INPUTS = {[70] = "start", [80] = "start", [90] = "start"}\nAT = 200\nNAME = "title"\n'
    Path("test/lua/_cg.lua").write_text(hdr + Path("test/lua/vram_dump.lua").read_text())
    assert mesen.run(rom.BASE, "_cg.lua", out) == 0
    return (out / "title.vram").read_bytes()


def test_decode_matches_title_vram(title_vram):
    base = bytes(rom.load_base())
    got = b"".join(chunkgfx.decode(base, chunkgfx.TITLE, i) for i in TITLE_IDS)
    assert got == title_vram[:0xE000]


def test_encode_round_trips_title():
    base = bytes(rom.load_base())
    for i in TITLE_IDS:
        data = chunkgfx.decode(base, chunkgfx.TITLE, i)
        dictionary, stream, start = chunkgfx.encode(data, start=0)
        assert chunkgfx.decode_stream(stream, lambda k: dictionary[16 * k:16 * k + 16], start) == data
