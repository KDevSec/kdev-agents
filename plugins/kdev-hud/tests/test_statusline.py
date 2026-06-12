import re
from kdev_hud import datasource as ds
from kdev_hud import statusline as sl

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(s):
    return ANSI.sub("", s)


def test_statusline_active_feature(tmp_workspace, seed):
    seed(tmp_workspace, display_name="用户管理模块",
         stories=[{"id": "s1", "title": "a", "status": "done"},
                  {"id": "s2", "title": "b", "status": "pending"}],
         current_node="code-review")
    model = ds.build_hud_model(tmp_workspace)
    line = sl.render(model)
    plain = _plain(line)
    assert "KDev 团队" in plain
    assert "用户管理模块" in plain
    assert "50%" in plain
    assert "code-review" in plain
    assert "\n" not in line  # 单行


def test_statusline_blocked_shows_alert(tmp_workspace, seed):
    seed(tmp_workspace, run_status="blocked", blocked_reason="超上限",
         stories=[{"id": "s1", "title": "a", "status": "pending"}])
    model = ds.build_hud_model(tmp_workspace)
    plain = _plain(sl.render(model))
    assert "待处理 1" in plain  # blocked → 1 告警


def test_statusline_empty(tmp_workspace):
    model = ds.build_hud_model(tmp_workspace)
    plain = _plain(sl.render(model))
    assert "KDev 团队" in plain and "暂无在跑需求" in plain


def test_statusline_truncates_long_name(tmp_workspace, seed):
    seed(tmp_workspace, display_name="超长需求名称" * 10)
    model = ds.build_hud_model(tmp_workspace)
    plain = _plain(sl.render(model))
    # 可见字符（不含 ANSI）控制在合理宽度
    assert len(plain) <= 90
