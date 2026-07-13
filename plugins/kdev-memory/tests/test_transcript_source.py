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


# ---- 0.24.0 分槽根治：.current-transcript.<session_id> 单会话独占槽 ----

def test_stash_writes_per_session_slot(tmp_path):
    """stash 除了写 legacy 单槽，还写 .current-transcript.<sid> 独占槽（sid = transcript stem）。"""
    sd = _sd(tmp_path)
    ts.stash_current_transcript(sd, "/p/sess-A.jsonl")
    assert (sd / ".current-transcript.sess-A").exists()
    assert ts.read_current_transcript(sd, session_id="sess-A") == "/p/sess-A.jsonl"


def test_session_slot_survives_concurrent_clobber(tmp_path):
    """核心根治：并发会话 B 覆盖了 legacy 单槽，但 A 的独占槽不受影响 → A 仍解出自己的 transcript。"""
    sd = _sd(tmp_path)
    ts.stash_current_transcript(sd, "/p/sess-A.jsonl")
    ts.stash_current_transcript(sd, "/p/sess-B.jsonl")     # 并发会话 B 覆盖 legacy 槽
    assert ts.read_current_transcript(sd) == "/p/sess-B.jsonl"                  # legacy 槽确实被覆盖
    assert ts.read_current_transcript(sd, session_id="sess-A") == "/p/sess-A.jsonl"   # A 的槽没被动


def test_verified_via_session_slot_needs_no_content_scan(tmp_path, monkeypatch):
    """有独占槽 → 直接采信、source=session-slot，不做任何内容扫描（扫描函数被禁用也能过）。"""
    sd = _sd(tmp_path)
    proj = tmp_path / "proj"; proj.mkdir()
    a = proj / "sess-A.jsonl"; _write_jsonl(a, '{"t":"无 sha 也无所谓"}')
    b = proj / "sess-B.jsonl"; _write_jsonl(b, '{"t":"并发会话"}')
    ts.stash_current_transcript(sd, str(a))
    ts.stash_current_transcript(sd, str(b))               # legacy 槽被 B 覆盖

    def _boom(*_a, **_k):
        raise AssertionError("有独占槽时不该扫内容")
    monkeypatch.setattr(ts, "_file_contains_any", _boom)

    m = ts.resolve_marker_verified(sd, ["abc1234"], projects_dir=proj, session_id="sess-A")
    assert m["transcript_path"] == str(a)
    assert m["verified"] is True
    assert m["source"] == "session-slot"
    assert m["degraded"] is False


# ---- 0.24.0 问题3：多命中不再猜，直接降级 ----

def test_ambiguous_multi_hit_degrades_instead_of_guessing_latest_mtime(tmp_path):
    """多个会话含同一 sha（讨论/评审/召回注入都会带）→ 必须显式 degraded，
    不得取最新 mtime 猜一个还盖 recovered=True 的权威戳。"""
    sd = _sd(tmp_path)
    proj = tmp_path / "proj"; proj.mkdir()
    dev = proj / "sess-dev.jsonl"
    talk = proj / "sess-talk.jsonl"
    _write_jsonl(dev, '{"t":"[main e41d003] feat: 真开发会话"}')
    _write_jsonl(talk, '{"t":"事后排查会话，brief 注入里也带 e41d003"}')
    _os.utime(talk, (2 ** 31 - 1, 2 ** 31 - 1))          # talk 是最新 mtime（错误答案）
    other = proj / "sess-cur.jsonl"; _write_jsonl(other, '{"t":"无关"}')
    ts.stash_current_transcript(sd, str(other))

    m = ts.resolve_marker_verified(sd, ["e41d003"], projects_dir=proj, session_id="nope")
    assert m["degraded"] is True
    assert m["recovered"] is False
    assert m["ambiguous"] is True
    assert m["candidates"] == 2
    assert str(talk) not in m["transcript_path"]          # 绝不静默采信最新 mtime


# ---- 0.24.0 问题1：单命中也要写操作强判据（sha 会被 brief/gitStatus 注入污染）----

