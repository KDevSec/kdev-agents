from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_graph_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample-graph" / "knowledge-graph.json"


@pytest.fixture
def sample_rules_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample-rules"
