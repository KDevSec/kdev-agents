# Windows python3 命令兼容性问题

## 问题

kdev-memory 插件的 hooks.json 使用 `python3` 命令执行 hook 脚本，但在 Windows 上失败。

**错误信息**：
```
UserPromptSubmit hook error
Failed with non-blocking status code: No stderr output
```

**根因**：
- Windows 上 `python3` 通常指向 Windows Store stub（`C:\Users\...\AppData\Local\Microsoft\WindowsApps\python3.exe`）
- stub 执行时返回 exit code 49，不是真正的 Python 解释器
- 实际 Python 安装使用 `python` 命令（如 `C:\Python314\python.exe`）

## 原因分析

v0.8.0 纯 Python 化重构时，将 `bash` 调用改为 `python3` 调用，目的是让 Windows 不再依赖 Git Bash。但作者在 Unix/Mac 环境开发，默认使用 `python3`，未考虑 Windows 上 `python3` 可能是无效 stub。

## 解决方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **A. python** | 简单直接，大多数平台可用 | 旧系统可能只有 python3 |
| **B. py launcher** | Windows 特有，可靠 | Unix/Mac 不可用 |
| **C. wrapper 脚本** | 自动选择，覆盖边缘情况 | 多一个文件，稍复杂 |
| **D. polyglot wrapper** | 单文件跨平台，优雅 | 需要维护 |

## 采用方案：Polyglot Wrapper（方案 D）

参考 `superpowers` 插件的 `run-hook.cmd`，创建单文件 polyglot wrapper：

**文件**：`hooks/run-python-hook.cmd`

```cmd
: << 'PYBLOCK'
@echo off
REM Windows: prefers py -3, then python, then python3

set "SCRIPT=%~1"
if "%SCRIPT%"=="" exit /b 0

set "HOOK_DIR=%~dp0"

REM Primary: py -3 (Windows Python launcher, guaranteed Python 3)
py -3 "%HOOK_DIR%%SCRIPT%" %2 %3 %4 %5 %6 %7 %8 %9
if %ERRORLEVEL% equ 0 exit /b 0

REM Secondary: python (common on most Windows setups)
python "%HOOK_DIR%%SCRIPT%" %2 %3 %4 %5 %6 %7 %8 %9
if %ERRORLEVEL% equ 0 exit /b 0

REM Fallback: python3 (may be Windows Store stub)
python3 "%HOOK_DIR%%SCRIPT%" %2 %3 %4 %5 %6 %7 %8 %9
exit /b %ERRORLEVEL%

PYBLOCK
# Unix/Mac: use python3 first, fall back to python
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="$1"
shift
python3 "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@" 2>/dev/null || python "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@"
```

**优先级说明**：

| 平台 | 优先级 | 命令 | 原因 |
|------|--------|------|------|
| Windows | 1 | `py -3` | Python launcher，明确指定 Python 3，避免 Python 2 混淆 |
| Windows | 2 | `python` | 常见安装，但可能指向 Python 2（旧系统） |
| Windows | 3 | `python3` | 可能是 Windows Store stub（exit 49） |
| Unix/Mac | 1 | `python3` | 现代标准，Python 3 专用 |
| Unix/Mac | 2 | `python` | Fallback，现代系统通常也指向 Python 3 |

**为什么用 `py -3`**：
- Windows Python launcher (`py.exe`) 是官方工具，随 Python 安装
- `py -3` 明确指定 Python 3.x，即使系统有 Python 2 也不会混淆
- 比 `python` 更可靠，比 `python3` 更安全（后者可能是 stub）

**原理**：
- Windows cmd.exe 执行 `@echo off` 到 `PYBLOCK` 之间的 batch 代码
- Unix bash 执行 `PYBLOCK` 之后的 shell 代码
- `: << 'PYBLOCK'` 在 bash 中是 heredoc no-op

**hooks.json 调用方式**：
```json
{
  "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-python-hook.cmd\" session-start-brief.py"
}
```

## 测试验证

| 环境 | 命令 | 结果 |
|------|------|------|
| Windows cmd | `run-python-hook.cmd user-prompt-trigger.py` | Exit code 0 ✓ |
| Git Bash | `bash run-python-hook.cmd user-prompt-trigger.py` | JSON 输出 ✓ |

## 版本历史

- v0.8.0：纯 Python 化，引入 `python3` 调用（Windows 失败）
- v0.8.2：新增 polyglot wrapper，修复 Windows 兼容性

## 相关

- 发现日期：2026-04-27
- 修复日期：2026-04-27
- 影响范围：所有 Windows 用户
- 参考：`superpowers` 插件的 `run-hook.cmd` polyglot 设计