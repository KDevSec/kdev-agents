<#
.SYNOPSIS
  kdev-code-graph 一键安装脚本 (Windows / PowerShell)

.DESCRIPTION
  完成 3 步：
    1. add KDevSec/kdev-agents marketplace
    2. add Lum1104/Understand-Anything marketplace (UA 依赖)
    3. install kdev-code-graph（UA 自动连带）

  兼容 Windows 10 + PowerShell 5.1 默认环境。

.EXAMPLE
  ./scripts/setup-kdev-codegraph.ps1
  iwr -useb https://raw.githubusercontent.com/KDevSec/kdev-agents/main/scripts/setup-kdev-codegraph.ps1 | iex
#>

$ErrorActionPreference = 'Stop'

function Write-Step($msg) { Write-Host "`n▶ $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  ✗ $msg" -ForegroundColor Red; exit 1 }

Write-Step "检查 claude CLI 是否可用"
$claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
if ($null -eq $claudeCmd) {
    Write-Err "未找到 claude CLI。请先安装 Claude Code (https://claude.com/claude-code)"
}
$claudeVersion = (& claude --version 2>&1 | Select-Object -First 1)
Write-Ok "claude $claudeVersion"

Write-Step "添加 KDevSec/kdev-agents marketplace"
& claude plugin marketplace add KDevSec/kdev-agents
if ($LASTEXITCODE -ne 0) { Write-Err "marketplace add 失败" }
Write-Ok "kdev-agents marketplace 已添加"

Write-Step "添加 Lum1104/Understand-Anything marketplace (UA 依赖)"
& claude plugin marketplace add Lum1104/Understand-Anything
if ($LASTEXITCODE -ne 0) { Write-Err "marketplace add 失败" }
Write-Ok "understand-anything marketplace 已添加"

Write-Step "安装 kdev-code-graph（UA 自动连带）"
& claude plugin install kdev-code-graph
if ($LASTEXITCODE -ne 0) { Write-Err "plugin install 失败" }
Write-Ok "kdev-code-graph 已安装"

Write-Step "完成"
Write-Host ""
Write-Host "下一步："
Write-Host "  1. 重启 Claude Code 会话以加载 plugin"
Write-Host "  2. 在目标项目下跑 /kdev-codegraph-build 建图"
Write-Host "  3. ingestor 通过 run.py 零安装运行，无需额外步骤"
