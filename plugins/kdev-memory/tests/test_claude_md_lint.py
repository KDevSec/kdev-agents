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

### 4 条铁规

🔴 实时落盘到 .kdev/memory/
🔴 文件聚合不翻会话
🔴 记忆分流：工程记录默认写 .kdev，仅跨项目/所有项目通用才写 host 内建 ~/.claude
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
        # 4 个主题都用关键词命中（含分流主题的独有词 ~/.claude）
        section = "<tag> and path/X here. 实时落盘 + 文件聚合 + 优先处理 + 跨项目才写 ~/.claude"
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

    def test_missing_memory_routing_theme_flagged(self):
        """分流主题：CLAUDE.md 有前 3 铁规但无分流规则独有词 → 漂移报出「记忆分流」。"""
        contract = {"hook_injection_tags": [], "hook_file_patterns": [], "cross_session_rules": []}
        section = "实时落盘 文件聚合不翻会话 优先处理 hook 产出——但没写记忆分流规则"
        r = claude_md_lint.check_drift(contract, section)
        missing = [t for t, _ in r["missing_rule_themes"]]
        self.assertIn("记忆分流", missing)

    def test_memory_routing_theme_present_not_flagged(self):
        """含分流规则独有词（~/.claude / 跨项目 等）→ 不报「记忆分流」漂移。
        关键词刻意不含 .kdev/memory（太common、别的铁规也提，会假阳性放过）。"""
        contract = {"hook_injection_tags": [], "hook_file_patterns": [], "cross_session_rules": []}
        section = ("实时落盘 文件聚合不翻会话 优先处理 hook 产出。"
                   "工程记录默认写 .kdev，仅跨项目/所有项目通用才写 host 内建 ~/.claude")
        r = claude_md_lint.check_drift(contract, section)
        missing = [t for t, _ in r["missing_rule_themes"]]
        self.assertNotIn("记忆分流", missing)


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


# marker 块常量（与 claude_md_merge 对齐）
_MK_BEGIN = "<!-- BEGIN kdev-memory:智能体自动记录规则 (managed · 勿手改正文，升级会覆盖) -->"
_MK_END = "<!-- END kdev-memory:智能体自动记录规则 -->"


class TestExtractByMarker(unittest.TestCase):
    def test_extracts_block_between_markers(self):
        text = (
            "# proj\n\n"
            f"{_MK_BEGIN}\n"
            "## 智能体自动记录规则\n\n"
            "🔴 实时落盘到 .kdev/memory/\n"
            "🔴 文件聚合不翻会话\n"
            "🔴 优先处理 hook 产出：\n"
            "- `<kdev-memory-brief>` 注入\n"
            "- `<kdev-memory-recall>` 注入\n"
            "- `.kdev/memory/WARN-未记录-*.md`\n"
            "- `.kdev/memory/checkpoints/压缩前-*.md`\n"
            f"{_MK_END}\n\n"
            "## 用户自定义章节\n这里有 <kdev-memory-brief> 字样但在 marker 块外\n"
        )
        section = claude_md_lint.extract_kdev_section(text)
        self.assertIsNotNone(section)
        self.assertIn("实时落盘", section)
        self.assertNotIn("用户自定义章节", section)

    def test_marker_block_passes_drift_when_complete(self):
        contract = claude_md_lint.parse_contract(MINIMAL_CONTRACT)
        text = (
            f"{_MK_BEGIN}\n"
            "## 智能体自动记录规则\n"
            "🔴 实时落盘到 .kdev/memory/\n"
            "🔴 文件聚合不翻会话\n"
            "🔴 记忆分流：默认写 .kdev，仅跨项目才写 host 内建 ~/.claude\n"
            "🔴 优先处理 hook 产出：\n"
            "- `<kdev-memory-brief>` 注入\n"
            "- `<kdev-memory-recall>` 注入\n"
            "- `.kdev/memory/WARN-未记录-*.md`\n"
            "- `.kdev/memory/checkpoints/压缩前-*.md`\n"
            f"{_MK_END}\n"
        )
        section = claude_md_lint.extract_kdev_section(text)
        result = claude_md_lint.check_drift(contract, section)
        self.assertFalse(result["drift"])

    def test_no_marker_falls_back_to_heading(self):
        section = claude_md_lint.extract_kdev_section(FULL_KDEV_SECTION)
        self.assertIsNotNone(section)
        self.assertIn("优先处理 hook 产出", section)
        self.assertNotIn("其他章节", section)

    def test_begin_without_end_falls_back(self):
        text = f"{_MK_BEGIN}\n## 智能体自动记录规则\n🔴 实时落盘\n"
        section = claude_md_lint.extract_kdev_section(text)
        self.assertIsNotNone(section)
        self.assertIn("实时落盘", section)

    def test_marker_slicing_includes_inner_h2_that_heading_logic_truncates(self):
        # marker 块内含一个非托管 H2 子标题：heading 回退逻辑会在此截断，
        # marker 切块则应包含到 END 之前的全部内容 —— 真正区分两条路径的判别测试
        text = (
            "# proj\n\n"
            f"{_MK_BEGIN}\n"
            "## 智能体自动记录规则\n"
            "🔴 实时落盘\n"
            "## 块内子章节（非托管标题）\n"
            "MARKER_ONLY_SENTINEL 仅 marker 切块能保留\n"
            f"{_MK_END}\n\n"
            "## 外部章节\n外部内容\n"
        )
        section = claude_md_lint.extract_kdev_section(text)
        self.assertIsNotNone(section)
        self.assertIn("MARKER_ONLY_SENTINEL", section)  # heading 回退会在「## 块内子章节」截断 → 缺这句
        self.assertNotIn("外部章节", section)


