#!/usr/bin/env python3
"""SessionStart: bootstrap the .kdev/ nested memory repo (Q-009). Best-effort, never blocks."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
import kdev_sync  # noqa: E402


def main():
    repo_root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        res = kdev_sync.bootstrap(repo_root)
    except Exception as exc:  # hooks must never crash the session
        print(f"[kdev-sync] bootstrap skipped: {exc}", file=sys.stderr)
        return
    if res["action"] == "remind":
        print(f"<kdev-sync-reminder>\n{res['message']}\n</kdev-sync-reminder>")
    elif not res["ok"]:
        print(f"[kdev-sync] {res['action']} failed: {res['message']}", file=sys.stderr)


if __name__ == "__main__":
    main()
