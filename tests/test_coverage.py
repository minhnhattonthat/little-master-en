import json
from pathlib import Path

import pytest
from lmtools import ips
from lmtools.blocks import dump_block, load_blocks, spans
from lmtools.script import parse
from lmtools.tbl import Table

BETA2 = Path("patch/LM3-Beta2.IPS")


def test_blocks_dump(base):
    t = Table.load("tbl/jp.tbl")
    for b in load_blocks():
        assert dump_block(base, b, t), b.name


@pytest.mark.skipif(not BETA2.exists(), reason="Beta2 reference patch not present")
def test_beta2_regions_covered(base):
    t = Table.load("tbl/jp.tbl")
    known = [s for b in load_blocks() for s in spans(base, b, t)]
    known += [(int(r["start"], 16), int(r["end"], 16))
              for r in json.loads(Path("data/beta2_nontext.json").read_text(encoding="utf-8"))]
    missing = [(s, e) for s, e in ips.regions(ips.records(BETA2.read_bytes()))
               if not any(a < e and s < z for a, z in known)]
    assert not missing, " ".join(f"{s:06X}-{e:06X}" for s, e in missing)


def test_no_unknown_bytes_in_script():
    for p in Path("script").glob("*.txt"):
        for e in parse(p.read_text(encoding="utf-8")):
            assert "[" not in e.jp, f"{p.name} #{e.id}: {e.jp}"
