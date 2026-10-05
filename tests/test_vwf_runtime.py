"""Runtime checks of VWF edge cases in Mesen2 (review findings #3, #5)."""
from pathlib import Path

import pytest
from lmtools import build, mesen

pytestmark = pytest.mark.skipif(not mesen.MESEN.exists() or not Path("test/states").exists(),
                                reason="needs Mesen2 and test/states")

LOAD = '''local frame, loaded, ref = 0, false, nil
ref = emu.addMemoryCallback(function()
  if loaded then return end
  local f = io.open(STATE, "rb"); local d = f:read("a"); f:close()
  emu.loadSavestate(d); loaded = true
  emu.removeMemoryCallback(ref, emu.callbackType.exec, 0, 0xFFFFFF)
end, emu.callbackType.exec, 0, 0xFFFFFF)
emu.addEventCallback(function()
  if loaded and frame >= 10 and frame < 14 then emu.setInput({a = true}, 0) end
end, emu.eventType.inputPolled)
'''


def run(sfc, state, body, out):
    Path("test/lua/_rt.lua").write_text(f'STATE=[[{Path("test/states", state + ".mss").resolve()}]]\n' + LOAD + body)
    assert mesen.run(sfc, "_rt.lua", out) == 0
    return (Path(out) / "rt.txt").read_text()


def test_fixed_char_between_vwf_glyphs_keeps_its_cell(tmp_path, monkeypatch):
    real = build.parse

    def inject(text):
        es = real(text)
        for e in es:
            if "Peacock, run home!" in e.en:
                e.en = e.en.replace("Peacock", "Pea{g10}cock")
        return es

    monkeypatch.setattr(build, "parse", inject)
    sfc = build.build(tmp_path / "b", "en")
    res = run(sfc, "ordinary_field_message", '''
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 300 then
    local found = 0
    for a = 0x9000, 0x97FE, 2 do
      if (emu.read16(a, emu.memType.snesWorkRam) & 0x3FF) == 0x010 then found = found + 1 end
    end
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(tostring(found)); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''', tmp_path / "o1")
    assert int(res) >= 1, "the {g10} cell was overwritten by the next VWF glyph"


def test_vwf_code_leaves_slot_buffer_alone_in_kanji_messages(tmp_path):
    sfc = build.build(tmp_path / "b", "en")
    res = run(sfc, "batte_caution", '''
local vwfwrites = 0
emu.addMemoryCallback(function()
  local st = emu.getState()
  if loaded and frame > 10 and (st["cpu.k"] or 0) == 0xC0
     and emu.read16(0x0A18, emu.memType.snesWorkRam) ~= 0 then vwfwrites = vwfwrites + 1 end
end, emu.callbackType.write, 0x1B000, 0x1B7FF, emu.cpuType.snes, emu.memType.snesWorkRam)
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 200 then
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(tostring(vwfwrites)); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''', tmp_path / "o2")
    assert int(res) == 0, f"{res} writes to $7F:B000 from VWF code during a kanji message"


def test_overlong_inline_text_renders_and_event_continues(tmp_path, monkeypatch):
    real = build.parse
    long_line = '{p7F:02}{speed:02}"Peacock, hurry back home now!{n}{delay:30} We will hold those thugs off."{end}'

    def inject(text):
        es = real(text)
        for e in es:
            if "Peacock, run home!" in e.en:
                e.en = long_line if "{speed:02}" in e.jp else e.en
        return es

    monkeypatch.setattr(build, "parse", inject)
    sfc = build.build(tmp_path / "b", "en")
    res = run(sfc, "ordinary_field_message", '''
local inline = 0
emu.addMemoryCallback(function() if loaded then inline = inline + 1 end end,
  emu.callbackType.exec, 0x01FA4E, 0x01FA4E, emu.cpuType.snes, emu.memType.snesMemory)
emu.addEventCallback(function()
  if loaded and frame > 300 and frame % 60 < 4 then emu.setInput({a = true}, 0) end
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 250 then local s = io.open(OUT_DIR .. "/long.png", "wb"); s:write(emu.takeScreenshot()); s:close() end
  if frame == 900 then
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(tostring(inline)); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''', tmp_path / "o3")
    assert int(res) >= 2, "event did not continue to the next inline text"
