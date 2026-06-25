# plugins/kdev-memory/tests/test_step_recorder_e2e.py
"""e2e: simulate step-recorder full lifecycle from input through lib calls.

Doesn't dispatch an actual subagent; tests the lib-level contract that recorder
walks through: mint ID, build JSON record, append to 执行日志.jsonl (validate passes),
dual-read can read it back, update 当前状态.md frontmatter, clear pending.
R-001 v1 task 12 → Phase B: md heredoc → JSONL append_step。
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import step_log  # noqa: E402
import step_dualread  # noqa: E402
from pending_commits import append as pc_append, clear as pc_clear, read as pc_read  # noqa: E402
from step_id import mint_record_id, parse_record_id  # noqa: E402


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=repo, check=True,
    )
    (repo / ".kdev" / "memory" / "state").mkdir(parents=True)
    (repo / ".kdev" / "memory" / "当前状态.md").write_text(
        "---\ncurrent_step: Step 00000000-000000-init\nlast_updated: 2026-01-01\n---\n",
        encoding="utf-8")
    return repo


def _build_record(minted: str) -> dict:
    """recorder 组的 JSON Step record（无 delegation——kdev 独立插件）。"""
    return {
        "record_id": minted, "type": "Step", "title": "e2e: recorder 落 jsonl 链路",
        "date": "2026-06-25", "about": "feature/jsonl-recorder",
        "triggers": ["jsonl", "step-recorder", "phase-b", "append_step", "dual-read"],
        "status": "scored",
        "key_facts": {
            "tools_invoked_count": 7, "errors_hit": 0, "detours": 0,
            "token_feel": "light", "skills_used": [], "commit_shas": [],
            "files_touched": ["agents/kdev-step-recorder.md"],
            "key_decisions": ["heredoc md → step_log.append_step JSONL"], "related": [],
        },
        "model_eval": {"quality": 4, "deduction": "字段对齐三处须人工核，无证据时不编造",
                       "skills_invoked": [], "subagents": []},
        "user_rating": {"completed_at": "11:00", "smoothness": 4, "comment": None},
        "score_diff": {"delta": 0, "note": "持平"},
    }


def test_recorder_lifecycle_mint_append_jsonl_dualread_clear_pending(tmp_path, monkeypatch):
    repo = _init_repo(tmp_path)
    monkeypatch.chdir(repo)
    root = repo / ".kdev" / "memory"
    state = root / "state"

    # Simulate: 3 commits accumulated in pending
    now = int(time.time())
    pc_append(state, "a" * 40, "fix(x): a", now - 100)
    pc_append(state, "b" * 40, "fix(x): b", now - 50)
    pc_append(state, "c" * 40, "fix(x): c", now - 10)
    assert len(pc_read(state)["commits"]) == 3

    # Recorder action 1: mint next ID via timestamp primitive (Q-020)
    minted = mint_record_id("Step", state)
    assert minted.startswith("Step ")
    parsed = parse_record_id(minted)
    assert parsed is not None and parsed["scheme"] == "timestamp"

    # Recorder action 2+3: build JSON record + append_step to 执行日志.jsonl.
    # append_step runs validate() internally — if record is malformed it raises.
    record = _build_record(minted)
    step_log.append_step(record, scope="shared", root=root)

    # Verify: jsonl 主账 written + record readable via step_log
    jsonl = step_log.jsonl_path(root=root)
    assert jsonl == root / "执行日志.jsonl"  # flat layout
    assert jsonl.is_file()
    steps = step_log.read_steps(root=root)
    assert len(steps) == 1
    assert steps[0]["record_id"] == minted
    assert steps[0]["title"] == "e2e: recorder 落 jsonl 链路"
    assert "delegation" not in steps[0]  # kdev 独立插件——无 delegation 字段

    # Verify: dual-read 投影器能把它合成出含全部 grep 锚点的 md body
    body = step_dualread.record_to_md_body(steps[0])
    assert f"## {minted}: e2e: recorder 落 jsonl 链路" in body
    assert "日期：2026-06-25" in body
    assert "status: scored" in body
    assert "about: feature/jsonl-recorder" in body
    assert "顺畅度：4/5" in body
    assert "完成时间：11:00" in body
    assert "扣分项：字段对齐三处须人工核，无证据时不编造" in body
    assert "差值：0" in body

    # Recorder action 4: update 当前状态.md frontmatter (shared scope only)
    cur = root / "当前状态.md"
    cur.write_text(
        cur.read_text(encoding="utf-8")
        .replace("current_step: Step 00000000-000000-init", f"current_step: {minted}")
        .replace("last_updated: 2026-01-01", "last_updated: 2026-06-25"),
        encoding="utf-8")
    fm = cur.read_text(encoding="utf-8")
    assert f"current_step: {minted}" in fm
    assert "last_updated: 2026-06-25" in fm

    # Recorder action 5: clear pending-commits, update since
    pc_clear(state, minted.replace("Step ", ""), int(time.time()))
    pending = pc_read(state)
    assert pending["commits"] == []
    assert pending["since_step_id"] == minted[len("Step "):]

    # No counter file written — timestamp IDs have no counter (Q-020)
    assert not list(state.glob("step-counter-*.txt"))


def test_recorder_rejects_malformed_record(tmp_path, monkeypatch):
    """append_step 内 validate() 守门：generic title / <5 triggers 等被拒，不落盘。"""
    repo = _init_repo(tmp_path)
    monkeypatch.chdir(repo)
    root = repo / ".kdev" / "memory"
    minted = mint_record_id("Step", root / "state")

    bad = _build_record(minted)
    bad["title"] = "完成"          # gate 1: generic title
    bad["triggers"] = ["a", "b"]   # gate 4: <5 triggers
    import pytest
    with pytest.raises(step_log.StepValidationError):
        step_log.append_step(bad, scope="shared", root=root)
    # 落盘被拒 → jsonl 不应存在/为空
    assert step_log.read_steps(root=root) == []
