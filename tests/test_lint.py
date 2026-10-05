from lmtools.lint import lint_entry
from lmtools.script import Entry
from lmtools.tbl import Table

W = {"dialog": {"px": 40, "lines": 2}, "wide": {"px": 999, "lines": 9}, "name10": {"bytes": 4}}
WID = {c: 6 for c in map(chr, range(32, 127))}
EN = Table.load("tbl/en.tbl")


def test_width_per_visual_line_counts_trailing_spaces():
    e = Entry(1, 0, {}, "あ{end}", "AAAAAA{n}AAAAA  {end}")
    assert lint_entry(e, "dialog", WID, W, {}) == ["#1: line 2 is 42 px > 40"]


def test_glossary_spelling():
    e = Entry(2, 0, {}, "リイムが来た{end}", "Rime came.{end}")
    assert lint_entry(e, "wide", WID, W, {"リイム": "Reem"}) == ["#2: glossary: リイム should be 'Reem'"]


def test_control_parity():
    e = Entry(3, 0, {}, "{c85:600E00}ポイント{end}", "points{end}")
    assert "control" in lint_entry(e, "wide", WID, W, {})[0]


def test_layout_codes_dont_count_for_parity():
    e = Entry(4, 0, {}, "あ{n}い{delay:30}{clear:00}う{end}", "A B C{end}")
    assert lint_entry(e, "wide", WID, W, {}) == []


def test_lines_per_page():
    e = Entry(5, 0, {}, "あ{n}い{end}", "A{n}B{n}C{end}")
    assert lint_entry(e, "dialog", WID, W, {}) == ["#5: page 1 has 3 lines > 2"]
    e2 = Entry(6, 0, {}, "あ{n}い{clear:00}う{end}", "A{n}B{clear:00}C{n}D{end}")
    assert lint_entry(e2, "dialog", WID, W, {}) == []


def test_positioned_segments_keep_their_cells():
    e = Entry(7, 0, {}, "{p02:10}勇者軍{p02:12}OK{end}", "{p02:10}Heroes!{p02:12}OK{end}")
    assert lint_entry(e, "wide", WID, W, {}) == ["#7: segment 1 is 7 cells > 6 (positioned layout)"]


def test_name_byte_limit():
    e = Entry(8, 0, {}, "こんぼう", "Clubs")
    assert lint_entry(e, "name10", WID, W, {}, EN) == ["#8: 5 bytes > 4"]


def test_name_inserts_count_in_width():
    e = Entry(9, 0, {}, "{c87:2A0E00}が来た{end}", "{c87:2A0E00} came{end}")
    assert lint_entry(e, "dialog", WID, W, {}) == ["#9: line 1 is 78 px > 40"]   # name = 8 x 6 px


def test_repository_is_lint_clean():
    from lmtools.lint import lint_all
    assert lint_all() == []
