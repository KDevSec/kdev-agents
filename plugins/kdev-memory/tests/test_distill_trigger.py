"""单测 distill_trigger.py + memory_config.py 的 distill 配置块。

覆盖：
- memory_config.read_distill_mode 各种 fallback 路径（auto 默认 / manual 显式 / 嵌套 / flat key）
- memory_config.read_distill_thresholds 默认值 + 自定义值
- _parse_kv_yaml 嵌套语法解析
- distill_trigger.check_distill_trigger 触发逻辑各种场景

零外部依赖，纯 stdlib + tempfile fixture。
"""

from __future__ import annotations

import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks" / "lib"))

import distill_trigger  # noqa: E402
import memory_config  # noqa: E402


# ==================== memory_config distill 字段 ====================

class TestDistillMode(unittest.TestCase):

    def test_no_config_returns_auto(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            self.assertEqual(memory_config.read_distill_mode(kdev), "auto")

    def test_manual_explicit_flat(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text("distill_mode: manual\n", encoding="utf-8")
            self.assertEqual(memory_config.read_distill_mode(kdev), "manual")

    def test_manual_explicit_nested(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text(dedent("""\
                distill:
                  mode: manual
            """), encoding="utf-8")
            self.assertEqual(memory_config.read_distill_mode(kdev), "manual")

    def test_auto_explicit_nested(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text(dedent("""\
                distill:
                  mode: auto
            """), encoding="utf-8")
            self.assertEqual(memory_config.read_distill_mode(kdev), "auto")

    def test_invalid_value_falls_back_to_auto(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text("distill_mode: yolo\n", encoding="utf-8")
            self.assertEqual(memory_config.read_distill_mode(kdev), "auto")

    def test_record_mode_still_works_alongside_distill(self):
        """同时配 record_mode 和 distill 块不互相干扰。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text(dedent("""\
                record_mode: inline
                distill:
                  mode: manual
                  reminder_days: 14
            """), encoding="utf-8")
            self.assertEqual(memory_config.read_record_mode(kdev), "inline")
            self.assertEqual(memory_config.read_distill_mode(kdev), "manual")


class TestDistillThresholds(unittest.TestCase):

    def test_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            t = memory_config.read_distill_thresholds(kdev)
            self.assertEqual(t["reminder_days"], 7)
            self.assertEqual(t["reminder_new_f"], 10)
            self.assertEqual(t["reminder_new_misalign"], 3)

    def test_custom_nested(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text(dedent("""\
                distill:
                  reminder_days: 14
                  reminder_new_f: 20
                  reminder_new_misalign: 5
            """), encoding="utf-8")
            t = memory_config.read_distill_thresholds(kdev)
            self.assertEqual(t["reminder_days"], 14)
            self.assertEqual(t["reminder_new_f"], 20)
            self.assertEqual(t["reminder_new_misalign"], 5)

    def test_custom_flat_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text(dedent("""\
                distill_reminder_days: 30
                distill_reminder_new_f: 50
            """), encoding="utf-8")
            t = memory_config.read_distill_thresholds(kdev)
            self.assertEqual(t["reminder_days"], 30)
            self.assertEqual(t["reminder_new_f"], 50)
            # 未配置项保留默认
            self.assertEqual(t["reminder_new_misalign"], 3)

    def test_invalid_int_falls_back_to_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text(dedent("""\
                distill:
                  reminder_days: not-a-number
            """), encoding="utf-8")
            t = memory_config.read_distill_thresholds(kdev)
            self.assertEqual(t["reminder_days"], 7)


# ==================== distill_trigger ====================

def _write_minimal_kdev(kdev: Path, with_distill_marker: bool = False) -> None:
    """建一个最小可触发检测的 fixture。"""
    kdev.mkdir(parents=True, exist_ok=True)
    (kdev / "skill-feedback.md").write_text("# Skill Feedback\n", encoding="utf-8")
    (kdev / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    (kdev / "改进建议.md").write_text("# 改进建议\n", encoding="utf-8")
    if with_distill_marker:
        (kdev / ".last-distill").touch()


class TestDistillTrigger(unittest.TestCase):

    def test_never_distilled_no_data_does_not_trigger(self):
        """从未蒸馏 + 无数据 → 不触发。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_minimal_kdev(kdev)
            r = distill_trigger.check_distill_trigger(kdev)
            self.assertFalse(r.should_trigger)
            self.assertIsNone(r.days_since_distill)

    def test_never_distilled_with_f_data_triggers(self):
        """从未蒸馏 + 有 F-NNN 数据 → 首次触发。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_minimal_kdev(kdev)
            (kdev / "skill-feedback.md").write_text(dedent("""\
                # Skill Feedback

                ## F-001: 测试反馈
                日期：2026-05-10
                subject: plugin:test
                verbatim: "test"
            """), encoding="utf-8")
            r = distill_trigger.check_distill_trigger(kdev)
            self.assertTrue(r.should_trigger)
            self.assertIsNone(r.days_since_distill)
            self.assertEqual(r.new_f_count, 1)
            self.assertTrue(any("首次蒸馏" in x for x in r.reasons))

    def test_recent_distill_no_new_data_does_not_trigger(self):
        """最近刚蒸馏过 + 无新数据 → 不触发。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_minimal_kdev(kdev, with_distill_marker=True)
            r = distill_trigger.check_distill_trigger(kdev)
            self.assertFalse(r.should_trigger)

    def test_old_distill_with_new_f_triggers(self):
        """旧 .last-distill + F 新增超阈值 → 触发。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_minimal_kdev(kdev)

            # .last-distill 改成 10 天前
            marker = kdev / ".last-distill"
            marker.touch()
            old_ts = time.time() - (10 * 86400)
            import os
            os.utime(marker, (old_ts, old_ts))

            # 写 12 条 F 条目（超过默认阈值 10）
            # R-002 修：日期动态计算为"5 天前"，保证晚于 .last-distill (10 天前)
            # 避开 hardcode date drift（原来写死 2026-05-15 + .last-distill 10 天前导致
            # 当 today 漂到 2026-05-26+ 时所有 entries 被日期过滤掉 → new_f=0 → 失败）
            recent_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
            f_entries = ["# Skill Feedback\n"]
            for i in range(1, 13):
                f_entries.append(dedent(f"""\
                    ## F-{i:03d}
                    日期：{recent_date}
                    subject: plugin:test
                    verbatim: "test {i}"
                """))
            (kdev / "skill-feedback.md").write_text("\n".join(f_entries), encoding="utf-8")

            r = distill_trigger.check_distill_trigger(kdev)
            self.assertTrue(r.should_trigger)
            self.assertGreaterEqual(r.days_since_distill or 0, 10)
            self.assertGreaterEqual(r.new_f_count, 12)

    def test_time_only_without_new_data_does_not_trigger(self):
        """时间够久但完全无新数据 → 不触发（AND 语义）。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_minimal_kdev(kdev, with_distill_marker=True)

            # .last-distill 改成 30 天前
            marker = kdev / ".last-distill"
            old_ts = time.time() - (30 * 86400)
            import os
            os.utime(marker, (old_ts, old_ts))

            r = distill_trigger.check_distill_trigger(kdev)
            # 时间满足但无新 F/R/misalign → 不触发
            self.assertFalse(r.should_trigger)

    def test_mode_picked_up_from_config(self):
        """check_distill_trigger.mode 字段反映 config.yaml 设置。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_minimal_kdev(kdev)
            (kdev / "config.yaml").write_text("distill_mode: manual\n", encoding="utf-8")
            r = distill_trigger.check_distill_trigger(kdev)
            self.assertEqual(r.mode, "manual")

    def test_fallback_to_last_promote_marker(self):
        """老项目只有 .last-promote 没有 .last-distill → 用 .last-promote 作为基线。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_minimal_kdev(kdev)

            marker = kdev / ".last-promote"
            marker.touch()
            old_ts = time.time() - (5 * 86400)  # 5 天前
            import os
            os.utime(marker, (old_ts, old_ts))

            r = distill_trigger.check_distill_trigger(kdev)
            self.assertIsNotNone(r.days_since_distill)
            self.assertGreaterEqual(r.days_since_distill, 4)
            self.assertLessEqual(r.days_since_distill, 6)

    def test_misalign_step_counted(self):
        """差值 ≥ 1.5 的 Step 计入 new_misalign_count。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_minimal_kdev(kdev)
            (kdev / "执行日志.md").write_text(dedent("""\
                # 执行日志

                ## Step 1
                日期：2026-05-15

                ### 评分差异分析段
                差值 +2，明显偏差

                ## Step 2
                日期：2026-05-15

                ### 评分差异分析段
                差值 -1.8

                ## Step 3
                日期：2026-05-15

                ### 评分差异分析段
                差值 -0.5（不算 misalign）
            """), encoding="utf-8")

            r = distill_trigger.check_distill_trigger(kdev)
            self.assertEqual(r.new_misalign_count, 2)


class TestTimestampFormDualRecognition(unittest.TestCase):
    """Q-020/v0.17 时间戳形 F/R 条目（`## F 20260625-...`）也要被计数。

    回归：distill_trigger 用硬编码 `^##\\s+F-\\d+` / `R-\\d+`，时间戳形被静默漏掉，
    导致 v0.17 后所有新 F/R 不计入触发判定。应改用 id_label_fragment。
    """

    def test_timestamp_form_f_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_minimal_kdev(kdev)
            recent_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            (kdev / "skill-feedback.md").write_text(dedent(f"""\
                # Skill Feedback

                ## F 20260625-093000-ly: 时间戳形反馈
                日期：{recent_date}
                subject: plugin:test
                verbatim: "test"
            """), encoding="utf-8")
            r = distill_trigger.check_distill_trigger(kdev)
            self.assertEqual(r.new_f_count, 1, "时间戳形 F 未被计数")

    def test_timestamp_form_r_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_minimal_kdev(kdev)
            recent_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            (kdev / "改进建议.md").write_text(dedent(f"""\
                # 改进建议

                ## R 20260625-095000-ly: 时间戳形改进
                日期：{recent_date}
                项目：test
            """), encoding="utf-8")
            r = distill_trigger.check_distill_trigger(kdev)
            self.assertEqual(r.new_r_count, 1, "时间戳形 R 未被计数")


if __name__ == "__main__":
    unittest.main()
