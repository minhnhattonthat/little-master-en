"""Little Master translation toolkit. Run from repo root: python lm.py <command> -h"""
import argparse
import sys
from pathlib import Path

from lmtools import gfx, rom


def cmd_info(a):
    b = rom.load_base()
    print(f"base ROM ok: {len(b):#x} bytes, checksum {rom.checksum(b):04X}")


def cmd_gfx(a):
    img = gfx.render(rom.load_base(), int(a.offset, 0), a.count, a.mode, a.bpp, a.w, a.h, a.cols, a.scale,
                     None if a.label is None else int(a.label, 0))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(a.out)
    print(f"wrote {a.out}")


def build_parser():
    ap = argparse.ArgumentParser(prog="lm")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(fn=cmd_info)
    p = sub.add_parser("gfx", help="render ROM graphics to PNG")
    p.add_argument("--offset", required=True)
    p.add_argument("--count", type=int, default=256)
    p.add_argument("--mode", choices=["tile", "linear"], default="tile")
    p.add_argument("--bpp", type=int, choices=[1, 2, 4], default=1)
    p.add_argument("--w", type=int, default=8)
    p.add_argument("--h", type=int, default=8)
    p.add_argument("--cols", type=int, default=16)
    p.add_argument("--scale", type=int, default=3)
    p.add_argument("--label", help="label first glyph with this number (hex ok)")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_gfx)
    return ap


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.fn(args)
