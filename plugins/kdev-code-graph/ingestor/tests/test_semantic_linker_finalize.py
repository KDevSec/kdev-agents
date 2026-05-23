import json
from pathlib import Path

import pytest

from kdev_ingestor.cli import main
from kdev_ingestor.graph_io import load_graph


def _write_graph(p: Path, nodes: list[dict], edges: list[dict] | None = None,
                 extras: dict | None = None):
    payload = {
        "version": "1", "project": {}, "layers": [], "tour": [],
        "nodes": nodes, "edges": edges or [],
    }
    if extras:
        payload.update(extras)
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _doc(rel):
    return {"id": f"document:{rel}", "type": "document", "name": rel,
            "filePath": rel, "summary": "d", "tags": [], "complexity": "simple"}


def _func(rel, name, tags=None):
    return {"id": f"function:{rel}:{name}", "type": "function", "name": name,
            "filePath": rel, "lineRange": [1, 5], "summary": "s",
            "tags": tags or [], "complexity": "simple"}


def _verdicts(items):
    return {"schema_version": 1, "generated_at": "2026-05-22T10:00:00+00:00",
            "verdicts": items}


@pytest.fixture(autouse=True)
def _no_git(monkeypatch):
    """Disable git mtime lookups in finalize during tests (deterministic)."""
    from kdev_ingestor.linkers import semantic_linker_finalize as f
    monkeypatch.setattr(f, "_git_mtime", lambda path, repo_root=None: None)


def test_finalize_writes_documents_edges(tmp_path):
    g = tmp_path / "kg.json"
    _write_graph(g, [_doc("docs/spec.md"), _func("app.py", "login")])
    v = tmp_path / "verdicts.json"
    v.write_text(json.dumps(_verdicts([
        {"intent_id": "docs/spec.md#X", "status": "implemented",
         "linked": [{"target_node_id": "function:app.py:login",
                     "confidence": 0.85, "reason": "ok"}]},
    ])), encoding="utf-8")
    rc = main(["spec-link-finalize",
               "--graph", str(g), "--verdicts", str(v),
               "--source-root", str(tmp_path),
               "--report-dir", str(tmp_path / "reports")])
    assert rc == 0
    kg = load_graph(g)
    docs_edges = [e for e in kg.edges if e["type"] == "documents"]
    assert len(docs_edges) == 1
    e = docs_edges[0]
    assert e["source"] == "function:app.py:login"
    assert e["target"] == "document:docs/spec.md"
    assert e["direction"] == "backward"
    assert e["weight"] == pytest.approx(0.85)


def test_finalize_writes_extras_metadata(tmp_path):
    g = tmp_path / "kg.json"
    _write_graph(g, [_doc("docs/s.md"), _func("a.py", "f")])
    v = tmp_path / "v.json"
    v.write_text(json.dumps(_verdicts([
        {"intent_id": "docs/s.md#X", "status": "implemented",
         "linked": [{"target_node_id": "function:a.py:f",
                     "confidence": 0.9, "reason": "r"}]},
    ])), encoding="utf-8")
    main(["spec-link-finalize", "--graph", str(g), "--verdicts", str(v),
          "--source-root", str(tmp_path), "--report-dir", str(tmp_path / "r")])
    raw = json.loads(g.read_text(encoding="utf-8"))
    extras = raw.get("kdev_spec_link")
    assert extras is not None
    assert extras["schema_version"] == 1
    assert extras["intents_processed"] == 1
    assert extras["implemented_count"] == 1
    assert extras["not_found_count"] == 0
    assert "last_run_at" in extras
    assert any(t["target"] == "document:docs/s.md"
               for t in extras["owned_edge_triples"])


def test_finalize_idempotent(tmp_path):
    g = tmp_path / "kg.json"
    _write_graph(g, [_doc("docs/s.md"), _func("a.py", "f")])
    v = tmp_path / "v.json"
    v.write_text(json.dumps(_verdicts([
        {"intent_id": "docs/s.md#X", "status": "implemented",
         "linked": [{"target_node_id": "function:a.py:f",
                     "confidence": 0.9, "reason": "r"}]},
    ])), encoding="utf-8")
    args = ["spec-link-finalize", "--graph", str(g), "--verdicts", str(v),
            "--source-root", str(tmp_path), "--report-dir", str(tmp_path / "r")]
    main(args)
    n1 = len([e for e in load_graph(g).edges if e["type"] == "documents"])
    main(args)
    n2 = len([e for e in load_graph(g).edges if e["type"] == "documents"])
    assert n1 == n2 == 1


