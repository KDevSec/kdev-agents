"""tests/test_sync.py — sync.py 单元测试（TDD：先写测试再实现）"""
from __future__ import annotations

import csv
import io
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── 加 scripts/ 到路径（pytest.ini 已配好 PYTHONPATH，显式保险）
_SCRIPTS = Path(__file__).parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


# ---------------------------------------------------------------------------
# 辅助：造最小 CSV 行
# ---------------------------------------------------------------------------

def _make_csv_text(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 测试 existing_tc_ids：从 paginate 里提取 [TC-ID]
# ---------------------------------------------------------------------------

class TestExistingTcIds:
    def test_extracts_tc_id_from_bug_title(self):
        """existing_tc_ids 应从 bug title 提取 [TC-xxx] 形式的 ID。"""
        from sync import existing_tc_ids

        client = MagicMock()
        client.paginate.return_value = [
            {"title": "[TC-LOGIN-001] 用户名为空时登录失败", "id": 10},
            {"title": "[TC-REG-002] 注册手机号重复报错", "id": 11},
        ]
        result = existing_tc_ids(client, product=1)
        assert result == {"TC-LOGIN-001", "TC-REG-002"}

    def test_ignores_bugs_without_tc_id(self):
        """没有 [TC-xxx] 标记的 bug 不应出现在返回集合里。"""
        from sync import existing_tc_ids

        client = MagicMock()
        client.paginate.return_value = [
            {"title": "手动录入的 bug 无 TC-ID", "id": 99},
        ]
        result = existing_tc_ids(client, product=1)
        assert result == set()

    def test_calls_correct_api_path(self):
        """应调用 /api.php/v1/products/{product}/bugs 端点。"""
        from sync import existing_tc_ids

        client = MagicMock()
        client.paginate.return_value = []
        existing_tc_ids(client, product=42)
        client.paginate.assert_called_once_with("/api.php/v1/products/42/bugs", "bugs")


# ---------------------------------------------------------------------------
# 测试 cmd_submit_bugs：dry-run 路径
# ---------------------------------------------------------------------------

class TestCmdSubmitBugsDryRun:
    def _make_args(self, csv_path: Path, execute: bool = False):
        args = MagicMock()
        args.csv = csv_path
        args.execute = execute
        args.product = 1
        args.build = "trunk"
        args.cred = Path("/fake/cred")
        return args

    def test_dry_run_prints_todo_and_does_not_post(self, tmp_path, capsys):
        """dry-run 模式应打印待提列表，不调用 post_json。"""
        from sync import cmd_submit_bugs

        csv_file = tmp_path / "defects.csv"
        csv_file.write_text(
            _make_csv_text([
                {"用例ID": "TC-A-001", "用例名称": "测试A", "用例函数": "test_a",
                 "原因分类": "真实-UI", "失败摘要": "按钮未响应", "时间": "2026-06-20",
                 "截图": "", "日志文件": ""},
            ]),
            encoding="utf-8",
        )
        args = self._make_args(csv_file, execute=False)

        mock_client = MagicMock()
        mock_client.paginate.return_value = []  # 无已存在 bug

        with patch("sync._client", return_value=mock_client):
            rc = cmd_submit_bugs(args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "[DRY-RUN]" in out
        assert "1" in out  # 1 条待提
        mock_client.post_json.assert_not_called()

    def test_dry_run_previews_real_bug_title(self, tmp_path, capsys):
        """dry-run 预览应是真实将创建的 bug title（含原因分类+失败摘要），而非仅用例名（F-001）。"""
        from sync import cmd_submit_bugs

        csv_file = tmp_path / "defects.csv"
        csv_file.write_text(
            _make_csv_text([
                {"用例ID": "TC-A-001", "用例名称": "测试A", "用例函数": "test_a",
                 "原因分类": "真实-后端缺陷", "失败摘要": "后端未校验非法字符",
                 "时间": "2026-06-26", "截图": "", "日志文件": ""},
            ]),
            encoding="utf-8",
        )
        args = self._make_args(csv_file, execute=False)

        mock_client = MagicMock()
        mock_client.paginate.return_value = []

        with patch("sync._client", return_value=mock_client):
            rc = cmd_submit_bugs(args)

        assert rc == 0
        out = capsys.readouterr().out
        # 所见即所提：原因分类 + 失败摘要 + [TC-ID] 锚都应出现在 dry-run 预览里
        assert "[TC-A-001]" in out
        assert "真实-后端缺陷" in out
        assert "后端未校验非法字符" in out
        mock_client.post_json.assert_not_called()

    def test_dry_run_skips_already_submitted_tc(self, tmp_path, capsys):
        """已在禅道存在 [TC-ID] 的 bug 应被去重跳过，不出现在待提列表。"""
        from sync import cmd_submit_bugs

        csv_file = tmp_path / "defects.csv"
        csv_file.write_text(
            _make_csv_text([
                {"用例ID": "TC-A-001", "用例名称": "已提bug", "用例函数": "test_a",
                 "原因分类": "真实-UI", "失败摘要": "x", "时间": "2026-06-20",
                 "截图": "", "日志文件": ""},
                {"用例ID": "TC-A-002", "用例名称": "新bug", "用例函数": "test_b",
                 "原因分类": "真实-接口", "失败摘要": "y", "时间": "2026-06-20",
                 "截图": "", "日志文件": ""},
            ]),
            encoding="utf-8",
        )
        args = self._make_args(csv_file, execute=False)

        mock_client = MagicMock()
        # TC-A-001 已存在
        mock_client.paginate.return_value = [
            {"title": "[TC-A-001] 已提bug"}
        ]

        with patch("sync._client", return_value=mock_client):
            rc = cmd_submit_bugs(args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "TC-A-002" in out      # 新 bug 出现在列表
        assert "TC-A-001" not in out  # 已提 bug 不出现在待提列表

    def test_filters_non_real_defects(self, tmp_path, capsys):
        """非"真实-"分类的行应被过滤，不出现在待提列表。"""
        from sync import cmd_submit_bugs

        csv_file = tmp_path / "defects.csv"
        csv_file.write_text(
            _make_csv_text([
                {"用例ID": "TC-B-001", "用例名称": "框架错误", "用例函数": "test_b1",
                 "原因分类": "框架-异常", "失败摘要": "import error", "时间": "2026-06-20",
                 "截图": "", "日志文件": ""},
                {"用例ID": "TC-B-002", "用例名称": "脚本错误", "用例函数": "test_b2",
                 "原因分类": "脚本-断言", "失败摘要": "wrong assert", "时间": "2026-06-20",
                 "截图": "", "日志文件": ""},
            ]),
            encoding="utf-8",
        )
        args = self._make_args(csv_file, execute=False)

        mock_client = MagicMock()
        mock_client.paginate.return_value = []

        with patch("sync._client", return_value=mock_client):
            rc = cmd_submit_bugs(args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "[DRY-RUN] 共 0 条" in out

    def test_schema_b_columns_normalized(self, tmp_path, capsys):
        """Schema B（用例/原因分析/失败截图）已分诊的真缺陷应被列名归一后正确识别+待提（F-002）。"""
        from sync import cmd_submit_bugs

        csv_file = tmp_path / "defects_b.csv"
        csv_file.write_text(
            _make_csv_text([
                {"用例": "TC-B-001", "用例名称": "项目名超长", "复现操作步骤": "...",
                 "错误信息": "应拒绝", "原因分析": "真实-后端缺陷", "失败截图": "/x/a.png"},
            ]),
            encoding="utf-8",
        )
        args = self._make_args(csv_file, execute=False)
        mock_client = MagicMock()
        mock_client.paginate.return_value = []

        with patch("sync._client", return_value=mock_client):
            rc = cmd_submit_bugs(args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "真实缺陷 1" in out
        assert "[TC-B-001]" in out      # 用例→用例ID 归一后 [TC-ID] 锚正常
        assert "真实-后端缺陷" in out     # 原因分析→原因分类 归一进真实 title
        mock_client.post_json.assert_not_called()

    def test_schema_b_apitest_real_defect_prefix(self, tmp_path, capsys):
        """apitest Schema B 自动分诊前缀『real-defect』也应识别为真缺陷+待提（F-002）。"""
        from sync import cmd_submit_bugs

        csv_file = tmp_path / "defects_api.csv"
        csv_file.write_text(
            _make_csv_text([
                {"用例": "TC-API-001", "用例名称": "负向用例期望被拒却成功", "复现操作步骤": "...",
                 "错误信息": "后端漏校验", "原因分析": "real-defect：后端漏校验/未拦截", "失败截图": ""},
                {"用例": "TC-API-002", "用例名称": "传输层抖动", "复现操作步骤": "...",
                 "错误信息": "SSL RST", "原因分析": "framework：传输层连接异常", "失败截图": ""},
            ]),
            encoding="utf-8",
        )
        args = self._make_args(csv_file, execute=False)
        mock_client = MagicMock()
        mock_client.paginate.return_value = []

        with patch("sync._client", return_value=mock_client):
            rc = cmd_submit_bugs(args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "真实缺陷 1" in out       # 仅 real-defect 行算真缺陷；framework 行排除
        assert "[TC-API-001]" in out
        assert "[TC-API-002]" not in out  # framework 不提
        mock_client.post_json.assert_not_called()

    def test_fail_loud_on_undiagnosed_schema_b(self, tmp_path):
        """Schema B 未分诊（原因分析=（待人工分析）占位）→ 0 真缺陷应 Fail Loud raise，不静默提 0（F-002）。"""
        from sync import cmd_submit_bugs

        csv_file = tmp_path / "defects_undiag.csv"
        csv_file.write_text(
            _make_csv_text([
                {"用例": "TC-B-001", "用例名称": "待分诊", "复现操作步骤": "...",
                 "错误信息": "x", "原因分析": "（待人工分析）", "失败截图": ""},
            ]),
            encoding="utf-8",
        )
        args = self._make_args(csv_file, execute=False)
        mock_client = MagicMock()
        mock_client.paginate.return_value = []

        with patch("sync._client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="待人工分析|Fail Loud"):
                cmd_submit_bugs(args)

    def test_fail_loud_on_missing_cause_column(self, tmp_path):
        """CSV 缺『原因分类/原因分析』列（列名漂移）且 0 真缺陷 → Fail Loud raise（F-002）。"""
        from sync import cmd_submit_bugs

        csv_file = tmp_path / "defects_nocol.csv"
        csv_file.write_text(
            _make_csv_text([
                {"用例": "TC-C-001", "用例名称": "无分类列", "错误信息": "x"},
            ]),
            encoding="utf-8",
        )
        args = self._make_args(csv_file, execute=False)
        mock_client = MagicMock()
        mock_client.paginate.return_value = []

        with patch("sync._client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="列名漂移|原因分类"):
                cmd_submit_bugs(args)


# ---------------------------------------------------------------------------
# 测试 build_parser：argparse 结构
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_submit_bugs_subcommand_requires_csv(self):
        """submit-bugs 子命令必须有 --csv 参数。"""
        from sync import build_parser

        ap = build_parser()
        with pytest.raises(SystemExit):
            ap.parse_args(["--cred", "/fake", "--product", "1", "submit-bugs"])

    def test_execute_defaults_to_false(self):
        """--execute 默认应为 False（dry-run 优先）。"""
        from sync import build_parser

        ap = build_parser()
        args = ap.parse_args([
            "--cred", "/fake", "--product", "1",
            "submit-bugs", "--csv", "/fake.csv",
        ])
        assert args.execute is False

    def test_build_defaults_to_trunk(self):
        """--build 默认应为 trunk。"""
        from sync import build_parser

        ap = build_parser()
        args = ap.parse_args([
            "--cred", "/fake", "--product", "1",
            "submit-bugs", "--csv", "/fake.csv",
        ])
        assert args.build == "trunk"


# ---------------------------------------------------------------------------
# M3: cmd_submit_bugs — 真实缺陷行缺 用例ID 时 Fail Loud
# ---------------------------------------------------------------------------

class TestCmdSubmitBugsMissingTcId:
    def _make_args(self, csv_path: Path, execute: bool = False):
        args = MagicMock()
        args.csv = csv_path
        args.execute = execute
        args.product = 1
        args.build = "trunk"
        args.cred = Path("/fake/cred")
        return args

    def test_dry_run_raises_when_real_defect_has_no_tc_id(self, tmp_path):
        """dry-run 模式下：真实缺陷行用例ID为空时应 raise RuntimeError，不静默用空锚点提交。"""
        from sync import cmd_submit_bugs

        csv_file = tmp_path / "defects_missing_id.csv"
        csv_file.write_text(
            _make_csv_text([
                {"用例ID": "TC-A-001", "用例名称": "正常行", "用例函数": "test_a",
                 "原因分类": "真实-UI", "失败摘要": "x", "时间": "2026-06-20",
                 "截图": "", "日志文件": ""},
                {"用例ID": "",          "用例名称": "缺ID行", "用例函数": "test_b",
                 "原因分类": "真实-接口", "失败摘要": "y", "时间": "2026-06-20",
                 "截图": "", "日志文件": ""},
            ]),
            encoding="utf-8",
        )
        args = self._make_args(csv_file, execute=False)
        mock_client = MagicMock()

        with patch("sync._client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="用例ID"):
                cmd_submit_bugs(args)

    def test_execute_raises_when_real_defect_has_no_tc_id(self, tmp_path):
        """execute 模式下：真实缺陷行用例ID为空时也应 raise RuntimeError（校验在 _client 调用前）。"""
        from sync import cmd_submit_bugs

        csv_file = tmp_path / "defects_missing_id_exec.csv"
        csv_file.write_text(
            _make_csv_text([
                {"用例ID": "", "用例名称": "缺ID真实行", "用例函数": "test_c",
                 "原因分类": "真实-UI", "失败摘要": "z", "时间": "2026-06-20",
                 "截图": "", "日志文件": ""},
            ]),
            encoding="utf-8",
        )
        args = self._make_args(csv_file, execute=True)
        mock_client = MagicMock()

        with patch("sync._client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="用例ID"):
                cmd_submit_bugs(args)


# ---------------------------------------------------------------------------
# story_ar_map：需求库 story 标题里的 AR 主键 → story id
# ---------------------------------------------------------------------------

class TestStoryArMap:
    def test_extracts_ar_from_story_title(self):
        """story 标题『AR编号：描述』应抽出 AR 主键映射到 id；无 AR 的需求跳过。"""
        from sync import story_ar_map

        client = MagicMock()
        client.paginate.return_value = [
            {"id": 1, "title": "AR-PRL-FUN-01.001.00：查看产品线列表"},
            {"id": 6, "title": "AR-AUTH-FUN-04.001.00：为用户配置产品线数据范围"},
            {"id": 9, "title": "无 AR 编号的手工需求"},
        ]
        m = story_ar_map(client, product=1)
        assert m == {"AR-PRL-FUN-01.001.00": 1, "AR-AUTH-FUN-04.001.00": 6}

    def test_calls_stories_endpoint(self):
        """应调用 /api.php/v1/products/{product}/stories 端点。"""
        from sync import story_ar_map

        client = MagicMock()
        client.paginate.return_value = []
        story_ar_map(client, product=7)
        client.paginate.assert_called_once_with("/api.php/v1/products/7/stories", "stories")


# ---------------------------------------------------------------------------
# story_module_map：AR 主键 → story.module（用例自动归到与其需求同一模块，绕开 /browse）
# ---------------------------------------------------------------------------

class TestStoryModuleMap:
    def test_extracts_module_from_story(self):
        """story 带 module 时映射 AR→module；module=0/缺失的 story 跳过（不参与自动归类）。"""
        from sync import story_module_map

        client = MagicMock()
        client.paginate.return_value = [
            {"id": 7, "title": "[AR-PRJ-FUN-02.001.00] 查看项目列表", "module": 12},
            {"id": 12, "title": "[AR-VER-FUN-03.001.00] 查看版本列表", "module": 13},
            {"id": 1, "title": "AR-PRL-FUN-01.001.00：查看产品线列表", "module": 0},
            {"id": 9, "title": "无 AR 编号的需求", "module": 5},
        ]
        m = story_module_map(client, product=1)
        assert m == {"AR-PRJ-FUN-02.001.00": 12, "AR-VER-FUN-03.001.00": 13}

    def test_calls_stories_endpoint(self):
        """应调用 /api.php/v1/products/{product}/stories 端点。"""
        from sync import story_module_map

        client = MagicMock()
        client.paginate.return_value = []
        story_module_map(client, product=7)
        client.paginate.assert_called_once_with("/api.php/v1/products/7/stories", "stories")


# ---------------------------------------------------------------------------
# parse_module_map：'名=id,名=id' → {名: id}；本实例无模块 GET API 故手工给
# ---------------------------------------------------------------------------

class TestParseModuleMap:
    def test_parses_name_id_pairs(self):
        from sync import parse_module_map
        assert parse_module_map("产品管理中心=2,系统管理=3") == {"产品管理中心": 2, "系统管理": 3}

    def test_empty_returns_empty_dict(self):
        from sync import parse_module_map
        assert parse_module_map("") == {}

    def test_malformed_pair_fail_loud(self):
        """格式不含 = 时应 raise（loud），不静默吞掉一个模块映射。"""
        from sync import parse_module_map
        with pytest.raises(RuntimeError, match="module-map"):
            parse_module_map("产品管理中心:2")


# ---------------------------------------------------------------------------
# cmd_import_cases：dry-run 解析 story+module + 未命中 Fail Loud
# ---------------------------------------------------------------------------

class TestCmdImportCasesDryRun:
    def _make_args(self, md_path: Path, module_map: str = "", execute: bool = False):
        args = MagicMock()
        args.md = md_path
        args.module_map = module_map
        args.module = 0
        args.execute = execute
        args.product = 1
        args.cred = Path("/fake/cred")
        return args

    def _md_one_case(self) -> str:
        return (
            "【测试用例信息】\n"
            "- 用例编号：TC-AR0100100-G1-001\n"
            "- 用例名称：查看产品线列表，列表字段展示\n"
            "- 需求编号：AR-PRL-FUN-01.001.00\n"
            "- 所属模块：产品管理中心\n"
            "- 用例类型：基本流\n"
            "- 优先级：1\n"
            "- 测试步骤：\n"
            "  1. 登录\n"
            "  2. 进入列表\n"
            "- 预期结果：\n"
            "  1. 列表展示\n"
            "```\n"
        )

    def _client_with_stories(self, stories: list[dict]) -> MagicMock:
        client = MagicMock()

        def _paginate(path, key, *a, **k):
            if key == "testcases":
                return iter([])           # 无已存在同名用例
            if key == "stories":
                return iter(stories)
            return iter([])

        client.paginate.side_effect = _paginate
        return client

    def test_dry_run_resolves_story_and_module_no_post(self, tmp_path, capsys):
        """AR 命中需求库 + 模块名命中 map → 打印 story=1 module=2，且不 post。"""
        from sync import cmd_import_cases

        md = tmp_path / "cases.md"; md.write_text(self._md_one_case(), encoding="utf-8")
        args = self._make_args(md, module_map="产品管理中心=2,系统管理=3")
        client = self._client_with_stories(
            [{"id": 1, "title": "AR-PRL-FUN-01.001.00：查看产品线列表"}])

        with patch("sync._client", return_value=client):
            rc = cmd_import_cases(args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "story=1 module=2" in out
        assert "[DRY-RUN]" in out
        client.post_json.assert_not_called()

    def test_dry_run_warns_when_ar_has_no_story(self, tmp_path, capsys):
        """用例 AR 在需求库找不到对应 story → 必须 [WARN] loud surface，不静默留空。"""
        from sync import cmd_import_cases

        md = tmp_path / "cases.md"; md.write_text(self._md_one_case(), encoding="utf-8")
        args = self._make_args(md, module_map="产品管理中心=2")
        client = self._client_with_stories(
            [{"id": 5, "title": "AR-OTHER-99.999.99：别的需求"}])

        with patch("sync._client", return_value=client):
            cmd_import_cases(args)

        out = capsys.readouterr().out
        assert "[WARN]" in out and "AR-PRL-FUN-01.001.00" in out

    def test_dry_run_warns_when_module_name_unmapped(self, tmp_path, capsys):
        """给了 --module-map 但漏了某模块名 → [WARN] 该名将回退，不静默落根。"""
        from sync import cmd_import_cases

        md = tmp_path / "cases.md"; md.write_text(self._md_one_case(), encoding="utf-8")
        args = self._make_args(md, module_map="系统管理=3")   # 漏了『产品管理中心』
        client = self._client_with_stories(
            [{"id": 1, "title": "AR-PRL-FUN-01.001.00：查看产品线列表"}])

        with patch("sync._client", return_value=client):
            cmd_import_cases(args)

        out = capsys.readouterr().out
        assert "[WARN]" in out and "产品管理中心" in out

    def test_module_map_flag_parsed_by_argparse(self):
        """import-cases 应接受 --module-map 参数。"""
        from sync import build_parser

        ap = build_parser()
        args = ap.parse_args([
            "--cred", "/fake", "--product", "1",
            "import-cases", "--md", "/fake.md", "--module-map", "产品管理中心=2",
        ])
        assert args.module_map == "产品管理中心=2"

    def test_dry_run_dedups_html_escaped_title(self, tmp_path, capsys):
        """WHY 回归：禅道把标题 <script> 存成 &lt;script&gt;；按 md 原文去重会永远匹配不上
        → 每跑一次重复建一次。修复后须反转义识别为已存在 → 跳过，不重复建。"""
        from sync import cmd_import_cases

        md_text = (
            "【测试用例信息】\n"
            "- 用例编号：TC-AR0100200-G2-006\n"
            "- 用例名称：新增产品线，产品线名称含特殊符号「\\<script\\>」\n"
            "- 需求编号：AR-PRL-FUN-01.002.00\n"
            "- 所属模块：产品管理中心\n"
            "- 用例类型：异常流\n"
            "- 优先级：2\n"
            "- 测试步骤：\n"
            "  1. 输入 <script>\n"
            "- 预期结果：\n"
            "  1. 被拒绝\n"
            "```\n"
        )
        md = tmp_path / "cases.md"; md.write_text(md_text, encoding="utf-8")
        args = self._make_args(md, module_map="产品管理中心=2")

        client = MagicMock()

        def _paginate(path, key, *a, **k):
            if key == "testcases":
                # 禅道里存的是 HTML 转义后的标题
                return iter([{"title": "新增产品线，产品线名称含特殊符号「\\&lt;script\\&gt;」"}])
            if key == "stories":
                return iter([{"id": 2, "title": "AR-PRL-FUN-01.002.00：新增产品线"}])
            return iter([])

        client.paginate.side_effect = _paginate

        with patch("sync._client", return_value=client):
            cmd_import_cases(args)

        out = capsys.readouterr().out
        assert "跳过(同名已存在) 1" in out
        assert "[DRY-RUN] 共 0 条" in out


# ---------------------------------------------------------------------------
# existing_case_titles：反转义禅道存储标题（修复 HTML 特殊字符去重失效）
# ---------------------------------------------------------------------------

class TestExistingCaseTitlesUnescape:
    def test_unescapes_stored_titles(self):
        """禅道存的 &lt;/&gt;/&amp; 等实体应被反转义回原文，供按 md 原文去重比对。"""
        from sync import existing_case_titles

        client = MagicMock()
        client.paginate.return_value = [
            {"title": "名称含「\\&lt;script\\&gt;」"},
            {"title": "A &amp; B"},
            {"title": "普通标题"},
        ]
        s = existing_case_titles(client, product=1)
        assert "名称含「\\<script\\>」" in s
        assert "A & B" in s
        assert "普通标题" in s
