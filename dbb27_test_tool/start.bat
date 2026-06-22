@echo off
REM ============================================================
REM  DBB-27 Serial Test Tool - tu khoi dong server
REM  Bam dup file nay de chay. Lan dau se tu cai thu vien.
REM ============================================================
setlocal
cd /d "%~dp0"

set "PORT=8000"
set "PY=.venv\Scripts\python.exe"

REM --- Lan dau: tao virtual environment va cai dependencies ---
if not exist "%PY%" (
    echo [SETUP] Chua co moi truong .venv - dang tao lan dau...
    where py >nul 2>nul
    if %errorlevel%==0 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if not exist "%PY%" (
        echo [LOI] Khong tao duoc .venv. Hay cai Python 3.10+ tu python.org roi chay lai.
        pause
        exit /b 1
    )
    echo [SETUP] Cai dat thu vien...
    "%PY%" -m pip install --upgrade pip
    "%PY%" -m pip install -r requirements.txt
)

echo.
echo [RUN] Mo dashboard tai: http://localhost:%PORT%
echo [RUN] Dong cua so nay (hoac nhan Ctrl+C) de tat server.
echo.

REM Mo trinh duyet (cho server 2 giay roi mo)
start "" cmd /c "timeout /t 2 >nul & start http://localhost:%PORT%"

REM Chay server (chay nen tien trinh nay; cua so giu mo)
"%PY%" -m uvicorn backend.server:app --port %PORT%

endlocal
