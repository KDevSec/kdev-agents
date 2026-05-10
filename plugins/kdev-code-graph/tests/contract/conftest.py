from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
UA_SCHEMA = (
    REPO_ROOT
    / "docs/skills/kdev-code-graph/references/Understand-Anything"
    / "understand-anything-plugin/packages/core/src/schema.ts"
)
UA_TYPES = (
    REPO_ROOT
    / "docs/skills/kdev-code-graph/references/Understand-Anything"
    / "understand-anything-plugin/packages/core/src/types.ts"
)


@pytest.fixture(scope="session")
def ua_schema_text() -> str:
    if not UA_SCHEMA.exists():
        pytest.skip(f"UA repo not cloned at {UA_SCHEMA}")
    return UA_SCHEMA.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def ua_types_text() -> str:
    if not UA_TYPES.exists():
        pytest.skip(f"UA repo not cloned at {UA_TYPES}")
    return UA_TYPES.read_text(encoding="utf-8")
