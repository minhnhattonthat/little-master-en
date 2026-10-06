"""Playtest bug_menu (M6 C-log #1): the system-menu cursor froze on "Item" because its description ran into the
window's wrap column (forced newline below the box -> the engine waits for a key)."""
from pathlib import Path

import pytest
from lmtools import build, mesen

STATE = Path("test/states/bug_menu.mss")
pytestmark = pytest.mark.skipif(not mesen.MESEN.exists() or not STATE.exists(), reason="needs Mesen2 and bug_menu state")

KEYS = ["a", "up", "up", "left", "down", "down", "right", "up"]     # a clears the RC1 wait; down,down reaches Item


def test_system_menu_cursor_leaves_item(tmp_path):
    sfc = build.build(tmp_path / "b")
    lua = (f'STATE=[[{STATE.resolve()}]]\nNAME="m"\nKEYS={{' + ",".join(f'"{k}"' for k in KEYS) + "}\n"
           + Path("test/lua/menu_keys.lua").read_text())
    Path("test/lua/_menu.lua").write_text(lua)
    out = tmp_path / "o"
    assert mesen.run(sfc, "_menu.lua", out) == 0
    shots = [(out / f"m_{i}.png").read_bytes() for i in range(len(KEYS))]
    assert shots[4] != shots[3], "cursor did not reach Item"
    assert shots[5] != shots[4] and shots[7] != shots[6], "cursor stuck after the Item description"
