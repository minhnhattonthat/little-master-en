-- Dump VRAM, CGRAM, OAM, PPU layer addresses and a screenshot at frame AT.
-- Globals: STATE (optional save state path), INPUTS (optional {[frame] = "start"} etc., held 4 frames), AT, NAME.
local frame, loaded, ref = 0, (STATE == nil), nil
if STATE then
  ref = emu.addMemoryCallback(function()
    if loaded then return end
    local f = io.open(STATE, "rb"); local d = f:read("a"); f:close()
    emu.loadSavestate(d); loaded = true
    emu.removeMemoryCallback(ref, emu.callbackType.exec, 0, 0xFFFFFF)
  end, emu.callbackType.exec, 0, 0xFFFFFF)
end
local function dump(mem, n, path)
  local b = {}
  for a = 0, n - 1 do b[#b + 1] = string.char(emu.read(a, mem)) end
  local f = io.open(path, "wb"); f:write(table.concat(b)); f:close()
end
emu.addEventCallback(function()
  if not loaded then return end
  for f, key in pairs(INPUTS or {}) do
    if frame >= f and frame < f + 4 then local t = {}; t[key] = true; emu.setInput(t, 0) end
  end
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == AT then
    local base = OUT_DIR .. "/" .. NAME
    dump(emu.memType.snesVideoRam, 0x10000, base .. ".vram")
    dump(emu.memType.snesCgRam, 512, base .. ".cgram")
    dump(emu.memType.snesSpriteRam, 544, base .. ".oam")
    local st, t = emu.getState(), {}
    t[#t + 1] = "mode=" .. st["ppu.bgMode"]
    for i = 0, 3 do
      local L = "ppu.layers[" .. i .. "]."
      t[#t + 1] = string.format("bg%d chr=%d map=%d w64=%s h64=%s hs=%d vs=%d", i + 1, st[L .. "chrAddress"], st[L .. "tilemapAddress"],
        tostring(st[L .. "doubleWidth"]), tostring(st[L .. "doubleHeight"]), st[L .. "hscroll"], st[L .. "vscroll"])
    end
    local p = io.open(base .. ".ppu", "w"); p:write(table.concat(t, string.char(10))); p:close()
    local s = io.open(base .. ".png", "wb"); s:write(emu.takeScreenshot()); s:close()
    emu.stop(0)
  end
end, emu.eventType.endFrame)
