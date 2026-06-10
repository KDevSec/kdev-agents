"""P-C1 端到端：迁移 → per-scope counter → 召回 → rollup → brief 贯通。"""
from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
HOOKS = Path(__file__).parent.parent / "hooks"
sys.path.insert(0, str(LIB_DIR))


def _git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "--allow-empty", "-m", "init"], cwd=repo, check=True)
    return repo


def test_end_to_end_scoped(tmp_path, monkeypatch):
    repo = _git_repo(tmp_path)
    mem = repo / ".kdev" / "memory"
    mem.mkdir(parents=True)
    (mem / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    (mem / "当前状态.md").write_text("---\nphase: stage2\ncurrent_step: main-1\n---\n", encoding="utf-8")
    (mem / "state").mkdir()

    from migrate_scope import migrate_to_scoped
    from scope import is_scoped, resolve_step_slug
    from step_id import mint_next_step_id

    # 1) 迁移
    migrate_to_scoped(mem, staff=["dev-engineer", "req-architect"], today="2026-06-10")
    assert is_scoped(mem)

    monkeypatch.chdir(repo)

    # 2) per-scope counter 独立
    state = mem / "state"
    assert mint_next_step_id(state, slug=resolve_step_slug("shared")) == "Step main-1"
    assert mint_next_step_id(state, slug=resolve_step_slug("dev-engineer")) == "Step dev-engineer-1"
    assert mint_next_step_id(state, slug=resolve_step_slug("req-architect")) == "Step req-architect-1"
    assert mint_next_step_id(state, slug=resolve_step_slug("dev-engineer")) == "Step dev-engineer-2"
    assert mint_next_step_id(state, slug=resolve_step_slug("shared")) == "Step main-2"

    # 3) 写两 scope 的 Step → 召回
    today = "2026-06-10"
    block = "---\n\n## {sid}: {t}\ntriggers: [{kw}]\n日期：{d}\n\n### 执行事实\n- 工具调用次数：1\n"
    (mem / "shared" / "执行日志.md").write_text(block.format(sid="Step main-2", t="主线活", kw="sharedkw", d=today), encoding="utf-8")
    (mem / "staff" / "dev-engineer" / "执行日志.md").write_text(block.format(sid="Step dev-engineer-2", t="员工活", kw="devkw", d=today), encoding="utf-8")

    spec = importlib.util.spec_from_file_location("trigger_match", LIB_DIR / "trigger-match.py")
    tm = importlib.util.module_from_spec(spec); spec.loader.exec_module(tm)
    monkeypatch.setenv("KDEV_TRIGGER_TODAY", today)
    entries = tm.scan_step_entries()
    by_id = {e["id"]: e for e in entries}
    assert "Step main-2" in by_id and "Step dev-engineer-2" in by_id
    assert by_id["Step dev-engineer-2"].get("scope") == "dev-engineer"

    # 4) weekly 聚合两 scope
    import weekly
    buf = io.StringIO()
    with redirect_stdout(buf):
        weekly.render(mem, date(2026, 6, 10), date(2026, 6, 10))
    out = buf.getvalue()
    assert "**Step**：2 条" in out
    assert "dev-engineer" in out

    # 5) brief 员工 scope block
    bspec = importlib.util.spec_from_file_location("ssb", HOOKS / "session-start-brief.py")
    ssb = importlib.util.module_from_spec(bspec); bspec.loader.exec_module(ssb)
    sblock = ssb._staff_scope_block(mem)
    assert "dev-engineer" in sblock and "req-architect" in sblock
