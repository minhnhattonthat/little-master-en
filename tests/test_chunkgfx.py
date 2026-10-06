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



def test_stream_len_counts_operands():
    stream = bytes([0x03, 0x41, 0x22, 0x80, 0x05, 0x85, 0x00, 0xAA])
    assert chunkgfx.stream_len(stream, 0) == 7


def test_off_palette_pixel_in_graphics_png_is_named(tmp_path, monkeypatch):
    from PIL import Image
    from lmtools import build
    im = Image.new("RGB", (8, 8), (248, 248, 248)); im.putpixel((3, 5), (250, 0, 0)); im.save(tmp_path / "bad.png")
    e = {"png": str(tmp_path / "bad.png"), "greys": {"248": 1}, "x": 0, "y": 96, "piece_y": 96, "id": 11}
    with pytest.raises(ValueError, match=r"bad.png: pixel \(3,5\)"):
        build._patch_bitmap8(bytes(0x2000), e)


def test_graphics_png_outside_piece_is_rejected(tmp_path):
    from PIL import Image
    from lmtools import build
    Image.new("RGB", (8, 8), (248, 248, 248)).save(tmp_path / "ok.png")
    e = {"png": str(tmp_path / "ok.png"), "greys": {"248": 1}, "x": 0, "y": 125, "piece_y": 96, "id": 11}
    with pytest.raises(ValueError, match="outside piece 11"):
        build._patch_bitmap8(bytes(0x2000), e)


def test_new_chunks_must_stay_reachable_and_below_text():
    import json
    from lmtools import build
    e = dict(json.loads(Path("data/graphics.json").read_text(encoding="utf-8"))[0], new_at="0x207000")
    work = rom.expand(rom.load_base())
    with pytest.raises(ValueError, match="title_subtitle"):
        build.insert_graphics(work, [e])
