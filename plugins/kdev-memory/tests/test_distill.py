"""单测 hooks/lib/distill.py + sanitize.py + memory_config.py。

覆盖：
- memory_config.read_record_mode 的 4 个 fallback 路径
- sanitize.sanitize_text 各类 PII 规则
- sanitize.verify_no_leaks 反查
- distill.collect_entries 解析 frontmatter / 切分条目 / 归档目录
- distill.is_misalignment_step 筛选逻辑
- distill.is_skill_feedback_high 筛选逻辑
- distill.subject_slug 文件名安全化
- distill.export_markdown_slices 端到端（含输出文件 / 条目数 / sanitize 验证）

零外部依赖，纯 stdlib + tempfile fixture。

注意：测试硬规——所有 fixture 都用 tempfile 而非真实 .kdev/，不污染项目本身的 .kdev/。
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks" / "lib"))

import distill  # noqa: E402
import memory_config  # noqa: E402
import sanitize  # noqa: E402


# ==================== memory_config ====================

class TestMemoryConfig(unittest.TestCase):

    def test_no_config_file_returns_hybrid(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            self.assertEqual(memory_config.read_record_mode(kdev), "hybrid")

    def test_config_with_record_mode_inline(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text("record_mode: inline\n", encoding="utf-8")
            self.assertEqual(memory_config.read_record_mode(kdev), "inline")

    def test_config_with_record_mode_hybrid(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text("record_mode: hybrid\n", encoding="utf-8")
            self.assertEqual(memory_config.read_record_mode(kdev), "hybrid")

    def test_config_invalid_value_falls_back_to_hybrid(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text("record_mode: subagent\n", encoding="utf-8")
            # "subagent" 不在枚举内 → fallback hybrid
            self.assertEqual(memory_config.read_record_mode(kdev), "hybrid")

    def test_config_quoted_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text('record_mode: "inline"\n', encoding="utf-8")
            self.assertEqual(memory_config.read_record_mode(kdev), "inline")

    def test_config_with_comment_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "config.yaml").write_text(
                "# kdev-memory config\n"
                "\n"
                "record_mode: inline  # comment after value\n",
                encoding="utf-8",
            )
            self.assertEqual(memory_config.read_record_mode(kdev), "inline")


# ==================== sanitize ====================

class TestSanitize(unittest.TestCase):

    def test_email(self):
        r = sanitize.sanitize_text("contact alice@example.com please")
        self.assertIn("<email>", r.text)
        self.assertNotIn("alice@example.com", r.text)
        self.assertEqual(r.counts.get("email"), 1)

    def test_home_path(self):
        r = sanitize.sanitize_text("file at /home/lyadmin/projects/foo.py here")
        self.assertIn("<home>/projects/foo.py", r.text)
        self.assertNotIn("lyadmin", r.text)

    def test_home_path_macos(self):
        r = sanitize.sanitize_text("see /Users/alice/Documents/secret.txt")
        self.assertIn("<home>/Documents/secret.txt", r.text)
        self.assertNotIn("alice", r.text)

    def test_api_key_sk(self):
        r = sanitize.sanitize_text("Use sk-proj-abcdefghijklmnopqrstuvwxyz123 for auth")
        self.assertIn("<redacted>", r.text)
        self.assertNotIn("sk-proj-abcdef", r.text)

    def test_api_key_ghp(self):
        r = sanitize.sanitize_text("token ghp_abc123def456ghi789jkl0 here")
        self.assertIn("<redacted>", r.text)
        self.assertNotIn("ghp_abc", r.text)

    def test_bearer(self):
        r = sanitize.sanitize_text("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        self.assertIn("Bearer <redacted>", r.text)
        self.assertNotIn("eyJhbGci", r.text)

    def test_private_ip(self):
        for ip in ("10.0.0.1", "172.16.5.10", "192.168.1.100"):
            r = sanitize.sanitize_text(f"connect to {ip} please")
            self.assertIn("<private-ip>", r.text, f"failed for {ip}")
            self.assertNotIn(ip, r.text, f"failed for {ip}")

    def test_internal_url(self):
        for url in (
            "http://localhost:3000/api",
            "https://app.internal/health",
            "http://service.local",
            "https://127.0.0.1:8080/admin",
        ):
            r = sanitize.sanitize_text(f"see {url} ok?")
            self.assertIn("<internal-url>", r.text, f"failed for {url}")

    def test_public_url_preserved(self):
        text = "see https://github.com/anthropic/claude for source"
        r = sanitize.sanitize_text(text)
        self.assertIn("github.com/anthropic/claude", r.text)
        self.assertEqual(r.counts.get("internal_url"), None)

    def test_public_ip_preserved(self):
        r = sanitize.sanitize_text("dns 8.8.8.8 works")
        # 8.8.8.8 不是私网，应保留
        self.assertIn("8.8.8.8", r.text)

    def test_verify_no_leaks_clean(self):
        clean = "完全干净的文本，没有 PII"
        self.assertEqual(sanitize.verify_no_leaks(clean), [])

    def test_verify_no_leaks_finds_leak(self):
        leaky = "leak: user@example.com is here"
        leaks = sanitize.verify_no_leaks(leaky)
        self.assertEqual(len(leaks), 1)
        self.assertEqual(leaks[0][0], "email")


# ==================== distill ====================

def _write_fixture(kdev: Path) -> None:
    """建一个完整 fixture，含所有 5 类条目 + misalignment + skill-feedback 多 subject。"""
    kdev.mkdir(parents=True, exist_ok=True)

    # 执行日志：3 条 Step（其中 Step 2 差值 +2 进 misalignment / Step 3 差值 -1 不进）
    (kdev / "执行日志.md").write_text(dedent("""\
        # 执行日志

        ## Step 1: 初始化
        日期：2026-05-10
        status: scored
        about: project

        ### 执行
        建骨架

        ### 评分差异分析
        差值：0

        ## Step 2: 重构（差值 +2 = misalignment）
        日期：2026-05-12
        status: scored
        about: project

        ### 执行
        改了核心

        ### 评分差异分析
        差值：+2

        ## Step 3: 优化（差值 -1，不进 misalignment）
        日期：2026-05-14
        status: scored
        about: project

        ### 评分差异分析
        差值：-1
    """), encoding="utf-8")

    # 决策日志：2 Q
    (kdev / "决策日志.md").write_text(dedent("""\
        # 决策日志

        ## Q-001: 用 Postgres 还是 SQLite？
        日期：2026-05-10
        选项：A / B
        用户选择：A

        ## Q-002: API 设计
        日期：2026-05-13
        选项：REST / GraphQL
        用户选择：REST
    """), encoding="utf-8")

    # 踩坑日志：2 G
    (kdev / "踩坑日志.md").write_text(dedent("""\
        # 踩坑日志

        ## G-001: pnpm 坑
        日期：2026-05-11

        ## G-002: aiohttp 坑
        日期：2026-05-13
    """), encoding="utf-8")

    # skill-feedback：4 F（3 high + 1 low；3 个 subject）
    (kdev / "skill-feedback.md").write_text(dedent("""\
        # Skill Feedback (F-NNN)

        ## F-001: kdev-memory 召回吵
        日期：2026-05-12
        subject: plugin:kdev-memory
        subject_inferred_by: L1-显式提及
        subject_confidence: high
        type: 痛点
        verbatim: "召回太吵了"
        score: null

        ## F-002: kdev-memory RFE
        日期：2026-05-13
        subject: plugin:kdev-memory
        subject_inferred_by: L1-显式提及
        subject_confidence: high
        type: RFE
        verbatim: "要是能 demote 就好了"
        score: null

        ## F-003: brainstorming 好用
        日期：2026-05-13
        subject: skill:brainstorming
        subject_inferred_by: L1-显式提及
        subject_confidence: high
        type: 表扬
        verbatim: "引导得很到位"
        score: null

        ## F-004: 不确定的反馈（low confidence，不进 by-subject）
        日期：2026-05-14
        subject: unknown
        subject_inferred_by: L3-用户选择
        subject_confidence: low
        type: 痛点
        verbatim: "这玩意没用"
        score: null
    """), encoding="utf-8")

    # 改进建议：1 R
    (kdev / "改进建议.md").write_text(dedent("""\
        # 改进建议

        ## R-001: 字段对齐
        日期：2026-05-11
        项目：test-fixture
    """), encoding="utf-8")


class TestEntryParsing(unittest.TestCase):

    def test_collect_entries_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_fixture(kdev)
            entries = distill.collect_entries(kdev)
            kinds = {}
            for e in entries:
                kind = e.entry_id.split("-")[0] if "-" in e.entry_id else e.entry_id.split()[0]
                kinds[kind] = kinds.get(kind, 0) + 1
            self.assertEqual(kinds.get("Step"), 3)
            self.assertEqual(kinds.get("Q"), 2)
            self.assertEqual(kinds.get("G"), 2)
            self.assertEqual(kinds.get("F"), 4)
            self.assertEqual(kinds.get("R"), 1)

    def test_entry_fields_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_fixture(kdev)
            entries = distill.collect_entries(kdev)
            f001 = next(e for e in entries if e.entry_id == "F-001")
            self.assertEqual(f001.fields.get("subject"), "plugin:kdev-memory")
            self.assertEqual(f001.fields.get("subject_confidence"), "high")
            self.assertEqual(f001.fields.get("type"), "痛点")
            self.assertEqual(f001.date, "2026-05-12")

    def test_archive_dir_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_fixture(kdev)
            # 加一个归档文件
            archive = kdev / "归档"
            archive.mkdir()
            (archive / "执行日志-2026-04.md").write_text(dedent("""\
                ## Step 0: 旧的 Step
                日期：2026-04-15
                status: scored
            """), encoding="utf-8")
            entries = distill.collect_entries(kdev)
            old_step = [e for e in entries if e.entry_id == "Step 0"]
            self.assertEqual(len(old_step), 1)
            self.assertEqual(old_step[0].source_file, "执行日志-2026-04.md")


class TestFilters(unittest.TestCase):

    def test_misalignment_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_fixture(kdev)
            entries = distill.collect_entries(kdev)
            misalign = [e for e in entries if distill.is_misalignment_step(e)]
            # 只有 Step 2 应该 PASS（差值 +2 ≥ 1.5），Step 1（0）和 Step 3（-1）不应该
            self.assertEqual(len(misalign), 1)
            self.assertEqual(misalign[0].entry_id, "Step 2")

    def test_skill_feedback_high_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_fixture(kdev)
            entries = distill.collect_entries(kdev)
            high = [e for e in entries if distill.is_skill_feedback_high(e)]
            # F-001 / F-002 / F-003 应该进（high）；F-004 不进（low + unknown）
            self.assertEqual(len(high), 3)
            ids = sorted(e.entry_id for e in high)
            self.assertEqual(ids, ["F-001", "F-002", "F-003"])

    def test_subject_slug(self):
        cases = [
            ("plugin:kdev-memory", "plugin-kdev-memory"),
            ("skill:brainstorming", "skill-brainstorming"),
            ("tool:bash", "tool-bash"),
            ("plugin:kdev-memory/skill:kdev-memory", "plugin-kdev-memory--skill-kdev-memory"),
            ("methodology:TDD", "methodology-tdd"),
        ]
        for subject, expected in cases:
            self.assertEqual(distill.subject_slug(subject), expected, f"failed for {subject}")


class TestEndToEnd(unittest.TestCase):

    def test_full_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_fixture(kdev)
            out = Path(tmp) / "dataset"

            stats = distill.export_markdown_slices(kdev, out, do_sanitize=True)

            # 文件齐全
            self.assertTrue((out / "dataset-full.md").is_file())
            self.assertTrue((out / "dataset-misalignment.md").is_file())
            self.assertTrue((out / "dataset-skill-feedback-by-subject").is_dir())

            # 3 个 subject 切片
            subject_files = list((out / "dataset-skill-feedback-by-subject").glob("*.md"))
            self.assertEqual(len(subject_files), 2)  # plugin-kdev-memory + skill-brainstorming
            names = sorted(f.name for f in subject_files)
            self.assertEqual(names, ["plugin-kdev-memory.md", "skill-brainstorming.md"])

            # stats
            self.assertEqual(stats.counts["total"], 3 + 2 + 2 + 4 + 1)
            self.assertEqual(stats.counts["misalignment"], 1)
            self.assertEqual(stats.counts["skill_feedback_high"], 3)
            self.assertEqual(stats.counts["subjects"], 2)
            self.assertEqual(stats.sanitize_status, "verified")

    def test_no_jsonl_output(self):
        """硬规：绝不能产 .jsonl 文件。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_fixture(kdev)
            out = Path(tmp) / "dataset"
            distill.export_markdown_slices(kdev, out, do_sanitize=True)
            jsonl_files = list(out.rglob("*.jsonl"))
            self.assertEqual(jsonl_files, [], "出现了 .jsonl 文件，违反架构终态决策")

    def test_source_files_not_modified(self):
        """硬规：导出是只读，原 .kdev/memory/*.md 不能被改。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            _write_fixture(kdev)
            before = {
                p.name: p.read_text(encoding="utf-8")
                for p in kdev.glob("*.md")
            }
            distill.export_markdown_slices(kdev, kdev / "dataset", do_sanitize=True)
            for name, content in before.items():
                self.assertEqual(
                    (kdev / name).read_text(encoding="utf-8"),
                    content,
                    f"源文件 {name} 被改了",
                )

    def test_misalignment_filter_excludes_subject_skill(self):
        """misalignment 筛选必须排除 about != project 的 Step（避免和 skill 反馈污染）。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "执行日志.md").write_text(dedent("""\
                ## Step 99: 测试某 skill 的 meta Step
                日期：2026-05-15
                status: scored
                about: skill:brainstorming

                ### 评分差异分析
                差值：+2
            """), encoding="utf-8")
            entries = distill.collect_entries(kdev)
            misalign = [e for e in entries if distill.is_misalignment_step(e)]
            self.assertEqual(misalign, [], "about=skill 的 Step 不应进 misalignment")

    def test_sanitize_in_export(self):
        """端到端验证：fixture 含 PII 时导出后被脱敏。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "skill-feedback.md").write_text(dedent("""\
                # Skill Feedback

                ## F-001: 含 PII 的反馈
                日期：2026-05-15
                subject: plugin:kdev-memory
                subject_inferred_by: L1
                subject_confidence: high
                type: 痛点
                verbatim: "联系 alice@example.com 看看 /home/lyadmin/secret.txt"
                score: null
            """), encoding="utf-8")
            out = Path(tmp) / "dataset"
            stats = distill.export_markdown_slices(kdev, out, do_sanitize=True)

            self.assertEqual(stats.sanitize_status, "verified")
            full = (out / "dataset-full.md").read_text(encoding="utf-8")
            self.assertIn("<email>", full)
            self.assertNotIn("alice@example.com", full)
            self.assertIn("<home>/secret.txt", full)
            self.assertNotIn("lyadmin", full)


class TestDistillStatusDefense(unittest.TestCase):
    def _step_entry(self, status_val):
        raw = (
            "## Step z-1: t\n"
            f"status: {status_val}\n"
            "about: project\n\n"
            "### 评分差异分析\n"
            "- 模型 vs 用户差值：+2\n"
        )
        # NOTE: distill.Entry real field names: entry_id, title, date, source_file, raw, fields
        return distill.Entry(
            entry_id="Step z-1",
            title="t",
            date="2026-06-13",
            source_file="执行日志.md",
            raw=raw,
            fields={"status": status_val, "about": "project"},
        )

    def test_voided_r_digit_filtered_from_misalignment(self):
        e = self._step_entry("voided-r-001")
        self.assertFalse(distill.is_misalignment_step(e))

    def test_non_enum_status_warns_and_stays_in_misalignment(self):
        import io, contextlib
        e = self._step_entry("fixed")
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            keep = distill.is_misalignment_step(e)
        self.assertTrue(keep)                 # fixed 不是 voided- → 不过滤
        self.assertIn("非枚举", buf.getvalue())


class TestTimestampFormSkillFeedback(unittest.TestCase):
    """Q-020/v0.17 时间戳形 F 条目（`## F 20260625-...`）也要进 skill-feedback 切片。

    回归：is_skill_feedback_high 用 `entry.entry_id.startswith("F-")`，
    时间戳形 entry_id（`F 20260625-...`）被漏掉，与同文件计数口径
    （`startswith("F-") or startswith("F ")`）不一致。
    """

    def _ts_f_entry(self):
        raw = (
            "## F 20260625-093000-ly: 时间戳形反馈\n"
            "日期：2026-06-25\n"
            "subject: plugin:kdev-memory\n"
            "subject_inferred_by: L1-显式提及\n"
            "subject_confidence: high\n"
            "type: 痛点\n"
            'verbatim: "时间戳形反馈原话"\n'
            "score: null\n"
        )
        return distill.Entry(
            entry_id="F 20260625-093000-ly",
            title="时间戳形反馈",
            date="2026-06-25",
            source_file="skill-feedback.md",
            raw=raw,
            fields={
                "subject": "plugin:kdev-memory",
                "subject_confidence": "high",
                "type": "痛点",
                "verbatim": "时间戳形反馈原话",
            },
        )

    def test_is_skill_feedback_high_accepts_timestamp_form(self):
        self.assertTrue(
            distill.is_skill_feedback_high(self._ts_f_entry()),
            "时间戳形 F 条目未被 is_skill_feedback_high 识别",
        )

    def test_timestamp_form_f_in_by_subject_slice(self):
        """端到端：时间戳形 F 应出现在 skill-feedback by-subject 切片里。"""
        with tempfile.TemporaryDirectory() as tmp:
            kdev = Path(tmp) / "memory"
            kdev.mkdir()
            (kdev / "skill-feedback.md").write_text(dedent("""\
                # Skill Feedback

                ## F 20260625-093000-ly: 时间戳形反馈
                日期：2026-06-25
                subject: plugin:kdev-memory
                subject_inferred_by: L1-显式提及
                subject_confidence: high
                type: 痛点
                verbatim: "时间戳形反馈原话"
                score: null
            """), encoding="utf-8")
            out = Path(tmp) / "dataset"
            stats = distill.export_markdown_slices(kdev, out, do_sanitize=True)
            self.assertEqual(stats.counts["skill_feedback_high"], 1)
            slice_file = out / "dataset-skill-feedback-by-subject" / "plugin-kdev-memory.md"
            self.assertTrue(slice_file.is_file(), "时间戳形 F 未产出 by-subject 切片")
            self.assertIn("时间戳形反馈原话", slice_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
