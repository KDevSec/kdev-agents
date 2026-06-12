"""kdev-hud 测试基座。

防漂移（R-009）：运行时 HUD 直读文件，但 fixture 用 kdev_core 真实写 API 生成，
保证测的永远是底座真实落地格式。core 改格式 → 这里 import/调用红 → HUD 测试红。
"""
import sys
from pathlib import Path

import pytest

# kdev_hud 包可导入
_HUD_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_HUD_ROOT))
# 测试期注入 kdev_core（plugins/kdev-core），仅 fixture 生成用，运行时 HUD 不依赖
_CORE_ROOT = _HUD_ROOT.parent / "kdev-core"
sys.path.insert(0, str(_CORE_ROOT))


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """模拟项目工作区；.kdev/features/<slug>/ 由 seed 按需建。"""
    return tmp_path


@pytest.fixture
def seed():
    """用 kdev_core 真实 API 在 ws 里造一个 feature 的真实落地数据。

    返回 _seed(ws, slug='user-mgmt', display_name='用户管理模块', flow='design', stories=[...],
              current_node='code-review', run_status='in_progress',
              blocked_reason=None, gates=[...], transitions=[...]) -> slug
    gates 元素: dict 形如 GateResult（gate/kind/node/verdict/iter/by/issues/ts）
    transitions 元素: dict 形如 phase_history 条目（from/to/reflow/forced_fail/reason/entered_at）
    """
    from kdev_core import flow_state, events

    def _seed(ws, *, slug="user-mgmt", display_name="用户管理模块", flow="design",
              stories=None, current_node="code-review",
              run_status="in_progress", blocked_reason=None,
              gates=None, transitions=None):
        flow_state.init_state(ws, flow, slug, display_name=display_name,
                              initial_node=current_node)
        for s in (stories or []):
            flow_state.add_story(ws, slug, story_id=s["id"], title=s["title"],
                                 status=s.get("status", "pending"))
        # 把 active 推到指定 node / status
        st = flow_state.read_state(ws, slug=slug)
        st["current_node"] = current_node
        st["status"] = run_status
        st["blocked_reason"] = blocked_reason
        flow_state.write_state(ws, slug=slug, state=st)
        # 真实格式事件
        for tr in (transitions or []):
            events.append_event(ws, slug, events.transition_event(
                slug=slug, flow=flow, run=1, entry=tr))
        for gr in (gates or []):
            events.append_event(ws, slug, events.gate_event(
                slug=slug, flow=flow, run=1, gate_result=gr))
        return slug

    return _seed
