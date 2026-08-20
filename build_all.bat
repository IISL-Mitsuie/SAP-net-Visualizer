@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   SAP-net Visualizer One-Click Build Script
echo ============================================================

python packaging\build.py
if errorlevel 1 (
    echo [ERROR] Build script exited with an error.
)

pause
