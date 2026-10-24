import pytest
from lmtools.blocks import Block, dump_block, jump_targets, pointers
from lmtools.relocate import Alloc, relocate_block, table_groups
from lmtools.rom import lorom_to_pc, pc_to_lorom
from lmtools.tbl import Table

T = Table(["41=A", "42=B", "43=C", "FFC0={goto:3}", "FF={end}"])


def synth():
    """Bank 0. List at PC 0 (2 entries -> tables 0x40, 0x60). Table 0x40: 2 ptrs, table 0x60: 1 ptr (shares "B").
    Table 0x80 (not in list): 1 ptr. Strings at 0x100."""
    rom = bytearray(0x10000)
    rom[0x100:0x109] = b"AA\xffB\xffCC\xff\xff"            # "AA" 0x100, "B" 0x103, "CC" 0x105

    def ptrs(at, pcs):
        for i, pc in enumerate(pcs):
            rom[at + 2 * i:at + 2 * i + 2] = (0x8000 | pc).to_bytes(2, "little")
    ptrs(0x40, [0x100, 0x103]); ptrs(0x60, [0x103]); ptrs(0x80, [0x105])
    for i, t in enumerate([0x40, 0x60]):
        rom[i * 4:i * 4 + 3] = pc_to_lorom(t).to_bytes(3, "little")
    return rom


B = Block(name="p", type="ptr16", tables=[[0x40, 2], [0x60, 1], [0x80, 1]], bank=0)


@pytest.fixture
def small_list(monkeypatch):
    import lmtools.relocate as r
    monkeypatch.setattr(r, "TABLE_LIST", 0x0000)
    monkeypatch.setattr(r, "LIST_LEN", 2)


def test_groups_join_tables_sharing_strings():
    groups = table_groups(synth(), B, T)
    assert sorted(sorted(t for t, _ in g) for g, _ in groups) == [[0x40, 0x60], [0x80]]


def test_relocates_listed_group_and_patches_list(small_list):
    rom = synth(); base = bytes(rom)
    es = dump_block(rom, B, T)
    es[0].en, es[1].en, es[2].en = "AAAAAAAA{end}", "BBBB{end}", "C{end}"
    relocate_block(rom, base, B, es, T, "en", T, Alloc(0x8000, 0x10000))
    new_t = lorom_to_pc(int.from_bytes(rom[0:3], "little"))
    assert new_t >= 0x8000                                            # table 0x40 moved

    def ptr(table_pc, i):                                             # 16-bit pointer in the table's bank
        return lorom_to_pc(pc_to_lorom(table_pc) & 0xFF0000 | int.from_bytes(rom[table_pc + 2 * i:table_pc + 2 * i + 2], "little"))
    assert bytes(rom[ptr(new_t, 0):ptr(new_t, 0) + 9]) == b"AAAAAAAA" + bytes([0xFF])
    t60 = lorom_to_pc(int.from_bytes(rom[4:7], "little"))
    assert ptr(t60, 0) == ptr(new_t, 1)                               # shared "B" stays shared
    assert rom[0x105:0x107] == b"C\xff"                               # unlisted table: in place
    assert pointers(rom, Block(name="u", type="ptr16", tables=[[0x80, 1]], bank=0)) == [0x105]


def test_group_too_big_for_a_bank():
    with pytest.raises(ValueError, match="> 32 KB"):
        Alloc(0, 0x10000).take(0x8001)


def test_alloc_never_crosses_a_bank():
    a = Alloc(0x7FF0, 0x20000)
    assert a.take(0x20) == 0x8000


def test_jump_out_of_group_is_an_error(small_list):
    rom = synth(); base = bytes(rom)
    es = dump_block(rom, B, T)
    for e in es:
        e.en = e.jp
    es[0].en = "A{goto:058100}"                                       # jumps to "CC" (only table 0x80's)
    with pytest.raises(ValueError, match="outside its group"):
        relocate_block(rom, base, B, es, T, "en", T, Alloc(0x8000, 0x10000))


def test_lowercase_jump_args_are_recognised():
    assert jump_targets("{goto:00b222}") == [0x113200]


from lmtools.blocks import insert_block

TI = Table(["41=A", "FF7F={p7F:1}", "FFC0={goto:3}", "CE={nop}", "00={end}"])


def test_inline_overflow_goes_out_and_back():
    rom = bytearray(0x10000)
    rom[0x10:0x1B] = b"\x10\xff\x7f\x02AAAAAA\x00"         # slot 0x11-0x1A: header + 6 chars + end
    blk = Block(name="ev", type="inline", ranges=[[0, 0x100]])
    es = dump_block(rom, blk, TI)
    es[0].en = "{p7F:02}" + "A" * 20 + "{end}"
    insert_block(rom, blk, es, TI, "en", alloc=Alloc(0x8000, 0x10000))
    assert rom[0x11:0x14] == b"\xff\x7f\x02" and rom[0x14:0x16] == b"\xff\xc0" and rom[0x1A] == 0x00
    assert rom[0x19] == 0xCE                                   # padding
    new = lorom_to_pc(int.from_bytes(rom[0x16:0x19], "little"))
    assert rom[new:new + 20] == b"A" * 20 and rom[new + 20:new + 22] == b"\xff\xc0"
    assert lorom_to_pc(int.from_bytes(rom[new + 22:new + 25], "little")) == 0x1A


def test_inline_slot_too_small_for_stub():
    rom = bytearray(b"\x10\xff\x7f\x02A\x00" + bytes(0x100))
    blk = Block(name="ev", type="inline", ranges=[[0, 6]])
    es = dump_block(rom, blk, TI)
    es[0].en = "{p7F:02}AAAAAAA{end}"
    with pytest.raises(ValueError, match="ev #0: slot too small"):
        insert_block(rom, blk, es, TI, "en", alloc=Alloc(0x8000, 0x10000))


def test_allocator_never_reaches_wram_banks():
    from lmtools.relocate import Alloc
    from lmtools.rom import pc_to_lorom
    assert pc_to_lorom(Alloc().end - 1) >> 16 < 0x7E      # $7E/$7F are WRAM, not ROM