_TEMPLATE_DOC = (
    Path(__file__).resolve().parents[1]
    / "skills" / "kdev-memory" / "references" / "初始化-claude-md-模板.md"
)


def _extract_fenced_template_body(doc_text: str) -> str:
    """从参考文档抽出实际贴进下游 CLAUDE.md 的 ```markdown 模板块（含 BEGIN/END marker 的那段）。"""
    import re
    for m in re.finditer(r"```markdown\n(.*?)\n```", doc_text, re.DOTALL):
        block = m.group(1)
        if "BEGIN kdev-memory:智能体自动记录规则" in block:
            return block
    return ""


class TestTemplateSelfConsistency(unittest.TestCase):
    """加固：参考文档的模板正文必须满足它自己 frontmatter 声明的 contract。

    捕捉两种漂移：① 编辑模板正文时漏掉某条贯穿铁规主题；② 改 frontmatter 契约
    （加 hook tag / 铁规主题）却没同步模板正文。任一发生 → 下游新装项目的 CLAUDE.md
    从落地起就缺护栏，且无任何测试拦——本测试就是那道拦。
    """

    def test_template_body_satisfies_own_contract(self):
        doc = _TEMPLATE_DOC.read_text(encoding="utf-8")
        contract = claude_md_lint.parse_contract(doc)
        self.assertIsNotNone(contract, "参考文档 frontmatter 缺 claude_md_contract")
        body = _extract_fenced_template_body(doc)
        self.assertTrue(body, "没在参考文档里找到含 BEGIN marker 的 ```markdown 模板块")
        r = claude_md_lint.check_drift(contract, body)
        self.assertFalse(
            r["drift"],
            "模板正文与自身 contract 漂移："
            f"missing_themes={[t for t, _ in r['missing_rule_themes']]} "
            f"missing_tags={r['missing_hook_tags']} missing_files={r['missing_hook_files']}",
        )

    def test_contract_declares_four_cross_session_rules(self):
        """契约必须含 4 条贯穿铁规（记忆分流是第 4 条）——防有人误删回 3 条。"""
        contract = claude_md_lint.parse_contract(_TEMPLATE_DOC.read_text(encoding="utf-8"))
        self.assertEqual(len(contract["cross_session_rules"]), 4)
        self.assertTrue(any("记忆分流" in r for r in contract["cross_session_rules"]))


if __name__ == "__main__":
    unittest.main()
