"""
claude_md_lint.py 的单元测试。

覆盖范围（优先级高→低）：
  1. parse_contract          —— 从 frontmatter 抽取契约字段
  2. extract_kdev_section    —— CLAUDE.md 里抽规则段
  3. check_drift             —— 三类字段的缺失判定
  4. _file_pattern_matches   —— 带/不带 * 的 pattern 匹配
  5. run_lint（主入口）      —— 4 种终态（ok / drift / no-claude-md / no-kdev-section）
  6. format_hint_for_brief   —— 给 SessionStart hook 用的提示文本

跑法：
    cd plugins/kdev-memory
    python3 -m unittest discover tests -v

零外部依赖（stdlib unittest），几十毫秒跑完。
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

# 用 spec 加载 hooks/lib/claude_md_lint.py（本仓库 hook 脚本不在 sys.path）
_LINT_PATH = Path(__file__).resolve().parents[1] / "hooks" / "lib" / "claude_md_lint.py"
_spec = importlib.util.spec_from_file_location("claude_md_lint", _LINT_PATH)
assert _spec and _spec.loader
claude_md_lint = importlib.util.module_from_spec(_spec)
sys.modules["claude_md_lint"] = claude_md_lint
_spec.loader.exec_module(claude_md_lint)


MINIMAL_CONTRACT = """---
claude_md_contract:
  cross_session_rules:
    - "实时落盘：每做完一步"
    - "文件聚合不翻会话"
    - "优先处理 hook 产出"
  hook_injection_tags:
    - "<kdev-memory-brief>"
    - "<kdev-memory-recall>"
  hook_file_patterns:
    - ".kdev/memory/WARN-未记录-*.md"
    - ".kdev/memory/checkpoints/压缩前-*.md"
---

# 模板
"""

FULL_KDEV_SECTION = """# project

## 智能体自动记录规则

### 3 条铁规

🔴 实时落盘到 .kdev/memory/
🔴 文件聚合不翻会话
🔴 优先处理 hook 产出：
- `.kdev/memory/WARN-未记录-*.md`
- `<kdev-memory-brief>` 注入
- `<kdev-memory-recall>` 注入
- `.kdev/memory/checkpoints/压缩前-*.md`

## 其他章节
（skill 不管这个）
"""


class TestParseContract(unittest.TestCase):
    def test_extracts_three_lists(self):
        c = claude_md_lint.parse_contract(MINIMAL_CONTRACT)
        self.assertEqual(c["hook_injection_tags"], ["<kdev-memory-brief>", "<kdev-memory-recall>"])
        self.assertEqual(
            c["hook_file_patterns"],
            [".kdev/memory/WARN-未记录-*.md", ".kdev/memory/checkpoints/压缩前-*.md"],
        )
        self.assertEqual(len(c["cross_session_rules"]), 3)

    def test_missing_frontmatter_returns_none(self):
        self.assertIsNone(claude_md_lint.parse_contract("# no frontmatter"))

    def test_missing_contract_block_returns_none(self):
        text = "---\nname: something\n---\n\n# body"
        self.assertIsNone(claude_md_lint.parse_contract(text))

    def test_empty_list_field(self):
        text = """---
claude_md_contract:
  hook_injection_tags:
  hook_file_patterns:
    - "X"
  cross_session_rules:
---

