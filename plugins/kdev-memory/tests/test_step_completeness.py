"""
step_completeness.py 的单元测试。

覆盖范围：
  1. parse_steps               —— 执行日志切分 Step 条目
  2. _extract_section          —— ### 子段提取
  3. _extract_field            —— '- 字段：值' 提取
  4. _is_placeholder           —— 各种占位符判定
  5. check_step                —— Step 半残判定（用户评分 / 模型自评扣分项）
  6. _within_lookback          —— 日期 lookback 过滤
  7. run_check（主入口）       —— 4 种终态（ok / has_half_complete / no-log-file / 超期过滤）
  8. format_hint_for_brief     —— SessionStart brief 注入文本
  9. format_hint_for_stop      —— Stop hook 软提醒文本
  10. strict_mode_should_block —— 今日半残 → 阻塞判定

跑法：
    cd plugins/kdev-memory
    python3 -m unittest discover tests -v
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "hooks" / "lib" / "step_completeness.py"
_spec = importlib.util.spec_from_file_location("step_completeness", _PATH)
assert _spec and _spec.loader
step_completeness = importlib.util.module_from_spec(_spec)
sys.modules["step_completeness"] = step_completeness
_spec.loader.exec_module(step_completeness)


SAMPLE_LOG = """# 执行日志

## Step 1: 完整条目
日期：2026-04-22

### 模型自评
- 完成时间：2026-04-22 10:00
- 顺畅度自评：4/5
- 扣分项：没加单测

### 用户评分
- 完成时间：2026-04-22 10:05
- 顺畅度：4/5
- 用户评价：OK

## Step 2: 时分戳为占位
日期：2026-04-22

### 模型自评
- 完成时间：2026-04-22 14:00
- 顺畅度自评：5/5
- 扣分项：良好

### 用户评分
- 完成时间：—
- 顺畅度：—/5

## Step 3: 污染样本
日期：2026-04-21

### 用户评分
- 完成时间：污染样本
- 顺畅度：污染样本

## Step 4: 扣分项为空
日期：2026-04-22

### 模型自评
- 完成时间：2026-04-22 16:00
- 顺畅度自评：5/5
- 扣分项：—

### 用户评分
- 完成时间：2026-04-22 16:10
- 顺畅度：5/5
- 用户评价：perfect

## Step 5: 完全无用户评分段
日期：2026-04-22

