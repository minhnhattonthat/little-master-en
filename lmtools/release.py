"""Release packaging: verified .bps + README with base ROM checksums, zipped into dist/."""
import hashlib
import zipfile
import zlib
from pathlib import Path

from . import bps, build, rom

TEMPLATE = Path(__file__).resolve().parent.parent / "src/release/README.txt"


def hashes(data: bytes) -> dict:
    return {"size": len(data), "crc32": f"{zlib.crc32(data):08X}",
            "md5": hashlib.md5(data).hexdigest(), "sha1": hashlib.sha1(data).hexdigest()}


def readme(version: str, base: bytes, patched: bytes) -> str:
    return TEMPLATE.read_text(encoding="utf-8").format(version=version, out_crc32=hashes(patched)["crc32"], **hashes(base))


def release(version: str, out="dist", build_dir="build") -> Path:
    base = bytes(rom.load_base(rom.BASE))                 # raises on a wrong/headered-and-wrong ROM
    sfc = build.build(build_dir)
    built = sfc.read_bytes()
    patch = (Path(build_dir) / "lm_en.bps").read_bytes()
    if bps.apply(base, patch) != built:
        raise RuntimeError("patch does not reproduce the build")
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    name = f"LittleMaster_EN_v{version}"
    (out / f"{name}.bps").write_bytes(patch)
    (out / "README.txt").write_text(readme(version, base, built), encoding="utf-8", newline="\r\n")
    z = out / f"{name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        f.write(out / f"{name}.bps", f"{name}.bps")
        f.write(out / "README.txt", "README.txt")
    return z
