import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest
import yaml as _yaml

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Temp dir simulating a project workspace.

    `.kdev/features/<slug>/` is created on demand by the code under test.
    """
    return tmp_path


@pytest.fixture
def run_cli(tmp_workspace):
    """Invoke cli.main(argv), auto-inject --workspace, capture stdout.

    Asserts rc == 0 and returns captured stdout (str). For new feature-first
    subcommand tests that read JSON / paths back out of the CLI.
    """
    from kdev_core.cli import main as _cli_main

    def _run(argv):
        if "--workspace" not in argv:
            argv = argv + ["--workspace", str(tmp_workspace)]
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = _cli_main(argv)
        assert rc == 0, f"CLI {argv} exited {rc}"
        return buf.getvalue()

    return _run


@pytest.fixture
def toy_table_file(tmp_path: Path) -> Path:
    """A minimal toy node-table YAML on disk (for advance/events CLI tests)."""
    table = {
        "flow": "toy", "max_retries": 2, "terminal_fail": "failed",
        "nodes": [
            {"id": "n1", "kind": "action", "next": ["g1"]},
            {"id": "g1", "kind": "gate", "next": ["n2", "n1"]},
            {"id": "n2", "kind": "action", "next": ["done"]},
            {"id": "done", "kind": "terminal", "next": []},
            {"id": "failed", "kind": "terminal", "next": []},
        ],
    }
    p = tmp_path / "toy.node-table.yml"
    p.write_text(_yaml.safe_dump(table), encoding="utf-8")
    return p