### 模型自评
- 完成时间：2026-04-22 18:00
- 顺畅度自评：3/5
- 扣分项：赶工
"""


class TestParseSteps(unittest.TestCase):
    def test_extracts_multiple_steps(self):
        steps = step_completeness.parse_steps(SAMPLE_LOG)
        self.assertEqual(len(steps), 5)
        self.assertEqual(steps[0]["label"], "Step 1")
        self.assertEqual(steps[0]["date"], "2026-04-22")
        self.assertEqual(steps[4]["label"], "Step 5")

    def test_supports_step_variants(self):
        text = "## Step 5.5: 迭代内\n日期：2026-04-10\n\n## Step M-7 meta 回补\n日期：2026-04-15\n"
        steps = step_completeness.parse_steps(text)
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["label"], "Step 5.5")
        self.assertEqual(steps[1]["label"], "Step M-7")

    def test_empty_log(self):
        self.assertEqual(step_completeness.parse_steps(""), [])
        self.assertEqual(step_completeness.parse_steps("# 执行日志\n\n无内容\n"), [])


class TestExtractSection(unittest.TestCase):
    def test_finds_and_stops_at_next(self):
        body = "### 模型自评\n- 扣分项：x\n\n### 用户评分\n- 顺畅度：4/5\n"
        s = step_completeness._extract_section(body, "### 模型自评")
        self.assertIn("扣分项：x", s)
        self.assertNotIn("顺畅度", s)

    def test_missing_returns_none(self):
        self.assertIsNone(step_completeness._extract_section("body", "### XXX"))


class TestExtractField(unittest.TestCase):
    def test_chinese_colon(self):
        self.assertEqual(
            step_completeness._extract_field("- 完成时间：2026-04-22 10:00\n", "完成时间"),
            "2026-04-22 10:00",
        )

    def test_english_colon(self):
        self.assertEqual(
            step_completeness._extract_field("- 顺畅度: 4/5\n", "顺畅度"),
            "4/5",
        )

    def test_strips_trailing_comment(self):
        # 带 "# 注释" 的一行
        self.assertEqual(
            step_completeness._extract_field("- 完成时间：14:32 # 必须带时分\n", "完成时间"),
            "14:32",
        )

    def test_missing(self):
        self.assertIsNone(step_completeness._extract_field("body without field", "顺畅度"))


class TestIsPlaceholder(unittest.TestCase):
    def test_empty_and_none(self):
        self.assertTrue(step_completeness._is_placeholder(None))
        self.assertTrue(step_completeness._is_placeholder(""))
        self.assertTrue(step_completeness._is_placeholder("   "))

    def test_dashes(self):
        self.assertTrue(step_completeness._is_placeholder("—"))
        self.assertTrue(step_completeness._is_placeholder("-"))

    def test_keyword_values(self):
        self.assertTrue(step_completeness._is_placeholder("待补"))
        self.assertTrue(step_completeness._is_placeholder("污染样本"))
        self.assertTrue(step_completeness._is_placeholder("TBD"))
        self.assertTrue(step_completeness._is_placeholder("TODO"))

    def test_score_with_placeholder(self):
        # "—/5" 或 " / 5" 也算占位
        self.assertTrue(step_completeness._is_placeholder("—/5"))
        self.assertTrue(step_completeness._is_placeholder("-/5"))
        self.assertTrue(step_completeness._is_placeholder("待补/5"))

    def test_mixed_placeholder(self):
        self.assertTrue(step_completeness._is_placeholder("— 待补"))

    def test_real_values_not_placeholder(self):
        self.assertFalse(step_completeness._is_placeholder("4/5"))
        self.assertFalse(step_completeness._is_placeholder("2026-04-22 10:00"))
        self.assertFalse(step_completeness._is_placeholder("挺顺利"))


class TestCheckStep(unittest.TestCase):
    def test_complete_step_no_issues(self):
        steps = step_completeness.parse_steps(SAMPLE_LOG)
        issues = step_completeness.check_step(steps[0])
        self.assertEqual(issues, [])

    def test_placeholder_timestamp(self):
        steps = step_completeness.parse_steps(SAMPLE_LOG)
        issues = step_completeness.check_step(steps[1])  # Step 2
        self.assertTrue(any("完成时间" in i for i in issues))
        self.assertTrue(any("顺畅度" in i for i in issues))

    def test_polluted_sample(self):
        steps = step_completeness.parse_steps(SAMPLE_LOG)
        issues = step_completeness.check_step(steps[2])  # Step 3
        self.assertTrue(any("污染样本" in i for i in issues))

    def test_empty_deduction(self):
        steps = step_completeness.parse_steps(SAMPLE_LOG)
        issues = step_completeness.check_step(steps[3])  # Step 4
        self.assertTrue(any("扣分项" in i for i in issues))

    def test_no_user_section_but_has_model(self):
        """有模型自评段但完全无用户评分段 → 半残。"""
        steps = step_completeness.parse_steps(SAMPLE_LOG)
        issues = step_completeness.check_step(steps[4])  # Step 5
        self.assertTrue(any("用户评分" in i for i in issues))


class TestWithinLookback(unittest.TestCase):
    def test_in_range(self):
        self.assertTrue(step_completeness._within_lookback("2026-04-20", "2026-04-22", 14))

    def test_out_of_range(self):
        self.assertFalse(step_completeness._within_lookback("2026-01-01", "2026-04-22", 14))

    def test_none_date_included(self):
        # 保守处理：无日期的 Step 默认算在扫描范围内
        self.assertTrue(step_completeness._within_lookback(None, "2026-04-22", 14))


class TestRunCheck(unittest.TestCase):
    def _write(self, content: str) -> Path:
        tmpdir = Path(tempfile.mkdtemp())
        path = tmpdir / "执行日志.md"
        path.write_text(content, encoding="utf-8")
        return path

    def test_no_log_file(self):
        r = step_completeness.run_check(Path("/does/not/exist.md"), "2026-04-22")
        self.assertEqual(r["status"], "no-log-file")

    def test_has_half_complete(self):
        path = self._write(SAMPLE_LOG)
        r = step_completeness.run_check(path, "2026-04-22")
        self.assertEqual(r["status"], "has_half_complete")
        # Step 2/3/4/5 都是半残
        self.assertEqual(len(r["half_complete_steps"]), 4)
        # 今日（2026-04-22）半残有 Step 2/4/5 共 3 条
        self.assertEqual(r["today_half_complete"], 3)

    def test_all_ok(self):
        text = SAMPLE_LOG.split("## Step 2")[0]  # 只保留 Step 1
        path = self._write(text)
        r = step_completeness.run_check(path, "2026-04-22")
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["half_complete_steps"], [])

    def test_lookback_filters_old_steps(self):
        text = SAMPLE_LOG + "\n## Step 99: 老历史\n日期：2026-01-01\n\n### 用户评分\n- 完成时间：—\n"
        path = self._write(text)
        r = step_completeness.run_check(path, "2026-04-22", lookback_days=14)
        labels = [s["step_label"] for s in r["half_complete_steps"]]
        self.assertNotIn("Step 99", labels)


class TestFormatHintForBrief(unittest.TestCase):
    def test_no_hint_when_ok(self):
        self.assertIsNone(step_completeness.format_hint_for_brief({"status": "ok"}))

    def test_hint_lists_half_complete(self):
        result = {
            "status": "has_half_complete",
            "total_scanned": 10,
            "half_complete_steps": [
                {"step_label": "Step 8", "date": "2026-04-22", "issues": ["用户评分段「完成时间」为 '—'"]},
                {"step_label": "Step 9", "date": "2026-04-21", "issues": ["扣分项为空"]},
            ],
        }
        hint = step_completeness.format_hint_for_brief(result)
        self.assertIn("欠评 / 半残", hint)
        self.assertIn("Step 8", hint)
        self.assertIn("Step 9", hint)
        self.assertIn("新会话第一件事", hint)

    def test_hint_truncates_long_list(self):
        result = {
            "status": "has_half_complete",
            "total_scanned": 30,
            "half_complete_steps": [
                {"step_label": f"Step {i}", "date": "2026-04-22", "issues": ["x"]}
                for i in range(10)
            ],
        }
        hint = step_completeness.format_hint_for_brief(result, max_list=5)
        self.assertIn("...还有 5 条", hint)


class TestStrictModeShouldBlock(unittest.TestCase):
    def test_blocks_when_today_half_complete(self):
        self.assertTrue(step_completeness.strict_mode_should_block({"today_half_complete": 1}))

    def test_no_block_when_today_zero(self):
        self.assertFalse(step_completeness.strict_mode_should_block({"today_half_complete": 0}))

    def test_no_block_when_status_ok(self):
        self.assertFalse(step_completeness.strict_mode_should_block({"today_half_complete": 0, "status": "ok"}))


if __name__ == "__main__":
    unittest.main()
