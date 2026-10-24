"""Run Mesen2 headless with a Lua script from tools/lua/."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MESEN = ROOT / "tools" / "mesen2" / "Mesen.exe"
# settings.json next to the exe = portable mode (skips the first-run wizard); Lua needs io for screenshots
SETTINGS = '{"Debug": {"ScriptWindow": {"AllowIoOsAccess": true}}}'


def run(rom_path, script: str, out_dir, timeout=120) -> int:
    settings = MESEN.parent / "settings.json"
    if not settings.exists():
        settings.write_text(SETTINGS)
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    lua = out_dir / "_run.lua"
    lua.write_text(f"OUT_DIR = [[{out_dir}]]\n" + (ROOT / "tools" / "lua" / script).read_text(encoding="utf-8"),
                   encoding="utf-8")
    return subprocess.run([str(MESEN), "--testrunner", str(Path(rom_path).resolve()), str(lua)],
                          timeout=timeout, capture_output=True).returncode
