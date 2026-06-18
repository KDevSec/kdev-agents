# Plan — kdev-hud `/kdev-hud-setup`：把 statusLine 一键接进 settings.json

## 背景 / 这块在哪

CC 插件**不能自动注册 statusLine**（plugin.json `settings` 只认 agent/subagentStatusLine）。所以
kdev-hud 装完「statusline 不显示」是预期——必须有命令把 `statusLine` 条目幂等**合并**进用户的
settings.json。本计划照 OMC installer 的判例模式（合并不覆盖其他键 + 备份 + 所有权检测 + force）
实现 `kdev_hud/setup.py` + `setup` 子命令 + `/kdev-hud-setup` slash 命令。

工作区：worktree `../kdev-hud-setup`，分支 `feat/kdev-hud-setup`。只动 `plugins/kdev-hud/`，
不碰其他插件 / roadmap / main。

## 已证实的关键事实（编排主控实测，必须照做）

1. 🔴 **`python3 <abs>/kdev_hud/__main__.py statusline` 直跑会 `ModuleNotFoundError: No module named 'kdev_hud'`**。
   原因：按文件路径跑脚本时 sys.path[0] 是脚本所在目录（`kdev_hud/`），而 `from kdev_hud.cli import main`
   需要 `kdev_hud` 的**父目录**在 path 上。已实测：在 `__main__.py` 顶部 `sys.path.insert(0, parent_of_kdev_hud)`
   后直跑成功输出 `KDev 团队 │ …`。**故 Task 1 必须改 `__main__.py` 自举父目录**，否则 setup 写出的
   statusLine 命令全是 traceback、CC 什么都不显示——这正是「绕开 PYTHONPATH / FF-2」的真实落地点。
2. `<abs>`（statusLine 命令里 `<abs>/kdev_hud/__main__.py` 的 `<abs>`）= **含 `kdev_hud/` 包的那个目录**
   = 插件根。`CLAUDE_PLUGIN_ROOT` 优先；回退用 `Path(__file__).resolve().parent.parent`（setup.py 在
   `kdev_hud/` 里，`.parent`=`kdev_hud/`、`.parent.parent`=插件根）。**注意：brief 写的「回退 Path(__file__).parent」
   不精确——必须 `.parent.parent`，否则路径会变成 `…/kdev_hud/kdev_hud/__main__.py` 跑不通。**
3. 兄弟插件（kdev-memory / kdev-team）的 `commands/` 靠**自动发现**，plugin.json **不声明 `commands` 键**。
   故新建 `commands/kdev-hud-setup.md` 同样自动发现，无需改 plugin.json 结构（只 bump version）。
4. `${workspaceFolder}` 在非 VSCode 终端可能不展开 → cli.py 的 `_resolve_workspace` 拿到字面量当路径 →
   `build_hud_model` 失败 → `safe_fallback()` 兜底仍出单行（降级不崩）。可接受，照 brief 保留该形。

## Global Constraints（评审注意力镜——逐条 binding）

- **TDD**：每个有代码的 task 先写 RED 测试再实现，结束 `cd plugins/kdev-hud && python3 -m pytest -q` 必须全绿。
- **只动 `statusLine` 键，绝不 clobber 其他键**：读现有 JSON → 仅加/改 `statusLine` → 写回，`theme`/`env`/`hooks`/
  `permissions` 等一律原样保留（含 key 顺序）。
- **坏 JSON 不写**：现有 settings.json 解析失败 → 抛 `SetupError`、**绝不写入**（原文件字节不变）。
- **所有权检测**：`statusLine.command`（或 legacy 字符串）含子串 `kdev_hud` 即判为「本插件的」。
- **覆盖他者 statusLine 必须 `--force` 且先备份**：已有**非本插件** statusLine 时，无 `--force` → 不写、报「需 --force」；
  有 `--force` → 先把原文件原样备份到**同目录 `settings.json.bak`**（即 `<settings路径>.bak`，名字是 `settings.json.bak`
  不是 `settings.bak`）再覆盖。本插件自己的 statusLine → 直接幂等更新路径、不需 force、不备份。
- **作用域**：`--project`（缺省，写 `<workspace>/.claude/settings.json`）/ `--user`（写 `~/.claude/settings.json`），二选一。
- **statusLine 命令串形**：`python3 "<abs>/kdev_hud/__main__.py" statusline --workspace ${workspaceFolder}`
  （python 脚本路径**带引号**防空格；`${workspaceFolder}` 字面保留）。`<abs>` 运行时解析见上「关键事实 2」。
