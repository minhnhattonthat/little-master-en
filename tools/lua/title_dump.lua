-- Boot, press Start until the title bitmap starts unpacking ($00:AF6B, id 8), then dump VRAM 30 frames after the
-- last piece (id 14). Independent of boot timing (Mesen SRAM differs per ROM file). Writes OUT_DIR/title.vram.
local frame, started, done_at = 0, false, nil
emu.addMemoryCallback(function()
  local id = emu.getState()["cpu.a"] & 0xFF
  if id == 8 then started = true end
  if id == 14 then done_at = frame end
end, emu.callbackType.exec, 0x00AF6B, 0x00AF6B, emu.cpuType.snes, emu.memType.snesMemory)
emu.addEventCallback(function()
  if not started and frame % 10 < 4 then emu.setInput({start = true}, 0) end
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  frame = frame + 1
  if done_at and frame == done_at + 30 then
    local b = {}
    for a = 0, 0xFFFF do b[#b + 1] = string.char(emu.read(a, emu.memType.snesVideoRam)) end
    local f = io.open(OUT_DIR .. "/title.vram", "wb"); f:write(table.concat(b)); f:close()
    emu.stop(0)
  elseif frame > 3000 then
    emu.stop(1)
  end
end, emu.eventType.endFrame)
