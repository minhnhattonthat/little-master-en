"""Little Master translation toolkit. Run from repo root: python lm.py <command> -h"""
import argparse
import sys
from pathlib import Path

from lmtools import rom


def cmd_info(a):
    b = rom.load_base()
    print(f"base ROM ok: {len(b):#x} bytes, checksum {rom.checksum(b):04X}")


def build_parser():
    ap = argparse.ArgumentParser(prog="lm")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").set_defaults(fn=cmd_info)
    return ap


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.fn(args)
