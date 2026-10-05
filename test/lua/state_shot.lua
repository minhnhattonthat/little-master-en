-- Load STATE (path) on the first CPU instruction (Mesen2 requires an exec callback), run SHOT_AFTER frames,
-- save NAME.png + text window RAM ($09F0-$0A0B) to NAME.txt, stop.
local frame, loaded, after, ref = 0, false, SHOT_AFTER or 30, nil
ref = emu.addMemoryCallback(function()
  if loaded then return end
  local f = io.open(STATE, "rb"); local data = f:read("a"); f:close()
  emu.loadSavestate(data); loaded = true; frame = 0
  emu.removeMemoryCallback(ref, emu.callbackType.exec, 0, 0xFFFFFF)
end, emu.callbackType.exec, 0, 0xFFFFFF)
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame == after then
    local s = io.open(OUT_DIR .. "/" .. NAME .. ".png", "wb"); s:write(emu.takeScreenshot()); s:close()
    local t = {}
    for a = 0x09F0, 0x0A1F, 2 do t[#t+1] = string.format("%04X=%04X", a, emu.read16(a, emu.memType.snesWorkRam)) end
    local r = io.open(OUT_DIR .. "/" .. NAME .. ".txt", "w"); r:write(table.concat(t, " ")); r:close()
    emu.stop(0)
  end
end, emu.eventType.endFrame)
