# Giftuner one-shot build script (Windows / PowerShell).
# Usage:
#     .\build.ps1
#
# Produces dist\Giftuner\Giftuner.exe together with all bundled
# runtime files (Qt, Pillow, bin/ ncnn-vulkan binaries, etc.).

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "==> Checking Python..." -ForegroundColor Cyan
python --version
if ($LASTEXITCODE -ne 0) { throw "Python not found on PATH" }

Write-Host "==> Installing build requirements..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

Write-Host "==> Cleaning previous build output..." -ForegroundColor Cyan
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist)  { Remove-Item -Recurse -Force dist }

Write-Host "==> Running PyInstaller..." -ForegroundColor Cyan
python -m PyInstaller --clean --noconfirm giftuner.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# Make sure output/ exists inside the distribution so first-time
# users see it right away.
$distOutput = Join-Path "dist\Giftuner" "output"
if (-not (Test-Path $distOutput)) {
    New-Item -ItemType Directory -Path $distOutput | Out-Null
}

Write-Host ""
Write-Host "✅ Build complete." -ForegroundColor Green
Write-Host "   Executable: dist\Giftuner\Giftuner.exe"
Write-Host "   Run package.ps1 to create a distributable ZIP."
