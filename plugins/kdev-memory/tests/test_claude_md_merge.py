"""claude_md_merge.py 单测：marker 切块 + insert-or-replace 三场景 + 幂等。"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "hooks" / "lib" / "claude_md_merge.py"
_spec = importlib.util.spec_from_file_location("claude_md_merge", _PATH)
assert _spec and _spec.loader
claude_md_merge = importlib.util.module_from_spec(_spec)
sys.modules["claude_md_merge"] = claude_md_merge
_spec.loader.exec_module(claude_md_merge)

merge = claude_md_merge.merge_managed_section
BEGIN = claude_md_merge.MARKER_BEGIN
END = claude_md_merge.MARKER_END

BODY_V1 = "## 智能体自动记录规则\n\n旧正文 v1\n"
BODY_V2 = "## 智能体自动记录规则\n\n新正文 v2\n"


class TestScenario1ReplaceInsideMarkers(unittest.TestCase):
    def test_replaces_inner_body_keeps_outside(self):
        src = f"# 标题\n\n前文段落\n\n{BEGIN}\n{BODY_V1}\n{END}\n\n后文段落\n"
        out = merge(src, BODY_V2)
        self.assertIn("新正文 v2", out)
        self.assertNotIn("旧正文 v1", out)
        self.assertIn("前文段落", out)
        self.assertIn("后文段落", out)
        self.assertEqual(out.count(BEGIN), 1)
        self.assertEqual(out.count(END), 1)

    def test_idempotent_on_marked_doc(self):
        src = f"# 标题\n\n{BEGIN}\n{BODY_V1}\n{END}\n"
        once = merge(src, BODY_V2)
        twice = merge(once, BODY_V2)
        self.assertEqual(once, twice)


class TestScenario2RetrofitBareSection(unittest.TestCase):
    def test_wraps_existing_section_without_changing_body(self):
        src = "# 标题\n\n## 智能体自动记录规则\n\n用户自定义正文\n\n## 其他章节\n保留\n"
        out = merge(src, BODY_V2)
        self.assertIn("用户自定义正文", out)
        self.assertNotIn("新正文 v2", out)
        self.assertEqual(out.count(BEGIN), 1)
        self.assertEqual(out.count(END), 1)
        self.assertLess(out.index(END), out.index("## 其他章节"))
        self.assertIn("## 其他章节", out)

    def test_retrofit_then_remerge_no_duplicate_markers(self):
        src = "# 标题\n\n## 智能体自动记录规则\n\n用户自定义正文\n"
        retro = merge(src, BODY_V2)
        again = merge(retro, BODY_V2)
        self.assertEqual(again.count(BEGIN), 1)
        self.assertEqual(again.count(END), 1)


class TestScenario3AppendWhenAbsent(unittest.TestCase):
    def test_appends_marker_block(self):
        src = "# 标题\n\n## 别的章节\n内容\n"
        out = merge(src, BODY_V2)
        self.assertIn(BEGIN, out)
        self.assertIn(END, out)
        self.assertIn("新正文 v2", out)
        self.assertIn("## 别的章节", out)
        self.assertEqual(out.count(BEGIN), 1)
        self.assertGreater(out.index(BEGIN), out.index("## 别的章节"))

    def test_idempotent_after_append(self):
        src = "# 标题\n\n## 别的章节\n内容\n"
        once = merge(src, BODY_V2)
        twice = merge(once, BODY_V2)
        self.assertEqual(once, twice)


class TestHalfMarkerRecovery(unittest.TestCase):
    def test_lone_begin_no_duplicate_one_pair_body_kept(self):
        src = f"# 标题\n\n{BEGIN}\n## 智能体自动记录规则\n\n用户正文\n"
        out = merge(src, BODY_V2)
        self.assertEqual(out.count(BEGIN), 1)
        self.assertEqual(out.count(END), 1)
        self.assertIn("用户正文", out)  # 孤儿 BEGIN 归一化为 retrofit，正文保留

    def test_lone_begin_idempotent_no_marker_growth(self):
        src = f"{BEGIN}\n## 智能体自动记录规则\n\n用户正文\n"
        once = merge(src, BODY_V2)
        twice = merge(once, BODY_V2)
        self.assertEqual(twice.count(BEGIN), 1)
        self.assertEqual(twice.count(END), 1)

    def test_lone_end_normalized(self):
        src = f"# 标题\n\n## 智能体自动记录规则\n\n用户正文\n{END}\n"
        out = merge(src, BODY_V2)
        self.assertEqual(out.count(BEGIN), 1)
        self.assertEqual(out.count(END), 1)
        self.assertIn("用户正文", out)

    def test_reversed_markers_normalized(self):
        src = f"# 标题\n\n{END}\n## 智能体自动记录规则\n\n用户正文\n{BEGIN}\n"
        out = merge(src, BODY_V2)
        self.assertEqual(out.count(BEGIN), 1)
        self.assertEqual(out.count(END), 1)


if __name__ == "__main__":
    unittest.main()
