import pytest
from lmtools.blocks import Block, dump_block, spans
from lmtools.tbl import Table

T = Table(["41=A", "42=B", "20= ", "FF={end}"])


def synth():
    """Bank-0 LoROM image: ptr table at PC 0 (3 entries, #2 shares #0's string) and a 2nd table at PC 0x10."""
    rom = bytearray(0x200)
    rom[0x100:0x106] = b"AB\xffB\xff\xff"  # "AB" at 0x100, "B" at 0x103
    for i, pc in enumerate([0x100, 0x103, 0x100]):
        rom[i * 2:i * 2 + 2] = (0x8000 | pc).to_bytes(2, "little")
    rom[0x10:0x12] = (0x8103).to_bytes(2, "little")  # table 2: one entry -> "B"
    return rom


B = Block(name="t", type="ptr16", tables=[[0, 3]], bank=0)
B2 = Block(name="t2", type="ptr16", tables=[[0, 3], [0x10, 1]], bank=0)


def test_dump_unique_strings_in_address_order():
    es = dump_block(synth(), B, T)
    assert [(e.id, e.ptr, e.jp) for e in es] == [(0, 0x100, "AB{end}"), (1, 0x103, "B{end}")]


def test_dump_pool_with_two_tables():
    assert [e.ptr for e in dump_block(synth(), B2, T)] == [0x100, 0x103]


def test_spans():
    assert sorted(spans(synth(), B2, T)) == [(0, 6), (0x10, 0x12), (0x100, 0x103), (0x103, 0x105)]


def test_pointer_into_middle_splits_at_char_boundary():
    rom = synth()
    rom[2:4] = (0x8101).to_bytes(2, "little")  # points into the middle of "AB"
    assert [(e.ptr, e.jp, e.meta) for e in dump_block(rom, B, T)] == [(0x100, "A", {"cont": "1"}), (0x101, "B{end}", {})]


def test_dump_fixed_strips_pad():
    rom = bytearray(b"AB  BA  ")
    es = dump_block(rom, Block(name="f", type="fixed", start=0, count=2, stride=4, length=4, pad=0x20), T)
    assert [(e.ptr, e.jp) for e in es] == [(0, "AB"), (4, "BA")]


def test_dump_follows_jump_targets_in_pool():
    t = Table(["41=A", "42=B", "FFC0={goto:3}", "FFC5={jC5:3}", "00={end}"])
    rom = bytearray(0x200)
    rom[0x100:0x105] = b"A\xff\xc0\x08\x81"          # "A" goto $00:8108 (PC 0x108)
    rom[0x105:0x108] = b"\x00\x00\x00"
    rom[0x108:0x10A] = b"B\x00"                     # reached only via goto
    rom[0:2] = (0x8100).to_bytes(2, "little")
    es = dump_block(rom, Block(name="j", type="ptr16", tables=[[0, 1]], bank=0), t)
    assert [(e.ptr, e.jp) for e in es] == [(0x100, "A{goto:088100}"), (0x108, "B{end}")]


def test_entry_inside_a_string_splits_it():
    rom = synth()
    rom[4:6] = (0x8102).to_bytes(2, "little")  # #2 -> the terminator byte of "AB" (empty string)
    es = dump_block(rom, B, T)
    assert [(e.ptr, e.jp, e.meta) for e in es] == [(0x100, "AB", {"cont": "1"}), (0x102, "{end}", {}),
                                                    (0x103, "B{end}", {})]


def test_split_inside_a_token_raises():
    t = Table(["41=A", "8142=X", "FF={end}"])
    rom = bytearray(0x200)
    rom[0x100:0x104] = bytes.fromhex("418142ff")
    rom[0:2] = (0x8100).to_bytes(2, "little")
    rom[2:4] = (0x8102).to_bytes(2, "little")  # points at the 2nd byte of a 2-byte kanji
    with pytest.raises(ValueError, match="splits a token"):
        dump_block(rom, Block(name="k", type="ptr16", tables=[[0, 2]], bank=0), t)


def test_excluded_range_is_not_an_entry():
    t = Table(["41=A", "42=B", "FFC0={goto:3}", "00={end}"])
    rom = bytearray(0x200)
    rom[0x100:0x106] = b"A\xff\xc0\x08\x81\x00"     # goto $00:8108, an excluded screen script
    rom[0x108:0x10A] = b"B\x00"
    rom[0:2] = (0x8100).to_bytes(2, "little")
    blk = Block(name="x", type="ptr16", tables=[[0, 1]], bank=0, exclude=[[0x108, 0x10A]])
    assert [e.ptr for e in dump_block(rom, blk, t)] == [0x100]


def test_dump_inline_text_after_opcode():
    t = Table(["41=A", "42=B", "FF7F={p7F:1}", "00={end}"])
    rom = bytearray(b"\x01\x10\xff\x7f\x02AB\x00\x05\x10\xff\x7f\x00B\x00\x10\xff\x7f\x02\x99\x00")
    blk = Block(name="ev", type="inline", ranges=[[0, len(rom)]])
    es = dump_block(rom, blk, t)
    assert [(e.ptr, e.jp) for e in es] == [(2, "{p7F:02}AB{end}"), (10, "{p7F:00}B{end}")]  # 3rd has unknown byte
    assert sorted(spans(rom, blk, t)) == [(2, 8), (10, 15)]


def test_inline_caption_with_position_header_and_garbage_rejected():
    t = Table(["41=A", "42=B", "FF7F={p7F:1}", "FF08={p08:1}", "FF21={clear:1}", "10={g10}", "00={end}"])
    rom = bytearray(b"\x10\xff\x08\x0cAB\x00" + b"\x10\xff\x21\x07A\x00" + b"\x10\xff\x08\x00A\x10\x00")
    es = dump_block(rom, Block(name="ev", type="inline", ranges=[[0, len(rom)]]), t)
    assert [(e.ptr, e.jp) for e in es] == [(1, "{p08:0C}AB{end}")]



