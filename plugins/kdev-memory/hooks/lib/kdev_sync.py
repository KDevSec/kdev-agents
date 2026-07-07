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
import os
import subprocess
from datetime import date
from pathlib import Path

REMINDER = (
    "检测到工程记忆尚未 git 托管。强烈建议建立独立记忆仓（nested repo）并在 "
    "kdev-sync.yml 登记，以便跨机器 / 团队同步、换机不丢记忆。是否现在初始化？"
)

REMOTE_REMINDER = (
    "工程记忆已建本地独立仓（nested repo），但尚未配置远程。强烈建议在 kdev-sync.yml "
    "登记 memory_repo 并建远程仓，以便跨机器 / 团队同步、换机不丢记忆。"
)

# 项目级「不建记忆仓」退出提示——附在每条提醒后。标记写进**项目仓**（kdev-sync.yml，入库），
# 提交后全队读到即不再提示、不再建仓（团队都知道有人决定本项目不要记忆仓）。
OPTOUT_HINT = (
    "\n（工程记忆是与代码仓**分开**的独立 git 仓。本项目若不想建记忆仓 / 不想被提示，"
    "在项目根 `kdev-sync.yml` 写一行 `sync: off` 并**提交到本项目仓**——全队据此从此静默、"
    "不再提示也不再建仓；想重新启用删掉该行即可。）"
)


def read_sync_config(repo_root):
    """Parse the flat kdev-sync.yml -> {'memory_repo': url|None, 'branch': str, 'sync': str}.

    `sync: off` —— 项目级「不建记忆仓 / 不同步」开关。提交到**项目仓**后全队据此静默跳过、
    不再提示（团队都知道有人决定本项目不要记忆仓）；缺省 'on'。
    """
    cfg = {"memory_repo": None, "branch": "main", "sync": "on"}
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
    return REMINDER + OPTOUT_HINT


def remote_reminder_text():
    """本地仓已建、缺远程时的中文提醒。"""
    return REMOTE_REMINDER + OPTOUT_HINT


def sync_failed_reminder_text(action, detail=""):
    """联网同步（pull/clone/init）失败时给**会话内**的可读提示——替代 Windows 上会弹的
    Git Credential Manager「Connect to GitHub」GUI（_git 已禁交互，缺凭据静默失败）。
    引导用户在终端登录一次缓存凭据，之后每次会话自动静默同步。"""
    tail = f"（详情：{detail}）" if detail else ""
    return (
        f"工程记忆云同步未完成（{action} 失败）——已跳过，不影响本地使用与记忆留存。\n"
        "要开启跨机/团队同步，按 remote 类型排查：\n"
        "· SSH remote（git@…）：检查 SSH key / agent（`ssh -T git@github.com`）；\n"
        "· HTTPS remote：在终端登录一次缓存凭据（`gh auth login`，或对该账号任意仓库 `git pull` 按提示登录）。\n"
        "排查后每次会话启动会自动静默同步，不再弹窗。" + tail + OPTOUT_HINT
    )


def unpushed_reminder_text(count):
    """SessionStart 会话内提示：记忆仓有 N 条本地 commit 未推上远程（自动 push 可能失败）。

    换机不丢记忆依赖记忆仓被推上远程；push 失败会让本地累积领先 upstream 该 ref，
    这里把它显性化，别静默积压（实测曾积压 45 会话）。"""
    return (
        f"⚠️ 记忆仓有 {count} 条本地 commit 未推上远程——自动 push 可能失败"
        "（检查 SSH key/凭据，或在 .kdev 手动 git push）。换机不丢记忆依赖它，别忽略。"
    )


def unpushed_count(repo_root):
    """.kdev/ 本地领先 upstream 的 commit 条数（git rev-list --count @{u}..HEAD）。

    只读、**不 fetch**——push 失败会让本地累积领先 upstream ref，正是要抓的信号。
    无 .git / 无 upstream / 任何出错 → 返回 0（容错，永不抛）。
    """
    try:
        kdev = _kdev_dir(repo_root)
        if not (kdev / ".git").exists():
            return 0
        r = _git(["rev-list", "--count", "@{u}..HEAD"], cwd=kdev)
        if r.returncode != 0:
            return 0
        return int((r.stdout or "0").strip() or "0")
    except Exception:
        return 0


