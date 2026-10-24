import pytest
from lmtools.font import parse_font, vwf_blobs


def art(name, rows):
    return f"char {name}\n" + "\n".join(rows) + "\n"


ART = "; test font\n" + art("A", ["#.."] + ["..."] * 7 + ["..#"] + ["..."] * 7)
ART8 = art("A", ["#......."] + ["........"] * 7 + ["..#....."] + ["........"] * 7)


def test_parse_width_and_rows():
    w, rows = parse_font(ART)["A"]
    assert w == 3 and rows[0] == 0x80 and rows[8] == 0x20 and len(rows) == 16


def test_space_name():
    assert " " in parse_font(art("space", ["...."] * 16))


def test_vwf_blobs_layout():
    g, wid = vwf_blobs(parse_font(ART))
    i = ord("A") - 0x20
    assert len(g) == 95 * 16 and g[i * 16] == 0x80 and wid[i] == 3 and wid[0] == 0



def test_bad_glyph_errors():
    with pytest.raises(ValueError, match="char B.*16 rows"):
        parse_font("char B\n#\n")
    with pytest.raises(ValueError, match="char C.*width"):
        parse_font(art("C", ["#########"] * 16))


def test_errors_name_the_line():
    with pytest.raises(ValueError, match=r"line 2"):
        parse_font("; c\nchar B\n#\n")
    with pytest.raises(ValueError, match=r"line 2.*'x'"):
        parse_font("char D\n#x\n" + "\n".join(["##"] * 15))
    with pytest.raises(ValueError, match="outside"):
        parse_font(art("あ", ["#"] * 16))