def test_finalize_clears_old_owned_then_writes_new(tmp_path):
    g = tmp_path / "kg.json"
    _write_graph(g, [_doc("docs/s.md"),
                     _func("a.py", "old"), _func("a.py", "new")])
    v = tmp_path / "v.json"

    # First run: link to "old"
    v.write_text(json.dumps(_verdicts([
        {"intent_id": "docs/s.md#X", "status": "implemented",
         "linked": [{"target_node_id": "function:a.py:old",
                     "confidence": 0.9, "reason": "r"}]},
    ])), encoding="utf-8")
    main(["spec-link-finalize", "--graph", str(g), "--verdicts", str(v),
          "--source-root", str(tmp_path), "--report-dir", str(tmp_path / "r")])

    # Second run: link to "new" instead
    v.write_text(json.dumps(_verdicts([
        {"intent_id": "docs/s.md#X", "status": "implemented",
         "linked": [{"target_node_id": "function:a.py:new",
                     "confidence": 0.9, "reason": "r"}]},
    ])), encoding="utf-8")
    main(["spec-link-finalize", "--graph", str(g), "--verdicts", str(v),
          "--source-root", str(tmp_path), "--report-dir", str(tmp_path / "r")])

    edges = [e for e in load_graph(g).edges if e["type"] == "documents"]
    assert len(edges) == 1
    assert edges[0]["source"] == "function:a.py:new"


def test_finalize_skips_not_found_and_error(tmp_path):
    g = tmp_path / "kg.json"
    _write_graph(g, [_doc("docs/s.md"), _func("a.py", "f")])
    v = tmp_path / "v.json"
    v.write_text(json.dumps(_verdicts([
        {"intent_id": "docs/s.md#X", "status": "not_found", "linked": []},
        {"intent_id": "docs/s.md#Y", "status": "error",
         "linked": [{"target_node_id": "function:a.py:f",
                     "confidence": 0.9, "reason": "parse fail"}]},
    ])), encoding="utf-8")
    main(["spec-link-finalize", "--graph", str(g), "--verdicts", str(v),
          "--source-root", str(tmp_path), "--report-dir", str(tmp_path / "r")])
    assert [e for e in load_graph(g).edges if e["type"] == "documents"] == []
    raw = json.loads(g.read_text(encoding="utf-8"))
    assert raw["kdev_spec_link"]["not_found_count"] == 1
    assert raw["kdev_spec_link"]["error_count"] == 1


def test_finalize_skips_target_not_in_graph(tmp_path):
    g = tmp_path / "kg.json"
    _write_graph(g, [_doc("docs/s.md")])
    v = tmp_path / "v.json"
    v.write_text(json.dumps(_verdicts([
        {"intent_id": "docs/s.md#X", "status": "implemented",
         "linked": [{"target_node_id": "function:no.py:f",
                     "confidence": 0.9, "reason": "r"}]},
    ])), encoding="utf-8")
    main(["spec-link-finalize", "--graph", str(g), "--verdicts", str(v),
          "--source-root", str(tmp_path), "--report-dir", str(tmp_path / "r")])
    assert [e for e in load_graph(g).edges if e["type"] == "documents"] == []


def test_finalize_writes_report_file(tmp_path):
    g = tmp_path / "kg.json"
    _write_graph(g, [_doc("docs/s.md"), _func("a.py", "f")])
    v = tmp_path / "v.json"
    v.write_text(json.dumps(_verdicts([
        {"intent_id": "docs/s.md#X", "status": "implemented",
         "linked": [{"target_node_id": "function:a.py:f",
                     "confidence": 0.9, "reason": "r"}]},
    ])), encoding="utf-8")
    rdir = tmp_path / "reports"
    main(["spec-link-finalize", "--graph", str(g), "--verdicts", str(v),
          "--source-root", str(tmp_path), "--report-dir", str(rdir)])
    reports = list(rdir.glob("spec-link-*.md"))
    assert len(reports) == 1
    body = reports[0].read_text(encoding="utf-8")
    assert "Spec ↔ Code 对齐审计报告" in body
    assert "✅ 有实现" in body


def _fake_mtime_factory(doc_t: float, code_t: float):
    """Build a fake _git_mtime returning doc_t for .md paths, code_t otherwise."""
    def fake(path, repo_root=None):
        return doc_t if str(path).endswith(".md") else code_t
    return fake


