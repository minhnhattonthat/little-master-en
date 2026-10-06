"""Move listed message tables (+ the strings they reach) into the expanded ROM.

A table is "listed" when the message table list at PC 010000 points at it: patching that 24-bit entry moves it.
Tables that share strings form a group placed in one 32 KB bank (16-bit pointers). Unlisted tables stay in place.
"""
from .blocks import (Block, JUMP, REMAP, TERMINATED, _check_entries, _enc, _pick, insert_block, jump_targets,
                     pointers, pool_strings)
from .rom import lorom_to_pc, pc_to_lorom

TABLE_LIST, LIST_LEN = 0x010000, 20
TEXT_START = 0x208000          # $C1:8000; bank $C0 holds the VWF code and font


class Alloc:
    def __init__(self, start=TEXT_START, end=0x3F0000):
        # (end: PC 0x3F0000+ would map to banks $7E/$7F, which are WRAM)
        self.pos, self.end = start, end

    def take(self, size):
        if size > 0x8000:
            raise ValueError(f"{size} bytes > 32 KB: a 16-bit-pointer group must fit one bank")
        if self.pos % 0x8000 + size > 0x8000:
            self.pos = (self.pos // 0x8000 + 1) * 0x8000
        if self.pos + size > self.end:
            raise ValueError("expanded ROM text space exhausted")
        pc, self.pos = self.pos, self.pos + size
        return pc


def list_entries(rom):
    out = {}
    for i in range(LIST_LEN):
        at = TABLE_LIST + 4 * i
        v = int.from_bytes(rom[at:at + 3], "little")
        if v & 0xFFFF >= 0x8000:
            out.setdefault(lorom_to_pc(v), []).append(at)
    return out


def _reach(strings, layout, b, table):
    """Entry PCs reachable from one table: its pointers, jump targets and cont successors."""
    order = [pc for pc, *_ in strings]
    info = {pc: (text, cont) for pc, text, _, cont in strings}
    todo = set(pointers(layout, Block(name=b.name, type=b.type, tables=[table], bank=b.bank)))
    seen = set()
    while todo:
        pc = todo.pop()
        if pc in seen or pc not in info:
            continue
        seen.add(pc)
        text, cont = info[pc]
        todo |= {t for t in jump_targets(text, len(layout)) if t in info}
        if cont:
            todo.add(order[order.index(pc) + 1])
    return seen


def table_groups(layout, b, tbl):
    strings = pool_strings(layout, b, tbl)
    groups = []
    for t in b.tables:
        reach = _reach(strings, layout, b, t)
        merged = [g for g in groups if g[1] & reach]
        for g in merged:
            groups.remove(g)
        groups.append(([t] + [x for g in merged for x in g[0]], reach.union(*(g[1] for g in merged))))
    return groups


def relocate_block(rom, layout, b, entries, tbl, source, en_tbl, alloc):
    listed = list_entries(layout)
    by_pc = {e.ptr: e for e in entries}
    _check_entries(b, entries, [pc for pc, *_ in pool_strings(layout, b, tbl)])
    keep = []
    for tables, reach in table_groups(layout, b, tbl):
        if not all(t in listed for t, _ in tables):
            keep += tables
            continue
        group = sorted(reach)
        chosen = {pc: _pick(by_pc[pc], source, tbl, en_tbl) for pc in group}
        for pc, (text, _) in chosen.items():
            e = by_pc[pc]
            if not text and "cont" not in e.meta:
                raise ValueError(f"{b.name} #{e.id}: empty {source.upper()} text")
            if ("cont" in e.meta) == bool(TERMINATED.search(text)):
                raise ValueError(f"{b.name} #{e.id}: " + ("cont entry must not end with {end}/{goto}"
                                                         if "cont" in e.meta else "must end with {end} or {goto}"))
        data = {pc: _enc(b, by_pc[pc], t, text) for pc, (text, t) in chosen.items()}
        table_bytes = sum(n * 2 for _, n in tables)
        try:
            base = alloc.take(table_bytes + sum(map(len, data.values())))
        except ValueError as err:
            raise ValueError(f"{b.name} tables {' '.join(f'{t:06X}' for t, _ in tables)}: {err}") from None
        new, pos = {}, base + table_bytes
        for pc in group:
            new[pc], pos = pos, pos + len(data[pc])

        def remap(m):
            raw = int.from_bytes(bytes.fromhex(m[2]), "little")
            target = lorom_to_pc(raw)
            if target not in new:
                raise ValueError(f"{b.name}: jump to {target:06X} outside its group")
            v = pc_to_lorom(new[target]) | raw & 0x800000
            return f"{{{m[1]}:{v.to_bytes(3, 'little').hex().upper()}}}"

        for pc in group:
            text, t = chosen[pc]
            blob = _enc(b, by_pc[pc], t, REMAP.sub(remap, text)) if JUMP.search(text) else data[pc]
            rom[new[pc]:new[pc] + len(blob)] = blob
        at = base
        for t, n in tables:
            for i in range(n):
                old = lorom_to_pc(b.bank << 16 | int.from_bytes(layout[t + 2 * i:t + 2 * i + 2], "little"))
                rom[at + 2 * i:at + 2 * i + 2] = (pc_to_lorom(new[old]) & 0xFFFF).to_bytes(2, "little")
            for le in listed[t]:
                rom[le:le + 3] = pc_to_lorom(at).to_bytes(3, "little")
            at += 2 * n
    if keep:
        kb = Block(name=b.name, type=b.type, tables=keep, bank=b.bank, box=b.box, exclude=b.exclude)
        kept = {pc for pc, *_ in pool_strings(layout, kb, tbl)}
        insert_block(rom, kb, [by_pc[pc] for pc in sorted(kept)], tbl, source, en_tbl, base=layout)
