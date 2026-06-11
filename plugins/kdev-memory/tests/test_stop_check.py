"""test stop-check.py 按 rating.mode 降级半残检测（P-C0.5 / P-C1a）。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "stop-check.py"

# 今日半残 Step（用户评分空 + 扣分项齐全）；日期占位 __TODAY__ 运行时替换
_HALF_STEP = """# 执行日志

## Step main-40: 今日半残
日期：__TODAY__

### 模型自评
- 顺畅度自评：4/5
- 扣分项：赶工漏边界

### 用户评分
- 完成时间：—
- 顺畅度：—/5
"""


def _setup(tmp_path: Path, rating_line: str | None, strict: bool) -> Path:
    import datetime
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=repo, check=True,
    )
    mem = repo / ".kdev" / "memory"
    (mem / "state").mkdir(parents=True)
    today = datetime.date.today().isoformat()
    (mem / "执行日志.md").write_text(_HALF_STEP.replace("__TODAY__", today), encoding="utf-8")
    # 今日汇总写上，避免 "今天无汇总" 噪声干扰断言
    (mem / "每日汇总").mkdir()
    (mem / "每日汇总" / f"{today}.md").write_text("# 汇总\n", encoding="utf-8")
    if rating_line is not None:
        (mem / "config.yaml").write_text(rating_line + "\n", encoding="utf-8")
    if strict:
        (mem / "strict").write_text("", encoding="utf-8")
    return repo


def _run(repo: Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(HOOK)], cwd=str(repo),
                       input="{}", capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def test_model_only_skips_half_reminder(tmp_path):
    repo = _setup(tmp_path, "rating.mode: model-only", strict=False)
    rc, out = _run(repo)
    assert rc == 0
    assert "半残" not in out


def test_user_required_soft_reminds_half(tmp_path):
    repo = _setup(tmp_path, "rating.mode: user-required", strict=False)
    rc, out = _run(repo)
    assert rc == 0
    assert "半残" in out


def test_user_opt_in_no_strict_block(tmp_path):
    """user-opt-in + strict flag：半残不得 exit 2 阻塞。"""
    repo = _setup(tmp_path, "rating.mode: user-opt-in", strict=True)
    rc, _ = _run(repo)
    assert rc == 0


def test_model_only_no_strict_block(tmp_path):
    repo = _setup(tmp_path, "rating.mode: model-only", strict=True)
    rc, _ = _run(repo)
    assert rc == 0


def test_user_required_strict_blocks_half(tmp_path):
    """user-required + strict + 今日半残 → exit 2 阻塞（现行行为保留）。"""
    repo = _setup(tmp_path, "rating.mode: user-required", strict=True)
    rc, out = _run(repo)
    assert rc == 2
    assert "strict" in out