def warn_unpushed(repo_root, count):
    """push 失败时写持久信号文件 .kdev/memory/WARN-记忆未推送-<date>.md（仿 session-end-check WARN）。

    保证「自动 push 失败」有据可查、下次会话能被 SessionStart brief / 用户看到。
    只读依赖 count；写文件失败静默吞掉，永不抛。返回写入的 Path 或 None。
    """
    try:
        mem = _kdev_dir(repo_root) / "memory"
        if not mem.is_dir():
            return None
        today = date.today().isoformat()
        warn_file = mem / f"WARN-记忆未推送-{today}.md"
        body = (
            f"# ⚠️ 记忆仓未推送：{today}\n\n"
            f"会话结束时自动 push 失败，记忆仓有 **{count} 条本地 commit 未推上远程**。\n\n"
            "换机 / SSH 失效时会丢这些记忆。请检查：\n\n"
            "1. SSH key / 凭据是否有效（`ssh -T git@github.com` 或 `gh auth status`）\n"
            "2. 在 `.kdev` 目录手动 `git push` 补推\n"
            f"3. 补推成功后 `rm {warn_file}`\n\n"
            "_本文件由 kdev-memory SessionEnd hook 自动生成（push 失败兜底）。_\n"
        )
        warn_file.write_text(body, encoding="utf-8")
        return warn_file
    except Exception:
        return None


def is_sync_off(repo_root):
    """项目是否已选择「不建记忆仓」（kdev-sync.yml 里 sync: off）。"""
    return str(read_sync_config(repo_root).get("sync", "on")).strip().lower() == "off"


def decide_action(*, has_git, kdev_nonempty, remote):
    """Pure SessionStart bootstrap decision. Returns one of:
      'pull'       — .kdev/ 已是仓且配置了 remote（拉最新）。
      'clone'      — 无仓、.kdev/ 空/缺、有 remote（新机器）。
      'init'       — 无仓、.kdev/ 已有本地内容、有 remote（转 nested repo + 首推）。
      'init-local' — 无仓、.kdev/ 已有本地内容、无 remote（本地 git init 建独立仓 +
                     机器本地 .gitignore + 首次 commit；并提醒去建远程仓）。
      'remind'     — 无可建（空且无 remote），或本地仓已建但无 remote → 持续提醒建远程仓。
    """
    if has_git:
        return "pull" if remote else "remind"
    if remote:
        return "init" if kdev_nonempty else "clone"
    return "init-local" if kdev_nonempty else "remind"


# Fixed identity for the nested memory repo's own commits (hermetic; the code repo's
# AI/human identity is separate and set elsewhere).
_GIT_ID = ["-c", "user.name=kdev-memory", "-c", "user.email=kdev@local", "-c", "commit.gpgsign=false"]

# 禁止任何交互式凭据弹窗：本 hook 是 best-effort，缺凭据应静默失败、不弹框打断会话。
# Windows 上 Git Credential Manager 默认会弹「Connect to GitHub」GUI（SessionStart 的 bootstrap
# 做 pull/clone/push 时触发）。下面三件套关掉交互；已缓存的凭据仍可用，正常同步不受影响。
_NONINTERACTIVE_GIT_ENV = {
    "GIT_TERMINAL_PROMPT": "0",   # git 自身不在终端问账号密码
    "GCM_INTERACTIVE": "Never",   # Git Credential Manager 不弹 GUI（旧版 env 开关）
}
# 配置版开关（新版 GCM 读 credential.interactive），用 -c 注入，覆盖各版本。
_NONINTERACTIVE_GIT_CONF = ["-c", "credential.interactive=false"]

# Machine-local memory (NOT hosted to the shared memory repo) — §5.3 #13/#14/#15/#16.
# Bare names (no internal slash) match at any depth: covers flat (.kdev/memory/state/)
# and scoped (.kdev/state/) layouts.
_MACHINE_LOCAL_GITIGNORE = """# kdev-memory nested repo — machine-local, not hosted (§5.3)
state/
checkpoints/
hud.md
dataset/
"""


def _ensure_machine_local_gitignore(kdev):
    """Write .kdev/.gitignore excluding machine-local dirs if absent."""
    gi = Path(kdev) / ".gitignore"
    if not gi.exists():
        gi.write_text(_MACHINE_LOCAL_GITIGNORE, encoding="utf-8")


def _git(args, cwd, *, identity=False):
    pre = _NONINTERACTIVE_GIT_CONF + (_GIT_ID if identity else [])
    env = dict(os.environ)
    env.update(_NONINTERACTIVE_GIT_ENV)
    return subprocess.run(["git", *pre, *args], cwd=str(cwd),
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)


def _kdev_dir(repo_root):
    return Path(repo_root) / ".kdev"


