import pytest
from lmtools.tbl import Table

T = Table(["41=A", "42=B", "8142=漢", "43=A", "3D==", "F0={n}", "F5={color:1}", "FF={end}"])


def test_decode_chars_and_end():
    assert T.decode(b"AB\xf0\xff") == ("AB{n}{end}", 4)


def test_decode_stops_at_end():
    assert T.decode(b"\x00A\xffB\xff", 1) == ("A{end}", 2)


def test_multibyte_key_greedy():
    assert T.decode(b"\x81\x42\x42\xff") == ("漢B{end}", 4)


def test_control_with_arg_roundtrips():
    assert T.decode(b"\xf5\x03A\xff") == ("{color:03}A{end}", 4)
    assert T.encode("{color:03}A{end}") == b"\xf5\x03A\xff"


def test_unknown_byte_roundtrips():
    assert T.decode(b"\x99\xff") == ("[99]{end}", 2)
    assert T.encode("[99]{end}") == b"\x99\xff"


def test_duplicate_value_keeps_original_code():
    assert T.decode(b"\x43\xff") == ("[43]{end}", 2)
    assert T.encode("[43]A{end}") == b"\x43\x41\xff"


def test_equals_sign_value():
    assert T.decode(b"\x3d\xff") == ("={end}", 2)


def test_fixed_length_decode():
    assert T.decode(b"AB\x20", 0, 2) == ("AB", 2)


def test_missing_end_raises():
    with pytest.raises(ValueError):
        T.decode(b"AB")


def test_encode_errors():
    with pytest.raises(ValueError, match="unencodable"):
        T.encode("Z")
    with pytest.raises(ValueError, match="arg bytes"):
        T.encode("{color}")
    with pytest.raises(ValueError, match="unknown control"):
        T.encode("{nope}")


def test_load_bom_crlf(tmp_path):
    p = tmp_path / "t.tbl"
    p.write_bytes("﻿# c\r\n41=A\r\nFF={end}\r\n".encode("utf-8"))
    assert Table.load(p).decode(b"A\xff") == ("A{end}", 2)
