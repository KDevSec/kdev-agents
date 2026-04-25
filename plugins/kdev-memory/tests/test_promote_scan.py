"""test promote-scan.sh: 扫描 .kdev/memory/ 的沉淀候选"""

import os
import subprocess
import sys
import time
from pathlib import Path

LIB = Path(__file__).parent.parent / "hooks" / "lib" / "promote-scan.sh"

# Windows: Python subprocess 默认 'bash' 指向 WSL，需显式用 Git Bash
BASH = (
    "C:/Program Files/Git/usr/bin/bash.exe"
    if sys.platform == "win32"
    else "bash"
)


def _call(project: Path) -> str:
    """source 进来再调 scan_promote_candidates"""
    import os
    # Windows Path 用反斜杠，bash 需要正斜杠 -> 用 as_posix()
    lib_path = LIB.as_posix()
    kdev_path = Path(project, ".kdev", "memory").as_posix()
    script = f'''
source "{lib_path}"
scan_promote_candidates "{kdev_path}" "2026-04-24"
'''
    env = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"}
    # Windows: Python text=True 用系统编码(GBK)，但 Git Bash 输出 UTF-8
    # 解决方案：二进制捕获后手动 UTF-8 解码
    r = subprocess.run([BASH, "-c", script], capture_output=True, env=env)
    return r.stdout.decode("utf-8", errors="replace")


def _mkkdev(tmp_path: Path) -> Path:
    p = tmp_path / ".kdev" / "memory"
    p.mkdir(parents=True)
    return p


def test_empty_project_no_hint(tmp_path):
    """空项目（无任何条目）→ scan 返回空。"""
    _mkkdev(tmp_path)
    out = _call(tmp_path)
    assert out.strip() == ""


def test_time_trigger_over_7_days(tmp_path):
    """.last-promote 超过 7 天 + 有 R-NNN → 应输出沉淀提醒。"""
    k = _mkkdev(tmp_path)
    flush = k / ".last-promote"
    flush.touch()
    # 锚定到 _call 里硬编码的 today=2026-04-24，避免测试随真实日期漂移
    import datetime as _dt
    today_anchor = _dt.datetime.strptime("2026-04-24", "%Y-%m-%d").timestamp()
    old = today_anchor - 15 * 86400  # 15 天前 → 触发 P1（>7），未到 P0（>30）
    os.utime(flush, (old, old))
    (k / "改进建议.md").write_text("""# 改进建议

## R-014: 建议

triggers: [a]
""", encoding="utf-8")
    out = _call(tmp_path)
    assert "沉淀" in out or "promote" in out.lower()


def test_count_trigger_improvements_threshold(tmp_path):
    """改进建议 >= 3 条 pending（无 promote_status: done）→ 应输出。"""
    k = _mkkdev(tmp_path)
    (k / "改进建议.md").write_text("""# 改进建议

## R-1: a

## R-2: b

## R-3: c
""", encoding="utf-8")
    out = _call(tmp_path)
    assert "沉淀" in out


def test_skip_when_all_done(tmp_path):
    """所有 R 都有 promote_status: done → 不提醒。"""
    k = _mkkdev(tmp_path)
    (k / "改进建议.md").write_text("""# 改进建议

## R-1: a
---
promote_status: done
promote_target: docs/05-报告/实战总结.md
promote_date: 2026-04-23
---

## R-2: b
---
promote_status: done
---

## R-3: c
---
promote_status: done
---
""", encoding="utf-8")
    out = _call(tmp_path)
    assert "沉淀" not in out


def test_escalate_to_p0_over_30_days(tmp_path):
    """.last-promote 超 30 天 + 有 pending → 输出升级到 P0（含 🔴 或 "长期未沉淀"）。"""
    k = _mkkdev(tmp_path)
    flush = k / ".last-promote"
    flush.touch()
    # 锚定到 _call 里硬编码的 today=2026-04-24，避免测试随真实日期漂移
    import datetime as _dt
    today_anchor = _dt.datetime.strptime("2026-04-24", "%Y-%m-%d").timestamp()
    very_old = today_anchor - 35 * 86400
    os.utime(flush, (very_old, very_old))
    (k / "改进建议.md").write_text("## R-1\n", encoding="utf-8")
    out = _call(tmp_path)
    assert "长期" in out or "P0" in out or "🔴" in out
