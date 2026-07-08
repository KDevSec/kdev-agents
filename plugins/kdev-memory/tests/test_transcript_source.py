"""transcript_source：当前会话 transcript 指针 stash + resolve（修他评跨会话陈旧指针）。"""
from __future__ import annotations

import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "hooks" / "lib"
sys.path.insert(0, str(_LIB))

import pending_commits      # noqa: E402
import transcript_source as ts   # noqa: E402


def _sd(tmp_path):
    sd = tmp_path / "state"
    sd.mkdir()
    return sd


def test_stash_and_read_roundtrip(tmp_path):
    sd = _sd(tmp_path)
    ts.stash_current_transcript(sd, "/p/aaa-111.jsonl")
    assert ts.read_current_transcript(sd) == "/p/aaa-111.jsonl"


def test_stash_empty_is_noop(tmp_path):
    sd = _sd(tmp_path)
    ts.stash_current_transcript(sd, "")
    assert ts.read_current_transcript(sd) == ""


def test_resolve_no_current_falls_back_to_pending(tmp_path):
    sd = _sd(tmp_path)
    pending_commits.clear(sd, "Step x", 0, new_since_offset=654)
    # 手动塞 pending transcript_path（clear 不带 path；用 append 造）
    pending_commits.append(sd, "sha", "subj", 1, transcript_path="/p/old-999.jsonl")
    m = ts.resolve_marker(sd)
    assert m["transcript_path"] == "/p/old-999.jsonl"
    assert m["switched"] is False


def test_resolve_same_session_keeps_incremental_offset(tmp_path):
    sd = _sd(tmp_path)
    pending_commits.append(sd, "sha", "subj", 1, transcript_path="/p/sess-A.jsonl")
    pending_commits.clear(sd, "Step 1", 1, new_since_offset=120)  # 保留 transcript_path
    ts.stash_current_transcript(sd, "/p/sess-A.jsonl")            # 当前 == pending 会话
    m = ts.resolve_marker(sd)
    assert m["transcript_path"] == "/p/sess-A.jsonl"
    assert m["since_offset"] == 120        # 同会话续读，保留增量 offset
    assert m["switched"] is False


def test_resolve_switched_session_resets_offset_to_zero(tmp_path):
    """复现原 bug：pending 冻在老会话/654，当前是新会话 → 用新会话 + offset 0，不越界。"""
    sd = _sd(tmp_path)
    pending_commits.append(sd, "sha", "subj", 1, transcript_path="/p/old-975d.jsonl")
    pending_commits.clear(sd, "Step 1", 1, new_since_offset=654)  # 老会话 EOF 行号
    ts.stash_current_transcript(sd, "/p/new-cafa.jsonl")         # 当前是新会话
    m = ts.resolve_marker(sd)
    assert m["transcript_path"] == "/p/new-cafa.jsonl"   # 指向当前会话，不是老 975d
    assert m["since_offset"] == 0                        # 重置，不套老会话 654 越界
    assert m["switched"] is True


# ---- hook 集成：UserPromptSubmit / SessionStart 写 .current-transcript ----

import json as _json          # noqa: E402
import subprocess as _sp      # noqa: E402
import os as _os              # noqa: E402

_HOOKS = _LIB.parent


def _run_hook(name, project, inp):
    return _sp.run([sys.executable, str(_HOOKS / name)], cwd=str(project),
                   input=inp, text=True, capture_output=True,
                   env={**_os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"})


def test_user_prompt_hook_stashes_current_transcript(tmp_path):
    (tmp_path / ".kdev" / "memory" / "state").mkdir(parents=True)
    _run_hook("user-prompt-trigger.py", tmp_path,
              _json.dumps({"transcript_path": "/p/sess-B.jsonl", "prompt": "hi"}))
    assert ts.read_current_transcript(tmp_path / ".kdev" / "memory" / "state") == "/p/sess-B.jsonl"


def test_session_start_hook_stashes_current_transcript(tmp_path):
    (tmp_path / ".kdev" / "memory" / "state").mkdir(parents=True)
    (tmp_path / ".kdev" / "memory" / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    _run_hook("session-start-brief.py", tmp_path,
              _json.dumps({"source": "startup", "session_id": "s1",
                           "transcript_path": "/p/sess-C.jsonl"}))
    assert ts.read_current_transcript(tmp_path / ".kdev" / "memory" / "state") == "/p/sess-C.jsonl"
