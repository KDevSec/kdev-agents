"""kdev-hud CLI —— python -m kdev_hud {statusline,render,setup}（纯只读 + 一次性安装）。

statusline：输出单行接 Claude Code statusLine（消费并忽略 stdin 的 session JSON）。
render：读 features/ → 写 <workspace>/.kdev/hud.html（不在 features/ 下，gitignored）。
setup：把 statusLine 幂等合并进 settings.json（OMC installer 模式）。
workspace 解析：--workspace > stdin JSON 的 cwd > 当前工作目录。
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from kdev_hud import datasource, statusline, dashboard, setup


def _consume_stdin():
    """读并返回 stdin（Claude Code 传 session JSON）；非 tty 才读，避免阻塞。"""
    if sys.stdin is None or sys.stdin.isatty():
        return ""
    try:
        return sys.stdin.read()
    except (OSError, ValueError):
        return ""


def _workspace_from_stdin(raw):
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    for key in ("cwd", "workspace"):
        v = data.get(key) if isinstance(data, dict) else None
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            cur = v.get("current_dir") or v.get("path")
            if isinstance(cur, str):
                return cur
    return None


def _resolve_workspace(args):
    """--workspace > stdin JSON cwd > cwd。stdin 惰性消费：仅 --workspace 缺省时才读，
    避免 statusline（每键一跑）在无 EOF 管道上阻塞挂死。"""
    if getattr(args, "workspace", None):
        return args.workspace
    from_stdin = _workspace_from_stdin(_consume_stdin())
    return from_stdin or str(Path.cwd())


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def cmd_statusline(args):
    ws = _resolve_workspace(args)
    try:
        model = datasource.build_hud_model(ws)
        line = statusline.render(model)
    except Exception:
        # HUD 铁律：观测层永不崩用户视图（派生非真相，坏数据降级）
        line = statusline.safe_fallback()
    sys.stdout.write(line)
    return 0


def cmd_render(args):
    ws = _resolve_workspace(args)
    try:
        model = datasource.build_hud_model(ws)
    except Exception:
        model = {"features": [], "feature_count": 0, "primary": None}
    html = dashboard.render(model, generated_at=_now_iso())
    out = Path(args.out) if args.out else Path(ws) / ".kdev" / "hud.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(str(out))
    return 0


def cmd_setup(args):
    scope = "user" if getattr(args, "user", False) else "project"
    workspace = args.workspace or str(Path.cwd())
    plugin_root = setup.resolve_plugin_root()
    command = setup.build_statusline_command(plugin_root)
    settings_path = setup.resolve_settings_path(scope, workspace)
    try:
        result = setup.install_statusline(settings_path, command, force=args.force)
    except setup.SetupError as e:
        sys.stderr.write(str(e) + "\n")
        return 1
    action = result["action"]
    path = result["path"]
    if action == "created":
        print(f"✅ 已写入 {path}，重载/重启 session 后状态栏生效")
    elif action == "updated":
        print(f"✅ 已更新 {path}，重载/重启 session 后状态栏生效")
    elif action == "skipped_foreign":
        print(f"未改动：已有他者 statusLine，加 `--force` 覆盖（会先备份 settings.json.bak）")
    elif action == "forced":
        print(f"✅ 已强制写入 {path}（原文件已备份至 {result['backup']}），重载/重启 session 后状态栏生效")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="kdev-hud", description="KDev HUD 观测层（只读）")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workspace",
                        help="项目工作区根（含 .kdev/）；缺省取 stdin.cwd 或 cwd")
    sub = p.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("statusline", parents=[common], help="通道① 单行状态栏")
    ps.set_defaults(func=cmd_statusline)
    pr = sub.add_parser("render", parents=[common], help="通道② 生成 hud.html")
    pr.add_argument("--out", help="输出路径，缺省 <workspace>/.kdev/hud.html")
    pr.set_defaults(func=cmd_render)
    psetup = sub.add_parser("setup", parents=[common], help="把 statusLine 接进 settings.json")
    scope_group = psetup.add_mutually_exclusive_group()
    scope_group.add_argument("--user", action="store_true",
                             help="写入用户级 ~/.claude/settings.json（缺省 project）")
    scope_group.add_argument("--project", action="store_true",
                             help="写入项目级 <workspace>/.claude/settings.json（缺省）")
    psetup.add_argument("--force", action="store_true",
                        help="覆盖他者 statusLine（先备份 settings.json.bak）")
    psetup.set_defaults(func=cmd_setup)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)
