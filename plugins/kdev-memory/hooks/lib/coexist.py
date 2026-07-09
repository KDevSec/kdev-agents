#!/usr/bin/env python3
"""kdev↔ieidev 记忆共存守卫（presence-based，ieidev 固定为主）。

本机可能同时装了 kdev-memory 与 ieidev-team：两套是同 fork、钉同样 6 个 Claude Code
事件，会双份注入 / 双催建 / 双记录 / 两段 CLAUDE.md 契约打架。已定协议：

    一个仓里只要 `.ieidev/memory/` 存在（= 用户真在用 ieidev），kdev 就整体让位、全静默。

让位是**无条件**的：即便 `.kdev/memory/` 也存在（两个都在），kdev 也让位——原文件不动、
不删，用户历史由 ieidev 侧一次性迁移器接走（不是本模块的活）。

信号与 kdev 认自己 `.kdev/memory` 的现有立场**同构**：都是 cwd 相对目录探测。各 hook 在其
现有 `.kdev/memory` 守卫处紧挨着调 `defer_to_ieidev()`，命中即用该 hook 原生的「静默退出」
形态返回（PostToolUse/SessionStart-JSON 类 print(SUPPRESS) 后 return 0；纯 stderr/stdout
类直接 return，不打任何字）。**本模块只判定，不负责返回**——返回形态各 hook 自理。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# ieidev 侧迁移器迁完会在此写 marker（`.kdev/memory/.migrated-to-ieidev`）。认它可在
# `.ieidev/memory` 尚未落地的窗口内更快短路；但 `.ieidev/memory` 存在性判断已足够覆盖
# 主场景，marker 只是廉价加持、非必需（别过度设计）。
_MIGRATED_MARKER = Path(".kdev") / "memory" / ".migrated-to-ieidev"
_IEIDEV_MEMORY = Path(".ieidev") / "memory"


def defer_to_ieidev(root: Optional[Path] = None) -> bool:
    """检测 ieidev 记忆是否在场——在场则 kdev 应整体让位。

    root 缺省用 cwd（与其余 hook 的 `Path(".kdev/memory")` cwd 相对探测同构）；
    kdev-sync-bootstrap / kdev-sync-push 用 `CLAUDE_PROJECT_DIR` 作 repo_root，显式传入
    以对齐它们自己的根锚点。
    """
    base = Path(root) if root is not None else Path(".")
    if (base / _IEIDEV_MEMORY).is_dir():
        return True
    if (base / _MIGRATED_MARKER).exists():
        return True
    return False
