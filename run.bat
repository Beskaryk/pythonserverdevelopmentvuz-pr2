@echo off
setlocal
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
    where py >nul 2>&1
    if errorlevel 1 (
        python -m venv .venv
    ) else (
        py -3 -m venv .venv
    )
    if errorlevel 1 exit /b 1
)

"%PY%" -m pip install --quiet -r pr2\requirements.txt
if errorlevel 1 exit /b 1

if exist pr2\src\server.py (
    "%PY%" -m pr2.src.server %*
) else (
    "%PY%" -m pr2.src.demo
)
exit /b %errorlevel%
