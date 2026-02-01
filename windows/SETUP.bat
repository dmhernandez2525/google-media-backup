@echo off
title Google Media Backup - Setup
echo.
echo Starting Google Media Backup Setup...
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10 or later from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Run the setup script
cd /d "%~dp0"
python setup.py

:: Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo Setup encountered errors. See above for details.
    pause
)
