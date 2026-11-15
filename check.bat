@echo off
setlocal
cd /d "%~dp0"
set SDL_VIDEODRIVER=dummy
set SDL_AUDIODRIVER=dummy
set PYTHONUTF8=1

echo [1/2] ruff check
python -m ruff check --select F,E9 sap_visualizer main.py packaging tests
if errorlevel 1 goto :fail

echo [2/2] pytest
python -m pytest -q
if errorlevel 1 goto :fail

echo.
echo [OK] all checks passed
exit /b 0

:fail
echo.
echo [NG] checks failed
exit /b 1
