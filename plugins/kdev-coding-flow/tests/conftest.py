import sys
from pathlib import Path

# 复用 kdev-core 引擎做校验
KDEV_CORE = Path(__file__).resolve().parents[2] / "kdev-core"
sys.path.insert(0, str(KDEV_CORE))
