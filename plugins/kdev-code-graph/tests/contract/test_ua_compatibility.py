"""Contract guardrail: detect breaking changes in upstream UA schema.

Run on every CI pass and after every UA upgrade. Failure means our
S3-tag strategy assumption no longer holds and the kdev-code-graph
adapter needs review.
"""

import re

EXPECTED_NODE_TYPES = {
    "file", "function", "class", "module", "concept",
    "config", "document", "service", "table", "endpoint",
    "pipeline", "schema", "resource",
    "domain", "flow", "step",
    "article", "entity", "topic", "claim", "source",
}
EXPECTED_EDGE_TYPES_WE_USE = {
    "documents", "tested_by", "related", "contains", "calls",
    "imports", "depends_on",
}


def test_node_passthrough_still_present(ua_schema_text: str):
    node_block = re.search(
        r"GraphNodeSchema\s*=\s*z\.object\(\{.*?\}\)\.passthrough\(\)",
        ua_schema_text,
        re.DOTALL,
    )
    assert node_block, "GraphNodeSchema lost .passthrough() — kdev relies on it"


def test_node_types_superset(ua_schema_text: str):
    for ntype in EXPECTED_NODE_TYPES:
        assert f'"{ntype}"' in ua_schema_text, (
            f"node type {ntype!r} missing from UA schema.ts"
        )


def test_edge_types_superset(ua_schema_text: str):
    for etype in EXPECTED_EDGE_TYPES_WE_USE:
        assert f'"{etype}"' in ua_schema_text, (
            f"edge type {etype!r} missing from UA schema.ts"
        )


def test_node_has_tags_field(ua_types_text: str):
    assert re.search(
        r"interface\s+GraphNode\b.*?tags\s*:\s*string\[\]",
        ua_types_text,
        re.DOTALL,
    ), "GraphNode.tags field changed shape"


def test_edge_no_passthrough(ua_schema_text: str):
    edge_block = re.search(
        r"GraphEdgeSchema\s*=\s*z\.object\(\{(?:[^{}]|\{[^{}]*\})*?\}\)(?P<tail>[^;]*)",
        ua_schema_text,
        re.DOTALL,
    )
    assert edge_block, "GraphEdgeSchema not found"
    tail = edge_block.group("tail")
    assert ".passthrough()" not in tail, (
        "GraphEdgeSchema gained .passthrough() — opportunity to simplify; "
        "review docs/skills/kdev-code-graph/2026-05-10-实施计划-v2.md"
    )
