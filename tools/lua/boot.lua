-- Boot smoke test: run 900 frames (~15 s), save a screenshot, fail if the screen is black.
local frame = 0
emu.addEventCallback(function()
  frame = frame + 1
  if frame == 900 then
    local f = io.open(OUT_DIR .. "/boot.png", "wb")
    f:write(emu.takeScreenshot())
    f:close()
    local buf, lit = emu.getScreenBuffer(), 0
    for i = 1, #buf, 97 do
      if (buf[i] & 0xFFFFFF) ~= 0 then lit = lit + 1 end
    end
    emu.stop(lit > 0 and 0 or 1)
  end
end, emu.eventType.endFrame)
