"""Translation lint: line widths (VWF), lines per page, positioned-layout cells, control parity, glossary, name bytes."""
import json
import re
from collections import Counter
from pathlib import Path

from .blocks import load_blocks
from .font import parse_font
from .script import parse
from .tbl import Table

TOKEN = re.compile(r"\{(\w+)(?::([0-9A-Fa-f]*))?\}|\[[0-9A-Fa-f]{2}\]|.", re.S)
POS = re.compile(r"\{p(?!7F)[0-7][0-9A-Fa-f]:[0-9A-Fa-f]{2}\}")      # cursor positioning (p7F = speaker header)
LAYOUT = {"n", "delay", "speed", "nop", "clear", "scroll", "end"}    # may change freely between JP and EN
NAME_INS = {"c87", "c88", "c98", "c99"}                            # name copies: counted as 8 chars
NUM_INS = {"c83", "c84", "c85", "c86", "c8C", "c8D", "c8E", "c91", "c95", "c96", "c97", "c9A", "c9C"}  # 4 digits


def _tokens(text):
    for m in TOKEN.finditer(text):
        yield (m[1], m[0]) if m[1] else (None, m[0])


def _px(text, widths):
    w = 0
    for name, tok in _tokens(text):
        if name is None:
            w += widths.get(tok, 8)
        elif name in NAME_INS:
            w += 8 * widths.get("n", 6)
        elif name in NUM_INS:
            w += 4 * widths.get("0", 6)
    return w


def _cells(text):
    c = 0
    for name, tok in _tokens(text):
        if name is None:
            c += 2 if "㐀" <= tok <= "鿿" or tok == "々" else 1
        elif name in NAME_INS:
            c += 8
        elif name in NUM_INS:
            c += 4
    return c


def _pages(text):
    return [p.split("{n}") for p in re.split(r"\{clear:[0-9A-Fa-f]{2}\}", text)]


def _controls(text):
    return Counter(tok for name, tok in _tokens(text) if name and name not in LAYOUT)


def lint_entry(e, box, widths, windows, glossary, enc=None) -> list[str]:
    if not e.en:
        return []
    win = windows.get(e.meta.get("win", box), {})
    out = []
    if win.get("bytes") is not None:
        n = len(enc.encode(e.en)) if enc else len(e.en)
        if n > win["bytes"]:
            out.append(f"#{e.id}: {n} bytes > {win['bytes']}")
        return out
    if POS.search(e.en):
        jp_seg, en_seg = POS.split(e.jp), POS.split(e.en)
        for i, (j, s) in enumerate(zip(jp_seg, en_seg)):
            if _cells(s) > _cells(j):
                out.append(f"#{e.id}: segment {i} is {_cells(s)} cells > {_cells(j)} (positioned layout)")
    else:
        if win.get("px"):
            k = 0
            for page in _pages(e.en):
                for line in page:
                    k += 1
                    if _px(line, widths) > win["px"]:
                        out.append(f"#{e.id}: line {k} is {_px(line, widths)} px > {win['px']}")
        if win.get("lines"):
            jp_pages = _pages(e.jp)
            for i, page in enumerate(_pages(e.en)):
                allowed = max(win["lines"], len(jp_pages[i]) if i < len(jp_pages) else 0)
                if len(page) > allowed:
                    out.append(f"#{e.id}: page {i + 1} has {len(page)} lines > {allowed}")
    jc, ec = _controls(e.jp), _controls(e.en)
    if jc != ec:
        out.append(f"#{e.id}: control codes differ: missing {sorted((jc - ec).elements())} extra {sorted((ec - jc).elements())}")
    for term, en_term in glossary.items():
        if term in e.jp and en_term not in e.en:
            out.append(f"#{e.id}: glossary: {term} should be '{en_term}'")
    return out


def load_glossary(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(cells) >= 2 and cells[0] and cells[1] and cells[0] != "JP" and not set(cells[0]) <= set("-: "):
            out[cells[0]] = cells[1]
    return out


def lint_all(root=".") -> list[str]:
    root = Path(root)
    windows = json.loads((root / "data/windows.json").read_text(encoding="utf-8"))
    glossary = load_glossary(root / "glossary.md") if (root / "glossary.md").exists() else {}
    widths = {ch: w for ch, (w, _) in parse_font((root / "src/font/vwf.txt").read_text(encoding="utf-8")).items()}
    enc = Table.load(root / "tbl/en.tbl")
    out = []
    for b in load_blocks(root / "data/blocks.json"):
        for e in parse((root / f"script/{b.name}.txt").read_text(encoding="utf-8")):
            out += [f"{b.name} {m}" for m in lint_entry(e, b.box, widths, windows, glossary, enc)]
    return out
