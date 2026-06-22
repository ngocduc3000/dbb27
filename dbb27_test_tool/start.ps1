# ============================================================
#  DBB-27 Serial Test Tool - tu khoi dong server (PowerShell)
#  Chay: chuot phai > Run with PowerShell, hoac: .\start.ps1
# ============================================================
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$Port = 8000
$Py = ".venv\Scripts\python.exe"

# --- Lan dau: tao venv + cai dependencies ---
if (-not (Test-Path $Py)) {
    Write-Host "[SETUP] Tao moi truong .venv lan dau..." -ForegroundColor Cyan
    if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv .venv } else { python -m venv .venv }
    if (-not (Test-Path $Py)) {
        Write-Host "[LOI] Khong tao duoc .venv. Hay cai Python 3.10+ tu python.org." -ForegroundColor Red
        Read-Host "Nhan Enter de thoat"; exit 1
    }
    Write-Host "[SETUP] Cai dat thu vien..." -ForegroundColor Cyan
    & $Py -m pip install --upgrade pip
    & $Py -m pip install -r requirements.txt
}

Write-Host ""
Write-Host "[RUN] Mo dashboard tai: http://localhost:$Port" -ForegroundColor Green
Write-Host "[RUN] Nhan Ctrl+C de tat server." -ForegroundColor Green
Write-Host ""

# Mo trinh duyet sau 2 giay (tien trinh nen)
Start-Job -ScriptBlock { Start-Sleep -Seconds 2; Start-Process "http://localhost:$using:Port" } | Out-Null

# Chay server (giu tien trinh)
& $Py -m uvicorn backend.server:app --port $Port
