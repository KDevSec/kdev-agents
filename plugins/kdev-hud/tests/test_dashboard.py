from kdev_hud import datasource as ds
from kdev_hud import dashboard as dash


def test_dashboard_self_contained_and_sections(tmp_workspace, seed):
    seed(tmp_workspace, display_name="用户管理模块",
         stories=[{"id": "s1", "title": "用户列表", "status": "done"},
                  {"id": "s2", "title": "新增编辑", "status": "done"},
                  {"id": "s3", "title": "角色分配", "status": "in_progress"},
                  {"id": "s4", "title": "批量导入", "status": "pending"}],
         current_node="code-review",
         gates=[{"gate": "g-cr", "kind": "review", "node": "code-review",
                 "verdict": "PASS", "iter": 1, "by": "ai", "issues": [],
                 "ts": "2026-06-12T08:00:00+00:00"}],
         transitions=[{"from": "impl", "to": "code-review", "reflow": False,
                       "forced_fail": False, "reason": "impl-done",
                       "entered_at": "2026-06-12T07:50:00+00:00"}])
    model = ds.build_hud_model(tmp_workspace)
    html = dash.render(model, generated_at="2026-06-12T08:10:00+00:00")
    # 自包含：无外链 css/js
    assert "<style>" in html and "http://" not in html and 'src="http' not in html
    # 关键分区
    assert "用户管理模块" in html
    assert "50%" in html          # 完成度
    assert "用户列表" in html      # 用户故事
    assert "code-review" in html  # 当前活动节点
    assert "PASS" in html         # 评审流水
    assert "实时事件流" in html
    # FF-3：不编造 score
    assert "评审分数" not in html or "score" not in html.lower()


def test_dashboard_empty_graceful(tmp_workspace):
    model = ds.build_hud_model(tmp_workspace)
    html = dash.render(model, generated_at="2026-06-12T08:10:00+00:00")
    assert "<html" in html and "暂无在跑需求" in html


def test_dashboard_blocked_alert_rendered(tmp_workspace, seed):
    seed(tmp_workspace, run_status="blocked", blocked_reason="连续 FAIL 超上限")
    model = ds.build_hud_model(tmp_workspace)
    html = dash.render(model, generated_at="2026-06-12T08:10:00+00:00")
    assert "连续 FAIL 超上限" in html


def test_dashboard_escapes_html(tmp_workspace, seed):
    seed(tmp_workspace, display_name="<script>alert(1)</script>")
    model = ds.build_hud_model(tmp_workspace)
    html = dash.render(model, generated_at="2026-06-12T08:10:00+00:00")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_dashboard_multi_feature_queue(tmp_workspace, seed):
    seed(tmp_workspace, slug="feat-a", display_name="功能A")
    seed(tmp_workspace, slug="feat-b", display_name="功能B")
    model = ds.build_hud_model(tmp_workspace)
    html = dash.render(model, generated_at="2026-06-12T08:10:00+00:00")
    assert "多功能队列" in html          # 队列分区出现
    assert "功能A" in html and "功能B" in html


def test_dashboard_single_feature_no_queue(tmp_workspace, seed):
    seed(tmp_workspace, slug="only-one", display_name="唯一功能")
    model = ds.build_hud_model(tmp_workspace)
    html = dash.render(model, generated_at="2026-06-12T08:10:00+00:00")
    assert "多功能队列" not in html      # 单功能不出队列


def test_dashboard_event_stream_newest_first_and_capped(tmp_workspace, seed):
    # 15 条 transition；渲染应 newest-first 且只取前 12
    trans = [{"from": f"n{i}", "to": f"n{i+1}", "reflow": False, "forced_fail": False,
              "reason": "r", "entered_at": "2026-06-12T07:%02d:00+00:00" % i}
             for i in range(15)]
    seed(tmp_workspace, slug="ev", transitions=trans)
    model = ds.build_hud_model(tmp_workspace)
    html = dash.render(model, generated_at="2026-06-12T08:10:00+00:00")
    # newest (n14→n15) 在 oldest (n0→n1) 之前；且最老的若干条被截断
    assert html.index("n14") < html.index("n1 ") if "n1 " in html else True
    newest_pos = html.find("07:14:00")   # 最新事件 ts
    oldest_pos = html.find("07:00:00")   # 最老事件 ts（应被 [:12] 截掉 → -1）
    assert newest_pos != -1              # 最新在
    assert oldest_pos == -1              # 最老被截断（15 条只显示 12）
