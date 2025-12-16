@echo off
REM ============================================================
REM Response Report Generator - Windows Launcher
REM ============================================================
REM Double-click this file to start the application
REM The browser will open automatically
REM ============================================================

title Response Report Generator

echo.
echo ============================================================
echo   Response Report Generator - Starting...
echo ============================================================
echo.

REM Change to the parent directory (where app.py is located)
cd /d "%~dp0.."

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10 or later from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Check if virtual environment exists and activate it
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check if dependencies are installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Dependencies not found. Installing...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
    echo.
)

REM Create .env from example if it doesn't exist
if not exist ".env" (
    if exist "config_example.env" (
        echo Creating .env configuration file...
        copy "config_example.env" ".env" >nul
        echo Configuration file created. You can edit .env to customize settings.
        echo.
    )
)

REM Start the application
echo Starting the application...
echo The browser will open automatically.
echo.
echo To stop: Press Ctrl+C or close this window.
echo.
python run.py

REM If we get here, the server stopped
echo.
echo Server stopped.
pause
