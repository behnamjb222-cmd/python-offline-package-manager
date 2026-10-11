# Builds dist\POPM\POPM.exe (one-folder app).  Usage:  .\scripts\build_windows.ps1 [-SkipTests]
# Needs Python 3.11+ on the BUILD machine.  The EXE contains POPM and Python/Qt runtime only -
# it does NOT contain any user package repository and does NOT install Python for the target machine.
param([switch]$SkipTests)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Test-Path .venv)) { & .\scripts\create_venv.ps1 }
$py = ".\.venv\Scripts\python.exe"
if (-not $SkipTests) { & $py -m pytest -q; if ($LASTEXITCODE -ne 0) { throw "tests failed" } }
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist)  { Remove-Item dist  -Recurse -Force }
& $py -m PyInstaller scripts\popm.spec --noconfirm --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
# --- test the output ---------------------------------------------------------
& .\dist\POPM\POPM.exe --selftest
if ($LASTEXITCODE -ne 0) { throw "EXE self-test failed" }
New-Item -ItemType Directory -Force dist\POPM\docs | Out-Null
Copy-Item README.md, README_FA.md, LICENSE dist\POPM\ -Force
Copy-Item docs\*.md dist\POPM\docs\ -Force
Write-Host "OK -> dist\POPM\POPM.exe   (zip the dist\POPM folder to distribute it)"
Write-Host "Layout:  POPM.exe + _internal\  = the application;  your package repositories live in %APPDATA%\POPM (or the folder you choose in Settings), NOT inside dist\."
