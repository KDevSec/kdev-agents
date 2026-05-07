import os
import sys
import tempfile
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Provides a temporary directory simulating a project workspace.

    Layout:
        <tmp>/
            .kdev/design-flow/   (created on demand by tests)
            docs/                (created on demand)
    """
    return tmp_path
