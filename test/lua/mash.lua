-- Press Start/A alternately every 40 frames for 3600 frames; screenshot every 600 frames (for A/B comparisons).
local frame = 0
emu.addEventCallback(function()
  local phase = frame % 80
  if phase < 6 then emu.setInput({start = true}, 0) elseif phase >= 40 and phase < 46 then emu.setInput({a = true}, 0) end
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  frame = frame + 1
  if frame % 600 == 0 then
    local f = io.open(OUT_DIR .. "/mash_" .. frame .. ".png", "wb"); f:write(emu.takeScreenshot()); f:close()
  end
  if frame == 3600 then emu.stop(0) end
end, emu.eventType.endFrame)
