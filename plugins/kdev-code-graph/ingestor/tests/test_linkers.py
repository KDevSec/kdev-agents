from kdev_ingestor.graph_io import KnowledgeGraph
from kdev_ingestor.linkers.base import (
    build_path_index,
    resolve_node_id,
    make_security_edge,
)


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
