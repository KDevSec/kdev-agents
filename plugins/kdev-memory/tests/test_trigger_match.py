"""
trigger-match.py 的单元测试。

覆盖范围（优先级高→低）：
  1. sanitize_prompt          —— 8 条正则的防误触发逻辑
  2. parse_triggers_value     —— 三种 triggers 格式解析
  3. parse_multiline_triggers —— YAML 多行列表
  4. match_entries            —— 子串匹配 + 分数排序
  5. filter_already_injected  —— session 内去重
  6. load_dedup_state         —— TTL 过期清理

跑法：
    cd plugins/kdev-memory
    python3 -m unittest discover tests -v

零外部依赖（stdlib unittest），不需要 pytest。
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

_LIB_PATH = Path(__file__).resolve().parent.parent / "hooks" / "lib" / "trigger-match.py"
_spec = importlib.util.spec_from_file_location("trigger_match", _LIB_PATH)
tm = importlib.util.module_from_spec(_spec)
sys.modules["trigger_match"] = tm
_spec.loader.exec_module(tm)


class SanitizePromptTests(unittest.TestCase):
    """sanitize_prompt 的 8 条正则逻辑验证。"""

    def test_strips_fenced_code_blocks(self):
        prompt = "请看这段代码\n```\npnpm install\n```\n然后继续"
        result = tm.sanitize_prompt(prompt)
        self.assertNotIn("pnpm install", result)
        self.assertIn("请看这段代码", result)
        self.assertIn("然后继续", result)

    def test_strips_inline_code(self):
        prompt = "跑 `pnpm install` 会报错"
        result = tm.sanitize_prompt(prompt)
        self.assertNotIn("pnpm install", result)
        self.assertIn("跑", result)
        self.assertIn("会报错", result)

    def test_strips_xml_block(self):
        prompt = "看这段 <example>pnpm install</example> 不算数"
        result = tm.sanitize_prompt(prompt)
        self.assertNotIn("pnpm install", result)
        self.assertIn("不算数", result)

    def test_strips_self_closing_xml(self):
        prompt = "a <br/> b <img src='x'/> c"
        result = tm.sanitize_prompt(prompt)
        self.assertNotIn("<br", result)
        self.assertNotIn("<img", result)
        self.assertIn("a", result)
        self.assertIn("c", result)

    def test_strips_urls(self):
        prompt = "看 https://github.com/foo/pnpm-install 这个仓库"
        result = tm.sanitize_prompt(prompt)
        self.assertNotIn("pnpm-install", result)
        self.assertNotIn("github.com", result)
        self.assertIn("看", result)
        self.assertIn("这个仓库", result)

    def test_strips_blockquotes(self):
        prompt = "下面是错误引用\n> pnpm install failed\n真正我想说的是 workspace"
        result = tm.sanitize_prompt(prompt)
        self.assertNotIn("pnpm install failed", result)
        self.assertIn("真正我想说的", result)
        self.assertIn("workspace", result)

    def test_strips_git_diff_headers(self):
        prompt = (
            "看这段 diff\n"
            "diff --git a/pnpm-lock.yaml b/pnpm-lock.yaml\n"
            "index abc123..def456 100644\n"
            "--- a/pnpm-lock.yaml\n"
            "+++ b/pnpm-lock.yaml\n"
            "@@ -1,3 +1,4 @@\n"
            "这是用户的真实问题\n"
        )
        result = tm.sanitize_prompt(prompt)
        self.assertNotIn("pnpm-lock.yaml", result)
        self.assertIn("这是用户的真实问题", result)

    def test_strips_file_paths(self):
        prompt = "文件 src/collector/core.js 有问题，但 pnpm install 是对的"
        result = tm.sanitize_prompt(prompt)
        self.assertNotIn("src/collector/core.js", result)
        # 纯 pnpm install（没斜杠）不受路径正则影响
        self.assertIn("pnpm install", result)

    def test_preserves_plain_text(self):
        """普通文本应完整保留。"""
        prompt = "跑 pnpm install 的时候 workspace 依赖漏装了"
        result = tm.sanitize_prompt(prompt)
        self.assertIn("pnpm install", result)
        self.assertIn("workspace 依赖", result)
        self.assertIn("漏装", result)

    def test_preserves_chinese(self):
        prompt = "今天踩坑了：采集器核心循环挂了"
        result = tm.sanitize_prompt(prompt)
        self.assertIn("采集器", result)
        self.assertIn("核心循环", result)


class ParseTriggersValueTests(unittest.TestCase):
    """parse_triggers_value：三种 triggers 格式解析。"""

    def test_json_array_with_quotes(self):
        result = tm.parse_triggers_value('["pnpm install", "workspace 依赖"]')
        self.assertEqual(result, ["pnpm install", "workspace 依赖"])

    def test_json_array_without_quotes_tolerated(self):
        """没引号的 [a, b] 应被容错处理。"""
        result = tm.parse_triggers_value("[pnpm install, workspace 依赖]")
        self.assertEqual(result, ["pnpm install", "workspace 依赖"])

    def test_comma_separated_bare(self):
        result = tm.parse_triggers_value("采集器, 核心循环, collector")
        self.assertEqual(result, ["采集器", "核心循环", "collector"])

    def test_single_value(self):
        result = tm.parse_triggers_value("pnpm")
        self.assertEqual(result, ["pnpm"])

    def test_empty_returns_empty_list(self):
        self.assertEqual(tm.parse_triggers_value(""), [])
        self.assertEqual(tm.parse_triggers_value("   "), [])

    def test_dedup_case_insensitive_preserves_first(self):
        """大小写不敏感去重，保留首次出现的大小写形式。"""
        result = tm.parse_triggers_value('["PNPM", "pnpm", "Pnpm"]')
        self.assertEqual(result, ["PNPM"])

    def test_dedup_preserves_order(self):
        result = tm.parse_triggers_value('["a", "b", "a", "c"]')
        self.assertEqual(result, ["a", "b", "c"])

    def test_strips_surrounding_whitespace(self):
        result = tm.parse_triggers_value("  a  ,   b   ")
        self.assertEqual(result, ["a", "b"])

    def test_handles_mixed_quotes_in_bracket(self):
        result = tm.parse_triggers_value("""['a', "b", c]""")
        self.assertEqual(result, ["a", "b", "c"])


class ParseMultilineTriggersTests(unittest.TestCase):
    """parse_multiline_triggers：YAML 多行列表。"""

    def test_basic_yaml_list(self):
        lines = ["  - 架构决策", "  - 技术选型", "  - 不可逆"]
        items, consumed = tm.parse_multiline_triggers(lines, 0)
        self.assertEqual(items, ["架构决策", "技术选型", "不可逆"])
        self.assertEqual(consumed, 3)

    def test_stops_at_non_list_line(self):
        lines = ["  - a", "  - b", "日期：2026-04-21", "  - c"]
        items, consumed = tm.parse_multiline_triggers(lines, 0)
        self.assertEqual(items, ["a", "b"])
        self.assertEqual(consumed, 2)

    def test_handles_quoted_items(self):
        lines = ['  - "pnpm install"', "  - 'workspace 依赖'"]
        items, _ = tm.parse_multiline_triggers(lines, 0)
        self.assertEqual(items, ["pnpm install", "workspace 依赖"])

    def test_empty_when_no_list(self):
        lines = ["日期：2026-04-21", "其他内容"]
        items, consumed = tm.parse_multiline_triggers(lines, 0)
        self.assertEqual(items, [])
        self.assertEqual(consumed, 0)

    def test_skips_empty_items(self):
        lines = ["  - a", "  -   ", "  - b"]
        items, _ = tm.parse_multiline_triggers(lines, 0)
        self.assertEqual(items, ["a", "b"])


class MatchEntriesTests(unittest.TestCase):
    """match_entries：substring 匹配 + 分数排序。"""

    @staticmethod
    def _entry(entry_id, triggers):
        return {"id": entry_id, "title": f"T-{entry_id}", "triggers": triggers,
                "path": f"{entry_id}.md", "source": "G", "date": None}

    def test_single_match(self):
        entries = [self._entry("G-1", ["pnpm install"])]
        result = tm.match_entries("怎么 pnpm install 报错", entries)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0]["id"], "G-1")
        self.assertEqual(result[0][1], 1)

    def test_multiple_triggers_same_entry_stack_score(self):
        entries = [self._entry("G-1", ["pnpm", "install", "workspace"])]
        result = tm.match_entries("pnpm install 在 workspace 根目录", entries)
        self.assertEqual(result[0][1], 3)

    def test_case_insensitive_match(self):
        entries = [self._entry("G-1", ["PNPM"])]
        result = tm.match_entries("我的 pnpm 命令", entries)
        self.assertEqual(len(result), 1)

    def test_no_match_excluded(self):
        entries = [self._entry("G-1", ["aiohttp"])]
        result = tm.match_entries("完全无关的讨论", entries)
        self.assertEqual(result, [])

    def test_sorted_by_score_desc(self):
        entries = [
            self._entry("low", ["a"]),
            self._entry("high", ["a", "b", "c"]),
            self._entry("mid", ["a", "b"]),
        ]
        result = tm.match_entries("a b c", entries)
        ids = [e["id"] for e, _ in result]
        self.assertEqual(ids, ["high", "mid", "low"])


class DedupFilterTests(unittest.TestCase):
    """filter_already_injected：session 内去重。"""

    @staticmethod
    def _match(entry_id, score=1):
        return ({"id": entry_id, "title": "t", "triggers": [], "path": "p",
                 "source": "G", "date": None}, score)

    def test_injected_filtered_out(self):
        matches = [self._match("G-1"), self._match("G-2")]
        state = {"sessions": {"s1": {"injected_ids": ["G-1"], "timestamp": time.time()}}}
        result = tm.filter_already_injected(matches, "s1", state)
        self.assertEqual([e["id"] for e, _ in result], ["G-2"])

    def test_unknown_session_keeps_all(self):
        matches = [self._match("G-1"), self._match("G-2")]
        state = {"sessions": {}}
        result = tm.filter_already_injected(matches, "new-session", state)
        self.assertEqual(len(result), 2)

    def test_all_injected_returns_empty(self):
        matches = [self._match("G-1")]
        state = {"sessions": {"s1": {"injected_ids": ["G-1"], "timestamp": time.time()}}}
        result = tm.filter_already_injected(matches, "s1", state)
        self.assertEqual(result, [])


class TTLPruneTests(unittest.TestCase):
    """load_dedup_state：过期 session 自动清理。"""

    def _run_with_state(self, state_content):
        """在临时目录里写 state 文件，触发 load_dedup_state。"""
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "trigger-sessions.json"
            state_path.write_text(json.dumps(state_content), encoding="utf-8")
            with mock.patch.object(tm, "STATE_FILE", state_path):
                return tm.load_dedup_state()

    def test_expired_sessions_pruned(self):
        now = time.time()
        state = {"sessions": {
            "fresh": {"injected_ids": ["G-1"], "timestamp": now - 100},
            "old": {"injected_ids": ["G-2"], "timestamp": now - 7200},  # 2 小时前
        }}
        result = self._run_with_state(state)
        self.assertIn("fresh", result["sessions"])
        self.assertNotIn("old", result["sessions"])

    def test_all_expired_yields_empty_sessions(self):
        now = time.time()
        state = {"sessions": {
            "old1": {"injected_ids": ["a"], "timestamp": now - 7200},
            "old2": {"injected_ids": ["b"], "timestamp": now - 5000},
        }}
        result = self._run_with_state(state)
        self.assertEqual(result["sessions"], {})

    def test_just_under_ttl_kept(self):
        """距离 TTL 还差 1 秒应保留。"""
        now = time.time()
        state = {"sessions": {
            "fresh-edge": {"injected_ids": ["a"], "timestamp": now - (tm.DEDUP_TTL_SECONDS - 1)},
        }}
        result = self._run_with_state(state)
        self.assertIn("fresh-edge", result["sessions"])

    def test_just_over_ttl_pruned(self):
        """超过 TTL 1 秒应被清理。"""
        now = time.time()
        state = {"sessions": {
            "stale-edge": {"injected_ids": ["a"], "timestamp": now - (tm.DEDUP_TTL_SECONDS + 1)},
        }}
        result = self._run_with_state(state)
        self.assertNotIn("stale-edge", result["sessions"])

    def test_missing_state_file_returns_empty(self):
        """state 文件不存在时 load 应返回空骨架。"""
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "does-not-exist.json"
            with mock.patch.object(tm, "STATE_FILE", state_path):
                result = tm.load_dedup_state()
                self.assertEqual(result, {"sessions": {}})

    def test_malformed_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "trigger-sessions.json"
            state_path.write_text("not json at all", encoding="utf-8")
            with mock.patch.object(tm, "STATE_FILE", state_path):
                result = tm.load_dedup_state()
                self.assertEqual(result, {"sessions": {}})


class GlobScanTests(unittest.TestCase):
    """scan_g_entries / scan_step_entries 的 glob 扫描（覆盖归档文件）。"""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.kdev_dir = Path(self._td.name) / ".kdev" / "memory"
        self.kdev_dir.mkdir(parents=True)
        self._patcher = mock.patch.object(tm, "KDEV_DIR", self.kdev_dir)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._td.cleanup()

    def test_g_entries_scan_main_and_archive_dir(self):
        """踩坑日志.md（主文件） + 归档/踩坑日志-2026Q1.md（归档目录）都要被扫到。"""
        (self.kdev_dir / "踩坑日志.md").write_text(
            "## G-020: 当前季度的踩坑\ntriggers: [\"新坑\"]\n日期：2026-04-15\n\n",
            encoding="utf-8",
        )
        archive_dir = self.kdev_dir / "归档"
        archive_dir.mkdir()
        (archive_dir / "踩坑日志-2026Q1.md").write_text(
            "## G-012: 老坑归档\ntriggers: [\"pnpm install\"]\n日期：2026-03-15\n\n",
            encoding="utf-8",
        )
        entries = tm.scan_g_entries()
        ids = sorted(e["id"] for e in entries)
        self.assertEqual(ids, ["G-012", "G-020"])

    def test_g_entries_only_main_when_no_archive_dir(self):
        """无归档目录时只扫主文件（向后兼容 0.3.0）。"""
        (self.kdev_dir / "踩坑日志.md").write_text(
            "## G-001: 唯一一条\ntriggers: [\"foo\"]\n日期：2026-04-15\n\n",
            encoding="utf-8",
        )
        entries = tm.scan_g_entries()
        self.assertEqual([e["id"] for e in entries], ["G-001"])

    def test_g_entries_ignores_non_prefix_files_in_archive(self):
        """归档/里的其他文件（如 执行日志-2026-03.md）不应混入踩坑扫描结果。"""
        (self.kdev_dir / "踩坑日志.md").write_text(
            "## G-001: 主条目\ntriggers: [\"x\"]\n日期：2026-04-15\n\n",
            encoding="utf-8",
        )
        archive_dir = self.kdev_dir / "归档"
        archive_dir.mkdir()
        # 执行日志的归档不应混进来
        (archive_dir / "执行日志-2026-03.md").write_text(
            "## G-999: 不应该被扫到\ntriggers: [\"不应匹配\"]\n日期：2026-03-15\n\n",
            encoding="utf-8",
        )
        entries = tm.scan_g_entries()
        ids = [e["id"] for e in entries]
        self.assertEqual(ids, ["G-001"])
        self.assertNotIn("G-999", ids)

    def test_g_entries_empty_when_no_file(self):
        """主文件和归档都不存在时返回空。"""
        entries = tm.scan_g_entries()
        self.assertEqual(entries, [])

    def test_g_entries_recall_timestamp_form(self):
        """v0.17(Q-020) 时间戳形 G 条目（## G <YYYYMMDD-HHMMSS>-who）也要能被召回。

        旧扫描器 heading_re 只认顺序号 `G-\\d+`，时间戳形静默 MISS——踩坑防重踩
        是核心通道，漏召 = 用户再撞同类坑时 recall 不提示（静默失败）。
        """
        (self.kdev_dir / "踩坑日志.md").write_text(
            "## G 20260613-101432-ly: 时间戳形踩坑\ntriggers: [\"时间戳召回\"]\n日期：2026-06-13\n\n",
            encoding="utf-8",
        )
        entries = tm.scan_g_entries()
        ids = [e["id"] for e in entries]
        self.assertEqual(ids, ["G 20260613-101432-ly"])
        self.assertEqual(entries[0]["title"], "时间戳形踩坑")

    def test_g_entries_recall_both_legacy_and_timestamp(self):
        """新旧双认：同一文件里 G-NNN（旧）和时间戳形（新）都要召回。"""
        (self.kdev_dir / "踩坑日志.md").write_text(
            "## G-003: 旧顺序号坑\ntriggers: [\"旧坑\"]\n日期：2026-06-13\n\n"
            "## G 20260613-101432-ly1989abc: 时间戳形坑\ntriggers: [\"新坑\"]\n日期：2026-06-13\n\n",
            encoding="utf-8",
        )
        ids = sorted(e["id"] for e in tm.scan_g_entries())
        self.assertEqual(ids, ["G 20260613-101432-ly1989abc", "G-003"])

    def test_step_entries_date_filter_excludes_archive(self):
        """执行日志归档里的老 Step 被今日/昨日过滤剔除。"""
        today = datetime_today_str()
        (self.kdev_dir / "执行日志.md").write_text(
            f"## Step 23: 今日工作\ntriggers: [\"采集器\"]\n日期：{today}\n\n",
            encoding="utf-8",
        )
        archive_dir = self.kdev_dir / "归档"
        archive_dir.mkdir()
        (archive_dir / "执行日志-2026-03.md").write_text(
            "## Step 5: 老 Step 归档\ntriggers: [\"老功能\"]\n日期：2026-03-10\n\n",
            encoding="utf-8",
        )
        entries = tm.scan_step_entries()
        ids = [e["id"] for e in entries]
        self.assertIn("Step 23", ids)
        self.assertNotIn("Step 5", ids)

    def test_step_entries_yesterday_included(self):
        yesterday_str = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        (self.kdev_dir / "执行日志.md").write_text(
            f"## Step 22: 昨日 Step\ntriggers: [\"昨日功能\"]\n日期：{yesterday_str}\n\n",
            encoding="utf-8",
        )
        entries = tm.scan_step_entries()
        self.assertEqual([e["id"] for e in entries], ["Step 22"])

    def test_step_entries_recall_timestamp_form(self):
        """时间戳形 Step（## Step <YYYYMMDD-HHMMSS>-who）今日条目要被召回。

        回归守卫：当前靠宽松 `[\\w.-]+` 通配"碰巧"命中；改为显式双认（去通配）后
        仍须命中——锁住时间戳形 Step 不被重构误伤。
        """
        today = datetime_today_str()
        (self.kdev_dir / "执行日志.md").write_text(
            f"## Step 20260614-101432-ly1989abc: 时间戳形 Step\ntriggers: [\"时间戳step\"]\n日期：{today}\n\n",
            encoding="utf-8",
        )
        ids = [e["id"] for e in tm.scan_step_entries()]
        self.assertEqual(ids, ["Step 20260614-101432-ly1989abc"])


def datetime_today_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")


# GlobScanTests 用到 datetime 模块（不是从 trigger_match 里 re-export 的 datetime 类）
import datetime  # noqa: E402


if __name__ == "__main__":
    unittest.main(verbosity=2)
