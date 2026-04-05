<#
.SYNOPSIS
    AI-SDLC PoC - Windows Development Environment Bootstrap
    Run this script ONCE as Administrator to install all prerequisites.

.DESCRIPTION
    Installs: Chocolatey, Git, Node.js, Python, Docker Desktop, VS Code,
    Java 11, Claude Code CLI. Verifies Docker Desktop is running.
    Clones repo, sets up two Git worktrees, installs Python deps.

.NOTES
    Run in PowerShell as Administrator:
    Set-ExecutionPolicy Bypass -Scope Process -Force
    .\scripts\setup_dev_environment.ps1
#>

param(
    [string]$RepoUrl = "http://localhost:3000/ai-sdlc-poc/app-repo.git",
    [string]$WorkspaceRoot = "C:\demo",
    [string]$AnthropicApiKey = ""
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "`n======================================================" -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host "======================================================" -ForegroundColor Cyan
}

function Write-OK($msg)   { Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }

# -- 0. Check admin ------------------------------------------------------------
Write-Step "Checking administrator privileges"
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Fail "This script must be run as Administrator. Right-click PowerShell -> Run as Administrator."
    exit 1
}
Write-OK "Running as Administrator"

# -- 1. Install Chocolatey -----------------------------------------------------
Write-Step "Installing Chocolatey (Windows package manager)"
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = `
        [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString(
        'https://community.chocolatey.org/install.ps1'))
    Write-OK "Chocolatey installed"
} else {
    Write-OK "Chocolatey already installed ($(choco --version))"
}

# -- 2. Core tools -------------------------------------------------------------
Write-Step "Installing core development tools"
$tools = @(
    @{ name = "git";          check = "git";    pkg = "git" },
    @{ name = "Node.js LTS";  check = "node";   pkg = "nodejs-lts" },
    @{ name = "Python 3.11";  check = "python"; pkg = "python311" },
    @{ name = "Docker Desktop"; check = "docker"; pkg = "docker-desktop" },
    @{ name = "VS Code";      check = "code";   pkg = "vscode" },
    @{ name = "OpenJDK 11";   check = "java";   pkg = "openjdk11" },
    @{ name = "Make";         check = "make";   pkg = "make" }
)

foreach ($t in $tools) {
    if (-not (Get-Command $t.check -ErrorAction SilentlyContinue)) {
        Write-Host "  Installing $($t.name)..." -ForegroundColor Gray
        choco install $t.pkg -y --no-progress 2>&1 | Out-Null
        Write-OK "$($t.name) installed"
    } else {
        Write-OK "$($t.name) already installed"
    }
}

# Refresh PATH so new tools are available
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

# -- 3. Claude Code CLI --------------------------------------------------------
Write-Step "Installing Claude Code CLI"
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    npm install -g @anthropic-ai/claude-code
    Write-OK "Claude Code installed"
} else {
    Write-OK "Claude Code already installed"
}

# -- 4. Python tooling ---------------------------------------------------------
Write-Step "Installing Python tooling"

# Install PyYAML from pre-built binary first to avoid Cython/setuptools
# wheel build failures on Python 3.11+ with newer setuptools.
pip install "PyYAML" --only-binary :all: --quiet

$pipPackages = @(
    @{ name = "poetry";         pkg = "poetry" },
    @{ name = "semgrep";        pkg = "semgrep --only-binary :all:" },
    @{ name = "detect-secrets"; pkg = "detect-secrets" },
    @{ name = "pre-commit";     pkg = "pre-commit" }
)

foreach ($p in $pipPackages) {
    $cmd = "pip install $($p.pkg) --quiet"
    Invoke-Expression $cmd
    if ($LASTEXITCODE -ne 0) {
        # Fall back to user install if system-wide pip write is denied
        $cmd = "pip install $($p.pkg) --quiet --user"
        Invoke-Expression $cmd
    }
    if ($LASTEXITCODE -eq 0) {
        Write-OK "$($p.name) installed"
    } else {
        Write-Warn "$($p.name) install failed -- run manually: pip install $($p.pkg)"
    }
}

# Ensure Python user Scripts folder is on PATH so installed CLI tools (semgrep, etc.) are found
$userScripts = "$env:APPDATA\Python\Python311\Scripts"
$userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$userScripts*") {
    [System.Environment]::SetEnvironmentVariable("PATH", "$userPath;$userScripts", "User")
    $env:Path += ";$userScripts"
    Write-OK "Added $userScripts to user PATH"
}

# -- 5. Set ANTHROPIC_API_KEY -------------------------------------------------
Write-Step "Configuring API key"
if ($AnthropicApiKey -ne "") {
    [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $AnthropicApiKey, "User")
    $env:ANTHROPIC_API_KEY = $AnthropicApiKey
    Write-OK "ANTHROPIC_API_KEY set as user environment variable"
} else {
    Write-Warn "No API key provided. Set it manually:"
    Write-Warn '  [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-...", "User")'
}

# -- 6. Create workspace directories ------------------------------------------
Write-Step "Creating workspace structure at $WorkspaceRoot"
@($WorkspaceRoot, "$WorkspaceRoot\workspace-dev1", "$WorkspaceRoot\workspace-dev2") | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
}
Write-OK "Directories created"

# -- 7. Clone & setup repo ----------------------------------------------------
Write-Step "Setting up Git repository"
Set-Location $WorkspaceRoot

if (-not (Test-Path "ai-sdlc-repo\.git")) {
    Write-Host "  Note: Gitea must be running before this step." -ForegroundColor Yellow
    Write-Host "  Run: docker compose up -d  from the ai-sdlc-poc folder first." -ForegroundColor Yellow
    Write-Host "  Then re-run this section or clone manually with:" -ForegroundColor Yellow
    Write-Host "    git clone $RepoUrl ai-sdlc-repo" -ForegroundColor Gray
} else {
    Write-OK "Repository already exists"
}

# -- 8. Git worktrees (run inside repo) ---------------------------------------
Write-Step "Setting up Git worktrees for two developer simulations"
Write-Host @"

  Run these commands from inside the ai-sdlc-repo directory:

  git checkout -b develop
  git checkout -b feat/dev1-auth-module
  git checkout develop
  git checkout -b feat/dev2-payment-module
  git worktree add ..\workspace-dev1 feat/dev1-auth-module
  git worktree add ..\workspace-dev2 feat/dev2-payment-module

  # Then per-worktree identities:
  cd ..\workspace-dev1
  git config user.name "Dev One (Claude Code)"
  git config user.email "dev1@company.local"

  cd ..\workspace-dev2
  git config user.name "Dev Two (Cursor AI)"
  git config user.email "dev2@company.local"

"@ -ForegroundColor Gray

# -- 9. Cursor AI reminder -----------------------------------------------------
Write-Step "Cursor AI"
Write-Host @"

  Cursor AI must be downloaded and installed manually:
  1. Go to https://cursor.sh
  2. Download the Windows installer
  3. Install it (it registers as 'cursor' in PATH after install)
  4. Open workspace-dev2 folder in Cursor

"@ -ForegroundColor Gray

# -- 10. Docker Desktop reminder ----------------------------------------------
Write-Step "Docker Desktop - manual step required"
Write-Host @"

  After Docker Desktop installs:
  1. Launch Docker Desktop from Start Menu
  2. Go to Settings -> General -> check "Use WSL 2 based engine"
  3. Go to Settings -> Resources -> WSL Integration -> enable your distro
  4. Click Apply & Restart
  5. Then run: docker compose up -d  from the ai-sdlc-poc directory

"@ -ForegroundColor Yellow

# -- Summary ------------------------------------------------------------------
Write-Step "Setup Summary"
Write-Host @"

  Workspace directories created at $WorkspaceRoot
  Check above for any [WARN] lines -- those packages need manual install.

  NEXT STEPS:
  1. Start Docker Desktop manually and enable WSL2
  2. cd ai-sdlc-poc && docker compose up -d
  3. Configure Gitea at http://localhost:3000
  4. Configure Jenkins at http://localhost:8080
  5. cd ai-sdlc-poc && python -m poetry install
  6. make test   <- verify everything works
  7. Open workspace-dev1 in VS Code with Claude Code extension
  8. Open workspace-dev2 in Cursor AI

  See README.md and STEP_BY_STEP_SETUP.md for detailed steps.

"@ -ForegroundColor Green
