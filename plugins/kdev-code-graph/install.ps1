<#
.SYNOPSIS
  kdev-code-graph 安装/校验脚本 (Windows / PowerShell)

.DESCRIPTION
  检查 Node/Python，校验 UA marketplace 安装，验证 ingestor 零安装路径，
  并可选 install dev venv 跑测试。

  兼容 Windows 10 + PowerShell 5.1。
#>

$ErrorActionPreference = 'Stop'

$PluginRoot = $PSScriptRoot
$IngestorDir = Join-Path $PluginRoot 'ingestor'

function Write-Step($msg) { Write-Host "`n▶ $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  ✗ $msg" -ForegroundColor Red; exit 1 }

# Pick a Python launcher: py -3 (Windows recommended) > python > python3
function Get-PythonCmd {
    foreach ($candidate in @('py -3', 'python', 'python3')) {
        $parts = $candidate -split ' '
        $exe = Get-Command $parts[0] -ErrorAction SilentlyContinue
        if ($null -ne $exe) {
            try {
                $ver = & $parts[0] $parts[1..($parts.Count-1)] --version 2>&1
                if ($ver -match 'Python 3\.(\d+)') {
                    $minor = [int]$Matches[1]
                    if ($minor -ge 11) {
                        return $candidate
                    }
                }
            } catch {}
        }
    }
    return $null
}

Write-Step "检查 Node.js (>= 22)"
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($null -eq $nodeCmd) { Write-Err "未找到 node。请安装 Node.js 22+" }
$nodeMajor = & node -p "process.versions.node.split('.')[0]"
if ([int]$nodeMajor -lt 22) { Write-Err "Node $nodeMajor < 22" }
Write-Ok "node $(& node --version)"

Write-Step "检查 pnpm (>= 10)"
$pnpmCmd = Get-Command pnpm -ErrorAction SilentlyContinue
if ($null -eq $pnpmCmd) {
    Write-Warn2 "pnpm 未安装；尝试用 corepack..."
    & corepack enable pnpm 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Err "请手动安装 pnpm" }
    & corepack prepare pnpm@latest --activate
}
Write-Ok "pnpm $(& pnpm --version)"

Write-Step "检查 Python (>= 3.11)"
$pyCmd = Get-PythonCmd
if ($null -eq $pyCmd) {
    Write-Err "未找到 Python 3.11+。请安装 Python 3.11 或更高 (https://python.org)"
}
Write-Ok "python: $pyCmd"

Write-Step "校验依赖 plugin: Understand-Anything (UA)"
$uaCache = Join-Path $HOME '.claude\plugins\cache\understand-anything'
if (Test-Path $uaCache) {
    Write-Ok "UA 已装"
} else {
    Write-Warn2 "UA 未装"
    Write-Host ""
    Write-Host "  正常情况下 UA 会作为 kdev-code-graph 的依赖自动安装"
    Write-Host "  （通过 plugin.json dependencies + marketplace allowCrossMarketplaceDependenciesOn）"
    Write-Host ""
    Write-Host "  如果你是本地开发 / 未通过 /plugin install 安装，请手动加 UA marketplace："
    Write-Host "    /plugin marketplace add Lum1104/Understand-Anything"
    Write-Host "    /plugin install understand-anything"
}

Write-Step "kdev-ingestor 零安装验证"
$runPy = Join-Path $IngestorDir 'run.py'
$pyParts = $pyCmd -split ' '
$pyArgs = if ($pyParts.Count -gt 1) { $pyParts[1..($pyParts.Count-1)] + @($runPy, '--help') } else { @($runPy, '--help') }
& $pyParts[0] $pyArgs *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Ok "ingestor 可零安装运行 ($pyCmd run.py ...)"
} else {
    Write-Err "ingestor 零安装路径失败 — 检查 $runPy 是否存在"
}

Write-Step "（可选）dev venv 跑测试"
$venvPath = Join-Path $IngestorDir '.venv'
if (Test-Path (Join-Path $venvPath 'Scripts\Activate.ps1')) {
    Push-Location $IngestorDir
    & "$venvPath\Scripts\Activate.ps1"
    & pytest --quiet
    if ($LASTEXITCODE -eq 0) { Write-Ok "ingestor 测试通过 (dev venv)" } else { Write-Warn2 "ingestor 测试失败 (dev venv)" }
    Pop-Location
} else {
    Write-Warn2 "未安装 dev venv — 生产用不需要。若需跑测试："
    Write-Host "    cd $IngestorDir; & $pyCmd -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -e `".[dev]`"; pytest"
}

Write-Step "（可选）跑 UA contract test"
Push-Location $PluginRoot
$contractArgs = if ($pyParts.Count -gt 1) { $pyParts[1..($pyParts.Count-1)] + @('-m', 'pytest', 'tests/contract', '--quiet') } else { @('-m', 'pytest', 'tests/contract', '--quiet') }
& $pyParts[0] $contractArgs
if ($LASTEXITCODE -ne 0) {
    Write-Warn2 "contract test 失败 — 见 skills/_ua_adapter/SKILL.md"
}
Pop-Location

Write-Step "完成"
Write-Host "下一步：cd <project>; 在 Claude Code 中跑 /kdev-codegraph-build"