def _tool_use_line(tool: str, file_path: str) -> str:
    return _json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": tool, "input": {"file_path": file_path}}]}}, ensure_ascii=False)


def test_single_hit_without_write_evidence_degrades(tmp_path):
    """只是"提到"了 sha（如 kdev-memory brief 注入 / gitStatus Recent commits）但没有对
    files_touched 的 Edit/Write → 不是产出该 commit 的会话 → degraded，不得 recovered。"""
    sd = _sd(tmp_path)
    proj = tmp_path / "proj"; proj.mkdir()
    talk = proj / "sess-talk.jsonl"
    _write_jsonl(talk, '{"t":"<kdev-memory-brief> ... commit ce3212e/e41d003 ..."}')
    cur = proj / "sess-cur.jsonl"; _write_jsonl(cur, '{"t":"无关"}')
    ts.stash_current_transcript(sd, str(cur))

    m = ts.resolve_marker_verified(sd, ["e41d003"], projects_dir=proj, session_id="nope",
                                   files_touched=["hooks/lib/transcript_source.py"])
    assert m["degraded"] is True
    assert m["recovered"] is False


def test_single_hit_with_write_evidence_recovers(tmp_path):
    """会话既含 sha 又含对 files_touched 的 Edit/Write tool_use → 确是开发会话 → 恢复。"""
    sd = _sd(tmp_path)
    proj = tmp_path / "proj"; proj.mkdir()
    dev = proj / "sess-dev.jsonl"
    _write_jsonl(dev,
                 '{"t":"[main e41d003] feat: x"}',
                 _tool_use_line("Edit", "/repo/hooks/lib/transcript_source.py"))
    cur = proj / "sess-cur.jsonl"; _write_jsonl(cur, '{"t":"无关"}')
    ts.stash_current_transcript(sd, str(cur))

    m = ts.resolve_marker_verified(sd, ["e41d003"], projects_dir=proj, session_id="nope",
                                   files_touched=["hooks/lib/transcript_source.py"])
    assert m["transcript_path"] == str(dev)
    assert m["recovered"] is True
    assert m["since_offset"] == 0
    assert m["degraded"] is False


def test_write_evidence_disambiguates_multi_sha_hit(tmp_path):
    """多会话含 sha，但只有一个有写操作证据 → 不再 ambiguous，精确恢复到开发会话。"""
    sd = _sd(tmp_path)
    proj = tmp_path / "proj"; proj.mkdir()
    dev = proj / "sess-dev.jsonl"
    _write_jsonl(dev, '{"t":"[main e41d003] x"}', _tool_use_line("Write", "/repo/a.py"))
    talk = proj / "sess-talk.jsonl"
    _write_jsonl(talk, '{"t":"brief 注入 e41d003"}')
    _os.utime(talk, (2 ** 31 - 1, 2 ** 31 - 1))          # 最新 mtime 仍是讨论会话
    cur = proj / "sess-cur.jsonl"; _write_jsonl(cur, '{"t":"无关"}')
    ts.stash_current_transcript(sd, str(cur))

    m = ts.resolve_marker_verified(sd, ["e41d003"], projects_dir=proj, session_id="nope",
                                   files_touched=["a.py"])
    assert m["transcript_path"] == str(dev)
    assert m["recovered"] is True
    assert m["ambiguous"] is False


# ---- 0.24.0 问题4：扫描有界 + 空指针也能扫 ----

