# tests/test_daily_render.py
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks" / "lib"))
import step_log, daily_render  # noqa: E402

_SECTIONS = (
    "## 完成的工作",
    "## 未完成项",
    "## 明日计划",
    "## 本日新增踩坑 / 决策 / 改进信号",
    "## 负面评价观察",
)


def _rec(title, date, delta=1, status="scored"):
    return {"schema_version": 1, "record_id": f"Step 2026-{title}", "type": "Step",
            "title": title, "date": date, "about": "feature/x",
            "triggers": ["a", "b", "c", "d", "e"], "status": status,
            "key_facts": {"tools_invoked_count": 3, "errors_hit": 0, "detours": 0, "token_feel": "light",
                          "skills_used": [], "commit_shas": [], "files_touched": [], "key_decisions": ["x"], "related": []},
            "model_eval": {"quality": 4, "deduction": "小坑", "skills_invoked": [], "subagents": []},
            "user_rating": {"completed_at": None, "smoothness": 4, "comment": None},
            "score_diff": {"delta": delta, "note": ""}}


def test_render_completed_and_negative(tmp_path):
    step_log.append_step(_rec("拆分认证中间件", "2026-04-21", delta=1), root=tmp_path)
    step_log.append_step(_rec("补推限流", "2026-04-21", delta=-2), root=tmp_path)
    (tmp_path / "踩坑日志.md").write_text("## G-004：异步坑\n日期：2026-04-21\n正文\n", encoding="utf-8")
    out = daily_render.render_daily("2026-04-21", root=tmp_path)
    assert "## 完成的工作" in out
    assert "拆分认证中间件" in out
    assert "## 本日新增踩坑 / 决策 / 改进信号" in out
    assert "G-004" in out
    assert "## 负面评价观察" in out
    assert "补推限流" in out  # delta=-2 进负面段


def test_render_empty_day(tmp_path):
    out = daily_render.render_daily("2026-04-21", root=tmp_path)
    assert "（今日无 Step）" in out
    assert "## 明日计划" in out  # 承重墙仍出全 5 段


def test_render_tolerates_null_model_eval_and_user_rating(tmp_path):
    """承重墙：迁移/手改的行可能让 model_eval / user_rating 为 None（present-but-null）。
    render 必须不崩（不能 None.get() AttributeError），仍出全 5 段。
    直接写 jsonl 绕过 validate（validate 会拒 null，但渲染器需对历史/迁移行健壮）。"""
    rec_null_eval = _rec("空模型自评", "2026-04-21")
    rec_null_eval["model_eval"] = None
    rec_null_rating = _rec("空用户评分", "2026-04-21")
    rec_null_rating["user_rating"] = None
    path = step_log.jsonl_path(root=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(rec_null_eval, ensure_ascii=False) + "\n")
        f.write(json.dumps(rec_null_rating, ensure_ascii=False) + "\n")

    out = daily_render.render_daily("2026-04-21", root=tmp_path)
    assert isinstance(out, str)
    for section in _SECTIONS:
        assert section in out, f"缺段：{section}"
    assert "空模型自评" in out
    assert "空用户评分" in out


def test_render_jsonl_today_step_with_dual_scores_and_negative_section(tmp_path):
    """新增（kdev）：jsonl 有今日 Step → 渲染出标题 + 双评分摘要（模型 N / 用户 M）+ 负面评价段。
    覆盖『从 执行日志.jsonl 确定性渲染』的核心承重路径，区别于 ieidev 已有用例：
    显式断言双评分摘要文本 + 负面段差值标注。"""
    step_log.append_step(_rec("打通 daily_render 承重墙", "2026-06-25", delta=1), root=tmp_path)
    step_log.append_step(_rec("回归用户实测差评的限流改造", "2026-06-25", delta=-1), root=tmp_path)
    out = daily_render.render_daily("2026-06-25", root=tmp_path)
    # 标题进完成的工作段
    assert "# 每日汇总：2026-06-25" in out
    assert "打通 daily_render 承重墙" in out
    # 双评分摘要（_rec 给 quality=4 / smoothness=4）
    assert "模型 4" in out
    assert "用户 4" in out
    # 负面评价段：delta=-1 的条目进段并标差值
    neg_idx = out.index("## 负面评价观察")
    neg_block = out[neg_idx:]
    assert "回归用户实测差评的限流改造" in neg_block
    assert "差值 -1" in neg_block
    # delta=1 的条目不进负面段
    assert "打通 daily_render 承重墙" not in neg_block


def test_render_timestamp_form_qgr_into_daily_index(tmp_path):
    """新增（kdev）：时间戳形 Q/G/R（Q-020 ID 时间戳化）必须进当日索引，
    不能只认 legacy 的 X-\\d+ 形。base 既写 legacy 也写时间戳形，断言两类都被收。"""
    base = tmp_path  # flat 布局：shared_dir(root)==root
    (base / "决策日志.md").write_text(
        "## Q 20260625-101500-ly：时间戳形决策进索引\n日期：2026-06-25\n正文\n"
        "## Q-099：legacy 形决策也进索引\n日期：2026-06-25\n正文\n",
        encoding="utf-8")
    (base / "踩坑日志.md").write_text(
        "## G 20260625-102000-ly：时间戳形踩坑进索引\n日期：2026-06-25\n正文\n",
        encoding="utf-8")
    (base / "改进建议.md").write_text(
        "## R 20260625-103000：时间戳形改进进索引\n日期：2026-06-25\n正文\n",
        encoding="utf-8")
    out = daily_render.render_daily("2026-06-25", root=base)
    idx = out.index("## 本日新增踩坑 / 决策 / 改进信号")
    block = out[idx:out.index("## 负面评价观察")]
    assert "时间戳形决策进索引" in block
    assert "legacy 形决策也进索引" in block
    assert "时间戳形踩坑进索引" in block
    assert "时间戳形改进进索引" in block
