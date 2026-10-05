from lmtools.dis65 import disasm


def ops(code, **kw):
    return [l.split("  ", 2)[2] for l in disasm(code, 0, 0x008000, len(code), **kw)]


def test_immediate_width_tracks_rep_sep():
    assert ops(bytes.fromhex("c220 a93412 e220 a934")) == ["REP #$20", "LDA #$1234", "SEP #$20", "LDA #$34"]


def test_index_width_flag():
    assert ops(bytes.fromhex("a03412"), x16=True) == ["LDY #$1234"]
    assert ops(bytes.fromhex("a034")) == ["LDY #$34"]


def test_branch_targets_and_long():
    assert ops(bytes.fromhex("d0fe 22563412 b710")) == ["BNE $8000", "JSL $123456", "LDA [$10],y"]


def test_alu_group_modes():
    assert ops(bytes.fromhex("c901 cd0040 df563412 9100 8302")) == [
        "CMP #$01", "CMP $4000", "CMP $123456,x", "STA ($00),y", "STA $02,s"]
