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


# ---- resolve_marker_verified：内容校验 + 并发错会话自动恢复（修 .current-transcript 单槽竞争）----

def _write_jsonl(path: Path, *lines: str) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_verified_pointer_contains_anchor(tmp_path):
    """指针指向的会话内容含 commit 锚 → 采信、不恢复。"""
    sd = _sd(tmp_path)
    proj = tmp_path / "proj"; proj.mkdir()
    good = proj / "sess-A.jsonl"
    _write_jsonl(good, '{"t":"[main abc1234] feat: x"}')
    ts.stash_current_transcript(sd, str(good))
    m = ts.resolve_marker_verified(sd, ["abc1234"], projects_dir=proj)
    assert m["transcript_path"] == str(good)
    assert m["verified"] is True
    assert m["recovered"] is False
    assert m["degraded"] is False


def test_recover_when_pointer_points_at_concurrent_wrong_session(tmp_path):
    """核心场景：指针被并发会话覆盖成 sess-B（不含本次 commit），扫兄弟恢复到真正含锚的 sess-A。"""
    sd = _sd(tmp_path)
    proj = tmp_path / "proj"; proj.mkdir()
    real = proj / "sess-A.jsonl"
    other = proj / "sess-B.jsonl"
    _write_jsonl(real, '{"t":"[main e41d003] feat: 记忆分流"}')
    _write_jsonl(other, '{"t":"取证调研 无关内容"}')
    ts.stash_current_transcript(sd, str(other))          # 指针被并发会话 B 覆盖
    m = ts.resolve_marker_verified(sd, ["e41d003"], projects_dir=proj)
    assert m["transcript_path"] == str(real)             # 恢复到含锚的真会话
    assert m["recovered"] is True
    assert m["switched"] is True
    assert m["since_offset"] == 0                         # 恢复会话从头读
    assert m["degraded"] is False


def test_degrade_when_no_transcript_has_anchor(tmp_path):
    """无任何会话含该 commit 锚（如 transcript 尚未落盘）→ 显式降级、不静默采信错会话。"""
    sd = _sd(tmp_path)
    proj = tmp_path / "proj"; proj.mkdir()
    other = proj / "sess-B.jsonl"
    _write_jsonl(other, '{"t":"无关"}')
    ts.stash_current_transcript(sd, str(other))
    m = ts.resolve_marker_verified(sd, ["deadbee"], projects_dir=proj)
    assert m["degraded"] is True
    assert m["verified"] is False
    assert m["recovered"] is False


def test_empty_anchors_falls_back_to_resolve_marker(tmp_path):
    """无 commit 锚（zero-commit step）→ 退回裸 resolve_marker、向后兼容、标 unverified。"""
    sd = _sd(tmp_path)
    proj = tmp_path / "proj"; proj.mkdir()
    cur = proj / "sess-C.jsonl"
    _write_jsonl(cur, '{"t":"x"}')
    ts.stash_current_transcript(sd, str(cur))
    m = ts.resolve_marker_verified(sd, [], projects_dir=proj)
    assert m["transcript_path"] == str(cur)
    assert m["verified"] is False
    assert m["recovered"] is False
    assert m["degraded"] is False


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