from lmtools.blocks import insert_block, pointers


def test_insert_roundtrip_synth():
    rom = synth()
    orig = bytes(rom)
    insert_block(rom, B2, dump_block(rom, B2, T), T, "jp")
    assert bytes(rom) == orig


def test_shared_pointers_follow_their_string():
    rom = synth()
    es = dump_block(rom, B2, T)
    es[0].en, es[1].en = "A{end}", "BA{end}"
    insert_block(rom, B2, es, T, "en")
    assert pointers(rom, B2) == [0x100, 0x102, 0x100, 0x102]
    assert rom[0x100:0x105] == b"A\xffBA\xff"


def test_insert_overflow_raises():
    rom = synth()
    es = dump_block(rom, B, T)
    es[0].en, es[1].en = "ABAB{end}", "B{end}"
    with pytest.raises(ValueError, match="out of space"):
        insert_block(rom, B, es, T, "en")


def test_insert_fixed_pads_and_rejects_long():
    rom = bytearray(b"AB  BA  ")
    fb = Block(name="f", type="fixed", start=0, count=2, stride=4, length=4, pad=0x20)
    es = dump_block(rom, fb, T)
    es[0].en, es[1].en = "B", "AAAA"
    insert_block(rom, fb, es, T, "en")
    assert bytes(rom) == b"B   AAAA"
    es[0].en = "AAAAA"
    with pytest.raises(ValueError, match="bytes >"):
        insert_block(rom, fb, es, T, "en")


def test_empty_text_raises_when_no_jp_fallback():
    rom = synth()
    es = dump_block(rom, B, T)
    es[0].jp = ""
    with pytest.raises(ValueError, match="empty EN"):
        insert_block(rom, B, es, T, "en")


def test_inline_pads_with_nop_and_rejects_long():
    t = Table(["41=A", "42=B", "CE={nop}", "FF7F={p7F:1}", "00={end}"])
    rom = bytearray(b"\x10\xff\x7f\x02AB\x00\x05")
    blk = Block(name="ev", type="inline", ranges=[[0, len(rom)]])
    es = dump_block(rom, blk, t)
    es[0].en = "{p7F:02}A{end}"
    insert_block(rom, blk, es, t, "en")
    assert bytes(rom) == b"\x10\xff\x7f\x02A\xce\x00\x05"
    es[0].en = "{p7F:02}AAB{end}"
    with pytest.raises(ValueError, match="too long"):
        insert_block(rom, blk, es, t, "en")


def test_jump_args_follow_moved_strings():
    t = Table(["41=A", "42=B", "FFC0={goto:3}", "00={end}"])
    rom = bytearray(0x200)
    rom[0x100:0x108] = b"AA\xff\xc0\x07\x81\x00" + b"B"   # "AA" goto $00:8107 ("B" at PC 0x107)
    rom[0x108] = 0x00
    rom[0:2] = (0x8100).to_bytes(2, "little")
    blk = Block(name="j", type="ptr16", tables=[[0, 1]], bank=0)
    es = dump_block(rom, blk, t)
    es[0].en, es[1].en = "A" + es[0].jp[2:], es[1].jp    # 1 byte shorter -> "B" moves to 0x106
    insert_block(rom, blk, es, t, "en")
    assert rom[0x100:0x108] == b"A\xff\xc0\x06\x81\x00B\x00"


def test_cont_chain_moves_together():
    rom = synth()
    rom[4:6] = (0x8102).to_bytes(2, "little")             # splits "AB" into "AB"(cont) + "{end}"
    es = dump_block(rom, B, T)
    es[0].en, es[1].en, es[2].en = "A", "{end}", "B{end}"  # head shrinks; its tail must follow directly
    insert_block(rom, B, es, T, "en")
    assert rom[0x100:0x104] == b"A\xffB\xff"
    assert pointers(rom, B) == [0x100, 0x102, 0x101]


def test_pool_entry_without_terminator_raises():
    rom = synth()
    es = dump_block(rom, B, T)
    es[0].en, es[1].en = "A", "B{end}"
    with pytest.raises(ValueError, match=r"t #0: must end with \{end\} or \{goto\}"):
        insert_block(rom, B, es, T, "en")


def test_cont_head_ending_in_terminator_raises():
    rom = synth()
    rom[4:6] = (0x8102).to_bytes(2, "little")
    es = dump_block(rom, B, T)
    es[0].en, es[1].en, es[2].en = "A{end}", "{end}", "B{end}"
    with pytest.raises(ValueError, match="falls through"):
        insert_block(rom, B, es, T, "en")


def test_script_entries_not_matching_rom_raise_clearly():
    rom = synth()
    es = dump_block(rom, B, T)
    for e in es:
        e.en = e.jp
    with pytest.raises(ValueError, match=r"t: script entries don't match ROM.*000103"):
        insert_block(rom, B, es[:1], T, "en")
    t = Table(["41=A", "FF7F={p7F:1}", "CE={nop}", "00={end}"])
    irom = bytearray(b"\x10\xff\x7f\x02A\x00")
    blk = Block(name="ev", type="inline", ranges=[[0, len(irom)]])
    ies = dump_block(irom, blk, t)
    ies[0].ptr, ies[0].en = 5, ies[0].jp
    with pytest.raises(ValueError, match="ev: script entries don't match ROM"):
        insert_block(irom, blk, ies, t, "en")


def test_jump_target_past_rom_end_is_ignored():
    from lmtools.blocks import jump_targets
    assert jump_targets("{goto:00B222}{jC1:1BFA7A}", rom_size=0x200000) == [0x113200]
