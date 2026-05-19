"""Performance regression tests for graph_io upsert operations.

These tests guard against O(N²) / O(N·M) regressions in upsert_node and
upsert_edge. With index-backed lookups both operations must complete in
well under 1 second even for 10 000+ elements.
"""

import time

from kdev_ingestor.graph_io import (
    KnowledgeGraph,
    upsert_node,
    upsert_edge,
)


def _make_node(i: int) -> dict:
    return {
        "id": f"function:module_{i}:fn_{i}",
        "type": "function",
        "name": f"fn_{i}",
        "summary": f"Function number {i}",
        "tags": ["python"],
        "complexity": "simple",
    }


def _make_graph_with_nodes(n: int) -> KnowledgeGraph:
    """Return a KnowledgeGraph pre-loaded with n nodes (no edges)."""
    graph = KnowledgeGraph(
        version="1.0.0",
        project={"name": "perf-test"},
    )
    for i in range(n):
        upsert_node(graph, _make_node(i))
    return graph


def test_upsert_node_10k_new_ids_under_1s():
    """Inserting 10 000 nodes with unique IDs must complete in < 1 second."""
    graph = KnowledgeGraph(version="1.0.0", project={"name": "perf-test"})

    start = time.perf_counter()
    for i in range(10_000):
        upsert_node(graph, _make_node(i))
    elapsed = time.perf_counter() - start

    assert len(graph.nodes) == 10_000
    assert elapsed < 1.0, (
        f"upsert_node 10k took {elapsed:.3f}s — expected < 1.0s. "
        "Likely O(N) linear scan still present."
    )


def test_upsert_edge_5k_new_triples_under_1s():
    """Inserting 5 000 edges into a 10k-node graph must complete in < 1 second."""
    # Pre-build a graph with 10 000 nodes so that any O(N) node-set
    # rebuild per upsert_edge call is maximally punished.
    graph = _make_graph_with_nodes(10_000)

    # We need source/target pairs that already exist as nodes.
    # Use node 0 as universal source, nodes 1..5000 as targets.
    source_id = "function:module_0:fn_0"

    start = time.perf_counter()
    for i in range(1, 5_001):
        edge = {
            "source": source_id,
            "target": f"function:module_{i}:fn_{i}",
            "type": "calls",
            "direction": "forward",
            "weight": 0.5,
        }
        upsert_edge(graph, edge)
    elapsed = time.perf_counter() - start

    assert len(graph.edges) == 5_000
    assert elapsed < 1.0, (
        f"upsert_edge 5k took {elapsed:.3f}s — expected < 1.0s. "
        "Likely O(N) node-set rebuild or O(M) edge scan still present."
    )
