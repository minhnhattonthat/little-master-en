"""Script file format: one entry per string, JP original + EN translation."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Entry:
    id: int
    ptr: int
    meta: dict = field(default_factory=dict)
    jp: str = ""
    en: str = ""


def serialize(entries) -> str:
    out = []
    for e in entries:
        out += [f"#id {e.id:04d} ptr={e.ptr:06X}" + "".join(f" {k}={v}" for k, v in e.meta.items()),
                f"JP: {e.jp}", f"EN: {e.en}", ""]
    return "\n".join(out)


def parse(text: str) -> list[Entry]:
    entries = []
    for n, line in enumerate(text.lstrip("﻿").splitlines(), 1):
        if line.startswith("#id "):
            num, *kv = line[4:].split()
            e = Entry(int(num), 0)
            for item in kv:
                k, _, v = item.partition("=")
                if k == "ptr":
                    e.ptr = int(v, 16)
                else:
                    e.meta[k] = v
            entries.append(e)
        elif line[:3] in ("JP:", "EN:") and entries:
            setattr(entries[-1], line[:2].lower(), line[4:])
        elif line.strip():
            raise ValueError(f"line {n}: unexpected {line!r}")
    return entries


def save(path, entries, force=False):
    path = Path(path)
    if path.exists() and not force and any(e.en for e in parse(path.read_text(encoding="utf-8"))):
        raise FileExistsError(f"{path} has EN translations; refusing to overwrite (use --force)")
    path.write_text(serialize(entries), encoding="utf-8")
