import json
from pathlib import Path

from lmtools.tbl import Table

T = Table.load("tbl/jp.tbl")


def test_known_strings(base):
    for s in json.loads(Path("tests/data/known_strings.json").read_text(encoding="utf-8")):
        text, _ = T.decode(base, int(s["pc"], 16), s["length"])
        assert text.rstrip() == s["text"], s["pc"]


def test_table_has_end():
    assert "end" in T.ctrl_enc