- **绝对路径不依赖 `python3 -m kdev_hud` 可导入**——靠 `__main__.py` 自举（关键事实 1）。
- **版本**：kdev-hud 0.2.0 → 0.3.0（plugin.json + CHANGELOG）。⚠️ G-004：用户须刷 marketplace + 重启 session 才激活新命令。
- **测试只用 tmp 路径**：绝不在测试或实现里写真实 `~/.claude/settings.json` 或仓库 `.claude/`。
- **AI 身份提交**：`git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit ...`（`-c` 的 key=value 不加引号）。
- **不 push、不 merge**。

---

## Task 1: setup.py 合并引擎 + `__main__.py` 自举 + cli.py `setup` 子命令（TDD 核心）

**目标**：实现把 statusLine 幂等合并进 settings.json 的纯函数层 + 修 `__main__.py` 让绝对路径可跑 +
接 `setup` 子命令。全 TDD，RED→GREEN。

### 新建 `plugins/kdev-hud/kdev_hud/setup.py`（纯函数、可单测）

定义 `class SetupError(Exception): pass` 和以下函数：

1. `resolve_plugin_root() -> Path`
   - `os.environ.get("CLAUDE_PLUGIN_ROOT")` 非空 → `Path(...)`；
   - 否则 → `Path(__file__).resolve().parent.parent`（含 `kdev_hud/` 的插件根）。

2. `build_statusline_command(plugin_root: Path) -> str`
   - 返回 `f'python3 "{plugin_root}/kdev_hud/__main__.py" statusline --workspace ${{workspaceFolder}}'`
   - 即：`python3 "<abs>/kdev_hud/__main__.py" statusline --workspace ${workspaceFolder}`（脚本路径带双引号）。

3. `is_kdev_statusline(statusline) -> bool`
   - falsy/None → False；`str` → `"kdev_hud" in statusline`；
   - `dict` → `isinstance(sl.get("command"), str) and "kdev_hud" in sl["command"]`；其他 → False。

4. `resolve_settings_path(scope: str, workspace=None) -> Path`
   - `scope == "user"` → `Path.home() / ".claude" / "settings.json"`；
   - 否则（"project"）→ `Path(workspace) / ".claude" / "settings.json"`。

5. `install_statusline(settings_path: Path, command: str, *, force: bool = False) -> dict`
   返回 `{"action": str, "path": str(settings_path), "backup": str|None}`。`action` ∈
   `created`/`updated`/`skipped_foreign`/`forced`。逻辑：
   ```
   payload = {"type": "command", "command": command}
   if not settings_path.exists():
       settings_path.parent.mkdir(parents=True, exist_ok=True)
       _write(settings_path, {"statusLine": payload})
       return {"action": "created", "path": str(settings_path), "backup": None}
   raw = settings_path.read_text(encoding="utf-8")
   try:
       data = json.loads(raw) if raw.strip() else {}
   except json.JSONDecodeError as e:
       raise SetupError(f"settings.json 不是合法 JSON，未改动：{e}")
   if not isinstance(data, dict):
       raise SetupError("settings.json 顶层不是 JSON 对象，未改动")
   existing = data.get("statusLine")
   if existing is None:
       data["statusLine"] = payload
       _write(settings_path, data)
       return {"action": "created", "path": str(settings_path), "backup": None}
   if is_kdev_statusline(existing):
       data["statusLine"] = payload          # 幂等刷新自己的路径
       _write(settings_path, data)
       return {"action": "updated", "path": str(settings_path), "backup": None}
   # 他者 statusLine
   if not force:
       return {"action": "skipped_foreign", "path": str(settings_path), "backup": None}  # 不写
   backup_path = settings_path.parent / (settings_path.name + ".bak")   # settings.json.bak
   backup_path.write_text(raw, encoding="utf-8")                        # 原样备份
   data["statusLine"] = payload
   _write(settings_path, data)
   return {"action": "forced", "path": str(settings_path), "backup": str(backup_path)}
   ```
   `_write(path, data)` = `path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")`
   （读后再 dump 保留原 key 顺序、不 clobber；新 statusLine append 到尾、已存在则原位更新）。

### 改 `plugins/kdev-hud/kdev_hud/__main__.py`（自举父目录）

在 `from kdev_hud.cli import main` **之前**插入：
```python
import sys
from pathlib import Path

# 按绝对路径直跑本文件时，sys.path[0] 是 kdev_hud/ 自身；`from kdev_hud.cli import main`
# 需父目录在 path 上。setup 写出的 statusLine 命令正是绝对路径直跑本文件，故此处自举
# 父目录（绕开 PYTHONPATH，FF-2）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kdev_hud.cli import main
```
保持 `if __name__ == "__main__": sys.exit(main())` 不变。

