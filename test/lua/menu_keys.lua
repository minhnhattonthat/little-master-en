-- Load STATE, press KEYS[i] at frame 10+70*(i-1) (4 frames), screenshot OUT_DIR/NAME_i.png 65 frames later.
local loaded, frame, ref = false, 0, nil
ref = emu.addMemoryCallback(function()
  if loaded then return end
  local f = io.open(STATE, "rb"); local d = f:read("a"); f:close(); emu.loadSavestate(d); loaded = true
  emu.removeMemoryCallback(ref, emu.callbackType.exec, 0, 0xFFFFFF)
end, emu.callbackType.exec, 0, 0xFFFFFF)
emu.addEventCallback(function()
  if not loaded then return end
  for i, k in ipairs(KEYS) do
    local f0 = 10 + (i - 1) * 70
    if frame >= f0 and frame < f0 + 4 then local t = {}; t[k] = true; emu.setInput(t, 0) end
  end
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if (frame - 10) % 70 == 65 then local s = io.open(OUT_DIR .. "/" .. NAME .. "_" .. ((frame - 10) // 70) .. ".png", "wb"); s:write(emu.takeScreenshot()); s:close() end
  if frame >= 10 + 70 * #KEYS then emu.stop(0) end
end, emu.eventType.endFrame)
