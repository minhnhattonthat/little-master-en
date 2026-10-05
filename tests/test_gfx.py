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
