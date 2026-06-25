"""tests/test_main_entrypoint.py — 端到端证明 __main__.py 按绝对路径直跑自举生效。

按绝对路径直跑 __main__.py 时，Python 把脚本所在目录（kdev_hud/）加入 sys.path，
导致 `from kdev_hud.cli import main` 找不到 kdev_hud 包（ModuleNotFoundError）。
__main__.py 的自举行（sys.path.insert(0, parent.parent)）修复该问题。
本测试通过 subprocess 直接执行 __main__.py，剥离 PYTHONPATH，验证自举生效。
"""
import os
import sys
from pathlib import Path

import pytest


MAIN_PY = Path(__file__).resolve().parents[1] / "kdev_hud" / "__main__.py"


def test_main_runs_by_absolute_path(tmp_path):
    """按绝对路径直跑 __main__.py statusline，不依赖 PYTHONPATH，应成功且输出含 KDev 团队。"""
    import subprocess

    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    result = subprocess.run(
        [sys.executable, str(MAIN_PY), "statusline", "--workspace", str(tmp_path)],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"__main__.py 按绝对路径运行失败（rc={result.returncode}）\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )
    assert "KDev 团队" in result.stdout, (
        f"stdout 中未找到 'KDev 团队'，自举可能未生效\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )
