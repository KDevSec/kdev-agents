"""kdev-hud 只读数据层 —— 直接读 .kdev/features/<slug>/ 文件，零写入、零 kdev_core 依赖。

契约 = 文件格式（见 plan「数据契约」）。运行时不 import kdev_core：HUD 自包含，
底座可 headless 单装。解析容错：缺失/损坏一律降级（None / [] / 跳过坏行）。
"""
import json
from pathlib import Path


def _features_dir(workspace) -> Path:
    return Path(workspace) / ".kdev" / "features"


def _feature_dir(workspace, slug) -> Path:
    return _features_dir(workspace) / slug


def read_flow_state(workspace, slug):
    """读 flow-state.json → dict；缺失或损坏 → None。"""
    path = _feature_dir(workspace, slug) / "flow-state.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def read_events(workspace, slug):
    """读 events.jsonl（oldest first）→ list[dict]；缺失 → []；跳过空行/坏行。"""
    path = _feature_dir(workspace, slug) / "events.jsonl"
    if not path.exists():
        return []
    out = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def list_feature_slugs(workspace):
    """扫 .kdev/features/*/flow-state.json，返回 slug 列表（按目录名排序）。"""
    fdir = _features_dir(workspace)
    if not fdir.exists():
        return []
    out = []
    for sub in sorted(fdir.iterdir()):
        if (sub / "flow-state.json").exists():
            out.append(sub.name)
    return out