def test_scan_skips_oversized_and_stale_files(tmp_path, monkeypatch):
    """扫描要有 size cap + mtime 窗口，不能对 131M/67 个 transcript 无界整读。"""
    sd = _sd(tmp_path)
    proj = tmp_path / "proj"; proj.mkdir()
    huge = proj / "sess-huge.jsonl"; _write_jsonl(huge, '{"t":"[main e41d003] x"}' + " " * 5000)
    stale = proj / "sess-stale.jsonl"; _write_jsonl(stale, '{"t":"[main e41d003] x"}')
    _os.utime(stale, (1000, 1000))                        # 远古 mtime
    cur = proj / "sess-cur.jsonl"; _write_jsonl(cur, '{"t":"无关"}')
    ts.stash_current_transcript(sd, str(cur))
    monkeypatch.setattr(ts, "SCAN_MAX_BYTES", 1000)       # huge 超 cap → 跳过
    monkeypatch.setattr(ts, "SCAN_MAX_AGE_S", 3600)       # stale 超窗 → 跳过

    m = ts.resolve_marker_verified(sd, ["e41d003"], projects_dir=proj, session_id="nope")
    assert m["degraded"] is True                          # 两个候选都被界外剔除
    assert m["recovered"] is False


def test_empty_pointer_still_scans_via_derived_projects_dir(tmp_path, monkeypatch):
    """指针为空恰恰是最该恢复的场景：projects_dir 缺省不能只从候选父目录推，要能按 cwd 推。"""
    sd = _sd(tmp_path)
    proj = tmp_path / "proj"; proj.mkdir()
    dev = proj / "sess-dev.jsonl"
    _write_jsonl(dev, '{"t":"[main e41d003] x"}', _tool_use_line("Edit", "/repo/a.py"))
    # 不 stash → 指针为空
    monkeypatch.setattr(ts, "default_projects_dir", lambda: proj)

    m = ts.resolve_marker_verified(sd, ["e41d003"], files_touched=["a.py"])
    assert m["transcript_path"] == str(dev)
    assert m["recovered"] is True


def test_default_projects_dir_maps_cwd_to_claude_slug(tmp_path, monkeypatch):
    """~/.claude/projects/<slug>，slug = cwd 绝对路径把 / 换成 -。"""
    monkeypatch.chdir(tmp_path)
    got = ts.default_projects_dir()
    slug = str(tmp_path.resolve()).replace("/", "-")
    assert got == Path.home() / ".claude" / "projects" / slug


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


def test_hooks_key_slot_by_hook_input_session_id(tmp_path):
    """槽的 key 用 hook input 的 session_id（recorder 侧 CLAUDE_CODE_SESSION_ID 与之同源），
    而不是从 transcript 文件名 stem 反推——resume/compact 后 stem 未必等于 session_id。"""
    sd = tmp_path / ".kdev" / "memory" / "state"
    sd.mkdir(parents=True)
    (tmp_path / ".kdev" / "memory" / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    _run_hook("session-start-brief.py", tmp_path,
              _json.dumps({"source": "startup", "session_id": "sid-XYZ",
                           "transcript_path": "/p/sess-C.jsonl"}))
    # 断到槽文件本身——否则 legacy 单槽回落会让断言假绿
    assert (sd / ".current-transcript.sid-XYZ").exists()
    assert ts.read_current_transcript(sd, session_id="sid-XYZ") == "/p/sess-C.jsonl"

    _run_hook("user-prompt-trigger.py", tmp_path,
              _json.dumps({"session_id": "sid-UPS", "transcript_path": "/p/sess-D.jsonl",
                           "prompt": "hi"}))
    assert (sd / ".current-transcript.sid-UPS").exists()
    assert ts.read_current_transcript(sd, session_id="sid-UPS") == "/p/sess-D.jsonl"


def test_stale_session_slots_are_gc(tmp_path):
    """独占槽按会话生长，需 GC：过期槽在下次 stash 时清掉，别在 state/ 里无限堆积。"""
    sd = _sd(tmp_path)
    ts.stash_current_transcript(sd, "/p/old-sess.jsonl", session_id="old")
    old_slot = sd / ".current-transcript.old"
    assert old_slot.exists()
    _os.utime(old_slot, (1000, 1000))                     # 远古 mtime
    ts.stash_current_transcript(sd, "/p/new-sess.jsonl", session_id="new")
    assert not old_slot.exists()                          # 过期槽被回收
    assert (sd / ".current-transcript.new").exists()      # 当前槽还在
