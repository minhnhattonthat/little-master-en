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


def _encode(tbl, e, source, allow_empty=False):
    text = e.jp if source == "jp" else e.en
    if not text and not allow_empty:
        raise ValueError(f"#{e.id}: empty {source.upper()} text")
    return tbl.encode(text)


def insert_block(rom, b, entries, tbl, source="en") -> None:
    """Write entries' `source` text back in place of the block's original strings."""
    if b.type == "fixed":
        for e in entries:
            data = _encode(tbl, e, source, allow_empty=True)
            if len(data) > b.length:
                raise ValueError(f"{b.name} #{e.id}: {len(data)} bytes > {b.length}")
            rom[e.ptr:e.ptr + b.length] = data + bytes([b.pad]) * (b.length - len(data))
        return
    if b.type == "inline":
        endcode, nop = tbl.ctrl_enc["end"][0], tbl.ctrl_enc["nop"][0]
        old = {pc: n for pc, _, n in inline_starts(rom, b, tbl)}
        for e in entries:
            data = _encode(tbl, e, source)
            if not data.endswith(endcode):
                raise ValueError(f"{b.name} #{e.id}: inline text must end with {{end}}")
            if len(data) > old[e.ptr]:
                raise ValueError(f"{b.name} #{e.id}: too long ({len(data)} > {old[e.ptr]} bytes); needs relocation")
            pad = (old[e.ptr] - len(data)) // len(nop)
            rom[e.ptr:e.ptr + old[e.ptr]] = data[:-len(endcode)] + nop * pad + endcode
        return
    _insert_pool(rom, b, entries, tbl, source)


def _insert_pool(rom, b, entries, tbl, source):
    # free space = the original string spans, merged, split at 32 KB bank boundaries for 16-bit pointers
    free = []
    for s, z in string_spans(rom, b, tbl):
        if free and free[-1][1] == s and not (b.type == "ptr16" and s % 0x8000 == 0):
            free[-1][1] = z
        else:
            free.append([s, z])
    data = {e.ptr: _encode(tbl, e, source, allow_empty="cont" in e.meta) for e in entries}
    units, cur = [], []
    for e in sorted(entries, key=lambda e: e.ptr):  # cont chains are allocated as one unit
        cur.append(e)
        if "cont" not in e.meta:
            units.append(cur)
            cur = []
    if cur:
        units.append(cur)
    new, k, pos = {}, 0, free[0][0]
    for unit in units:
        size = sum(len(data[e.ptr]) for e in unit)
        while k < len(free) and pos + size > free[k][1]:
            k += 1
            pos = free[k][0] if k < len(free) else pos
        if k == len(free):
            raise ValueError(f"{b.name}: out of space at #{unit[0].id} ({size} bytes)")
        for e in unit:
            new[e.ptr] = pos
            pos += len(data[e.ptr])

    def remap(m):
        old = int.from_bytes(bytes.fromhex(m[2]), "little")
        pc = lorom_to_pc(old)
        if pc not in new:
            return m[0]
        v = pc_to_lorom(new[pc]) | old & 0x800000
        return f"{{{m[1]}:{v.to_bytes(3, 'little').hex().upper()}}}"

    for e in entries:
        text = e.jp if source == "jp" else e.en
        blob = tbl.encode(REMAP.sub(remap, text)) if JUMP.search(text) else data[e.ptr]
        rom[new[e.ptr]:new[e.ptr] + len(blob)] = blob
    w = _width(b)
    for s in slots(b):
        v = int.from_bytes(rom[s:s + w], "little")
        old = lorom_to_pc(b.bank << 16 | v if w == 2 else v)
        nv = pc_to_lorom(new[old])
        nv = nv & 0xFFFF if w == 2 else nv | v & 0x800000
        rom[s:s + w] = nv.to_bytes(w, "little")


REMAP = re.compile(r"\{(goto|j[0-9A-F]{2}):([0-9A-F]{6})\}")
