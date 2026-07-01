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
    action = res["action"]
    if not res.get("ok", True):
        # 联网同步失败（多半缺 GitHub 凭据）→ 在**会话内**给可读提示，不弹 GUI（_git 已禁交互）。
        if action in ("pull", "clone", "init"):
            msg = kdev_sync.sync_failed_reminder_text(action, res.get("message", ""))
            print(f"<kdev-sync-reminder>\n{msg}\n</kdev-sync-reminder>")
        else:
            print(f"[kdev-sync] {action} failed: {res['message']}", file=sys.stderr)
    elif action in ("remind", "init-local") and res.get("message"):
        print(f"<kdev-sync-reminder>\n{res['message']}\n</kdev-sync-reminder>")

    # 未推积压可见化：正常 bootstrap 之后，若记忆仓本地领先 upstream（自动 push 失败会累积
    # 领先），额外弹一段独立提醒——SessionEnd 的 push 失败到不了用户，必须在 SessionStart 抓。
    # sync:off（optout）时全静默，不提醒；与上面的 remind/clone/pull 提醒叠加、互不打架。
    if action != "optout":
        try:
            n = kdev_sync.unpushed_count(repo_root)
        except Exception:
            n = 0
        if n > 0:
            msg = kdev_sync.unpushed_reminder_text(n)
            print(f"<kdev-sync-reminder>\n{msg}\n</kdev-sync-reminder>")


if __name__ == "__main__":
    main()
