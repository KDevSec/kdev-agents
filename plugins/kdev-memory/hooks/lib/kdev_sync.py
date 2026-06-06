"""kdev-memory git 托管自举 (Q-009): .kdev/ 独立 nested repo + kdev-sync.yml 自举.

代码仓 .gitignore 忽略 /.kdev/；tracked 的 kdev-sync.yml 记"记忆仓 remote"。
SessionStart 自举：
  - .kdev/.git 存在                  -> pull（永远拿最新，胜 submodule 钉死 SHA）
  - 无 .git，.kdev/ 空/缺，有 remote  -> clone（新机器零手动）
  - 无 .git，.kdev/ 有内容，有 remote -> init（把本机已有记忆转成 nested repo + 首推）
  - 无 remote                        -> 中文托管提醒（强烈建议、非强制）
SessionEnd/rollup -> commit + push。
全程 stdlib-only —— hook 不能因缺依赖而炸。
"""
import subprocess
from pathlib import Path

REMINDER = (
    "检测到工程记忆尚未 git 托管。强烈建议建立独立记忆仓（nested repo）并在 "
    "kdev-sync.yml 登记，以便跨机器 / 团队同步、换机不丢记忆。是否现在初始化？"
)


def read_sync_config(repo_root):
    """Parse the flat kdev-sync.yml -> {'memory_repo': url|None, 'branch': str}."""
    cfg = {"memory_repo": None, "branch": "main"}
    path = Path(repo_root) / "kdev-sync.yml"
    if not path.exists():
        return cfg
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key in cfg and val:
            cfg[key] = val
    return cfg


def reminder_text():
    """The 中文 托管提醒 (记忆架构 §9.4)."""
    return REMINDER


def decide_action(*, has_git, kdev_nonempty, remote):
    """Pure SessionStart bootstrap decision.

    Returns one of:
      'pull'   — .kdev/ is already a repo (fetch latest).
      'clone'  — no repo, .kdev/ empty/absent, a remote is configured (new machine).
      'init'   — no repo, .kdev/ already has local content, a remote is configured
                 (convert this machine's existing memory into the nested repo + first push).
      'remind' — no remote configured (emit the 中文 托管提醒; do nothing destructive).
    """
    if has_git:
        return "pull"
    if remote:
        return "init" if kdev_nonempty else "clone"
    return "remind"
