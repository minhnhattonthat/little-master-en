import pytest
from lmtools.blocks import Block, dump_block, spans
from lmtools.tbl import Table

T = Table(["41=A", "42=B", "20= ", "FF={end}"])


def synth():
    """Bank-0 LoROM image: ptr table at PC 0 -> strings at PC 0x100."""
    rom = bytearray(0x200)
    rom[0x100:0x106] = b"AB\xffB\xff\xff"  # #0 "AB", #1 "B", #2 shares #0
    for i, pc in enumerate([0x100, 0x103, 0x100]):
        rom[i * 2:i * 2 + 2] = (0x8000 | pc).to_bytes(2, "little")
    return rom


B = Block(name="t", type="ptr16", table=0, count=3, bank=0)


def test_dump_ptr16_with_shared():
    es = dump_block(synth(), B, T)
    assert [(e.id, e.ptr, e.jp, e.meta) for e in es] == [
        (0, 0x100, "AB{end}", {}), (1, 0x103, "B{end}", {}), (2, 0x100, "", {"same": "0"})]


def test_spans():
    assert sorted(spans(synth(), B, T)) == [(0, 6), (0x100, 0x103), (0x103, 0x105)]


def test_overlap_raises():
    rom = synth()
    rom[2:4] = (0x8101).to_bytes(2, "little")  # #1 points into the middle of #0
    with pytest.raises(ValueError, match="overlaps"):
        dump_block(rom, B, T)


def test_dump_fixed_strips_pad():
    rom = bytearray(b"AB  BA  ")
    es = dump_block(rom, Block(name="f", type="fixed", start=0, count=2, stride=4, length=4, pad=0x20), T)
    assert [(e.ptr, e.jp) for e in es] == [(0, "AB"), (4, "BA")]
