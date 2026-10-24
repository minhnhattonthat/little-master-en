"""ASCII-art font sources -> VWF glyph/width blobs and fixed 2bpp tiles (plane0 = top 8 rows, plane1 = bottom 8).

Format: `char X` (or `char space`) then 16 rows of '#'/'.'; row length = advance width (1-8 px).
Lines starting with ';' are comments.
"""


def parse_font(text):
    font, name, rows, at = {}, None, [], 0

    def close():
        if name is None:
            return
        where = f"char {name} (line {at})"
        if len(rows) != 16:
            raise ValueError(f"{where}: needs 16 rows, got {len(rows)}")
        w = len(rows[0])
        if not 1 <= w <= 8 or any(len(r) != w for r in rows):
            raise ValueError(f"{where}: width must be 1-8 and equal on every row")
        ch = " " if name == "space" else name
        if len(ch) != 1 or not 0x20 <= ord(ch) <= 0x7E:
            raise ValueError(f"{where}: name must be one char $20-$7E (or 'space'), outside the font")
        font[ch] = (w, [int(r.replace("#", "1").replace(".", "0").ljust(8, "0"), 2) for r in rows])

    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith(";"):
            continue
        if line.startswith("char "):
            close()
            name, rows, at = line[5:], [], n
        else:
            row = line.strip()
            bad = set(row) - {"#", "."}
            if bad:
                raise ValueError(f"line {n}: unexpected {sorted(bad)[0]!r} (rows use '#' and '.')")
            rows.append(row)
    close()
    return font


def vwf_blobs(font):
    glyphs, widths = bytearray(95 * 16), bytearray(95)
    for ch, (w, rows) in font.items():
        i = ord(ch) - 0x20
        glyphs[i * 16:i * 16 + 16] = bytes(rows)
        widths[i] = w
    return bytes(glyphs), bytes(widths)

