"""Text block definitions (data/blocks.json), dumping and in-place insertion."""
import json
from dataclasses import dataclass
from pathlib import Path

from .rom import lorom_to_pc, pc_to_lorom
from .script import Entry


@dataclass
class Block:
    name: str
    type: str          # "ptr16" | "ptr24" | "fixed"
    table: int = 0     # ptr*: PC offset of pointer table
    count: int = 0
    bank: int = 0      # ptr16: SNES bank holding the strings
    start: int = 0     # fixed: PC offset of record 0's field
    stride: int = 0
    length: int = 0
    pad: int = 0x20
    box: str = ""


def load_blocks(path="data/blocks.json") -> list[Block]:
    out = []
    for raw in json.loads(Path(path).read_text(encoding="utf-8")):
        raw.pop("note", None)
        out.append(Block(**{k: int(v, 0) if isinstance(v, str) and k not in ("name", "type", "box") else v
                            for k, v in raw.items()}))
    return out


def _width(b):
    return 2 if b.type == "ptr16" else 3


def pointers(rom, b) -> list[int]:
    w, out = _width(b), []
    for i in range(b.count):
        v = int.from_bytes(rom[b.table + i * w:b.table + (i + 1) * w], "little")
        out.append(lorom_to_pc(b.bank << 16 | v if w == 2 else v))
    return out


def _meta(b):
    return {"box": b.box} if b.box else {}


def dump_block(rom, b, tbl) -> list[Entry]:
    if b.type == "fixed":
        out = []
        for i in range(b.count):
            off = b.start + i * b.stride
            raw = bytes(rom[off:off + b.length]).rstrip(bytes([b.pad]))
            out.append(Entry(i, off, _meta(b), tbl.decode(raw, 0, len(raw))[0]))
        return out
    seen, out, sp = {}, [], []
    for i, pc in enumerate(pointers(rom, b)):
        if pc in seen:
            out.append(Entry(i, pc, {**_meta(b), "same": str(seen[pc])}))
            continue
        text, n = tbl.decode(rom, pc)
        seen[pc] = i
        sp.append((pc, pc + n, i))
        out.append(Entry(i, pc, _meta(b), text))
    sp.sort()
    for (s0, e0, i0), (s1, _, i1) in zip(sp, sp[1:]):
        if s1 < e0:
            raise ValueError(f"{b.name}: string {i1} at {s1:06X} overlaps string {i0} at {s0:06X}")
    return out


def spans(rom, b, tbl) -> list[tuple[int, int]]:
    if b.type == "fixed":
        return [(b.start + i * b.stride, b.start + i * b.stride + b.length) for i in range(b.count)]
    out = [(b.table, b.table + b.count * _width(b))]
    for pc in sorted(set(pointers(rom, b))):
        out.append((pc, pc + tbl.decode(rom, pc)[1]))
    return out
