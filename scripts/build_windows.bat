@echo off
REM ============================================================
REM Response Report Generator - Windows Build Script
REM ============================================================
REM This script creates a standalone Windows executable using PyInstaller.
REM Runtime data is stored in user directories, NOT in Program Files.
REM ============================================================

title Building Response Report Generator

echo.
echo ============================================================
echo   Building Response Report Generator for Windows
echo ============================================================
echo.

REM Change to the parent directory
cd /d "%~dp0.."

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Install PyInstaller if not present
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Install all dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Build the executable using the spec file
echo.
echo Building executable using spec file...
echo This may take a few minutes...
echo.

pyinstaller ResponseReportGenerator.spec --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

REM Copy example config
echo.
echo Setting up distribution...
if exist "config_example.env" (
    copy "config_example.env" "dist\ResponseReportGenerator\.env.example" >nul
    echo Copied .env.example
)

REM Create a simple launcher
echo @echo off > "dist\ResponseReportGenerator\Start.bat"
echo title Response Report Generator >> "dist\ResponseReportGenerator\Start.bat"
echo start "" "%%~dp0ResponseReportGenerator.exe" >> "dist\ResponseReportGenerator\Start.bat"
echo Created Start.bat launcher

REM Create README for distribution
(
echo Response Report Generator - Windows Distribution
echo.
echo ============================================================
echo QUICK START
echo ============================================================
echo   Double-click Start.bat or ResponseReportGenerator.exe
echo.
echo ============================================================
echo CONFIGURATION
echo ============================================================
echo   1. Copy .env.example to .env ^(in same folder as .exe^)
echo   2. Edit .env with your API keys
echo.
echo ============================================================
echo DATA LOCATIONS ^(created automatically at runtime^)
echo ============================================================
echo   History/Drafts: %%APPDATA%%\ResponseReportGenerator\data
echo   Logs:           %%LOCALAPPDATA%%\ResponseReportGenerator\logs
echo   Exports:        Documents\ResponseReportGenerator\exports
echo.
echo ============================================================
echo NOTES
echo ============================================================
echo   - Data is stored in user folders, NOT next to the executable
echo   - This allows installation in Program Files without admin rights
echo   - Each Windows user has their own separate data
echo.
) > "dist\ResponseReportGenerator\README.txt"
echo Created README.txt

echo.
echo ============================================================
echo   BUILD SUCCESSFUL!
echo ============================================================
echo.
echo The application has been built to:
echo   dist\ResponseReportGenerator\
echo.
echo To run the application:
echo   Double-click Start.bat or ResponseReportGenerator.exe
echo.
echo IMPORTANT: Windows SmartScreen may block the first run.
echo   Click "More info" then "Run anyway" to proceed.
echo.
echo DATA STORAGE:
echo   User data is stored in AppData folders, NOT next to the .exe
echo   This allows proper installation in Program Files.
echo.
echo To create an installer, run:
echo   scripts\build_installer_inno.bat
echo.
echo ============================================================

pause
