"""Chunk-dictionary graphics codec (unpacker $00:AF6B, output to $7E:2000).

Data is 16-byte chunks. A set has a header table (8-byte entries: id, stream offset, first
new-chunk index, unused) and a dictionary of unique chunks. Stream ops, one output chunk each:
  00          end
  01-3F       n chunks: dictionary[next], next += 1 (next starts at the entry's index)
  40-7F xx    chunk ((op & 3F) << 8 | xx); remembered as `last`
  80 n        chunk `last`, n times
  81-FF       chunk last + (op & 7F)
"""
from . import rom

TITLE = {"table": 0x238000, "dict": 0x239000}   # SNES addresses; title bitmap = ids 8-14


def _entry(buf, table, id_):
    t = rom.lorom_to_pc(table)
    y = 8
    while True:
        w = buf[t + y] | buf[t + y + 1] << 8
        if w == 0:
            raise KeyError(f"chunk set {table:06X}: no id {id_}")
        if w == id_:
            word = lambda k: buf[t + y + k] | buf[t + y + k + 1] << 8
            return t + word(2), word(4)
        y += 8


def chunk_pc(dict_addr, idx):
    """PC of dictionary chunk `idx`; mirrors the unpacker's bank math (none/raises in the unreachable gap)."""
    off = 16 * idx
    low = (dict_addr & 0xFFFF) + (off & 0x7FFF)
    if low > 0xFFFF:
        raise ValueError(f"chunk {idx:#x} falls in the unreachable bank gap")
    return rom.lorom_to_pc(((dict_addr >> 16) + (off >> 15)) << 16 | low)


def decode_stream(stream, fetch, start, pos=0):
    out, nxt, last = bytearray(), start, 0
    while True:
        op = stream[pos]; pos += 1
        if op == 0:
            return bytes(out)
        if op < 0x40:
            for _ in range(op):
                out += fetch(nxt); nxt += 1
        elif op < 0x80:
            last = (op & 0x3F) << 8 | stream[pos]; pos += 1
            out += fetch(last)
        elif op == 0x80:
            n = stream[pos]; pos += 1
            out += fetch(last) * n
        else:
            out += fetch(last + (op & 0x7F))


def decode(buf, cset, id_):
    pos, start = _entry(buf, cset["table"], id_)
    return decode_stream(buf, lambda k: bytes(buf[chunk_pc(cset["dict"], k):chunk_pc(cset["dict"], k) + 16]), start, pos)


def encode(data, start):
    """Data -> (new dictionary bytes, stream, start). Dictionary index `start + i` holds chunk i of the dictionary.
    Back-refs (40-7F) reach indices < 0x4000 only, so repeats of chunks above that are stored again."""
    assert len(data) % 16 == 0
    seen, dictionary, stream = {}, bytearray(), bytearray()
    run, last = 0, None

    def flush():
        nonlocal run
        while run:
            n = min(run, 0x3F); stream.append(n); run -= n

    i = 0
    chunks = [bytes(data[k:k + 16]) for k in range(0, len(data), 16)]
    while i < len(chunks):
        c = chunks[i]
        idx = seen.get(c)
        if idx is None or idx >= 0x4000:
            idx = start + len(dictionary) // 16
            seen.setdefault(c, idx); dictionary += c; run += 1; i += 1
            continue
        flush()
        n = 1
        while i + n < len(chunks) and chunks[i + n] == c and n < 0xFF:
            n += 1
        if last is not None and 0 <= idx - last <= 0x7F and idx != last:
            stream.append(0x80 | (idx - last))
            n = 1
        else:
            stream += bytes([0x40 | idx >> 8, idx & 0xFF]); last = idx
            if n > 1:
                stream += bytes([0x80, n - 1])
        i += n
    flush()
    stream.append(0)
    return bytes(dictionary), bytes(stream), start