def test_finalize_drift_threshold_security_14d(tmp_path, monkeypatch):
    """Security-tagged doc with 20-day drift IS flagged (threshold = 14d)."""
    # doc 30 days ago, code 10 days ago → 20-day drift
    code_t = 1_700_000_000.0
    doc_t = code_t - 20 * 86400
    from kdev_ingestor.linkers import semantic_linker_finalize as f
    monkeypatch.setattr(f, "_git_mtime", _fake_mtime_factory(doc_t, code_t))

    g = tmp_path / "kg.json"
    # doc node carries kdev:security_rule tag → security threshold (14d)
    sec_doc = {
        "id": "document:docs/s.md", "type": "document", "name": "s.md",
        "filePath": "docs/s.md", "summary": "d",
        "tags": ["kdev:security_rule"], "complexity": "simple",
    }
    _write_graph(g, [sec_doc, _func("a.py", "f")])
    v = tmp_path / "v.json"
    v.write_text(json.dumps(_verdicts([
        {"intent_id": "docs/s.md#X", "status": "implemented",
         "linked": [{"target_node_id": "function:a.py:f",
                     "confidence": 0.9, "reason": "r"}]},
    ])), encoding="utf-8")
    rdir = tmp_path / "reports"
    main(["spec-link-finalize", "--graph", str(g), "--verdicts", str(v),
          "--source-root", str(tmp_path), "--report-dir", str(rdir)])
    body = list(rdir.glob("spec-link-*.md"))[0].read_text(encoding="utf-8")
    # 20-day drift exceeds 14-day security threshold → row present + marked "是"
    assert "## ⚠️ 漂移" in body
    assert "docs/s.md#X" in body
    # the "安全相关" column should show 是 for this row
    drift_section = body.split("## ⚠️ 漂移")[1].split("##")[0]
    assert "| 是 |" in drift_section


def test_finalize_drift_threshold_default_30d_suppresses_20d(tmp_path, monkeypatch):
    """Non-security doc with 20-day drift is NOT flagged (threshold = 30d)."""
    code_t = 1_700_000_000.0
    doc_t = code_t - 20 * 86400  # 20-day drift, below 30d default
    from kdev_ingestor.linkers import semantic_linker_finalize as f
    monkeypatch.setattr(f, "_git_mtime", _fake_mtime_factory(doc_t, code_t))

    g = tmp_path / "kg.json"
    _write_graph(g, [_doc("docs/s.md"), _func("a.py", "f")])  # no security tag
    v = tmp_path / "v.json"
    v.write_text(json.dumps(_verdicts([
        {"intent_id": "docs/s.md#X", "status": "implemented",
         "linked": [{"target_node_id": "function:a.py:f",
                     "confidence": 0.9, "reason": "r"}]},
    ])), encoding="utf-8")
    rdir = tmp_path / "reports"
    main(["spec-link-finalize", "--graph", str(g), "--verdicts", str(v),
          "--source-root", str(tmp_path), "--report-dir", str(rdir)])
    body = list(rdir.glob("spec-link-*.md"))[0].read_text(encoding="utf-8")
    # 20-day drift below 30d threshold → no drift section header
    assert "## ⚠️ 漂移" not in body


def test_finalize_report_surfaces_skipped_invalid_target(tmp_path):
    """LLM hallucination (target not in graph) is counted in extras and reported."""
    g = tmp_path / "kg.json"
    _write_graph(g, [_doc("docs/s.md"), _func("a.py", "f")])
    v = tmp_path / "v.json"
    # mix one valid + one hallucinated target
    v.write_text(json.dumps(_verdicts([
        {"intent_id": "docs/s.md#X", "status": "implemented",
         "linked": [
             {"target_node_id": "function:a.py:f",
              "confidence": 0.9, "reason": "r"},
             {"target_node_id": "function:NO_SUCH.py:ghost",
              "confidence": 0.9, "reason": "hallucination"},
         ]},
    ])), encoding="utf-8")
    rdir = tmp_path / "reports"
    main(["spec-link-finalize", "--graph", str(g), "--verdicts", str(v),
          "--source-root", str(tmp_path), "--report-dir", str(rdir)])
    # extras count
    raw = json.loads(g.read_text(encoding="utf-8"))
    assert raw["kdev_spec_link"]["skipped_invalid_target"] == 1
    # report surfaces the metric
    body = list(rdir.glob("spec-link-*.md"))[0].read_text(encoding="utf-8")
    assert "LLM 输出无效 target 被跳过" in body
    assert "| 🚫 LLM 输出无效 target 被跳过 | 1 |" in body
