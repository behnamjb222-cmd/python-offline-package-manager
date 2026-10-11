# Creates a development virtual environment with everything needed to run, test and build POPM.
# Usage (PowerShell, from the project root):   .\scripts\create_venv.ps1
$ErrorActionPreference = "Stop"
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py -3.12" } else { "python" }
Invoke-Expression "$py -m venv .venv"
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Write-Host "Done. Activate with:  .\.venv\Scripts\Activate.ps1   then run:  python main.py"
