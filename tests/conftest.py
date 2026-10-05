import pytest
from lmtools import rom


@pytest.fixture(scope="session")
def base():
    return bytes(rom.load_base())
