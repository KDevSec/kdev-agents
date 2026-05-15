"""kdev-memory 配置读取（.kdev/memory/config.yaml）

只支持 stdlib——`yaml` 不是标准库，所以 config.yaml 使用极简子集（顶层 key: value），
用 line-based parser 解析。未配置 = 视同 hybrid（fail-open）。

字段：
- record_mode: hybrid | inline  —— 落盘路径配置（详见 references/subagent-落盘机制.md）

未来加字段时，所有 reader 函数保持兼容：不认识的字段忽略。
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

RecordMode = Literal["hybrid", "inline"]
VALID_RECORD_MODES: tuple[RecordMode, ...] = ("hybrid", "inline")


def _parse_kv_yaml(text: str) -> dict[str, str]:
    """极简 YAML 子集：仅顶层 `key: value` 行；忽略注释 / 空行 / 不识别的格式。

    不支持嵌套、列表、多行字符串。如未来需要这些再换用 PyYAML（但增加依赖成本）。
    """
    result: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line or ":" not in line:
            continue
        if line.startswith((" ", "\t")):
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            result[key] = value
    return result


def read_record_mode(kdev_dir: Path | str = ".kdev/memory") -> RecordMode:
    """读 .kdev/memory/config.yaml 的 record_mode 字段。

    fallback 路径：
    1. config.yaml 不存在 → hybrid
    2. record_mode 字段缺失 → hybrid
    3. 字段值不在枚举内 → hybrid（不抛错，宽容处理）
    """
    config_path = Path(kdev_dir) / "config.yaml"
    if not config_path.is_file():
        return "hybrid"
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return "hybrid"
    config = _parse_kv_yaml(text)
    value = config.get("record_mode", "").lower()
    if value in VALID_RECORD_MODES:
        return value  # type: ignore[return-value]
    return "hybrid"


def main() -> int:
    """CLI：打印当前项目的 record_mode。

    用法：python3 memory_config.py [<kdev_dir>]
    """
    import sys
    kdev = sys.argv[1] if len(sys.argv) > 1 else ".kdev/memory"
    print(read_record_mode(kdev))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