def bootstrap(repo_root):
    """SessionStart bootstrap. Returns {'action', 'ok', 'message'}. Never raises."""
    repo_root = Path(repo_root)
    kdev = _kdev_dir(repo_root)
    has_git = (kdev / ".git").exists()
    kdev_nonempty = kdev.exists() and any(kdev.iterdir())
    cfg = read_sync_config(repo_root)
    # 项目级退出：kdev-sync.yml 标了 sync: off（已提交到项目仓）→ 全程静默，不建仓、不联网、不提示。
    if str(cfg.get("sync", "on")).strip().lower() == "off":
        return {"action": "optout", "ok": True, "message": ""}
    remote = cfg["memory_repo"]
    branch = cfg["branch"]
    action = decide_action(has_git=has_git, kdev_nonempty=kdev_nonempty, remote=remote)

    if action == "remind":
        # has_git 但无 remote：本地仓已建、缺远程 → 提醒去建远程仓；
        # 否则（无仓且无 remote）→ 原"尚未 git 托管"初始化提醒。
        msg = remote_reminder_text() if has_git else reminder_text()
        return {"action": "remind", "ok": True, "message": msg}

    if action == "init-local":
        # 无 remote：仍建本地独立 nested repo（记忆即刻被版本化），提醒去建远程仓。
        _ensure_machine_local_gitignore(kdev)
        msgs = []
        for args_, ident, tolerate in [
            (["init", "-b", branch], True, False),
            (["config", "core.quotepath", "false"], False, False),
            (["add", "-A"], False, False),
            (["commit", "-m", "chore(kdev-memory): bootstrap local memory repo (no remote)"], True, False),
        ]:
            r = _git(args_, cwd=kdev, identity=ident)
            msgs.append(f"git {args_[0]}: rc={r.returncode}")
            if r.returncode != 0 and not tolerate:
                return {"action": "init-local", "ok": False,
                        "message": "; ".join(msgs) + " :: " + (r.stderr or "").strip()}
        return {"action": "init-local", "ok": True, "message": remote_reminder_text()}

    if action == "pull":
        r = _git(["pull", "--ff-only"], cwd=kdev)
        return {"action": "pull", "ok": r.returncode == 0,
                "message": (r.stderr or r.stdout).strip()}

    if action == "clone":
        kdev.parent.mkdir(parents=True, exist_ok=True)
        # -b <branch>: the freshly-bootstrapped memory remote's HEAD may still point at the
        # host git's default branch (e.g. master) rather than our configured branch, which
        # would make a plain clone check out nothing. Clone the configured branch explicitly.
        r = _git(["clone", "-b", branch, remote, str(kdev)], cwd=repo_root, identity=True)
        if r.returncode == 0:
            # Chinese memory filenames must show as UTF-8 (not octal-escaped) in git output.
            _git(["config", "core.quotepath", "false"], cwd=kdev)
        return {"action": "clone", "ok": r.returncode == 0,
                "message": (r.stderr or r.stdout).strip()}

    # action == "init": convert existing local .kdev/ into the nested repo + first push
    _ensure_machine_local_gitignore(kdev)   # don't push machine-local counters/checkpoints (§5.3)
    msgs = []
    for args, ident, tolerate in [
        (["init", "-b", branch], True, False),
        # Chinese memory filenames must show as UTF-8 (not octal-escaped) in git output.
        (["config", "core.quotepath", "false"], False, False),
        (["remote", "add", "origin", remote], False, True),   # tolerate "already exists"
        (["add", "-A"], False, False),
        (["commit", "-m", "chore(kdev-memory): bootstrap nested memory repo"], True, False),
        (["push", "-u", "origin", branch], True, False),
    ]:
        r = _git(args, cwd=kdev, identity=ident)
        msgs.append(f"git {args[0]}: rc={r.returncode}")
        if r.returncode != 0 and not tolerate:
            return {"action": "init", "ok": False,
                    "message": "; ".join(msgs) + " :: " + (r.stderr or "").strip()}
    return {"action": "init", "ok": True, "message": "; ".join(msgs)}


def sync_push(repo_root, message="chore(kdev-memory): session sync"):
    """SessionEnd/rollup: commit + push .kdev/. Returns {'ok', 'pushed', 'message'}. Never raises."""
    if is_sync_off(repo_root):
        return {"ok": True, "pushed": False, "message": "sync off (项目已选择不建记忆仓)"}
    kdev = _kdev_dir(repo_root)
    if not (kdev / ".git").exists():
        return {"ok": True, "pushed": False, "message": "no .kdev/.git; skip (untracked memory)"}
    _git(["add", "-A"], cwd=kdev)
    status = _git(["status", "--porcelain"], cwd=kdev)
    committed = False
    if status.stdout.strip():
        c = _git(["commit", "-m", message], cwd=kdev, identity=True)
        if c.returncode != 0:
            return {"ok": False, "pushed": False, "message": (c.stderr or c.stdout).strip()}
        committed = True
    # 解耦 commit 与 push（修 G 20260707-104552）：无论这次有没有新 commit，只要本地
    # 领先 upstream（已 commit 未推的积压，如早期 push 失败留下）就 push——否则积压永远清不掉。
    if not committed and unpushed_count(repo_root) == 0:
        return {"ok": True, "pushed": False, "message": "nothing to commit, nothing to push"}
    p = _git(["push"], cwd=kdev)
    return {"ok": p.returncode == 0, "pushed": p.returncode == 0,
            "message": (p.stderr or p.stdout).strip()}
