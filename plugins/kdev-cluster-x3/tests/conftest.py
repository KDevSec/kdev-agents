import shutil
from pathlib import Path
import pytest


@pytest.fixture
def tmp_kdev(tmp_path: Path) -> Path:
    """A fresh .kdev/ dir with state.md/events.log/handoffs/ skeleton."""
    kdev = tmp_path / ".kdev"
    (kdev / "handoffs" / "reqs").mkdir(parents=True)
    (kdev / "handoffs" / "dev").mkdir()
    (kdev / "handoffs" / "test").mkdir()
    (kdev / "handoffs" / "review").mkdir()
    (kdev / "state.md").write_text("# KDev State\n\n", encoding="utf-8")
    (kdev / "events.log").write_text("", encoding="utf-8")
    return kdev
