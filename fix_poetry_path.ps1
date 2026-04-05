# fix_poetry_path.ps1
# Run this in PowerShell (no admin needed) to fix the poetry PATH issue
# Usage: .\fix_poetry_path.ps1

Write-Host ""
Write-Host "Diagnosing Poetry installation..." -ForegroundColor Cyan

# -- Step 1: Find where poetry.exe actually lives ------------------------------
$poetryExe = $null
$searchPaths = @(
    # pip install poetry location (Python 3.x Scripts)
    "$env:LOCALAPPDATA\Programs\Python\Python311\Scripts\poetry.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts\poetry.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python310\Scripts\poetry.exe",
    # Chocolatey Python
    "C:\Python311\Scripts\poetry.exe",
    "C:\Python312\Scripts\poetry.exe",
    "C:\Python310\Scripts\poetry.exe",
    # pipx location
    "$env:USERPROFILE\.local\bin\poetry.exe",
    # Official installer location
    "$env:APPDATA\Python\Scripts\poetry.exe",
    "$env:USERPROFILE\.poetry\bin\poetry.exe",
    # Common choco paths
    "C:\tools\python3\Scripts\poetry.exe",
    "C:\ProgramData\chocolatey\lib\python3\tools\Scripts\poetry.exe"
)

foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        $poetryExe = $path
        Write-Host "  [FOUND] Poetry at: $path" -ForegroundColor Green
        break
    }
}

# If not found via known paths, do a broader search
if (-not $poetryExe) {
    Write-Host "  Scanning for poetry.exe..." -ForegroundColor Yellow
    $found = Get-ChildItem -Path "$env:LOCALAPPDATA", "$env:APPDATA", "$env:USERPROFILE", "C:\Python*", "C:\tools" `
        -Filter "poetry.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) {
        $poetryExe = $found.FullName
        Write-Host "  [FOUND] Poetry at: $poetryExe" -ForegroundColor Green
    }
}

# -- Step 2: If still not found, install it properly --------------------------
if (-not $poetryExe) {
    Write-Host ""
    Write-Host "  Poetry not found. Installing via pip..." -ForegroundColor Yellow
    
    # Make sure pip works
    $pipOk = (Get-Command pip -ErrorAction SilentlyContinue) -or (Get-Command pip3 -ErrorAction SilentlyContinue)
    if (-not $pipOk) {
        Write-Host "  [ERROR] pip not found either. Make sure Python is installed." -ForegroundColor Red
        Write-Host "  Run: choco install python311 -y" -ForegroundColor Gray
        exit 1
    }
    
    pip install poetry
    
    # Search again after install
    $found = Get-ChildItem -Path "$env:LOCALAPPDATA", "$env:APPDATA", "$env:USERPROFILE" `
        -Filter "poetry.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) {
        $poetryExe = $found.FullName
        Write-Host "  [OK] Poetry installed at: $poetryExe" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Install completed but poetry.exe not found. Try restarting PowerShell." -ForegroundColor Red
        exit 1
    }
}

# -- Step 3: Add the Scripts folder to PATH permanently -----------------------
$poetryDir = Split-Path $poetryExe -Parent
Write-Host ""
Write-Host "  Poetry directory: $poetryDir" -ForegroundColor Cyan

$currentUserPath = [System.Environment]::GetEnvironmentVariable("Path", "User")

if ($currentUserPath -notlike "*$poetryDir*") {
    Write-Host "  Adding $poetryDir to user PATH..." -ForegroundColor Yellow
    $newPath = $currentUserPath.TrimEnd(";") + ";" + $poetryDir
    [System.Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "  [OK] PATH updated permanently for your user account" -ForegroundColor Green
} else {
    Write-Host "  [OK] $poetryDir already in PATH" -ForegroundColor Green
}

# Also update PATH for the current session immediately
$env:Path = $env:Path + ";" + $poetryDir

# -- Step 4: Verify ------------------------------------------------------------
Write-Host ""
Write-Host "  Verifying..." -ForegroundColor Cyan
try {
    $version = & $poetryExe --version 2>&1
    Write-Host "  [OK] $version" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Could not run poetry: $_" -ForegroundColor Red
}

# -- Step 5: Configure poetry to create venvs inside project folder ------------
Write-Host ""
Write-Host "  Configuring poetry (venv inside project)..." -ForegroundColor Cyan
& $poetryExe config virtualenvs.in-project true
Write-Host "  [OK] poetry will create .venv inside the project directory" -ForegroundColor Green

# -- Step 6: Run poetry install -----------------------------------------------
Write-Host ""
Write-Host "  Running: poetry install" -ForegroundColor Cyan
Write-Host "  (This will take 2-4 minutes on first run)" -ForegroundColor Gray
Write-Host ""
Set-Location (Split-Path $PSCommandPath -Parent | Split-Path -Parent)
& $poetryExe install

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "  DONE. Poetry is installed and dependencies are set." -ForegroundColor Green
Write-Host ""
Write-Host "  For future PowerShell sessions, poetry will work" -ForegroundColor Green
Write-Host "  automatically. No need to run this script again." -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "    poetry run pytest app/tests/ -v     (run tests)" -ForegroundColor Gray
Write-Host "    docker compose up -d                (start services)" -ForegroundColor Gray
Write-Host "=======================================================" -ForegroundColor Green
