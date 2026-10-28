# Package dist\Giftuner\ into a distributable ZIP.
# Usage:
#     .\package.ps1               # uses version from giftuner\__init__.py
#     .\package.ps1 -Version 0.2.0

param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not (Test-Path "dist\Giftuner\Giftuner.exe")) {
    throw "Build output missing. Run .\build.ps1 first."
}

if ([string]::IsNullOrEmpty($Version)) {
    $initPy = Get-Content "giftuner\__init__.py" -Raw
    if ($initPy -match '__version__\s*=\s*"([^"]+)"') {
        $Version = $Matches[1]
    } else {
        $Version = "dev"
    }
}

$zipName  = "Giftuner-v$Version-windows.zip"
$zipPath  = Join-Path "dist" $zipName

if (Test-Path $zipPath) { Remove-Item -Force $zipPath }

Write-Host "==> Creating $zipName ..." -ForegroundColor Cyan
Compress-Archive -Path "dist\Giftuner\*" -DestinationPath $zipPath -CompressionLevel Optimal

$sizeMB = "{0:N1}" -f ((Get-Item $zipPath).Length / 1MB)
Write-Host ""
Write-Host "✅ Package ready: $zipPath  ($sizeMB MB)" -ForegroundColor Green
