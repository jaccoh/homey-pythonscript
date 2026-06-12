import pytest
from pathlib import Path


@pytest.fixture
def tmp_venv_dir(tmp_path):
    """Temporary directory for venv storage."""
    venv_root = tmp_path / "venvs"
    venv_root.mkdir()
    return venv_root
