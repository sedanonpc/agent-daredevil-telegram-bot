@echo off
REM Agent Daredevil - Windows Service Launcher
title Agent Daredevil - Service Launcher

echo.
echo 🎯 Agent Daredevil - Windows Service Launcher
echo ============================================
echo 🤖 Starting Telegram RAG Bot with Memory ^& Knowledge Management
echo ============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to your PATH
    echo.
    pause
    exit /b 1
)

REM Check if launcher script exists
if not exist "launch_daredevil.py" (
    echo ❌ launch_daredevil.py not found
    echo Please make sure you're running this from the correct directory
    echo.
    pause
    exit /b 1
)

REM Launch the Python service manager
echo 🚀 Launching Agent Daredevil services...
echo.
python launch_daredevil.py

REM Pause to see any final output
echo.
echo Press any key to exit...
pause >nul 