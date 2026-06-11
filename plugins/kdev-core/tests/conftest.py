import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Temp dir simulating a project workspace.

    `.kdev/features/<slug>/` is created on demand by the code under test.
    """
    return tmp_path
