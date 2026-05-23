from kdev_ingestor.graph_io import KnowledgeGraph, upsert_node
from kdev_ingestor.candidates import KeywordRetriever


def _node(node_id: str, ntype: str, summary: str = "s"):
    return {
        "id": node_id, "type": ntype, "name": node_id,
        "filePath": "x.py", "summary": summary,
        "tags": [], "complexity": "simple",
    }


def _graph(nodes):
    g = KnowledgeGraph(version="1", project={}, nodes=[])
    for n in nodes:
        upsert_node(g, n)
    return g


def test_keyword_overlap_orders_by_score():
    g = _graph([
        _node("function:a.py:parse_ast", "function",
              "Parses TypeScript using tree-sitter for AST extraction"),
        _node("function:b.py:noop", "function", "does nothing"),
        _node("function:c.py:ast_walker", "function", "Walks an AST tree"),
    ])
    r = KeywordRetriever()
    res = r.retrieve("AST 解析", "Parse AST from source", g, top_k=2)
    assert len(res) == 2
    assert res[0]["node_id"] == "function:a.py:parse_ast"
    assert res[1]["node_id"] == "function:c.py:ast_walker"


def test_keyword_unicode_token_kept():
    g = _graph([
        _node("function:a.py:f", "function", "中文摘要 含 关键词 解析"),
        _node("function:b.py:g", "function", "totally unrelated"),
    ])
    r = KeywordRetriever()
    res = r.retrieve("解析", "中文 intent 关于 解析", g, top_k=5)
    assert len(res) >= 1
    assert res[0]["node_id"] == "function:a.py:f"


def test_zero_score_fallback_takes_top_k():
    g = _graph([
        _node("function:a.py:f", "function", "alpha"),
        _node("function:b.py:g", "function", "beta"),
        _node("function:c.py:h", "function", "gamma"),
    ])
    r = KeywordRetriever()
    res = r.retrieve("xxxxxx", "yyyyyy", g, top_k=2)
    assert len(res) == 2


def test_small_graph_returns_all():
    g = _graph([
        _node("function:a.py:f", "function", "alpha"),
        _node("function:b.py:g", "function", "beta"),
    ])
    r = KeywordRetriever()
    res = r.retrieve("alpha", "", g, top_k=30)
    assert len(res) == 2


def test_ignores_non_function_class_nodes():
    g = _graph([
        _node("file:a.py", "file", "alpha file"),
        _node("function:a.py:f", "function", "alpha function"),
        _node("concept:x", "concept", "alpha concept"),
    ])
    r = KeywordRetriever()
    res = r.retrieve("alpha", "", g, top_k=10)
    ids = {c["node_id"] for c in res}
    assert "function:a.py:f" in ids
    assert "file:a.py" not in ids
    assert "concept:x" not in ids


def test_returns_summary_field():
    g = _graph([_node("function:a.py:f", "function", "the summary here")])
    r = KeywordRetriever()
    res = r.retrieve("summary", "", g, top_k=5)
    assert res[0]["summary"] == "the summary here"
