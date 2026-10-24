"""Playtest bug_menu (M6 C-log #1): the system-menu cursor froze on "Item" because its description ran into the
window's wrap column (forced newline below the box -> the engine waits for a key)."""
from pathlib import Path

import pytest
from lmtools import build, mesen

STATE = Path("work/states/bug_menu.mss")
pytestmark = pytest.mark.skipif(not mesen.MESEN.exists() or not STATE.exists(), reason="needs Mesen2 and bug_menu state")

KEYS = ["a", "up", "up", "left", "down", "down", "right", "up"]     # a clears the RC1 wait; down,down reaches Item


def test_system_menu_cursor_leaves_item(tmp_path):
    sfc = build.build(tmp_path / "b")
    lua = (f'STATE=[[{STATE.resolve()}]]\nNAME="m"\nKEYS={{' + ",".join(f'"{k}"' for k in KEYS) + "}\n"
           + Path("tools/lua/menu_keys.lua").read_text())
    Path("tools/lua/_menu.lua").write_text(lua)
    out = tmp_path / "o"
    assert mesen.run(sfc, "_menu.lua", out) == 0
    shots = [(out / f"m_{i}.png").read_bytes() for i in range(len(KEYS))]
    assert shots[4] != shots[3], "cursor did not reach Item"
    assert shots[5] != shots[4] and shots[7] != shots[6], "cursor stuck after the Item description"


INFO_STATE = Path("work/states/bug_black_info_header.mss")


@pytest.mark.skipif(not INFO_STATE.exists(), reason="needs bug_black_info_header state")
def test_info_header_survives_map_scroll(tmp_path):
    # Playtest B2 (second cause): the map-scroll code ($01:F3A0) uses $7F:B000 as scratch; the VWF flush uploaded the
    # whole buffer, pushing the trashed label tiles ($180-$185, "Information") to VRAM -> black header bar.
    keys = ["b", "right", "right", "down", "down", "a", "left", "up", "left", "down"]   # select Reem, hover around
    sfc = build.build(tmp_path / "b")
    lua = (f'STATE=[[{INFO_STATE.resolve()}]]\nNAME="m"\nKEYS={{' + ",".join(f'"{k}"' for k in keys) + "}\n"
           + Path("tools/lua/menu_keys.lua").read_text() + '''
local snaps = {}
emu.addEventCallback(function()
  if not loaded then return end
  for _, i in ipairs({7, 9}) do
    if frame == 10 + 70 * i + 60 then
      local t = {}
      for a = 0xD800, 0xD85F do t[#t + 1] = string.format("%02X", emu.read(a, emu.memType.snesVideoRam)) end
      snaps[#snaps + 1] = table.concat(t)
    end
  end
  if #snaps == 2 and not done_snaps then
    done_snaps = true
    local f = io.open(OUT_DIR .. "/vram.txt", "w"); f:write(table.concat(snaps, string.char(10))); f:close()
  end
end, emu.eventType.endFrame)
''')
    Path("tools/lua/_info.lua").write_text(lua)
    out = tmp_path / "o"
    assert mesen.run(sfc, "_info.lua", out) == 0
    shown, after = (out / "vram.txt").read_text().split()
    assert shown.strip("0") and shown.strip("F"), "label tiles not drawn at step 7"
    assert after == shown, "label tiles changed after hovering on (black header)"
