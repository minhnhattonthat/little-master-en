import re
from pathlib import Path


def rows():
    text = Path("docs/playtest.md").read_text(encoding="utf-8")
    log = text.split("## Bug log", 1)[1].split("\n## ", 1)[0]
    return [[c.strip() for c in l.strip().strip("|").split("|")] for l in log.splitlines()
            if l.startswith("|") and not set(l) <= set("|- ") and "status" not in l]


def test_playtest_closed_bugs_name_tests():
    rs = rows()
    assert rs, "bug log has no rows"
    for r in rs:
        assert len(r) == 7, r
        assert r[4] in ("open", "fixed", "wontfix"), r
        if r[4] == "fixed":
            assert r[5].startswith("test_") and re.fullmatch(r"[0-9a-f]{7,}", r[6]), r
        if r[4] == "wontfix":
            assert r[5], f"wontfix needs a reason in the test column: {r}"
