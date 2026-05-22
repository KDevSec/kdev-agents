from pathlib import Path

from kdev_ingestor.graph_io import KnowledgeGraph
from kdev_ingestor.linkers.base import (
    build_path_index,
    resolve_node_id,
    make_security_edge,
)
from kdev_ingestor.security_rules import SecurityRule
from kdev_ingestor.graph_io import upsert_node
from kdev_ingestor.linkers.pattern_linker import PatternLinker


def _rule(rule_id, patterns):
    return SecurityRule(
        rule_id=rule_id, title="t", summary="s",
        category="input_validation", source_file=Path("/tmp/x.md"),
        patterns=patterns,
    )


def _full(n):
    base = {"name": n["id"], "summary": "s", "tags": [], "complexity": "simple"}
    base.update(n)
    return base


def _graph_with_rule(nodes, rule_node_id):
    g = KnowledgeGraph(version="1", project={}, nodes=[])
    for n in nodes:
        upsert_node(g, _full(n))
    upsert_node(g, {
        "id": rule_node_id, "type": "concept", "name": "r",
        "summary": "s", "tags": ["kdev:security_rule"], "complexity": "moderate",
    })
    return g


def test_pattern_linker_function_level(tmp_path):
    (tmp_path / "a.py").write_text(
        "def f():\n    flagged_call('x')\n", encoding="utf-8"
    )
    g = _graph_with_rule(
        [
            {"id": "file:a.py", "type": "file", "filePath": "a.py"},
            {"id": "function:a.py:f", "type": "function", "filePath": "a.py",
             "lineRange": [1, 2]},
        ],
        "kdev-sec:rule:3.1.1",
    )
    edges = PatternLinker().link([_rule("3.1.1", ["flagged_call"])], g, tmp_path)
    assert edges == [{
        "source": "kdev-sec:rule:3.1.1", "target": "function:a.py:f",
        "type": "related", "direction": "forward", "weight": 0.6,
    }]


def test_pattern_linker_file_fallback(tmp_path):
    (tmp_path / "a.py").write_text("flagged_call('top')\n", encoding="utf-8")
    g = _graph_with_rule(
        [
            {"id": "file:a.py", "type": "file", "filePath": "a.py"},
            {"id": "function:a.py:f", "type": "function", "filePath": "a.py",
             "lineRange": [5, 9]},
        ],
        "kdev-sec:rule:3.1.1",
    )
    edges = PatternLinker().link([_rule("3.1.1", ["flagged_call"])], g, tmp_path)
    assert edges[0]["target"] == "file:a.py"


def test_pattern_linker_no_patterns_no_edges(tmp_path):
    (tmp_path / "a.py").write_text("flagged_call('x')\n", encoding="utf-8")
    g = _graph_with_rule(
        [{"id": "file:a.py", "type": "file", "filePath": "a.py"}],
        "kdev-sec:rule:3.1.1",
    )
    assert PatternLinker().link([_rule("3.1.1", [])], g, tmp_path) == []


def test_pattern_linker_skips_rule_not_in_graph(tmp_path):
    (tmp_path / "a.py").write_text("flagged_call('x')\n", encoding="utf-8")
    g = KnowledgeGraph(version="1", project={}, nodes=[])
    upsert_node(g, _full({"id": "file:a.py", "type": "file", "filePath": "a.py"}))
    assert PatternLinker().link([_rule("3.1.1", ["flagged_call"])], g, tmp_path) == []


def test_pattern_linker_dedupes_multiple_hits(tmp_path):
    (tmp_path / "a.py").write_text(
        "flagged_call(1)\nflagged_call(2)\n", encoding="utf-8"
    )
    g = _graph_with_rule(
        [
            {"id": "file:a.py", "type": "file", "filePath": "a.py"},
            {"id": "function:a.py:f", "type": "function", "filePath": "a.py",
             "lineRange": [1, 2]},
        ],
        "kdev-sec:rule:3.1.1",
    )
    edges = PatternLinker().link([_rule("3.1.1", ["flagged_call"])], g, tmp_path)
    assert len(edges) == 1


def _graph_with(nodes):
    return KnowledgeGraph(version="1", project={}, nodes=list(nodes))


def test_resolve_function_level():
    g = _graph_with([
        {"id": "file:a.py", "type": "file", "filePath": "a.py"},
        {"id": "function:a.py:f", "type": "function", "filePath": "a.py",
         "lineRange": [10, 25]},
    ])
    idx = build_path_index(g)
    assert resolve_node_id(idx, "a.py", 15) == "function:a.py:f"


def test_resolve_file_fallback():
    g = _graph_with([
        {"id": "file:a.py", "type": "file", "filePath": "a.py"},
        {"id": "function:a.py:f", "type": "function", "filePath": "a.py",
         "lineRange": [10, 25]},
    ])
    idx = build_path_index(g)
    assert resolve_node_id(idx, "a.py", 3) == "file:a.py"


def test_resolve_missing_path_returns_none():
    g = _graph_with([{"id": "file:a.py", "type": "file", "filePath": "a.py"}])
    idx = build_path_index(g)
    assert resolve_node_id(idx, "other.py", 1) is None


def test_make_security_edge_shape():
    e = make_security_edge("kdev-sec:rule:3.1.1", "function:a.py:f")
    assert e == {
        "source": "kdev-sec:rule:3.1.1",
        "target": "function:a.py:f",
        "type": "related",
        "direction": "forward",
        "weight": 0.6,
    }
