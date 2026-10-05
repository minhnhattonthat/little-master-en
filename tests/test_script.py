import pytest
from lmtools.script import Entry, parse, save, serialize


def test_format_roundtrip():
    es = [Entry(0, 0x1B2307, {"box": "dialog"}, " あ い{end}", "Hi.{end}"), Entry(1, 0x1B2307, {"same": "0"})]
    assert parse(serialize(es)) == es


def test_tolerates_bom_crlf():
    e = [Entry(3, 0x10, {}, "あ", "")]
    assert parse("﻿" + serialize(e).replace("\n", "\r\n")) == e


def test_stripped_trailing_space_on_empty_en():
    assert parse("#id 0001 ptr=000010\nJP: あ\nEN:\n")[0].en == ""


def test_bad_line_reports_line_number():
    with pytest.raises(ValueError, match="line 2"):
        parse("#id 0000 ptr=000010\nhello\n")


def test_save_refuses_to_clobber_translations(tmp_path):
    p = tmp_path / "s.txt"
    save(p, [Entry(0, 0, {}, "あ", "A")])
    with pytest.raises(FileExistsError):
        save(p, [Entry(0, 0, {}, "あ", "")])
    save(p, [Entry(0, 0, {}, "い", "")], force=True)
    assert parse(p.read_text(encoding="utf-8"))[0].jp == "い"


def test_colon_without_space_keeps_first_char():
    e = parse("#id 0000 ptr=000010\nJP:あ\nEN:Hello\n")[0]
    assert (e.jp, e.en) == ("あ", "Hello")
