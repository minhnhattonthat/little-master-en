"""Read/apply IPS patches (used to map what Beta2 changed; Beta2 is reference only)."""


def records(patch: bytes) -> list[tuple[int, bytes]]:
    if patch[:5] != b"PATCH":
        raise ValueError("not an IPS patch")
    i, out = 5, []
    while patch[i:i + 3] != b"EOF":
        if i + 5 > len(patch):
            raise ValueError("truncated IPS patch")
        off, n = int.from_bytes(patch[i:i + 3], "big"), int.from_bytes(patch[i + 3:i + 5], "big")
        i += 5
        if n == 0:
            out.append((off, patch[i + 2:i + 3] * int.from_bytes(patch[i:i + 2], "big")))
            i += 3
        else:
            out.append((off, patch[i:i + n]))
            i += n
    return out


def apply(rom, patch: bytes) -> bytearray:
    out = bytearray(rom)
    for off, data in records(patch):
        if off + len(data) > len(out):
            out += bytes(off + len(data) - len(out))
        out[off:off + len(data)] = data
    return out


def regions(recs, gap=0x40) -> list[tuple[int, int]]:
    reg = []
    for off, data in sorted(recs):
        end = off + len(data)
        if reg and off <= reg[-1][1] + gap:
            reg[-1][1] = max(reg[-1][1], end)
        else:
            reg.append([off, end])
    return [tuple(r) for r in reg]
