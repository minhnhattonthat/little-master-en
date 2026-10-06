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
LAYOUT = {"n", "delay", "speed", "nop", "end", "c9B"}   # may change freely between JP and EN (c9B: number pad char)
NAME_INS = {"c87", "c88", "c98", "c99", "c9C"}          # name copies, sized by _name()
NAME_PX, LONG_NAME_PX, FIRST_NAME_PX = 68, 80, 56       # widest EN names (tests check them against the name tables)
NUM_INS = {"c83", "c84", "c85", "c86", "c8C", "c8D", "c8E", "c91", "c95", "c96", "c97", "c9A"}  # 4 digits


def _tokens(text):
    for m in TOKEN.finditer(text):
        yield (m[1], m[0]) if m[1] else (None, m[0])


def _name(name, tok):
    """(cells, px) of a name insert: c88 carries its byte length; c9C prints an 8-byte first name; c87/c98/c99 copy
    names of up to 11 bytes (monsters)."""
    if name == "c88":
        n = int(tok[5:7], 16)
        return n, NAME_PX if n <= 11 else LONG_NAME_PX
    return (8, FIRST_NAME_PX) if name == "c9C" else (11, NAME_PX)


def _px(text, widths):
    w = 0
    for name, tok in _tokens(text):
        if name is None:
            w += widths.get(tok, 8)
        elif name in NAME_INS:
            w += _name(name, tok)[1]
        elif name in NUM_INS:
            w += 4 * widths.get("0", 6)
    return w


def _cells(text):
    c = 0
    for name, tok in _tokens(text):
        if name is None:
            c += 2 if "㐀" <= tok <= "鿿" or tok == "々" else 1
        elif name in NAME_INS:
            c += _name(name, tok)[0]
        elif name in NUM_INS:
            c += 4
    return c


def _pages(text):
    return [p.split("{n}") for p in re.split(r"\{clear:[0-9A-Fa-f]{2}\}", text)]


def _controls(text, repos=False):
    """Control codes that must match JP; repos: cursor positions may move (count {pXX} codes, not their arguments)."""
    return Counter("{p}" if repos and POS.fullmatch(tok) else tok for name, tok in _tokens(text) if name and name not in LAYOUT)


HEADER = re.compile(r"^\{p7F:([0-9A-Fa-f]{2})\}")


def _window(e, box, windows):
    """Per-entry win= meta, else the speaker header's window ({p7F:xx}), else the block's box."""
    if "win" in e.meta:
        return windows.get(e.meta["win"], {})
    m = HEADER.match(e.jp)
    if m and m[1].upper() in windows.get("headers", {}):
        return windows[windows["headers"][m[1].upper()]]
    return windows.get(box, {})


def _shown_lines(page, cap):
    """Window lines a page occupies when the game wraps each line at `cap` cells."""
    return sum(max(1, -(-_cells(line) // cap)) for line in page) if cap else len(page)


def lint_entry(e, box, widths, windows, glossary, enc=None) -> list[str]:
    if not e.en:
        return []
    win = _window(e, box, windows)
    out = []
    if win.get("bytes") is not None:
        n = len(enc.encode(e.en)) if enc else len(e.en)
        if n > win["bytes"]:
            out.append(f"#{e.id}: {n} bytes > {win['bytes']}")
        return out
    if POS.search(e.en):
        jp_seg, en_seg = POS.split(e.jp), POS.split(e.en)
        slack = int(e.meta.get("slack", 0))       # slack=N: the screen has N free cells after the JP text
        for i, (j, s) in enumerate(zip(jp_seg, en_seg)):
            budget = max(_cells(x) for x in j.split("{n}")) + slack
            widest = max(_cells(x) for x in s.split("{n}"))
            if widest > budget:
                out.append(f"#{e.id}: segment {i} is {widest} cells > {budget} (positioned layout)")
    else:
        k = 0
        for page in _pages(e.en):
            for line in page:
                k += 1
                if win.get("px") and _px(line, widths) > win["px"]:
                    out.append(f"#{e.id}: line {k} is {_px(line, widths)} px > {win['px']}")
                cap = win.get("first_cells") if k == 1 and win.get("first_cells") else win.get("cells")   # first_cells:
                if cap and _cells(line) > cap:                                                   # line 1 is indented
                    out.append(f"#{e.id}: line {k} is {_cells(line)} cells > {cap}")
        if win.get("lines"):
            jp_pages = _pages(e.jp)
            cap = win.get("cells") or (win["px"] // 8 if win.get("px") else None)
            for i, page in enumerate(_pages(e.en)):
                jp_lines = _shown_lines(jp_pages[i], cap) if i < len(jp_pages) and win.get("scroll", True) else 0
                allowed = max(win["lines"], jp_lines)                # JP may auto-wrap and scroll; scroll=false: fixed
                if len(page) > allowed:
                    out.append(f"#{e.id}: page {i + 1} has {len(page)} lines > {allowed}")
    if enc is not None:
        try:
            enc.encode(e.en)
        except ValueError as err:
            out.append(f"#{e.id}: {err}")
    pal, ui = "01", ""
    for name, tok in _tokens(e.en):
        if name == "cF1":
            pal = tok[5:7]
        elif name is None and pal != "01" and "a" <= tok <= "z":
            ui += tok
    if ui:
        out.append(f"#{e.id}: lowercase under {{cF1}} palette draws UI graphics: '{ui}'")
    repos = "repos" in e.meta                   # repos: a value moved on its screen row (budget still per segment)
    jc, ec = _controls(e.jp, repos), _controls(e.en, repos)
    if jc != ec:
        out.append(f"#{e.id}: control codes differ: missing {sorted((jc - ec).elements())} extra {sorted((ec - jc).elements())}")
    flat = re.sub(r"\{(n|delay:[0-9A-Fa-f]{2})\}", " ", e.en).replace("_", " ")
    flat = re.sub(r" +", " ", flat)
    for term, en_term in (glossary.items() if e.meta.get("gloss") != "off" else []):   # gloss=off: tight UI labels
        if term in e.jp and en_term.lower() not in flat.lower():
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
