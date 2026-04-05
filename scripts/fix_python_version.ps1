# fix_python_version.ps1
# Finds a compatible Python (3.11-3.13) or installs 3.11, then pins it for this project

Write-Host ""
Write-Host "Checking available Python versions..." -ForegroundColor Cyan

# ?? Search for any Python 3.11, 3.12, or 3.13 already installed ??????????????
$compatiblePython = $null
$searchPaths = @(
    # py launcher (installed with any Python on Windows)
    # Chocolatey
    "C:\Python313\python.exe",
    "C:\Python312\python.exe",
    "C:\Python311\python.exe",
    # Windows Store / official installer
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    # pyenv-win
    "$env:USERPROFILE\.pyenv\pyenv-win\versions\3.13.0\python.exe",
    "$env:USERPROFILE\.pyenv\pyenv-win\versions\3.12.0\python.exe",
    "$env:USERPROFILE\.pyenv\pyenv-win\versions\3.11.0\python.exe",
    # Choco tools
    "C:\tools\python313\python.exe",
    "C:\tools\python312\python.exe",
    "C:\tools\python311\python.exe"
)

# Try py launcher first (most reliable on Windows)
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    Write-Host "  py launcher found - checking installed versions:" -ForegroundColor Gray
    $versions = py --list 2>&1
    Write-Host $versions -ForegroundColor Gray

    foreach ($ver in @("3.13", "3.12", "3.11")) {
        try {
            $result = py "-$ver" -c "import sys; print(sys.executable)" 2>&1
            if ($LASTEXITCODE -eq 0 -and $result -match "python") {
                $compatiblePython = $result.Trim()
                Write-Host "  [FOUND] Python $ver at: $compatiblePython" -ForegroundColor Green
                break
            }
        } catch {}
    }
}

# Fall back to path search
if (-not $compatiblePython) {
    foreach ($path in $searchPaths) {
        if (Test-Path $path) {
            $ver = & $path -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1
            if ($ver -match "^3\.(11|12|13)$") {
                $compatiblePython = $path
                Write-Host "  [FOUND] Python $ver at: $path" -ForegroundColor Green
                break
            }
        }
    }
}

# ?? If nothing found, install Python 3.11 via Chocolatey ?????????????????????
if (-not $compatiblePython) {
    Write-Host ""
    Write-Host "  No compatible Python found. Installing Python 3.11 via Chocolatey..." -ForegroundColor Yellow
    Write-Host "  (Python 3.14 will remain - we just add 3.11 alongside it)" -ForegroundColor Gray

    # Check if choco is available
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "  Chocolatey not found. Installing Python 3.11 manually." -ForegroundColor Yellow
        Write-Host "  Downloading Python 3.11.9 installer..." -ForegroundColor Gray
        $installer = "$env:TEMP\python-3.11.9-amd64.exe"
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $installer
        Write-Host "  Running installer (adds to PATH)..." -ForegroundColor Gray
        Start-Process -FilePath $installer -ArgumentList "/quiet InstallAllUsers=0 PrependPath=0 Include_launcher=1" -Wait
        Remove-Item $installer -ErrorAction SilentlyContinue
    } else {
        choco install python311 -y --no-progress
    }

    # Find it now
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        try {
            $result = py "-3.11" -c "import sys; print(sys.executable)" 2>&1
            if ($LASTEXITCODE -eq 0) {
                $compatiblePython = $result.Trim()
                Write-Host "  [OK] Python 3.11 installed at: $compatiblePython" -ForegroundColor Green
            }
        } catch {}
    }

    if (-not $compatiblePython) {
        $fallback = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
        if (Test-Path $fallback) { $compatiblePython = $fallback }
    }
}

if (-not $compatiblePython) {
    Write-Host ""
    Write-Host "  [ERROR] Could not find or install a compatible Python." -ForegroundColor Red
    Write-Host "  Please install Python 3.11 manually from https://python.org/downloads" -ForegroundColor Yellow
    Write-Host "  Then re-run this script." -ForegroundColor Yellow
    exit 1
}

# ?? Pin this Python for the poetry project ????????????????????????????????????
Write-Host ""
Write-Host "  Pinning project to: $compatiblePython" -ForegroundColor Cyan
Set-Location (Split-Path $PSCommandPath -Parent | Split-Path -Parent)

poetry env use "$compatiblePython"

if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] poetry env use failed." -ForegroundColor Red
    exit 1
}

# ?? Run install ???????????????????????????????????????????????????????????????
Write-Host ""
Write-Host "  Running poetry install..." -ForegroundColor Cyan
poetry install

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=======================================================" -ForegroundColor Green
    Write-Host "  SUCCESS. Virtual environment is ready." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Verify with:" -ForegroundColor Cyan
    Write-Host "    poetry run python --version" -ForegroundColor Gray
    Write-Host "    poetry run pytest app/tests/ -v" -ForegroundColor Gray
    Write-Host "=======================================================" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] poetry install failed. See errors above." -ForegroundColor Red
}
