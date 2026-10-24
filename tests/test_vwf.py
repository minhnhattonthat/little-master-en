"""Visual acceptance: English lines render in the field, battle and item windows (vs the JP build)."""
from pathlib import Path

import pytest
from PIL import Image, ImageChops
from lmtools import build, mesen

STATES = ["ordinary_field_message", "batte_message", "item_menu"]   # next message after one A press = EN test line
WINDOW = (0, 154, 256, 224)
pytestmark = pytest.mark.skipif(not mesen.MESEN.exists() or not Path("work/states").exists(),
                                reason="needs Mesen2 and work/states")


def shots(sfc, out):
    lua = Path("tools/lua/state_shot.lua").read_text()
    for s in STATES:
        Path("tools/lua/_s.lua").write_text(f'STATE=[[{Path("work/states", s + ".mss").resolve()}]]\nNAME="{s}"\n'
                                           f"SHOT_AFTER=200\nPRESS_A_AT={{10}}\n" + lua)
        assert mesen.run(sfc, "_s.lua", out) == 0, s
    return {s: Image.open(Path(out) / f"{s}.png").convert("RGB").crop(WINDOW) for s in STATES}


def test_english_lines_render(tmp_path):
    en = shots(build.build(tmp_path / "en", "en"), tmp_path / "en_shots")
    jp = shots(build.build(tmp_path / "jp", "jp"), tmp_path / "jp_shots")
    for s in STATES:
        assert ImageChops.difference(en[s], jp[s]).getbbox() is not None, s
