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


def symbols(sfc):
    """asar WLA symbols: 'bb:aaaa name' -> {name: snes address}."""
    out = {}
    for line in Path(sfc).with_suffix(".sym").read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and ":" in parts[0]:
            bank, addr = parts[0].split(":")
            out[parts[1]] = int(bank, 16) << 16 | int(addr, 16)
    return out


def inject_en(monkeypatch, old, new):
    real = build.parse

    def f(text):
        es = real(text)
        for e in es:
            if e.en == old:
                e.en = new
        return es
    monkeypatch.setattr(build, "parse", f)


ITEM = "{p7F:09}Item use{n}canceled.{scroll:00}{end}"


def test_speed0_text_requests_few_uploads(tmp_path):
    sfc = build.build(tmp_path / "b", "en")
    res = run(sfc, "item_menu", '''
local fe = 0
emu.addMemoryCallback(function(addr, val)
  if loaded and frame > 10 and val == 0xFE and (emu.getState()["cpu.k"] or 0) == 0xC0 then fe = fe + 1 end
end,
  emu.callbackType.write, 0x57, 0x57, emu.cpuType.snes, emu.memType.snesWorkRam)
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 120 then local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(tostring(fe)); f:close(); emu.stop(0) end
end, emu.eventType.endFrame)
''', tmp_path / "o4")
    assert 1 <= int(res) <= 3, f"{res} tile-upload requests for one instant message"


def test_empty_line_does_not_consume_a_slot(tmp_path, monkeypatch):
    inject_en(monkeypatch, ITEM, "{p7F:09}{n}Item use{n}canceled.{scroll:00}{end}")
    sfc = build.build(tmp_path / "b", "en")
    clear = symbols(sfc)["vwf_clearslot"]
    res = run(sfc, "item_menu", f'''
local n = 0
emu.addMemoryCallback(function() if loaded and frame > 10 then n = n + 1 end end,
  emu.callbackType.exec, {clear}, {clear}, emu.cpuType.snes, emu.memType.snesMemory)
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 120 then local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(tostring(n)); f:close(); emu.stop(0) end
end, emu.eventType.endFrame)
''', tmp_path / "o5")
    assert int(res) == 2, f"{res} slots cleared for 2 drawn lines"


def test_line_ending_on_the_edge_leaves_the_border(tmp_path, monkeypatch):
    peacock = '{p7F:02}{speed:02}"Peacock, run home!{n}{delay:30} We\'ll stop them."{end}'
    inject_en(monkeypatch, peacock, "{p7F:02}{speed:02}" + "M" * 28 + "{end}")
    sfc = build.build(tmp_path / "b", "en")
    res = run(sfc, "ordinary_field_message", '''
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 400 then
    local W = emu.memType.snesWorkRam
    local row = emu.read16(0x09F2, W)
    local e = emu.read16(0x9000 + 2 * (row * 32 + 30), W) & 0x3FF
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(tostring(e)); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''', tmp_path / "o6")
    assert not 0x180 <= int(res) <= 0x1FF, f"border cell holds VWF tile {int(res):03X}"


def test_fixed_font_draws_lowercase_with_uppercase_tiles(tmp_path, monkeypatch):
    real = build.parse

    def inject(text):
        es = real(text)
        for e in es:
            if "Peacock, run home!" in e.en:
                e.en = e.en.replace("Peacock", "{p02:16}zz_z")
        return es

    monkeypatch.setattr(build, "parse", inject)
    sfc = build.build(tmp_path / "b", "en")
    res = run(sfc, "ordinary_field_message", '''
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 300 then
    local up, low, under = 0, 0, 0
    for a = 0x9000, 0x97FE, 2 do
      local t = emu.read16(a, emu.memType.snesWorkRam) & 0xFF
      if t == 0x5A then up = up + 1 elseif t == 0x7A then low = low + 1 elseif t == 0x5F then under = under + 1 end
    end
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(up .. " " .. low .. " " .. under); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''', tmp_path / "o1")
    up, low, under = map(int, res.split())
    assert (up >= 3, low, under) == (True, 0, 0)


def test_personal_info_description_uses_vwf(tmp_path, monkeypatch):
    """$0A1A = 23 leaves 82 slot tiles: 3 lines need slots narrower than 32 cells (27 = 216 px)."""
    real = build.parse

    def inject(text):
        es = real(text)
        for e in es:
            if e.jp.startswith("怪力無双のミノタウロス"):
                e.en = "Moomoo is a mighty minotaur.{n}Second line of text here.{n}Third line, the last one.{end}"
        return es

    monkeypatch.setattr(build, "parse", inject)
    sfc = build.build(tmp_path / "b", "en")
    Path("test/lua/_rt.lua").write_text(f'STATE=[[{Path("test/states/personal_infomation.mss").resolve()}]]\n' + '''
local frame, loaded, ref = 0, false, nil
ref = emu.addMemoryCallback(function()
  if loaded then return end
  local f = io.open(STATE, "rb"); local d = f:read("a"); f:close()
  emu.loadSavestate(d); loaded = true
  emu.removeMemoryCallback(ref, emu.callbackType.exec, 0, 0xFFFFFF)
end, emu.callbackType.exec, 0, 0xFFFFFF)
emu.addEventCallback(function()
  if not loaded then return end
  if frame >= 10 and frame < 14 then emu.setInput({right = true}, 0) end
  if frame >= 30 and frame < 34 then emu.setInput({a = true}, 0) end
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 200 then
    local rows, fixed, inside, outside, shared = {}, 0, {}, {}, 0
    for r = 22, 27 do rows[r] = 0 end
    for a = 0x9000, 0x97FE, 2 do
      local t, r = emu.read16(a, emu.memType.snesWorkRam) & 0x3FF, (a - 0x9000) // 64
      if r >= 22 and r <= 27 and t >= 0x180 then rows[r] = rows[r] + 1; inside[t] = true end
      if (r < 22 or r > 27) and t >= 0x180 then outside[t] = true end
      if r >= 22 and r <= 27 and t >= 0x141 and t <= 0x15A then fixed = fixed + 1 end
    end
    local vwf, n = 999, 0
    for r = 22, 27 do vwf = math.min(vwf, rows[r]) end
    for t in pairs(inside) do if outside[t] then shared = shared + 1 end end
    fixed = fixed + 1000 * shared
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(vwf .. " " .. n .. " " .. fixed); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''')
    assert mesen.run(sfc, "_rt.lua", tmp_path / "o") == 0
    vwf, rows, fixed = map(int, (tmp_path / "o" / "rt.txt").read_text().split())
    assert vwf >= 15 and fixed == 0, (vwf, fixed)    # every row of the 3 lines has >= 15 VWF cells; no fixed letters
                                                     # (units) and no slot tile shared with labels outside (1000s)
