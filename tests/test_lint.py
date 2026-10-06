from lmtools import lint
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
    e = Entry(4, 0, {}, "あ{n}い{delay:30}う{end}", "A B C{end}")       # ({clear}/{scroll} do count)
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
    assert lint_entry(e, "dialog", WID, W, {}) == ["#9: line 1 is 98 px > 40"]   # name = NAME_PX (68)


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


def test_pad_char_switch_is_layout_and_c9C_is_a_name():
    e = Entry(19, 0, {}, "{c9C:120E00}は{c85:060E00}レベル{end}", "{c9C:120E00} is LV {c9B:CE}{c85:060E00}{c9B:20}.{end}")
    assert lint_entry(e, "wide", WID, W, {}) == []
    assert lint.NAME_INS >= {"c9C"} and "c9C" not in lint.NUM_INS


def test_window_without_scroll_gets_no_jp_line_allowance():
    jp = "あああああああああああああああああああああああああああああああああああああああ{n}あ{n}あ{end}"   # JP line wraps
    e = Entry(20, 0, {}, jp, "a{n}b{n}c{n}d{end}")
    assert lint_entry(e, "w", WID, {"w": {"px": 216, "lines": 3}}, {}) == []
    assert lint_entry(e, "w", WID, {"w": {"px": 216, "lines": 3, "scroll": False}}, {}) == ["#20: page 1 has 4 lines > 3"]


def test_name_inserts_sized_by_table():
    wide = {"px": 999, "lines": 9}
    e = Entry(21, 0, {}, "{c88:12E0A402}あ{end}", "{c88:12E0A402}x{end}")
    assert lint_entry(e, "w", WID, {"w": {**wide, "cells": 18}}, {}) == ["#21: line 1 is 19 cells > 18"]
    e = Entry(22, 0, {}, "{c87:2A0E00}{end}", "{c87:2A0E00}{end}")
    assert lint_entry(e, "w", WID, {"w": {"px": 67, "lines": 9}}, {}) == ["#22: line 1 is 68 px > 67"]


def test_name_constants_cover_the_name_tables():
    from pathlib import Path
    from lmtools.font import parse_font
    from lmtools.script import parse
    w = {ch: x for ch, (x, _) in parse_font(Path("src/font/vwf.txt").read_text(encoding="utf-8")).items()}
    widest = lambda b: max(lint._px(e.en.replace("{end}", "").replace("_", " "), w)
                           for e in parse(Path(f"script/{b}.txt").read_text(encoding="utf-8")) if e.en)
    assert max(widest(b) for b in ("monsters", "accessories", "spells", "unit_weapon0", "unit_armor0")) <= lint.NAME_PX
    assert widest("spell_powerup") <= lint.LONG_NAME_PX and widest("unit_names") <= lint.FIRST_NAME_PX


def test_scroll_and_clear_count_in_control_parity():
    e = Entry(23, 0, {}, "あ{scroll:00}{end}", "A{end}")
    assert lint_entry(e, "wide", WID, W, {}) == ["#23: control codes differ: missing ['{scroll:00}'] extra []"]


def test_repos_meta_lets_positions_move():
    e = Entry(24, 0, {}, "{p19:18}ステレオ{end}", "{p18:18}Stereo{end}")
    assert lint_entry(e, "wide", WID, W, {}) != []
    e.meta["repos"] = "1"
    e.jp = "{p19:18}ステレオ  {end}"
    assert lint_entry(e, "wide", WID, W, {}) == []


def test_first_line_cell_limit():
    win = {"t": {"px": 999, "cells": 19, "first_cells": 12, "lines": 3}}
    e = Entry(25, 0, {}, "魔方陣{n}消費MV 2{n}あ{end}", "Frozen circle{n}MV cost 2{n}Heals{end}")
    assert lint_entry(e, "t", WID, win, {}) == ["#25: line 1 is 13 cells > 12"]


def test_speaker_label_must_match_glossary():
    g = {"リイム": "Reem"}
    e = Entry(30, 0, {}, "リイム{n}「はい」{end}", "Reem:{n}\"Yes.\"{end}")
    assert lint_entry(e, "wide", WID, W, g) == ["#30: speaker 'リイム' should be 'Reem'"]
    e.en = "Reem{n}\"Yes.\"{end}"
    assert lint_entry(e, "wide", WID, W, g) == []


def test_speaker_rule_checks_every_page():
    g = {"リイム": "Reem"}
    e = Entry(31, 0, {}, "「あ」{clear:00}リイム{n}「い」{end}", "\"Reem!\"{clear:00}Rem{n}\"I\"{end}")
    assert lint_entry(e, "wide", WID, W, g) == ["#31: speaker 'リイム' should be 'Reem'"]


def test_missing_lists_untranslated_text_entries(tmp_path):
    from lmtools.script import save
    (tmp_path / "script").mkdir()
    save(tmp_path / "script" / "b.txt", [Entry(0, 1, {}, "あ{end}", ""), Entry(1, 2, {}, "{end}", ""),
                                         Entry(2, 3, {}, "い{end}", "I{end}")])
    assert lint.missing(tmp_path, ["b"]) == ["b #0"]
