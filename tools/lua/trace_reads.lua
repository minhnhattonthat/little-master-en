-- RE tool: log ROM data reads (PC offset ranges) with the reading CPU PC, per frame, frames F0..F1.
local F0, F1 = TRACE_F0 or 1, TRACE_F1 or 900
local frame, log, cur = 0, {}, nil
local function flush() if cur then log[#log+1] = string.format("%d %06X %d %06X", cur.f, cur.s, cur.n, cur.pc) cur = nil end end
emu.addMemoryCallback(function(addr, val)
  if frame < F0 or frame > F1 then return end
  local st = emu.getState()
  local pc = (st["cpu.k"] or 0) * 0x10000 + (st["cpu.pc"] or 0)
  if cur and cur.f == frame and addr == cur.s + cur.n and pc == cur.pc then cur.n = cur.n + 1
  else flush(); cur = {f = frame, s = addr, n = 1, pc = pc} end
end, emu.callbackType.read, 0, 0x1FFFFF, emu.cpuType.snes, emu.memType.snesPrgRom)
emu.addEventCallback(function()
  frame = frame + 1
  if frame == F1 then
    flush()
    local f = io.open(OUT_DIR .. "/reads.txt", "w"); f:write(table.concat(log, "\n")); f:close()
    local s = io.open(OUT_DIR .. "/trace.png", "wb"); s:write(emu.takeScreenshot()); s:close()
    emu.stop(0)
  end
end, emu.eventType.endFrame)
