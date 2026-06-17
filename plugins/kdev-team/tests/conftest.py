import sys
from pathlib import Path
# 复用 kdev-core 引擎（test_orchestration_config 会用）
KDEV_CORE = Path(__file__).resolve().parents[2] / "kdev-core"
sys.path.insert(0, str(KDEV_CORE))
# 本插件 python 包根（from kdev_team import ...）
KDEV_TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KDEV_TEAM))
