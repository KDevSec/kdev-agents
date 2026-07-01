#!/usr/bin/env python3
"""SessionEnd: commit + push the .kdev/ nested memory repo (Q-009). Best-effort, never blocks."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
import kdev_sync  # noqa: E402


def main():
    repo_root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
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