### 改 `plugins/kdev-hud/kdev_hud/cli.py`（接 `setup` 子命令）

- `import os`（若用到）+ `from kdev_hud import ... setup`。
- 新增 `cmd_setup(args)`：
  - `scope = "user" if getattr(args, "user", False) else "project"`；
  - `workspace = args.workspace or str(Path.cwd())`（project 用）；
  - `plugin_root = setup.resolve_plugin_root()`；`command = setup.build_statusline_command(plugin_root)`；
  - `settings_path = setup.resolve_settings_path(scope, workspace)`；
  - `try: result = setup.install_statusline(settings_path, command, force=args.force)`
    `except setup.SetupError as e: sys.stderr.write(str(e)+"\n"); return 1`；
  - 按 `result["action"]` 打印中文结果 + **重载提示**（如「✅ 已写入 <path>，重载/重启 session 后状态栏生效」；
    `skipped_foreign` 打印「未改动：已有他者 statusLine，加 `--force` 覆盖（会先备份 settings.json.bak）」；
    `forced` 打印备份路径）；`return 0`（`skipped_foreign` 也 `return 0`——非错误、信息性）。
- `build_parser()` 加：`psetup = sub.add_parser("setup", parents=[common], help="把 statusLine 接进 settings.json")`，
  其上 `--user`/`--project`（`add_mutually_exclusive_group()`，默认 project：用 `store_true` 各一个，缺省都 False → project），
  `--force`（`store_true`），`psetup.set_defaults(func=cmd_setup)`。

### 测试（先 RED 再 GREEN）

**新建 `plugins/kdev-hud/tests/test_setup.py`**（纯函数层）：
- `test_resolve_plugin_root_env`：monkeypatch `CLAUDE_PLUGIN_ROOT=/x/y` → 返回 `Path("/x/y")`。
- `test_resolve_plugin_root_fallback`：删除该 env → 返回值 `.name == "kdev-hud"` 或其下存在 `kdev_hud` 目录。
- `test_build_statusline_command`：含 `kdev_hud/__main__.py`、`statusline`、`${workspaceFolder}`，且脚本路径被双引号包裹。
- `test_is_kdev_statusline`：本插件 dict（command 含 kdev_hud）True、他者 dict False、本插件 str True、他者 str False、None False。
- `test_resolve_settings_path_project`：`== Path(ws)/".claude"/"settings.json"`。
- `test_resolve_settings_path_user`：`== Path.home()/".claude"/"settings.json"`。
- `test_install_creates_new_file`：tmp 下无文件 → action `created`、文件存在、parent 目录被建、内容 `statusLine.command` 含 kdev_hud。
- `test_install_merges_without_clobber`：预置 `{"theme":"dark","env":{"A":"1"}}`（无 statusLine）→ action `created`、
  `theme=="dark"` 且 `env=={"A":"1"}` 仍在、statusLine 已加。
- `test_install_bad_json_raises_and_no_write`：预置非法 JSON 文本 → `pytest.raises(setup.SetupError)`、文件字节**不变**。
- `test_install_skips_foreign_without_force`：预置他者 statusLine（command 不含 kdev_hud）→ action `skipped_foreign`、
  文件不变、无 `settings.json.bak`。
- `test_install_force_backs_up_and_overwrites_foreign`：同上 + `force=True` → action `forced`、`settings.json.bak` 存在且
  内容 == 原文本、现文件 statusLine 已是本插件的。
- `test_install_updates_own_idempotent`：预置本插件 statusLine + 其他键 `{"theme":"x"}` → action `updated`、`theme` 保留、
  无 `.bak`；再调一次仍 `updated`、文件里只有一个 statusLine。

**新建 `plugins/kdev-hud/tests/test_setup_cli.py`**（CLI 层，复用 `_run` 模式 `cli.main([...])`）：
- `test_cli_setup_project_writes_settings`：`cli.main(["setup","--project","--workspace",str(ws)])` → rc 0、
  `ws/.claude/settings.json` 存在、其 `statusLine.command` 含 `kdev_hud`、含 `statusline`。
- `test_cli_setup_idempotent`：跑两次 → 两次 rc 0、最终只一个 statusLine。
- `test_cli_setup_foreign_skipped_then_force`：预置他者 statusLine → 不带 force 跑：rc 0 且文件 statusLine 仍是他者、无 `.bak`；
  带 `--force` 跑：rc 0、`settings.json.bak` 出现、statusLine 变本插件。

