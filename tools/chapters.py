"""Story-pass chapter files: the story blocks in script order, split into chapters for one reviewer each.

    python -X utf8 tools/chapters.py [--size 120] [--out work/qa/story/chapters]

Writes <block>_<NN>.txt, one `>> block:id | speaker | JP` / `EN` pair per entry, with control codes stripped
(page breaks shown as ` || `, line breaks as ` / `). Then:
    python -X utf8 $SKILL/scripts/qa_gate.py init work/qa/story/manifest.tsv work/qa/story/chapters --glob "*.txt"
"""
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lmtools.script import parse

STORY = ["msg36", "msg37", "ev03", "ev0A", "ev22"]
JPCHAR = re.compile(r"[぀-ヿ一-鿿]")
SPEAKER = re.compile(r"^(?:\{[^}]*\})*([^{「\"]{1,16}?)\{n\}[「\"]")


def clean(s):
    s = re.sub(r"\{clear:[0-9A-Fa-f]{2}\}", " || ", s)
    s = s.replace("{n}", " / ")
    s = re.sub(r"\{[^}]*\}", "", s)
    return re.sub(r" +", " ", s).strip(" |/")


def speaker(e):
    m = SPEAKER.match(e.en) or SPEAKER.match(e.jp)
    return m[1].strip() if m else "-"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", type=int, default=120)
    ap.add_argument("--out", default="work/qa/story/chapters")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for b in STORY:
        rows = [e for e in parse(Path(f"script/{b}.txt").read_text(encoding="utf-8")) if e.en and JPCHAR.search(e.jp)]
        for k in range(0, len(rows), a.size):
            path = out / f"{b}_{k // a.size + 1:02d}.txt"
            path.write_text("".join(f">> {b}:{e.id:04d} | {speaker(e)}\nJP: {clean(e.jp)}\nEN: {clean(e.en)}\n"
                                    for e in rows[k:k + a.size]), encoding="utf-8")
            n += 1
    print(f"{n} chapter files in {out}")


if __name__ == "__main__":
    main()
