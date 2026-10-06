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


def glyph_kanji16(data: bytes) -> list[list[int]]:
    """Little Master kanji: 16x16 1bpp, left 8px column (16 bytes) then right; rows interlaced (even rows first)."""
    px = [[0] * 16 for _ in range(16)]
    for r in range(16):
        y = r // 2 + 8 * (r % 2)
        for x in range(16):
            px[y][x] = (data[(x // 8) * 16 + r] >> (7 - x % 8)) & 1
    return px


def render(rom, offset, count, mode="tile", bpp=1, w=8, h=8, cols=16, scale=3, label=None):
    if mode == "tile":
        w = h = 8
        size, maxv = 8 * bpp, (1 << bpp) - 1
    elif mode == "kanji16":
        w = h = 16
        size, maxv = 32, 1
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
        px = (tile_planar(data, bpp) if mode == "tile" else
              glyph_kanji16(data) if mode == "kanji16" else glyph_linear(data, w, h))
        ox, oy = i % cols * cw + 1, i // cols * ch + 1 + lab
        for y, row in enumerate(px):
            for x, v in enumerate(row):
                d.rectangle([ox + x * scale, oy + y * scale, ox + (x + 1) * scale - 1, oy + (y + 1) * scale - 1],
                            fill=255 - v * 255 // maxv)
        if lab:
            d.text((ox, oy - lab), f"{label + i:X}", fill=0)
    return img


def encode_tiles(pixels, bpp) -> bytes:
    """One 8x8 tile of color indices -> SNES planar bytes (inverse of tile_planar)."""
    out = bytearray(8 * bpp)
    for r, row in enumerate(pixels):
        for x, c in enumerate(row):
            for p in range(bpp):
                if (c >> p) & 1:
                    i = r if bpp == 1 else 16 * (p // 2) + 2 * r + (p % 2)
                    out[i] |= 0x80 >> x
    return bytes(out)


def cgram_palette(cgram, index, bpp):
    """Palette `index` of 2**bpp colors from a CGRAM dump (BGR555) as RGB tuples."""
    n = 1 << bpp
    words = [cgram[2 * i] | cgram[2 * i + 1] << 8 for i in range(index * n, index * n + n)]
    return [((w & 31) << 3, (w >> 5 & 31) << 3, (w >> 10 & 31) << 3) for w in words]


def tiles_to_png(data, bpp, palette, cols, path):
    size = 8 * bpp
    tiles = [tile_planar(data[i:i + size], bpp) for i in range(0, len(data) - size + 1, size)]
    rows = -(-len(tiles) // cols)
    im = Image.new("RGB", (cols * 8, rows * 8), palette[0])
    for t, px in enumerate(tiles):
        for y in range(8):
            for x in range(8):
                im.putpixel(((t % cols) * 8 + x, (t // cols) * 8 + y), palette[px[y][x]])
    im.save(path)


def png_to_tiles(path, bpp, palette) -> bytes:
    """PNG (multiple of 8 in both sizes, palette colors only) -> planar tiles, left-to-right then top-to-bottom."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if w % 8 or h % 8:
        raise ValueError(f"{path}: size {w}x{h} not a multiple of 8")
    index = {tuple(c): i for i, c in reversed(list(enumerate(palette)))}
    out = bytearray()
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            px = []
            for y in range(ty, ty + 8):
                row = []
                for x in range(tx, tx + 8):
                    rgb = im.getpixel((x, y))
                    if rgb not in index:
                        raise ValueError(f"{path}: pixel ({x},{y}) color {rgb} not in palette")
                    row.append(index[rgb])
                px.append(row)
            out += encode_tiles(px, bpp)
    return bytes(out)


def find_in_rom(rom, vram, start, end, tile_bytes):
    """Runs (vram_addr, rom_pc, tiles) of VRAM tiles found verbatim in the ROM; blank/flat tiles are skipped."""
    runs = []
    for v in range(start, end - tile_bytes + 1, tile_bytes):
        t = vram[v:v + tile_bytes]
        if len(set(t)) <= 1:
            continue
        pc = rom.find(t)
        if pc < 0:
            continue
        if runs and runs[-1][0] + runs[-1][2] * tile_bytes == v and runs[-1][1] + runs[-1][2] * tile_bytes == pc:
            runs[-1] = (runs[-1][0], runs[-1][1], runs[-1][2] + 1)
        else:
            runs.append((v, pc, 1))
    return runs
