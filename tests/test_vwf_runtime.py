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


PEACOCK_JP = "ピーコック、君は急いで家にもどるんだ"      # ev0A #24, the line open in ordinary_field_message
PEACOCK_EN = '{p7F:02}{speed:02}"Peacock, run home!{n}{delay:30} We\'ll stop them."{end}'   # fixed baseline (M2 test line)


def inject_peacock(monkeypatch, make):
    """Replace the EN of the field line in ordinary_field_message with make(PEACOCK_EN), whatever the script says."""
    real, real_build, hits = build.parse, build.build, []

    def f(text):
        es = real(text)
        for e in es:
            if PEACOCK_JP in e.jp and "{speed:02}" in e.jp:
                e.en = make(PEACOCK_EN)
                hits.append(e.id)
        return es

    def checked_build(*a, **k):                     # the injection must really happen, or the test proves nothing
        hits.clear()
        out = real_build(*a, **k)
        assert len(hits) == 1, f"field line matched {len(hits)} entries"
        return out
    monkeypatch.setattr(build, "parse", f)
    monkeypatch.setattr(build, "build", checked_build)


def test_fixed_char_between_vwf_glyphs_keeps_its_cell(tmp_path, monkeypatch):
    inject_peacock(monkeypatch, lambda en: en.replace("Peacock", "Pea{g10}cock"))
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


def test_vwf_code_leaves_kanji_tiles_alone(tmp_path):
    """Messages with UI/kanji glyphs: the game copies them to slots $0A1A.. (2 tiles each); the VWF must not touch them."""
    sfc = build.build(tmp_path / "b", "en")
    res = run(sfc, "batte_caution", '''
local hits = 0
emu.addMemoryCallback(function(addr)
  local st = emu.getState()
  local first = 0x1B000 + 32 * emu.read16(0x0A1A, emu.memType.snesWorkRam)
  local last = first + 32 * emu.read16(0x0A18, emu.memType.snesWorkRam)
  if loaded and frame > 10 and (st["cpu.k"] or 0) == 0xC0 and addr >= first and addr < last then hits = hits + 1 end
end, emu.callbackType.write, 0x1B000, 0x1B7FF, emu.cpuType.snes, emu.memType.snesWorkRam)
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 200 then
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(tostring(hits)); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''', tmp_path / "o2")
    assert int(res) == 0, f"{res} VWF writes to the message's kanji tiles"


def test_overlong_inline_text_renders_and_event_continues(tmp_path, monkeypatch):
    long_line = '{p7F:02}{speed:02}"Peacock, hurry back home now!{n}{delay:30} We will hold those thugs off."{end}'
    inject_peacock(monkeypatch, lambda en: long_line)
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
    inject_peacock(monkeypatch, lambda en: "{p7F:02}{speed:02}" + "M" * 28 + "{end}")
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
    inject_peacock(monkeypatch, lambda en: en.replace("Peacock", "{p02:16}zz_z"))
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


def test_eight_letter_unit_names_stop_at_their_record(tmp_path):
    """unit_names records are 8 bytes, printed up to a space: 'Dynamite' must not run into 'Tamborin Bread'."""
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
    local b = 0
    for a = 0x9000, 0x90FE, 2 do if (emu.read16(a, emu.memType.snesWorkRam) & 0xFF) == 0x42 then b = b + 1 end end
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(tostring(b)); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''')
    assert mesen.run(sfc, "_rt.lua", tmp_path / "o") == 0
    assert (tmp_path / "o" / "rt.txt").read_text() == "0"     # no 'B' (TAMBORIN BREAD) in the MOOMOO DYNAMITE title rows




def test_overwide_vwf_line_stays_inside_its_slot(tmp_path, monkeypatch):
    """Personal info wraps at 28 cells: a line past 27 cells (216 px) must not draw past its 27-cell slot."""
    real = build.parse

    def inject(text):
        es = real(text)
        for e in es:
            if e.jp.startswith("怪力無双のミノタウロス"):
                e.en = "W" * 34 + "{end}"
        return es

    monkeypatch.setattr(build, "parse", inject)
    sfc = build.build(tmp_path / "b", "en")
    Path("test/lua/_rt.lua").write_text(f'STATE=[[{Path("test/states/personal_infomation.mss").resolve()}]]\n' + '''
