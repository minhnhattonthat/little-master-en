"""Render ROM graphics (SNES planar tiles or linear 1bpp glyphs) to a labelled PNG sheet."""
from PIL import Image, ImageDraw


def tile_planar(data: bytes, bpp: int) -> list[list[int]]:
    rows = []
    for r in range(8):
        planes = [data[r]] if bpp == 1 else [data[2 * r], data[2 * r + 1]]
        if bpp == 4:
            planes += [data[16 + 2 * r], data[17 + 2 * r]]
        rows.append([sum(((p >> (7 - x)) & 1) << i for i, p in enumerate(planes)) for x in range(8)])
    return rows


def glyph_linear(data: bytes, w: int, h: int) -> list[list[int]]:
    bpr = (w + 7) // 8
    return [[(data[y * bpr + x // 8] >> (7 - x % 8)) & 1 for x in range(w)] for y in range(h)]


def render(rom, offset, count, mode="tile", bpp=1, w=8, h=8, cols=16, scale=3, label=None):
    if mode == "tile":
        w = h = 8
        size, maxv = 8 * bpp, (1 << bpp) - 1
    else:
        size, maxv = (w + 7) // 8 * h, 1
    lab = 10 if label is not None else 0
    cw, ch = w * scale + 2, h * scale + 2 + lab
    img = Image.new("L", (cols * cw, (count + cols - 1) // cols * ch), 128)
    d = ImageDraw.Draw(img)
    for i in range(count):
        data = bytes(rom[offset + i * size:offset + (i + 1) * size])
        if len(data) < size:
            break
        px = tile_planar(data, bpp) if mode == "tile" else glyph_linear(data, w, h)
        ox, oy = i % cols * cw + 1, i // cols * ch + 1 + lab
        for y, row in enumerate(px):
            for x, v in enumerate(row):
                d.rectangle([ox + x * scale, oy + y * scale, ox + (x + 1) * scale - 1, oy + (y + 1) * scale - 1],
                            fill=255 - v * 255 // maxv)
        if lab:
            d.text((ox, oy - lab), f"{label + i:X}", fill=0)
    return img
