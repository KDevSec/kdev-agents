"""design-flow 接底座迁移断言：SKILL 回归方法论参考，不自跑状态机。"""
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
SKILL = PLUGIN / "skills" / "kdev-design-flow" / "SKILL.md"


def _body():
    return SKILL.read_text(encoding="utf-8")


def test_skill_no_longer_imports_own_flow_state():
    """编排状态迁到 kdev-core——SKILL 不再 import/驱动自带 lib.flow_state。"""
    body = _body()
    assert "lib.flow_state" not in body
    assert "from lib.flow_state import" not in body
    assert "init_state(" not in body


def test_skill_points_to_generic_driver_and_engine():
    """编排归通用 kdev-flow-driver + kdev-core，不在 SKILL 自跑。"""
    body = _body()
    assert "kdev-flow-driver" in body
    assert "kdev_core" in body or "kdev-core" in body


def test_skill_uses_feature_first_storage():
    """运行时状态落 feature-first .kdev/features/<slug>/（非旧 .kdev/design-flow 状态机）。"""
    body = _body()
    assert ".kdev/features/" in body


def test_skill_methodology_preserved():
    """方法论（Stage/Gate）仍在——回归参考不是删内容。"""
    body = _body()
    for tok in ["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Gate 1", "Gate 2", "Gate 3"]:
        assert tok in body, f"方法论 token 丢失: {tok}"
