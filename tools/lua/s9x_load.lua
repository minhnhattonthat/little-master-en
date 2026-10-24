-- Run a player's Snes9x state in Mesen: load base STATE (.mss, same game mode), then overwrite WRAM, VRAM,
-- SRAM and CPU regs from tools/s9x_state.py dumps (S9X_PREFIX, S9X_REGS). PPU regs/CGRAM stay the base
-- state's until the game rewrites them. KEYS = {{frame, "a"}, ...} (4-frame press); shot every SHOT_EVERY
-- frames to OUT_DIR/fNNNN.png, stop at FRAMES. Optional WATCH = {lo, hi} logs writes there, and
-- EXEC = {addr, ...} logs regs + 16-bit return address at each call, to writes.txt.
local frame, loaded, ref = 0, false, nil
local log = {}
local function inject(path, mem, base)
  local f = io.open(path, "rb"); local d = f:read("a"); f:close()
  local n = math.min(#d, emu.getMemorySize(mem))
  for i = 1, n do emu.write(base + i - 1, d:byte(i), mem) end
end
ref = emu.addMemoryCallback(function()
  if loaded then return end
  local f = io.open(STATE, "rb"); local d = f:read("a"); f:close()
  emu.loadSavestate(d)
  inject(S9X_PREFIX .. ".RAM", emu.memType.snesWorkRam, 0)
  inject(S9X_PREFIX .. ".VRA", emu.memType.snesVideoRam, 0)
  inject(S9X_PREFIX .. ".SRA", emu.memType.snesSaveRam, 0)
  local s = {}
  for k, v in pairs(S9X_REGS) do s[k] = v end
  s["cpu.emulationMode"] = false
  emu.setState(s)
  loaded = true
  emu.removeMemoryCallback(ref, emu.callbackType.exec, 0, 0xFFFFFF)
end, emu.callbackType.exec, 0, 0xFFFFFF)
if WATCH then
  emu.addMemoryCallback(function(addr, val)
    if not loaded then return end
    local s = emu.getState()
    log[#log+1] = string.format("f%d %02X:%04X w%06X=%02X", frame, s["cpu.k"], s["cpu.pc"], addr, val)
  end, emu.callbackType.write, WATCH[1], WATCH[2])
end
for _, a in ipairs(EXEC or {}) do
  emu.addMemoryCallback(function()
    if not loaded then return end
    local s = emu.getState()
    local sp = s["cpu.sp"]
    local ret = emu.read(sp + 1, emu.memType.snesWorkRam) | (emu.read(sp + 2, emu.memType.snesWorkRam) << 8)
    local dp = s["cpu.d"] + 0x14   -- the message routines keep the string pointer in [$14]
    local p14 = emu.read16(dp, emu.memType.snesWorkRam) | (emu.read(dp + 2, emu.memType.snesWorkRam) << 16)
    log[#log+1] = string.format("f%d exec %06X A=%04X X=%04X Y=%04X ret=%04X [14]=%06X", frame, a, s["cpu.a"], s["cpu.x"], s["cpu.y"], ret, p14)
  end, emu.callbackType.exec, a, a)
end
emu.addEventCallback(function()
  for _, p in ipairs(KEYS or {}) do
    if loaded and frame >= p[1] and frame < p[1] + 4 then emu.setInput({[p[2]] = true}, 0) end
  end
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  if not loaded then return end
  frame = frame + 1
  if frame % (SHOT_EVERY or 30) == 0 then
    local h = io.open(string.format("%s/f%04d.png", OUT_DIR, frame), "wb"); h:write(emu.takeScreenshot()); h:close()
  end
  if frame >= (FRAMES or 300) then
    local s = emu.getState()
    log[#log+1] = string.format("end PC %02X:%04X", s["cpu.k"], s["cpu.pc"])
    local h = io.open(OUT_DIR .. "/writes.txt", "w"); h:write(table.concat(log, "\n")); h:close()
    emu.stop(0)
  end
end, emu.eventType.endFrame)
