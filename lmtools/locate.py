"""Helpers for finding text, pointers and free space in the ROM."""
import re

from .rom import pc_to_lorom

TAG = re.compile(r"\{[^}]*\}")


def find_bytes(rom, needle: bytes) -> list[int]:
    return [m.start() for m in re.finditer(b"(?=" + re.escape(needle) + b")", rom)]


def find_pointers(rom, pc) -> list[tuple[int, int]]:
    v = pc_to_lorom(pc)
    hits = [(o, 2) for o in find_bytes(rom, (v & 0xFFFF).to_bytes(2, "little"))]
    for hi in (0, 0x800000):
        hits += [(o, 3) for o in find_bytes(rom, (v | hi).to_bytes(3, "little"))]
    return sorted(set(hits))


def free_runs(rom, min_len=0x100) -> list[tuple[int, int, int]]:
    pat = rb"\x00{%d,}|\xff{%d,}" % (min_len, min_len)
    return [(m.start(), len(m[0]), m[0][0]) for m in re.finditer(pat, rom)]


def scan_strings(rom, tbl, min_chars=4, exclude=()) -> list[tuple[int, str]]:
    """Heuristic: strings start at 0 or right after an {end} code; keep fully-decodable ones."""
    end = tbl.ctrl_enc["end"][0]
    out = []
    for s in [0] + [m.start() + len(end) for m in re.finditer(re.escape(end), rom)]:
        if any(a <= s < b for a, b in exclude):
            continue
        try:
            text, _ = tbl.decode(rom, s, maxlen=256)
        except ValueError:
            continue
        if "[" not in text and len(TAG.sub("", text)) >= min_chars:
            out.append((s, text))
    return out
