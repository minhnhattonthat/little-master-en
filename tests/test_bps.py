import zlib

import pytest
from lmtools import bps


def test_create_apply_roundtrip():
    src = bytes(range(256)) * 64
    tgt = bytearray(src) + b"tail" * 100
    tgt[100:110] = b"X" * 10
    p = bps.create(src, bytes(tgt))
    assert p[:4] == b"BPS1" and bps.apply(src, p) == bytes(tgt)


def test_patch_crc_checked():
    p = bytearray(bps.create(b"abc", b"abd"))
    p[-5] ^= 1
    with pytest.raises(ValueError, match="crc"):
        bps.apply(b"abc", bytes(p))


def test_wrong_source_rejected():
    with pytest.raises(ValueError, match="source"):
        bps.apply(b"xyz", bps.create(b"abc", b"abd"))


def test_repeated_bytes_are_compact():
    src = bytes(range(256)) * 16
    tgt = src + bytes(0x100000) + b"\x01\x02"
    p = bps.create(src, tgt)
    assert len(p) < 200 and bps.apply(src, p) == tgt