**新建 `plugins/kdev-hud/tests/test_main_entrypoint.py`**（端到端证明自举生效）：
- `test_main_runs_by_absolute_path`：`MAIN_PY = Path(__file__).resolve().parents[1] / "kdev_hud" / "__main__.py"`；
  `subprocess.run([sys.executable, str(MAIN_PY), "statusline", "--workspace", str(tmp_path)], cwd=str(tmp_path),
  env={k:v for k,v in os.environ.items() if k != "PYTHONPATH"}, capture_output=True, text=True)` →
  `rc == 0` 且 `"KDev 团队" in stdout`（证明按绝对路径直跑能 import 成功——自举生效）。

### Task 1 验收
- `cd plugins/kdev-hud && python3 -m pytest -q` 全绿（含原有用例）。
- 走 superpowers:verification-before-completion 贴真实 pytest 输出。
- AI 身份 commit。

---

## Task 2: `/kdev-hud-setup` slash 命令 + README/CHANGELOG + version bump + WP-B 设计 note

依赖 Task 1 完成（引用其最终命令串 / 行为）。本 task 无新代码逻辑，但改 plugin.json/版本后须再跑一遍
`cd plugins/kdev-hud && python3 -m pytest -q` 确认全绿、且 plugin.json 仍是合法 JSON。

### 新建 `plugins/kdev-hud/commands/kdev-hud-setup.md`

- 仿兄弟命令（`commands/kdev-bugfix.md`）：frontmatter 仅 `description:`（中文，讲清「把 statusLine 接进
  settings.json、幂等、只动 statusLine 键、不 clobber、覆盖他者前备份」）。
- 正文：指导**主会话**用 `${CLAUDE_PLUGIN_ROOT}` 跑（项目级缺省）：
  ```
  python3 "${CLAUDE_PLUGIN_ROOT}/kdev_hud/__main__.py" setup --project
  ```
  跑完提示用户**重载/重启 session** 才生效；说明可选 `--user`（写 ~/.claude）/`--force`（覆盖他者，先备份
  `settings.json.bak`）；强调只动 `statusLine` 一个键、幂等、不覆盖其他配置。

### 改 `plugins/kdev-hud/README.md`
- 在「接 Claude Code statusLine」段附近加「## 一键接入」：首选 `/kdev-hud-setup`（或
  `python3 -m kdev_hud setup [--project|--user] [--force]`）；保留现手抄 JSON 片段作回退。
- 一句话点明：命令写的是**绝对路径**形（`__main__.py` 自举父目录绕开 PYTHONPATH），改完须刷 marketplace + 重启（G-004）。

### 改 `plugins/kdev-hud/CHANGELOG.md`
- 顶部加 `## 0.3.0 — 2026-06-18`：① `setup` 子命令 + `/kdev-hud-setup`：幂等合并 statusLine 进 settings.json
  （不 clobber、所有权检测、`--force` 前备份 `settings.json.bak`、`--project`/`--user` 作用域）；
  ② 修 `__main__.py` 自举父目录，使绝对路径直跑可 import（修 statusLine 装完不显示根因）。
  附 `> G-004：本次改了 plugin version/command，用户需刷 marketplace + 重启 session 才生效。`

### 改 `plugins/kdev-hud/.claude-plugin/plugin.json`
- `"version": "0.2.0"` → `"0.3.0"`。（可在 keywords 末加 `"setup"`，非必须。）保持合法 JSON。

### WP-B 设计 note（不实现，留坑）
- 在 README 末尾加「## WP-B（未实现）：statusLine 缓存包装 + 事件刷新」一小段，记 OMC 关键洞察：
  **CC v2.1.x 不持续重拉 statusLine（直到用户与面板交互）**，故未来应让 statusline 命令**快读缓存**
  （`.kdev/hud/statusline.<session>.txt`），HUD 计算由 hook/后台异步写缓存；可加 `--cached` 读缓存 +
  复用触发 hud.html 重生成的同一信号写缓存；并建议 `refreshInterval`。标 `TODO(WP-B)`，本次 defer。

### Task 2 验收
- `cd plugins/kdev-hud && python3 -m pytest -q` 仍全绿；plugin.json `python3 -c "import json;json.load(open(...))"` 通过。
- 实测一次 `python3 "<worktree>/plugins/kdev-hud/kdev_hud/__main__.py" setup --project --workspace <tmp>` 写出 settings.json 正确（tmp，不污染真实配置）。
- 走 superpowers:verification-before-completion 贴真实输出。AI 身份 commit。
