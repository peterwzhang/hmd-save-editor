import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def save_dir(tmp_path):
    """A temp copy of the synthetic fixture save folder, safe to mutate."""
    dest = tmp_path / "save"
    shutil.copytree(FIXTURES_DIR, dest)
    return dest
