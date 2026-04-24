"""test weekly.sh 滚动 7 天窗口聚合逻辑"""

import subprocess
from datetime import date, timedelta
from pathlib import Path

LIB = Path(__file__).parent.parent / "hooks" / "lib" / "weekly.sh"


def _call(project: Path, date_from: str = "", date_to: str = "") -> subprocess.CompletedProcess:
    args = [str(LIB)]
    if date_from:
        args.extend(["--from", date_from])
    if date_to:
        args.extend(["--to", date_to])
    return subprocess.run(["bash"] + args, cwd=project, capture_output=True, text=True)


def _setup(tmp_path: Path) -> Path:
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    return k


def test_default_window_is_today_minus_6_to_today(tmp_path):
    """无参数 → 汇总 today-6 ~ today。"""
    k = _setup(tmp_path)
    today = date.today()
    from_d = (today - timedelta(days=6)).isoformat()
    (k / "执行日志.md").write_text(f"""## Step 10: foo

日期：{today.isoformat()}

### 模型自评
- 顺畅度：4/5
""", encoding="utf-8")
    r = _call(tmp_path)
    assert r.returncode == 0
    assert from_d in r.stdout
    assert today.isoformat() in r.stdout
    assert "Step 10" in r.stdout


def test_custom_range_via_from_to(tmp_path):
    """--from / --to 指定范围。"""
    k = _setup(tmp_path)
    (k / "执行日志.md").write_text("""## Step 5: in-range

日期：2026-04-15

## Step 6: out-of-range

日期：2026-04-22
""", encoding="utf-8")
    r = _call(tmp_path, "2026-04-14", "2026-04-18")
    assert "Step 5" in r.stdout
    assert "Step 6" not in r.stdout


def test_four_section_reporting_skeleton(tmp_path):
    """周总结必须有"汇报四段"骨架：过程资产 / 经验总结 / 问题教训 / 开发进展。"""
    k = _setup(tmp_path)
    (k / "执行日志.md").write_text("""## Step 1: ordinary

日期：2026-04-18

### 用户评分
- 顺畅度：3/5

## Step 2: brilliant

日期：2026-04-19

### 用户评分
- 顺畅度：4.5/5
""", encoding="utf-8")
    r = _call(tmp_path, "2026-04-15", "2026-04-21")
    # 四段必须全在输出里
    assert "过程资产" in r.stdout
    assert "经验总结" in r.stdout
    assert "问题教训" in r.stdout
    assert "开发进展" in r.stdout


def test_experience_section_contains_high_score_steps(tmp_path):
    """经验总结段应包含评分 4.5+ 的 Step。"""
    k = _setup(tmp_path)
    (k / "执行日志.md").write_text("""## Step 2: brilliant

日期：2026-04-19

### 用户评分
- 顺畅度：4.5/5
""", encoding="utf-8")
    r = _call(tmp_path, "2026-04-15", "2026-04-21")
    exp_idx = r.stdout.find("经验总结")
    nxt_idx = min(
        (r.stdout.find(h, exp_idx) for h in ("问题教训", "开发进展") if r.stdout.find(h, exp_idx) > 0),
        default=len(r.stdout),
    )
    assert exp_idx >= 0
    section = r.stdout[exp_idx:nxt_idx]
    assert "Step 2" in section, f"经验总结段应含高分 Step 2，实际段内容：\n{section}"


def test_lessons_section_contains_high_diff_steps(tmp_path):
    """问题教训段应包含评分差值 ≥ 1.5 的 Step。"""
    k = _setup(tmp_path)
    (k / "执行日志.md").write_text("""## Step 3: misaligned

日期：2026-04-19

### 模型自评
- 顺畅度：4.5/5

### 用户评分
- 顺畅度：2.5/5

### 评分差异分析
- 差值：2.0（模型自评偏高，用户感受实际受损）
""", encoding="utf-8")
    r = _call(tmp_path, "2026-04-15", "2026-04-21")
    lesson_idx = r.stdout.find("问题教训")
    assert lesson_idx >= 0
    nxt_idx = min(
        (r.stdout.find(h, lesson_idx) for h in ("开发进展",) if r.stdout.find(h, lesson_idx) > 0),
        default=len(r.stdout),
    )
    section = r.stdout[lesson_idx:nxt_idx]
    assert "Step 3" in section, f"问题教训段应含差值 2.0 的 Step 3，实际段内容：\n{section}"


def test_friendly_hint_about_custom_range(tmp_path):
    """输出顶部应有一行友好提示说明 --from/--to 可覆盖。"""
    _setup(tmp_path)
    r = _call(tmp_path)
    first_lines = "\n".join(r.stdout.splitlines()[:10])
    assert "--from" in first_lines or "指定" in first_lines


def test_no_entries_in_range_message(tmp_path):
    """范围内无条目 → 输出清晰提示而不是空 markdown。"""
    _setup(tmp_path)
    r = _call(tmp_path, "2020-01-01", "2020-01-07")
    assert "无记录" in r.stdout or "空" in r.stdout or "no entries" in r.stdout.lower()
