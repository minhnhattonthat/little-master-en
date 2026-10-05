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