local frame, loaded, ref, outside, maxcol = 0, false, nil, 0, 0
ref = emu.addMemoryCallback(function()
  if loaded then return end
  local f = io.open(STATE, "rb"); local d = f:read("a"); f:close()
  emu.loadSavestate(d); loaded = true
  emu.removeMemoryCallback(ref, emu.callbackType.exec, 0, 0xFFFFFF)
end, emu.callbackType.exec, 0, 0xFFFFFF)
emu.addMemoryCallback(function()
  if loaded and (emu.getState()["cpu.k"] or 0) == 0xC0 then outside = outside + 1 end
end, emu.callbackType.write, 0x1B800, 0x1B8FF, emu.cpuType.snes, emu.memType.snesWorkRam)
emu.addMemoryCallback(function()
  if loaded then local c = emu.read16(0x1FF1C, emu.memType.snesWorkRam); if c < 64 then maxcol = math.max(maxcol, c) end end
end, emu.callbackType.exec, 0xC00000, 0xC0FFFF, emu.cpuType.snes)
emu.addEventCallback(function()
  if not loaded then return end
  if frame >= 10 and frame < 14 then emu.setInput({right = true}, 0) end
  if frame >= 30 and frame < 34 then emu.setInput({a = true}, 0) end
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 200 then
    local high = 0
    for a = 0x9000, 0x97FE, 2 do if (emu.read16(a, emu.memType.snesWorkRam) & 0x3FF) >= 0x200 then high = high + 1 end end
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(outside .. " " .. high .. " " .. maxcol); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''')
    assert mesen.run(sfc, "_rt.lua", tmp_path / "o") == 0
    outside, high, maxcol = map(int, (tmp_path / "o" / "rt.txt").read_text().split())
    assert maxcol >= 26, f"injection did not reach the slot edge (max cell {maxcol})"
    assert (outside, high) == (0, 0), (outside, high, maxcol)


def test_menu_tilemap_requests_upload_vwf_tiles(tmp_path):
    """Menus (hospital) request the tilemap from $01:ECCC every frame: VWF tiles must reach VRAM too."""
    sfc = build.build(tmp_path / "b", "en")
    Path("test/lua/_rt.lua").write_text(f'STATE=[[{Path("test/states/hospital.mss").resolve()}]]\n' + '''
local frame, loaded, ref = 0, false, nil
ref = emu.addMemoryCallback(function()
  if loaded then return end
  local f = io.open(STATE, "rb"); local d = f:read("a"); f:close()
  emu.loadSavestate(d); loaded = true
  emu.removeMemoryCallback(ref, emu.callbackType.exec, 0, 0xFFFFFF)
end, emu.callbackType.exec, 0, 0xFFFFFF)
emu.addEventCallback(function()
  if loaded and frame >= 10 and frame < 14 then emu.setInput({down = true}, 0) end
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 90 then
    local used, bad = 0, 0
    for a = 0x9000, 0x97FE, 2 do
      local t = emu.read16(a, emu.memType.snesWorkRam) & 0x3FF
      if t >= 0x180 then
        used = used + 1
        for b = 0, 15 do
          if emu.read(0xD800 + (t - 0x180) * 16 + b, emu.memType.snesVideoRam) ~= emu.read(0x1B000 + (t - 0x180) * 16 + b, emu.memType.snesWorkRam) then bad = bad + 1 break end
        end
      end
    end
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(used .. " " .. bad); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''')
    assert mesen.run(sfc, "_rt.lua", tmp_path / "o") == 0
    used, bad = map(int, (tmp_path / "o" / "rt.txt").read_text().split())
    assert used > 0 and bad == 0, (used, bad)


def test_scenario_briefing_fits_without_a_blind_scroll(tmp_path):
    """An overlong briefing scrolls while the screen is still blanked ($10 = 3) and waits for a key: black screen."""
    sfc = build.build(tmp_path / "b", "en")
    Path("test/lua/_rt.lua").write_text(f'STATE=[[{Path("test/states/map.mss").resolve()}]]\n' + LOAD + '''
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 220 then
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(tostring(emu.read(0x10, emu.memType.snesWorkRam))); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''')
    assert mesen.run(sfc, "_rt.lua", tmp_path / "o") == 0
    assert (tmp_path / "o" / "rt.txt").read_text() == "0"     # display on: Scenario Information is shown


LINE_PX = 208                                        # lint px limit of dialog/msg windows (data/windows.json)


def test_full_width_line_then_newline_has_no_blank_line(tmp_path, monkeypatch):
    """A line filling the 216 px limit followed by {n}: the next text must be on the very next line (M3 briefing bug)."""
    from lmtools.font import parse_font
    w = {c: x for c, (x, _) in parse_font(Path("src/font/vwf.txt").read_text(encoding="utf-8")).items()}
    line = ""
    while sum(w[c] for c in line) + w["n"] <= LINE_PX:
        line += "n"
    while sum(w[c] for c in line) + w["i"] <= LINE_PX:
        line += "i"
    inject_peacock(monkeypatch, lambda en: en.replace("Peacock, run home!", line + "{n}B"))
    sfc = build.build(tmp_path / "b", "en")
    res = run(sfc, "ordinary_field_message", '''
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == 300 then
    local rows = {}
    for r = 0, 31 do
      for c = 0, 31 do
        if (emu.read16(0x9000 + r * 64 + c * 2, emu.memType.snesWorkRam) & 0x3FF) >= 0x180 then rows[#rows+1] = r break end
      end
    end
    local f = io.open(OUT_DIR .. "/rt.txt", "w"); f:write(table.concat(rows, " ")); f:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
''', tmp_path / "o")
    rows = sorted({int(r) for r in res.split()})
    assert sum(w[c] for c in line) > LINE_PX - 4, sum(w[c] for c in line)
    assert {24, 26} <= set(rows), rows       # window rows 24-27: the long line on 24, 'B' on 26 (no blank line, no scroll)
