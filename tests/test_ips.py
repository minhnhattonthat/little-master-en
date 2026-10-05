import pytest
from lmtools import ips

PATCH = b"PATCH" + b"\x00\x00\x02\x00\x02AB" + b"\x00\x00\x10\x00\x00\x00\x03Z" + b"\x00\x00\x30\x00\x01Q" + b"EOF"


def test_records_with_rle():
    assert ips.records(PATCH) == [(2, b"AB"), (0x10, b"ZZZ"), (0x30, b"Q")]


def test_apply_extends_rom():
    out = ips.apply(bytes(0x20), PATCH)
    assert len(out) == 0x31 and out[2:4] == b"AB" and out[0x10:0x13] == b"ZZZ" and out[0x30] == ord("Q")


def test_regions_merge_by_gap():
    assert ips.regions(ips.records(PATCH), gap=0x08) == [(2, 4), (0x10, 0x13), (0x30, 0x31)]
    assert ips.regions(ips.records(PATCH), gap=0x20) == [(2, 0x31)]


def test_bad_patch():
    with pytest.raises(ValueError):
        ips.records(b"NOPE")
    with pytest.raises(ValueError):
        ips.records(b"PATCH\x00\x00")
