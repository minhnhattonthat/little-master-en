"""Text block definitions (data/blocks.json), dumping and in-place insertion."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .rom import lorom_to_pc, pc_to_lorom
from .script import Entry


@dataclass
class Block:
    name: str
    type: str          # "ptr16" | "ptr24" | "fixed" | "inline"
    tables: list = field(default_factory=list)  # ptr*: [[table_pc, count], ...] all pointing into one string pool
    bank: int = 0      # ptr16: SNES bank holding the strings
    count: int = 0     # fixed: record count
    start: int = 0     # fixed: PC offset of record 0's field
    stride: int = 0
    length: int = 0
    pad: int = 0x20
    box: str = ""
    exclude: list = field(default_factory=list)  # ptr*: [[start_pc, end_pc], ...] non-string data (screen scripts) never dumped
    ranges: list = field(default_factory=list)   # inline: [[start_pc, end_pc], ...] scanned for INLINE_OP text


def load_blocks(path="data/blocks.json") -> list[Block]:
    out = []
    for raw in json.loads(Path(path).read_text(encoding="utf-8")):
        raw.pop("note", None)
        raw["tables"] = [[int(t, 0) if isinstance(t, str) else t, n] for t, n in raw.get("tables", [])]
        for key in ("exclude", "ranges"):
            raw[key] = [[int(x, 0) if isinstance(x, str) else x for x in r] for r in raw.get(key, [])]
        out.append(Block(**{k: int(v, 0) if isinstance(v, str) and k not in ("name", "type", "box") else v
                            for k, v in raw.items()}))
    return out


def _width(b):
    return 2 if b.type == "ptr16" else 3


def slots(b):
    """PC offsets of every pointer slot in the block's tables."""
    w = _width(b)
    return [t + i * w for t, n in b.tables for i in range(n)]


def pointers(rom, b) -> list[int]:
    w, out = _width(b), []
    for s in slots(b):
        v = int.from_bytes(rom[s:s + w], "little")
        out.append(lorom_to_pc(b.bank << 16 | v if w == 2 else v))
    return out


def _meta(b):
    return {"box": b.box} if b.box else {}


JUMP = re.compile(r"\{(?:goto|j[0-9A-F]{2}):([0-9A-F]{6})\}")


def jump_targets(text) -> list[int]:
    """PC offsets of text addresses embedded in jump controls."""
    return [lorom_to_pc(int.from_bytes(bytes.fromhex(a), "little")) for a in JUMP.findall(text)]


def entry_points(rom, b, tbl) -> list[int]:
    """Pointer targets plus jump targets in the same LoROM bank(s) as the pool, sorted."""
    def inside(pc):
        return not any(a <= pc < z for a, z in b.exclude)

    todo = {pc for pc in pointers(rom, b) if inside(pc)}
    banks = {pc // 0x8000 for pc in todo}
    seen = set()
    while todo:
        pc = todo.pop()
        seen.add(pc)
        todo |= {t for t in jump_targets(tbl.decode(rom, pc)[0]) if t // 0x8000 in banks and inside(t)} - seen
    return sorted(seen)


INLINE_OP = bytes.fromhex("10ff")  # event opcode 10 = show text; inline text always starts with an FF control
INLINE_HEAD = re.compile(r"\{(p7F|p[0-7][0-9A-F]|color|speed):|\{clear:00\}")  # speaker header, position, colour...
INLINE_JUNK = re.compile(r"\{(g1[0-7E]|x0E)\}")


def _inline_ok(text) -> bool:
    if text.startswith("{p7F:"):
        return True
    return bool(INLINE_HEAD.match(text)) and not INLINE_JUNK.search(text) and len(re.sub(r"\{[^}]*\}", "", text)) >= 2


def inline_starts(rom, b, tbl) -> list[tuple[int, str, int]]:
    """(pc, text, length) for each cleanly-decoding inline text in b.ranges."""
    out, end = [], 0
    for lo, hi in b.ranges:
        pos = rom.find(INLINE_OP, lo, hi)
        while pos != -1:
            pc = pos + 1
            if pc >= end:
                try:
                    text, n = tbl.decode(rom, pc)
                except ValueError:
                    text = "["
                if "[" not in text and text.endswith("{end}") and pc + n <= hi and _inline_ok(text):
                    out.append((pc, text, n))
                    end = pc + n
            pos = rom.find(INLINE_OP, pos + 1, hi)
    return out


def dump_block(rom, b, tbl) -> list[Entry]:
    """Fixed: one entry per record. Pointer blocks: one entry per unique string, in address order.
    Inline: one entry per text found after the show-text opcode."""
    if b.type == "inline":
        return [Entry(i, pc, _meta(b), text) for i, (pc, text, _) in enumerate(inline_starts(rom, b, tbl))]
    if b.type == "fixed":
        out = []
        for i in range(b.count):
            off = b.start + i * b.stride
            raw = bytes(rom[off:off + b.length]).rstrip(bytes([b.pad]))
            out.append(Entry(i, off, _meta(b), tbl.decode(raw, 0, len(raw))[0]))
        return out
    return [Entry(i, pc, {**_meta(b), **({"cont": "1"} if cont else {})}, text)
            for i, (pc, text, n, cont) in enumerate(pool_strings(rom, b, tbl))]


def pool_strings(rom, b, tbl) -> list[tuple[int, str, int, bool]]:
    """(pc, text, length, cont) per entry point. A string that runs into the next entry point is cut there
    and flagged cont (it falls through into that entry, so the two must stay adjacent)."""
    eps = entry_points(rom, b, tbl)
    out = []
    for pc, nxt in zip(eps, eps[1:] + [None]):
        text, n = tbl.decode(rom, pc)
        cont = nxt is not None and pc + n > nxt
        if cont:
            full = text
            text, n = tbl.decode(rom, pc, nxt - pc)
            if n != nxt - pc or full != text + tbl.decode(rom, nxt)[0]:
                raise ValueError(f"{b.name}: entry point {nxt:06X} splits a token of the string at {pc:06X}")
        out.append((pc, text, n, cont))
    return out


def spans(rom, b, tbl) -> list[tuple[int, int]]:
    if b.type == "inline":
        return [(pc, pc + n) for pc, _, n in inline_starts(rom, b, tbl)]
    if b.type == "fixed":
        return [(b.start + i * b.stride, b.start + i * b.stride + b.length) for i in range(b.count)]
    return [(t, t + n * _width(b)) for t, n in b.tables] + string_spans(rom, b, tbl)


def string_spans(rom, b, tbl) -> list[tuple[int, int]]:
    return [(pc, pc + n) for pc, _, n, _ in pool_strings(rom, b, tbl)]
