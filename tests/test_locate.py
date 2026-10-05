from lmtools import locate
from lmtools.tbl import Table


def test_find_bytes_overlapping():
    assert locate.find_bytes(b"aaaa", b"aa") == [0, 1, 2]


def test_find_pointers_16_and_24():
    rom = bytearray(0x100)
    rom[0x10:0x12] = (0xA307).to_bytes(2, "little")
    rom[0x20:0x23] = (0x36A307).to_bytes(3, "little")
    rom[0x30:0x33] = (0xB6A307).to_bytes(3, "little")
    hits = locate.find_pointers(rom, 0x1B2307)
    assert (0x10, 2) in hits and (0x20, 3) in hits and (0x30, 3) in hits


def test_free_runs():
    rom = b"\x01" * 8 + b"\xff" * 0x200 + b"\x02" + b"\x00" * 0x50
    assert locate.free_runs(rom, 0x100) == [(8, 0x200, 0xFF)]


def test_scan_strings():
    t = Table(["41=A", "42=B", "FF={end}"])
    rom = b"AAAAB\xff\x99\x99\xffAB\xffBBBB\xff"
    assert locate.scan_strings(rom, t, min_chars=4) == [(0, "AAAAB{end}"), (12, "BBBB{end}")]


def test_scan_strings_excludes_overlapping_candidates():
    t = Table(["41=A", "42=B", "FF={end}"])
    rom = b"ABAB\xffAAAA\xff"
    # candidate at 0 overlaps the known span (2, 5) even though it starts before it
    assert locate.scan_strings(rom, t, min_chars=4, exclude=[(2, 5)]) == [(5, "AAAA{end}")]
