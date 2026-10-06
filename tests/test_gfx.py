from lmtools import gfx


def test_tile_planar_2bpp():
    data = bytes([0x80, 0x80] + [0] * 14)
    px = gfx.tile_planar(data, 2)
    assert px[0][0] == 3 and px[0][1] == 0 and px[1][0] == 0


def test_tile_planar_4bpp_high_planes():
    data = bytes(16) + bytes([0x80, 0x00] + [0] * 14)
    assert gfx.tile_planar(data, 4)[0][0] == 4


def test_glyph_linear_16():
    data = bytes([0x80, 0x01] + [0] * 30)
    px = gfx.glyph_linear(data, 16, 16)
    assert px[0][0] == 1 and px[0][15] == 1 and px[0][1] == 0 and px[1][0] == 0


def test_render_size():
    img = gfx.render(bytes(32 * 20), 0, 20, mode="linear", w=16, h=16, cols=8, scale=2, label=0)
    assert img.size == (8 * (16 * 2 + 2), 3 * (16 * 2 + 2 + 10))


def test_glyph_kanji16_column_major_interlaced():
    # left column bytes 0-15, right 16-31; stored row r is screen row r//2 + 8*(r%2)
    data = bytearray(32)
    data[1] = 0x80      # stored row 1 -> screen row 8, left column
    data[16 + 2] = 0x01  # stored row 2 -> screen row 1, right column
    px = gfx.glyph_kanji16(bytes(data))
    assert px[8][0] == 1 and px[1][15] == 1
    assert sum(map(sum, px)) == 2


def test_encode_tiles_inverts_tile_planar():
    import random
    random.seed(1)
    for bpp in (2, 4):
        px = [[random.randrange(1 << bpp) for _ in range(8)] for _ in range(8)]
        assert gfx.tile_planar(gfx.encode_tiles(px, bpp), bpp) == px


def test_png_round_trip(tmp_path):
    pal = [(0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 0, 255)]
    data = bytes(range(64))                       # 4 tiles of 2bpp
    gfx.tiles_to_png(data, 2, pal, 2, tmp_path / "t.png")
    assert gfx.png_to_tiles(tmp_path / "t.png", 2, pal) == data


def test_png_off_palette_pixel_is_named(tmp_path):
    import pytest
    from PIL import Image
    im = Image.new("RGB", (8, 8), (0, 0, 0)); im.putpixel((3, 5), (1, 2, 3)); im.save(tmp_path / "bad.png")
    with pytest.raises(ValueError, match=r"bad.png: pixel \(3,5\)"):
        gfx.png_to_tiles(tmp_path / "bad.png", 2, [(0, 0, 0), (255, 255, 255)])


def test_find_in_rom_reports_runs():
    rom = bytes(100) + bytes(range(1, 97)) + bytes(50)
    vram = bytes(64) + bytes(range(1, 97))
    assert gfx.find_in_rom(rom, vram, 0, len(vram), 32) == [(64, 100, 3)]


def test_cgram_palette_converts_bgr555():
    cg = bytes([0x00, 0x00, 0x1F, 0x00, 0xE0, 0x03, 0x00, 0x7C])     # black, red, green, blue
    assert gfx.cgram_palette(cg, 0, 2) == [(0, 0, 0), (248, 0, 0), (0, 248, 0), (0, 0, 248)]
