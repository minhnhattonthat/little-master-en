import pytest
from lmtools.tbl import Table

EN = Table.load("tbl/en.tbl")


def test_ascii_roundtrip():
    s = "Who are they?! Lv.5 HP:24/24 'Hi' (ok) 100%{n}Next{end}"
    assert EN.decode(EN.encode(s)) == (s, len(EN.encode(s)))


def test_controls_shared_with_jp():
    assert EN.encode("{p7F:02}{speed:02}{delay:30}{goto:00B222}") == bytes.fromhex("FF7F02FFFD02FFF230FFC000B222")


def test_tag_chars_not_encodable():
    for ch in "[]{}あ":
        with pytest.raises(ValueError):
            EN.encode(ch + "{end}")


def test_ui_symbols_use_the_game_glyph_codes():
    assert EN.encode("×∶◀▶©") == bytes.fromhex("2A3B3C3E40")
    for ch in "*;<>@":
        with pytest.raises(ValueError):
            EN.encode(ch)
