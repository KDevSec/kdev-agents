import json
from pathlib import Path

import pytest

from kdev_ingestor.graph_io import (
    GraphIOError,
    KnowledgeGraph,
    load_graph,
    save_graph,
    upsert_node,
    upsert_edge,
    find_nodes_by_tag,
)


def _copy_graph(src: Path, tmp_path: Path) -> Path:
    dst = tmp_path / "knowledge-graph.json"
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dst


def test_load_graph_returns_knowledge_graph(sample_graph_path: Path):
    graph = load_graph(sample_graph_path)
    assert isinstance(graph, KnowledgeGraph)
    assert graph.project["name"] == "tiny-project"
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1


def test_load_graph_missing_file_raises(tmp_path: Path):
    with pytest.raises(GraphIOError, match="not found"):
        load_graph(tmp_path / "nope.json")


def test_load_graph_rejects_non_object(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(GraphIOError, match="top-level"):
        load_graph(bad)


def test_load_graph_rejects_missing_required_keys(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"version":"1"}', encoding="utf-8")
    with pytest.raises(GraphIOError, match="required key"):
        load_graph(bad)


def test_save_graph_roundtrip(sample_graph_path: Path, tmp_path: Path):
    target = _copy_graph(sample_graph_path, tmp_path)
    graph = load_graph(target)
    save_graph(graph, target)
    reloaded = load_graph(target)
    assert reloaded.nodes == graph.nodes
    assert reloaded.edges == graph.edges


def test_upsert_node_inserts_new(sample_graph_path: Path, tmp_path: Path):
    target = _copy_graph(sample_graph_path, tmp_path)
    graph = load_graph(target)
    new_node = {
        "id": "kdev-sec:rule:3.1.1",
        "type": "concept",
        "name": "Command sanitization",
        "summary": "Avoid concatenating user input into shell commands",
        "tags": ["kdev:security_rule", "kdev:rule_id:3.1.1"],
        "complexity": "moderate",
    }
    upsert_node(graph, new_node)
    assert len(graph.nodes) == 3
    assert graph.nodes[-1]["id"] == "kdev-sec:rule:3.1.1"


def test_upsert_node_updates_existing_by_id(sample_graph_path: Path, tmp_path: Path):
    target = _copy_graph(sample_graph_path, tmp_path)
    graph = load_graph(target)
    same_id = {
        "id": "file:app.py",
        "type": "file",
        "name": "app.py",
        "filePath": "app.py",
        "summary": "UPDATED summary",
        "tags": ["python", "kdev:source:kdev-secure-coding"],
        "complexity": "simple",
    }
    upsert_node(graph, same_id)
    assert len(graph.nodes) == 2
    target_node = next(n for n in graph.nodes if n["id"] == "file:app.py")
    assert target_node["summary"] == "UPDATED summary"
    assert "kdev:source:kdev-secure-coding" in target_node["tags"]


def test_upsert_node_rejects_missing_required_field(sample_graph_path: Path, tmp_path: Path):
    target = _copy_graph(sample_graph_path, tmp_path)
    graph = load_graph(target)
    with pytest.raises(GraphIOError, match="missing required"):
        upsert_node(graph, {"id": "x", "type": "concept"})


def test_upsert_node_rejects_unknown_type(sample_graph_path: Path, tmp_path: Path):
    target = _copy_graph(sample_graph_path, tmp_path)
    graph = load_graph(target)
    bad = {
        "id": "x", "type": "vulnerability_xyz",
        "name": "x", "summary": "x", "tags": [], "complexity": "simple",
    }
    with pytest.raises(GraphIOError, match="unknown node type"):
        upsert_node(graph, bad)


def test_upsert_edge_inserts_new(sample_graph_path: Path, tmp_path: Path):
    target = _copy_graph(sample_graph_path, tmp_path)
    graph = load_graph(target)
    upsert_node(graph, {
        "id": "kdev-sec:rule:3.1.1", "type": "concept",
        "name": "rule", "summary": "summary",
        "tags": ["kdev:security_rule"], "complexity": "simple",
    })
    edge = {
        "source": "kdev-sec:rule:3.1.1",
        "target": "function:app.py:run_query",
        "type": "documents",
        "direction": "backward",
        "weight": 0.8,
    }
    upsert_edge(graph, edge)
    assert len(graph.edges) == 2


def test_upsert_edge_dedup_by_triple(sample_graph_path: Path, tmp_path: Path):
    target = _copy_graph(sample_graph_path, tmp_path)
    graph = load_graph(target)
    upsert_node(graph, {
        "id": "kdev-sec:rule:3.1.1", "type": "concept",
        "name": "x", "summary": "x", "tags": ["kdev:security_rule"],
        "complexity": "simple",
    })
    edge = {
        "source": "kdev-sec:rule:3.1.1",
        "target": "function:app.py:run_query",
        "type": "documents", "direction": "backward", "weight": 0.5,
    }
    upsert_edge(graph, edge)
    edge["weight"] = 0.9
    upsert_edge(graph, edge)
    matching = [e for e in graph.edges if e["source"] == "kdev-sec:rule:3.1.1"]
    assert len(matching) == 1
    assert matching[0]["weight"] == 0.9


def test_upsert_edge_rejects_dangling_source(sample_graph_path: Path, tmp_path: Path):
    target = _copy_graph(sample_graph_path, tmp_path)
    graph = load_graph(target)
    edge = {
        "source": "ghost:node", "target": "file:app.py",
        "type": "documents", "direction": "forward", "weight": 0.5,
    }
    with pytest.raises(GraphIOError, match="dangling source"):
        upsert_edge(graph, edge)


def test_upsert_edge_rejects_unknown_type(sample_graph_path: Path, tmp_path: Path):
    target = _copy_graph(sample_graph_path, tmp_path)
    graph = load_graph(target)
    upsert_node(graph, {
        "id": "kdev-sec:rule:1", "type": "concept", "name": "x",
        "summary": "x", "tags": [], "complexity": "simple",
    })
    edge = {
        "source": "kdev-sec:rule:1", "target": "file:app.py",
        "type": "secure_implements", "direction": "forward", "weight": 0.5,
    }
    with pytest.raises(GraphIOError, match="unknown edge type"):
        upsert_edge(graph, edge)


def test_find_nodes_by_tag(sample_graph_path: Path, tmp_path: Path):
    target = _copy_graph(sample_graph_path, tmp_path)
    graph = load_graph(target)
    upsert_node(graph, {
        "id": "kdev-sec:rule:3.1.1", "type": "concept", "name": "x",
        "summary": "x",
        "tags": ["kdev:security_rule", "kdev:rule_id:3.1.1"],
        "complexity": "simple",
    })
    upsert_node(graph, {
        "id": "kdev-sec:rule:3.1.2", "type": "concept", "name": "y",
        "summary": "y",
        "tags": ["kdev:security_rule", "kdev:rule_id:3.1.2"],
        "complexity": "simple",
    })
    matches = find_nodes_by_tag(graph, "kdev:security_rule")
    assert {n["id"] for n in matches} == {"kdev-sec:rule:3.1.1", "kdev-sec:rule:3.1.2"}


def test_save_graph_preserves_passthrough_fields(sample_graph_path: Path, tmp_path: Path):
    target = _copy_graph(sample_graph_path, tmp_path)
    graph = load_graph(target)
    upsert_node(graph, {
        "id": "kdev-sec:rule:1", "type": "concept", "name": "x",
        "summary": "x", "tags": ["kdev:security_rule"],
        "complexity": "simple",
        "kdevExtra": {"severity": "high"},
    })
    save_graph(graph, target)
    raw = json.loads(target.read_text(encoding="utf-8"))
    inserted = next(n for n in raw["nodes"] if n["id"] == "kdev-sec:rule:1")
    assert inserted["kdevExtra"] == {"severity": "high"}
