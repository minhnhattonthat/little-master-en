"""Static checks on the asm hooks in the built ROM (review findings #1, #2)."""
import pytest
from lmtools import build, dis65, rom

HOOK_SITES = {0x00BE43: 6, 0x00BE70: 5, 0x00BF01: 4, 0x00BF94: 5, 0x01ECE5: 5}   # site -> overwritten bytes
SCAN = [(0x00B600, 0x00C300), (0x01EC00, 0x01EE00)]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return build.build(tmp_path_factory.mktemp("hooks"), "jp").read_bytes()


def jml(addr):
    return bytes([0x5C]) + addr.to_bytes(3, "little")


def test_newline_hook_returns_after_replayed_cmp(built):
    assert jml(0x00BF04) not in built[0x200000:]          # $BF04 is the hook's own bank byte
    assert jml(0x00BF07) in built[0x200000:]


def test_hook_sites_are_where_the_asm_puts_them(built):
    for site in HOOK_SITES:
        pc = rom.lorom_to_pc(site)
        assert built[pc] == 0x5C, f"no JML at ${site:06X}"


def test_no_branch_lands_inside_a_hook(base):
    targets = set()
    for lo, hi in SCAN:
        for line in dis65.disasm(base, rom.lorom_to_pc(lo), lo, hi - lo, True, True):
            addr, _, ins = line.split("  ", 2)
            mn, _, op = ins.partition(" ")
            if mn in ("BRA", "BRL", "BEQ", "BNE", "BCC", "BCS", "BPL", "BMI", "BVC", "BVS", "JMP", "JSR") and op.startswith("$") and len(op) == 5:
                targets.add((lo & 0xFF0000) | int(op[1:], 16))
    bad = [f"${t:06X} (hook ${s:06X})" for s, n in HOOK_SITES.items() for t in targets if s < t < s + n]
    assert not bad, bad
