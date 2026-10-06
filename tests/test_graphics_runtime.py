import json
from pathlib import Path

import pytest
from PIL import Image
from lmtools import build, chunkgfx, mesen, rom

pytestmark = pytest.mark.skipif(not mesen.MESEN.exists(), reason="needs Mesen2")


def px8(t):
    return [[sum(((t[16 * (p // 2) + 2 * r + (p % 2)] >> (7 - x)) & 1) << p for p in range(8)) for x in range(8)] for r in range(8)]


def bitmap(vram):
    """BG1 8bpp title bitmap (32x28 tiles, linear tilemap) -> 224 rows of 256 color indices."""
    P = [[0] * 256 for _ in range(224)]
    for t in range(32 * 28):
        p = px8(vram[64 * t:64 * t + 64])
        for y in range(8):
            for x in range(8):
                P[(t // 32) * 8 + y][(t % 32) * 8 + x] = p[y][x]
    return P


def title_dump(sfc, out):
    assert mesen.run(sfc, "title_dump.lua", out) == 0
    return (out / "title.vram").read_bytes()


def test_title_subtitle_is_english(tmp_path):
    e = next(g for g in json.loads(Path("data/graphics.json").read_text(encoding="utf-8")) if g["name"] == "title_subtitle")
    sfc = build.build(tmp_path / "b")
    en = bitmap(title_dump(sfc, tmp_path / "en"))
    jp = bitmap(title_dump(rom.BASE, tmp_path / "jp"))
    im = Image.open(e["png"]).convert("RGB")
    colors = {int(v): i for v, i in e["greys"].items()}
    x0, y0 = e["x"], e["y"]
    for y in range(224):
        for x in range(256):
            if x0 <= x < x0 + im.width and y0 <= y < y0 + im.height:
                assert en[y][x] == colors[im.getpixel((x - x0, y - y0))[0]], (x, y)
            else:
                assert en[y][x] == jp[y][x], (x, y)
