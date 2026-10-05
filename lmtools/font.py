"""ASCII-art font sources -> VWF glyph/width blobs and fixed 2bpp tiles (plane0 = top 8 rows, plane1 = bottom 8).

Format: `char X` (or `char space`) then 16 rows of '#'/'.'; row length = advance width (1-8 px).
Lines starting with ';' are comments.
"""


def parse_font(text):
    font, name, rows = {}, None, []

    def close():
        if name is None:
            return
        if len(rows) != 16:
            raise ValueError(f"char {name}: needs 16 rows, got {len(rows)}")
        w = len(rows[0])
        if not 1 <= w <= 8 or any(len(r) != w for r in rows):
            raise ValueError(f"char {name}: width must be 1-8 and equal on every row")
        font[" " if name == "space" else name] = (
            w, [int(r.replace("#", "1").replace(".", "0").ljust(8, "0"), 2) for r in rows])

    for line in text.splitlines():
        if not line.strip() or line.startswith(";"):
            continue
        if line.startswith("char "):
            close()
            name, rows = line[5:], []
        else:
            rows.append(line.strip())
    close()
    return font


def vwf_blobs(font):
    glyphs, widths = bytearray(95 * 16), bytearray(95)
    for ch, (w, rows) in font.items():
        i = ord(ch) - 0x20
        glyphs[i * 16:i * 16 + 16] = bytes(rows)
        widths[i] = w
    return bytes(glyphs), bytes(widths)


def fixed_tiles(font):
    out = bytearray(95 * 16)
    for ch, (_, rows) in font.items():
        i = (ord(ch) - 0x20) * 16
        for r in range(8):
            out[i + 2 * r], out[i + 2 * r + 1] = rows[r], rows[r + 8]
    return bytes(out)
