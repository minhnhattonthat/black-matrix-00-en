-- Black/Matrix 00 debug warp for emu.py (PCSX-Redux). Globals (--var): SCENE = SCENARIO.DAT sub to start instead
-- of the New Game scenario. Boots cold, walks the title menu to NEW GAME, then leaves input to emu.py --mash.
-- Ends early when the script moves on to another scenario. Logs every DAT sub-file load and, in OUT/jp.txt,
-- every full-width (Japanese) glyph the font cache rasterised once the scene runs: "frame code".
--   python -X utf8 <skill>/scripts/emu.py build/bm00-en.cue --out work/qa/w020 --script tools/debug/warp.lua
--          --var SCENE=20 --frames 6000 --mash 20 --shot-every 60 --sheet --sav work/qa/blank.mcd
-- RAM (SLPS_035.73, docs/script-format.md): gp = 0x8006B224; gp+0x15c -> interpreter (in scratchpad), +0x10 = u16
-- script variables, var 0x50 = scenario to run; gp+0x18c -> CD request (+8 DAT index, +0xa sub);
-- gp+0x1fc -> glyph cache (+8 w, +0xa h, +0x1c entries of 12 bytes: u16 code ...).
-- The main loop loads var 0x50 at 0x8001231c: 0x80012328 `andi a1, v0, 0xffff` becomes `addiu a1, zero, SCENE`,
-- so the first scenario load (New Game: 1) fetches SCENE instead; the run ends before a second load.
local ffi = require("ffi")
local bit = require("bit")
local mem, scratch = PCSX.getMemPtr(), PCSX.getScratchPtr()
local function ptr(a)   -- byte pointer for a main-RAM or scratchpad address
  if a >= 0x1f800000 and a < 0x1f800400 then return scratch + (a - 0x1f800000) end
  return mem + bit.band(a, 0x1fffff)
end
local function u16(a) return ffi.cast("uint16_t*", ptr(a)) end
local function u32(a) return ffi.cast("uint32_t*", ptr(a)) end
local function ok(a) return (a >= 0x80000000 and a < 0x80200000) or (a >= 0x1f800000 and a < 0x1f800400) end
local GP = 0x8006B224
local DATS = { [0] = "SYSTEM", "SCENARIO", "BATTLE", "EVENT", "TOWN" }

local function vars()   -- u16 array (0x260 entries) and u32 array (0x20) of script variables, or nil
  local interp = u32(GP + 0x15c)[0]
  if not ok(interp) then return nil end
  local v16, v32 = u32(interp + 0x10)[0], u32(interp + 0x14)[0]
  if ok(v16) and ok(v32) then return v16, v32 end
end
local function var50()
  local v16 = vars()
  if v16 then return u16(v16 + 0x50 * 2) end
end

-- INJECT (from tools/debug/ds2inject.py): the regions the load-game routine (0x80039A30) fills from a save, taken
-- from a DuckStation savestate's RAM, as { {addr, hexbytes}, ... }; "V16"/"V32" stand for the variable arrays.
local function inject()
  local v16, v32 = vars()
  for _, e in ipairs(INJECT) do
    local addr = e[1] == "V16" and v16 or e[1] == "V32" and v32 or e[1]
    if addr then
      local p = ptr(addr)
      for i = 1, #e[2] / 2 do p[i - 1] = tonumber(e[2]:sub(2 * i - 1, 2 * i), 16) end
    end
  end
end

if SCENE then u32(0x80012328)[0] = 0x24050000 + SCENE end

local jp = Support.File.open(OUT .. "jp.txt", "TRUNCATE")
local seen, lastload, started, injected = {}, "", false, false
L.on_frame(function(n)
  local req = u32(GP + 0x18c)[0]
  if ok(req) then
    local s = string.format("%s/%d", DATS[u16(req + 8)[0]] or u16(req + 8)[0], u16(req + 0xa)[0])
    if s ~= lastload then L.log(n .. " load " .. s); lastload = s end
  end
  local cache = u32(GP + 0x1fc)[0]
  if ok(cache) then
    local w, h, ent = u16(cache + 8)[0], u16(cache + 0xa)[0], u32(cache + 0x1c)[0]
    if ok(ent) and w * h <= 1024 then
      for i = 0, w * h - 1 do
        local code = u16(ent + 12 * i)[0]
        if code > 0x8140 and not seen[code] then
          seen[code] = n
          if started or not SCENE then jp:write(string.format("%d %04X\n", n, code)) end
        end
      end
    end
  end
  local v = var50()
  local sc = v and v[0] or 0
  if sc > 0 and not started then
    started = true
    if SCENE then v[0] = SCENE; sc = SCENE end
    L.log(n .. " scenario " .. sc .. " running; vars at " .. string.format("%08X %08X", vars()))
  end
  if INJECT and started and not injected then
    if lastload == "SCENARIO/" .. (SCENE or sc) then injectat = injectat or n + (INJECT_AFTER or 30) end
    if injectat and n >= injectat then   -- after the scene's script has started
      injected = true
      inject()
      if SCENE then var50()[0] = SCENE end
      L.log(n .. " injected save regions")
    end
  end
  if not started then
    -- FMV skip, warning, title, then the menu: Up first because the cursor starts on LOAD GAME
    -- One-frame taps: a held Start opens the menu and is read again as a confirm on LOAD GAME. Start skips the
    -- FMV and warning and opens the menu. The title overlay (SYSTEM sub 216) keeps its highlight bar object at
    -- 0x801d60b8: byte +1 is 0xe0 while the menu is open (0x80 on the title), byte +6 its y: 12 NEW GAME,
    -- 52 LOAD GAME (the default), 92 CONFIG. On the LOAD/CONFIG screens (SYSTEM subs 80/50) Cross backs out.
    if n > 600 and n % 45 == 0 then
      if lastload == "SYSTEM/80" or lastload == "SYSTEM/50" then L.press("cross", 1)
      elseif mem[0x1d60b9] ~= 0xe0 then L.press("start", 1)
      else L.press(mem[0x1d60be] == 12 and "start" or "up", 1) end
    end
    if L.route_done() then L.press("-", 1) end   -- keep emu.py --mash (Circle confirms LOAD GAME) off the menus
  elseif sc ~= (SCENE or sc) then
    L.log(n .. " next scenario " .. sc); L.shot("final.png"); jp:close(); L.finish(0)
  end
end)
