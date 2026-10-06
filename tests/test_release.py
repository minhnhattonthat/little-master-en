import zipfile

import pytest
from lmtools import bps, release, rom


def test_hashes_known_value():
    h = release.hashes(b"abc")
    assert h == {"size": 3, "crc32": "352441C2", "md5": "900150983cd24fb0d6963f7d28e17f72",
                 "sha1": "a9993e364706816aba3e25717850c26c9cd0d89d"}


def test_readme_checksums_match_files():
    base, patched = bytes(rom.load_base()), b"\x01" * 16
    text = release.readme("1.0", base, patched)
    for v in release.hashes(base).values():
        assert str(v) in text
    assert release.hashes(patched)["crc32"] in text
    assert "512-byte header" in text and "v1.0" in text and "{" not in text


def test_release_patch_reproduces_build(tmp_path):
    z = release.release("0.9", out=tmp_path / "dist", build_dir=tmp_path / "b")
    names = zipfile.ZipFile(z).namelist()
    assert names == ["LittleMaster_EN_v0.9.bps", "README.txt"]
    patch = (tmp_path / "dist" / "LittleMaster_EN_v0.9.bps").read_bytes()
    assert bps.apply(bytes(rom.load_base()), patch) == (tmp_path / "b" / "lm_en.sfc").read_bytes()


def test_release_refuses_wrong_base(tmp_path, monkeypatch):
    bad = tmp_path / "bad.sfc"
    bad.write_bytes(b"\0" * 0x200000)
    monkeypatch.setattr(rom, "BASE", bad)
    with pytest.raises(ValueError, match="SHA1"):
        release.release("0.9", out=tmp_path / "dist", build_dir=tmp_path / "b")
    assert not (tmp_path / "dist").exists()
