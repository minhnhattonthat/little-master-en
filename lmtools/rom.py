"""Base ROM loading and LoROM address/checksum helpers."""
import hashlib
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "rom" / "Little Master - Nijiiro no Maseki (Japan).sfc"
SHA1 = "75b76715d4a20371e0340dbeee3a51ff6a1dbad3"


def load_base(path=BASE) -> bytearray:
    data = Path(path).read_bytes()
    if len(data) % 0x8000 == 512:  # copier header
        data = data[512:]
    got = hashlib.sha1(data).hexdigest()
    if got != SHA1:
        raise ValueError(f"{path}: SHA1 {got} != expected {SHA1} (need the unheadered Japan ROM)")
    return bytearray(data)


def lorom_to_pc(snes: int) -> int:
    addr = snes & 0xFFFF
    if addr < 0x8000:
        raise ValueError(f"{snes:06X} is not a LoROM ROM address")
    return ((snes >> 16) & 0x7F) * 0x8000 + addr - 0x8000


def pc_to_lorom(pc: int) -> int:
    return (pc // 0x8000) << 16 | 0x8000 | pc % 0x8000


def checksum(buf) -> int:
    # ponytail: plain sum, valid only for power-of-two ROM sizes (2MB/4MB are all we use)
    return (sum(buf) - sum(buf[0x7FDC:0x7FE0]) + 0x1FE) & 0xFFFF


def fix_checksum(buf: bytearray) -> None:
    c = checksum(buf)
    buf[0x7FDC:0x7FE0] = (c ^ 0xFFFF).to_bytes(2, "little") + c.to_bytes(2, "little")
