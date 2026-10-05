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


WC = {"desc": {"cells": 10, "lines": 2}, "item": {"cells": 5, "lines": 3}, "headers": {"09": "item"}}


def test_cell_width_for_fixed_or_wrapping_windows():
    e = Entry(10, 0, {}, "あ{end}", "ABCDEFGHIJK{end}")
    assert lint_entry(e, "desc", WID, WC, {}) == ["#10: line 1 is 11 cells > 10"]


def test_header_selects_the_window():
    e = Entry(11, 0, {}, "{p7F:09}あ{end}", "{p7F:09}ABCDEF{end}")
    assert lint_entry(e, "desc", WID, WC, {}) == ["#11: line 1 is 6 cells > 5"]


def test_jp_lines_counted_after_wrapping():
    # JP line of 30 cells wraps to 3 window lines (10 cells); EN may use 3 explicit lines
    e = Entry(12, 0, {}, "あ" * 30 + "{end}", "ABC{n}DEF{n}GHI{end}")
    assert lint_entry(e, "desc", WID, WC, {}) == []


def test_glossary_term_split_by_a_line_break_still_counts():
    e = Entry(13, 0, {}, "魔方陣を{end}", "the magic{n}circle{end}")
    assert lint_entry(e, "wide", WID, W, {"魔方陣": "magic circle"}) == []


def test_unencodable_text_is_reported():
    e = Entry(14, 0, {}, "あ{end}", "Hi; there{end}")
    assert lint_entry(e, "wide", WID, W, {}, EN) == ["#14: unencodable ';' at 2 in 'Hi; there{end}'"]


def test_glossary_ignores_case():
    e = Entry(15, 0, {}, "ポイズン攻撃{end}", "X is poisoned!{end}")
    assert lint_entry(e, "wide", WID, W, {"ポイズン": "Poison"}) == []


def test_gloss_off_meta_skips_glossary():
    e = Entry(16, 0, {"gloss": "off"}, "{p0C:16}地形効果{end}", "{p0C:16}Terrain{end}")
    assert lint_entry(e, "wide", WID, W, {"地形効果": "terrain bonus"}) == []


def test_positioned_budget_is_per_line_with_slack():
    e = Entry(17, 0, {}, "{p02:10}ああああ{n}あ{p02:12}ステレオ{end}", "{p02:10}ABCD{n}EFGH{p02:12}Stereo{end}")
    assert lint_entry(e, "wide", WID, W, {}) == ["#17: segment 2 is 6 cells > 4 (positioned layout)"]
    e.meta["slack"] = "2"
    assert lint_entry(e, "wide", WID, W, {}) == []


def test_lowercase_under_a_ui_palette_is_flagged():
    e = Entry(18, 0, {}, "{cF1:05}{p02:16}ぞ{cF1:01}{p03:16}ああ{end}", "{cF1:05}{p02:16}[69]{cF1:01}{p03:16}ok{end}")
    assert lint_entry(e, "wide", WID, W, {}) == []
    e.en = "{cF1:05}{p02:16}o{cF1:01}{p03:16}k{end}"
    assert lint_entry(e, "wide", WID, W, {}) == ["#18: lowercase under {cF1} palette draws UI graphics: 'o'"]
