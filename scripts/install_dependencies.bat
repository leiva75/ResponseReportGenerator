@echo off
REM ============================================================
REM Response Report Generator - Dependency Installer
REM ============================================================
REM Run this script to install all required Python packages
REM ============================================================

title Installing Dependencies

echo.
echo ============================================================
echo   Installing Response Report Generator Dependencies
echo ============================================================
echo.

REM Change to the parent directory
cd /d "%~dp0.."

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.10 or later from:
    echo   https://python.org/downloads/
    echo.
    echo IMPORTANT: During installation, check the box that says:
    echo   "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not available.
    echo Please reinstall Python with pip included.
    pause
    exit /b 1
)

REM Create virtual environment (optional but recommended)
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Warning: Could not create virtual environment, using global Python.
) else (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo Installing required packages...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Some packages failed to install.
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Installation Complete!
echo ============================================================
echo.
echo You can now run the application by:
echo   1. Double-clicking scripts\run_windows.bat
echo   2. Or running: python run.py
echo.
echo ============================================================

pause
