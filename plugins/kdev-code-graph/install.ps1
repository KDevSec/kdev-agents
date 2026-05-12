<#
.SYNOPSIS
  kdev-code-graph install/validation script (Windows / PowerShell)

.DESCRIPTION
  Checks Node/Python, validates UA marketplace installation, verifies ingestor
  zero-install path, and optionally sets up dev venv to run tests.

  Compatible with Windows 10 + PowerShell 5.1.
  Uses English comments to avoid UTF-8 encoding issues.
#>

$ErrorActionPreference = 'Stop'

$PluginRoot = $PSScriptRoot
$IngestorDir = Join-Path $PluginRoot 'ingestor'

function Write-Step($msg) { Write-Host "`n> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  [ERR] $msg" -ForegroundColor Red; exit 1 }

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

Write-Step "Check Node.js (>= 22)"
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($null -eq $nodeCmd) { Write-Err "node not found. Please install Node.js 22+" }
$nodeMajor = & node -p "process.versions.node.split('.')[0]"
if ([int]$nodeMajor -lt 22) { Write-Err "Node $nodeMajor < 22" }
Write-Ok "node $(& node --version)"

Write-Step "Check pnpm (>= 10)"
$pnpmCmd = Get-Command pnpm -ErrorAction SilentlyContinue
if ($null -eq $pnpmCmd) {
    Write-Warn2 "pnpm not installed; trying corepack..."
    try {
        & corepack enable pnpm 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Warn2 "corepack requires admin rights. Please run as Administrator or install pnpm manually:"
            Write-Host "    npm install -g pnpm"
            Write-Host "    (or run this script in an elevated PowerShell)"
        } else {
            & corepack prepare pnpm@latest --activate
            $pnpmCmd = Get-Command pnpm -ErrorAction SilentlyContinue
        }
    } catch {
        Write-Warn2 "corepack failed. Please install pnpm manually: npm install -g pnpm"
    }
}
if ($null -ne $pnpmCmd) {
    Write-Ok "pnpm $(& pnpm --version)"
} else {
    Write-Warn2 "pnpm not available - UA may need manual pnpm install"
}

Write-Step "Check Python (>= 3.11)"
$pyCmd = Get-PythonCmd
if ($null -eq $pyCmd) {
    Write-Err "Python 3.11+ not found. Please install Python 3.11 or higher (https://python.org)"
}
Write-Ok "python: $pyCmd"

Write-Step "Validate dependency plugin: Understand-Anything (UA)"
$uaCache = Join-Path $HOME '.claude\plugins\cache\understand-anything'
if (Test-Path $uaCache) {
    Write-Ok "UA installed"
} else {
    Write-Warn2 "UA not installed"
    Write-Host ""
    Write-Host "  Normally UA is auto-installed as kdev-code-graph dependency"
    Write-Host "  (via plugin.json dependencies + marketplace allowCrossMarketplaceDependenciesOn)"
    Write-Host ""
    Write-Host "  If you are doing local dev / did not use /plugin install, add UA manually:"
    Write-Host "    /plugin marketplace add Lum1104/Understand-Anything"
    Write-Host "    /plugin install understand-anything"
}

Write-Step "kdev-ingestor zero-install validation"
$runPy = Join-Path $IngestorDir 'run.py'
$pyParts = $pyCmd -split ' '
$pyArgs = if ($pyParts.Count -gt 1) { $pyParts[1..($pyParts.Count-1)] + @($runPy, '--help') } else { @($runPy, '--help') }
& $pyParts[0] $pyArgs *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Ok "ingestor zero-install works ($pyCmd run.py ...)"
} else {
    Write-Err "ingestor zero-install failed - check if $runPy exists"
}

Write-Step "(Optional) dev venv test run"
$venvPath = Join-Path $IngestorDir '.venv'
if (Test-Path (Join-Path $venvPath 'Scripts\Activate.ps1')) {
    Push-Location $IngestorDir
    & "$venvPath\Scripts\Activate.ps1"
    & pytest --quiet
    if ($LASTEXITCODE -eq 0) { Write-Ok "ingestor tests passed (dev venv)" } else { Write-Warn2 "ingestor tests failed (dev venv)" }
    Pop-Location
} else {
    Write-Warn2 "dev venv not installed - not needed for production. To run tests:"
    Write-Host "    cd $IngestorDir"
    Write-Host "    & $pyCmd -m venv .venv"
    Write-Host "    .\.venv\Scripts\Activate.ps1"
    Write-Host "    pip install -e `".[dev]`""
    Write-Host "    pytest"
}

Write-Step "(Optional) UA contract test"
Push-Location $PluginRoot
$contractArgs = if ($pyParts.Count -gt 1) { $pyParts[1..($pyParts.Count-1)] + @('-m', 'pytest', 'tests/contract', '--quiet') } else { @('-m', 'pytest', 'tests/contract', '--quiet') }
& $pyParts[0] $contractArgs
if ($LASTEXITCODE -ne 0) {
    Write-Warn2 "contract test failed or skipped - see skills/_ua_adapter/SKILL.md"
}
Pop-Location

Write-Step "Done"
Write-Host "Next step: cd <your-project>; run /kdev-codegraph-build in Claude Code"