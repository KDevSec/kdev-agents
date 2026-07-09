#!/usr/bin/env python3
"""SessionEnd: commit + push the .kdev/ nested memory repo (Q-009). Best-effort, never blocks."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
import kdev_sync  # noqa: E402
from coexist import defer_to_ieidev  # noqa: E402


def main():
    repo_root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    # ieidev 让位守卫：.ieidev/memory 在场 → kdev 整体让位、全静默（直接 return，不 commit、
    # 不 push、不写未推送 WARN）。让位是无条件的：kdev 记忆仓原样留在盘上，历史由 ieidev 侧接走。
    if defer_to_ieidev(Path(repo_root)):
        return
    try:
        res = kdev_sync.sync_push(repo_root)
    except Exception as exc:
        print(f"[kdev-sync] push skipped: {exc}", file=sys.stderr)
        return
    if not res["ok"]:
        print(f"[kdev-sync] push failed: {res['message']}", file=sys.stderr)
        # push 失败 stderr 到不了用户 → 仿 session-end-check 写持久 WARN 信号文件，保证有据可查。
        try:
            n = kdev_sync.unpushed_count(repo_root) or 1
            kdev_sync.warn_unpushed(repo_root, n)
        except Exception:
            pass


if __name__ == "__main__":
    main()
