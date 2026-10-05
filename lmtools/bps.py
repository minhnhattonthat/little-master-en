"""Minimal BPS patch writer/reader (SourceRead + TargetRead runs; apply supports all four actions)."""
import zlib


def _num(n):
    out = bytearray()
    while True:
        x, n = n & 0x7F, n >> 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def create(src: bytes, tgt: bytes) -> bytes:
    out = bytearray(b"BPS1" + _num(len(src)) + _num(len(tgt)) + _num(0))
    pos, n, t_rel = 0, len(tgt), 0
    while pos < n:
        same = pos < len(src) and src[pos] == tgt[pos]
        end = pos
        while end < n and (end < len(src) and src[end] == tgt[end]) == same:
            end += 1
        if same:
            out += _num(((end - pos - 1) << 2) | 0)
            pos = end
            continue
        while pos < end:  # literal bytes; long runs of one byte become TargetRead 1 + TargetCopy
            lit = pos
            while lit < end and not (lit + 16 <= end and tgt[lit:lit + 16] == tgt[lit:lit + 1] * 16):
                lit += 1
            if lit > pos:
                out += _num(((lit - pos - 1) << 2) | 1) + tgt[pos:lit]
                pos = lit
                continue
            run = pos + 1
            while run < end and tgt[run] == tgt[pos]:
                run += 1
            out += _num(1) + tgt[pos:pos + 1]          # TargetRead 1 byte
            off = pos - t_rel                          # TargetCopy from that byte
            out += _num(((run - pos - 2) << 2) | 3) + _num(abs(off) << 1 | (off < 0))
            t_rel = pos + (run - pos - 1)
            pos = run
    out += zlib.crc32(src).to_bytes(4, "little") + zlib.crc32(tgt).to_bytes(4, "little")
    return bytes(out + zlib.crc32(out).to_bytes(4, "little"))


def apply(src: bytes, patch: bytes) -> bytes:
    if patch[:4] != b"BPS1":
        raise ValueError("not a BPS patch")
    if zlib.crc32(patch[:-4]) != int.from_bytes(patch[-4:], "little"):
        raise ValueError("patch crc mismatch")
    if zlib.crc32(src) != int.from_bytes(patch[-12:-8], "little"):
        raise ValueError("source crc mismatch (wrong source ROM)")
    i = 4

    def num():
        nonlocal i
        data, shift = 0, 1
        while True:
            x = patch[i]
            i += 1
            data += (x & 0x7F) * shift
            if x & 0x80:
                return data
            shift <<= 7
            data += shift

    num()
    tgt_size, meta = num(), num()
    i += meta
    out, s_rel, t_rel = bytearray(), 0, 0
    while i < len(patch) - 12:
        d = num()
        act, length = d & 3, (d >> 2) + 1
        if act == 0:
            out += src[len(out):len(out) + length]
        elif act == 1:
            out += patch[i:i + length]
            i += length
        else:
            off = num()
            off = -(off >> 1) if off & 1 else off >> 1
            if act == 2:
                s_rel += off
                out += src[s_rel:s_rel + length]
                s_rel += length
            else:
                t_rel += off
                for _ in range(length):
                    out.append(out[t_rel])
                    t_rel += 1
    if len(out) != tgt_size or zlib.crc32(out) != int.from_bytes(patch[-8:-4], "little"):
        raise ValueError("target crc mismatch")
    return bytes(out)
