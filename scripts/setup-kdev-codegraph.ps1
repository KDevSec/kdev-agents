<#
.SYNOPSIS
  kdev-code-graph one-click install script (Windows / PowerShell)

.DESCRIPTION
  Performs 3 steps:
    1. add KDevSec/kdev-agents marketplace
    2. add Lum1104/Understand-Anything marketplace (UA dependency)
    3. install kdev-code-graph (UA auto-installed as dependency)

  Compatible with Windows 10 + PowerShell 5.1 default environment.
  Uses English comments to avoid UTF-8 encoding issues.

.EXAMPLE
  # Public repo - remote one-click
  iwr -useb https://raw.githubusercontent.com/KDevSec/kdev-agents/main/scripts/setup-kdev-codegraph.ps1 | iex

  # Private repo - clone first (raw URL not accessible)
  gh repo clone KDevSec/kdev-agents --depth 1; cd kdev-agents; ./scripts/setup-kdev-codegraph.ps1

  # Local clone
  ./scripts/setup-kdev-codegraph.ps1
#>

$ErrorActionPreference = 'Stop'

function Write-Step($msg) { Write-Host "`n> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  [ERR] $msg" -ForegroundColor Red; exit 1 }

Write-Step "Check claude CLI availability"
$claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
if ($null -eq $claudeCmd) {
    Write-Err "claude CLI not found. Please install Claude Code first (https://claude.com/claude-code)"
}
$claudeVersion = (& claude --version 2>&1 | Select-Object -First 1)
Write-Ok "claude $claudeVersion"

Write-Step "Add KDevSec/kdev-agents marketplace"
& claude plugin marketplace add KDevSec/kdev-agents
if ($LASTEXITCODE -ne 0) { Write-Err "marketplace add failed" }
Write-Ok "kdev-agents marketplace added"

Write-Step "Add Lum1104/Understand-Anything marketplace (UA dependency)"
& claude plugin marketplace add Lum1104/Understand-Anything
if ($LASTEXITCODE -ne 0) { Write-Err "marketplace add failed" }
Write-Ok "understand-anything marketplace added"

Write-Step "Install kdev-code-graph (UA auto-installed as dependency)"
& claude plugin install kdev-code-graph
if ($LASTEXITCODE -ne 0) { Write-Err "plugin install failed" }
Write-Ok "kdev-code-graph installed"

Write-Step "Done"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Restart Claude Code session to load the plugin"
Write-Host "  2. Run /kdev-codegraph-build in your target project to build the graph"
Write-Host "  3. ingestor runs via run.py with zero-install, no extra setup needed"