body
"""
        c = claude_md_lint.parse_contract(text)
        self.assertEqual(c["hook_injection_tags"], [])
        self.assertEqual(c["hook_file_patterns"], ["X"])
        self.assertEqual(c["cross_session_rules"], [])


class TestExtractKdevSection(unittest.TestCase):
    def test_finds_section(self):
        section = claude_md_lint.extract_kdev_section(FULL_KDEV_SECTION)
        self.assertIsNotNone(section)
        self.assertIn("🔴 实时落盘", section)
        self.assertNotIn("其他章节", section)  # 截到下一个 ## 就停

    def test_no_section_returns_none(self):
        text = "# project\n\n## 开发惯例\nsomething\n"
        self.assertIsNone(claude_md_lint.extract_kdev_section(text))

    def test_h1_header_stops_section(self):
        text = "## 智能体自动记录规则\n铁规内容\n# 下一个一级标题\n其他\n"
        section = claude_md_lint.extract_kdev_section(text)
        self.assertIn("铁规内容", section)
        self.assertNotIn("下一个一级标题", section)


class TestFilePatternMatches(unittest.TestCase):
    def test_literal_match(self):
        self.assertTrue(claude_md_lint._file_pattern_matches("foo.md", "see foo.md here"))
        self.assertFalse(claude_md_lint._file_pattern_matches("foo.md", "nothing"))

    def test_glob_full_path_match(self):
        self.assertTrue(
            claude_md_lint._file_pattern_matches(
                ".kdev/memory/WARN-*.md", "read .kdev/memory/WARN-abc.md file"
            )
        )

    def test_glob_basename_fallback(self):
        """路径前缀在 CLAUDE.md 里缺失时，basename 匹配也算命中。"""
        self.assertTrue(
            claude_md_lint._file_pattern_matches(
                ".kdev/memory/WARN-未记录-*.md", "look for WARN-未记录-2026-04-22.md"
            )
        )

    def test_glob_no_match(self):
        self.assertFalse(
            claude_md_lint._file_pattern_matches(
                ".kdev/memory/WARN-未记录-*.md", "unrelated text"
            )
        )


class TestCheckDrift(unittest.TestCase):
    def test_all_present_no_drift(self):
        contract = {
            "hook_injection_tags": ["<tag>"],
            "hook_file_patterns": ["path/X"],
            "cross_session_rules": [],
        }
        # 3 个主题都用关键词命中
        section = "<tag> and path/X here. 实时落盘 + 文件聚合 + 优先处理"
        r = claude_md_lint.check_drift(contract, section)
        self.assertFalse(r["drift"])

    def test_missing_tag_flagged(self):
        contract = {
            "hook_injection_tags": ["<tag>", "<other>"],
            "hook_file_patterns": [],
            "cross_session_rules": [],
        }
        section = "only <tag>. 实时落盘 文件聚合 优先处理"
        r = claude_md_lint.check_drift(contract, section)
        self.assertTrue(r["drift"])
        self.assertEqual(r["missing_hook_tags"], ["<other>"])

    def test_missing_rule_theme_flagged(self):
        contract = {"hook_injection_tags": [], "hook_file_patterns": [], "cross_session_rules": []}
        # 3 个主题只命中一个
        section = "只有 实时落盘。"
        r = claude_md_lint.check_drift(contract, section)
        self.assertTrue(r["drift"])
        # 返回的是 (theme, keywords) 二元组
        missing_themes = [t for t, _ in r["missing_rule_themes"]]
        self.assertIn("文件聚合不翻会话", missing_themes)
        self.assertIn("优先处理 hook 产出", missing_themes)


class TestRunLint(unittest.TestCase):
    def _write(self, tmpdir: Path, name: str, content: str) -> Path:
        path = tmpdir / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_ok_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            contract_path = self._write(tmp, "contract.md", MINIMAL_CONTRACT)
            claude_path = self._write(tmp, "CLAUDE.md", FULL_KDEV_SECTION)
            r = claude_md_lint.run_lint(contract_path, claude_path)
            self.assertEqual(r["status"], "ok")

    def test_drift_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            contract_path = self._write(tmp, "contract.md", MINIMAL_CONTRACT)
            claude_path = self._write(
                tmp, "CLAUDE.md", "## 智能体自动记录规则\n实时落盘 文件聚合 优先处理\n"
            )
            r = claude_md_lint.run_lint(contract_path, claude_path)
            self.assertEqual(r["status"], "drift")
            # 应该报出所有 tag 和 file 缺失
            self.assertIn("<kdev-memory-brief>", r["missing_hook_tags"])

    def test_no_claude_md_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            contract_path = self._write(tmp, "contract.md", MINIMAL_CONTRACT)
            r = claude_md_lint.run_lint(contract_path, tmp / "does-not-exist.md")
            self.assertEqual(r["status"], "no-claude-md")

    def test_no_kdev_section_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            contract_path = self._write(tmp, "contract.md", MINIMAL_CONTRACT)
            claude_path = self._write(tmp, "CLAUDE.md", "# proj\n## 开发惯例\n无记忆制度\n")
            r = claude_md_lint.run_lint(contract_path, claude_path)
            self.assertEqual(r["status"], "no-kdev-section")

    def test_contract_parse_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            contract_path = self._write(tmp, "contract.md", "# no frontmatter here")
            claude_path = self._write(tmp, "CLAUDE.md", FULL_KDEV_SECTION)
            r = claude_md_lint.run_lint(contract_path, claude_path)
            self.assertEqual(r["status"], "contract-parse-error")


class TestFormatHint(unittest.TestCase):
    def test_no_hint_when_ok(self):
        self.assertIsNone(claude_md_lint.format_hint_for_brief({"status": "ok"}))

    def test_hint_when_drift(self):
        result = {
            "status": "drift",
            "missing_hook_tags": ["<new-tag>"],
            "missing_hook_files": ["path/X-*.md"],
            "missing_rule_themes": [("实时落盘", ["kw1", "kw2"])],
        }
        hint = claude_md_lint.format_hint_for_brief(result)
        self.assertIn("CLAUDE.md 接口漂移", hint)
        self.assertIn("<new-tag>", hint)
        self.assertIn("path/X-*.md", hint)
        self.assertIn("实时落盘", hint)
        # 召唤指引必须带上，让用户知道怎么修
        self.assertIn("召唤", hint)
        self.assertIn("修 CLAUDE.md 漂移", hint)


if __name__ == "__main__":
    unittest.main()
