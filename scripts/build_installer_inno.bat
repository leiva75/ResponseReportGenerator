@echo off
REM ============================================================
REM Response Report Generator - Inno Setup Installer Build Script
REM ============================================================
REM This script compiles the Inno Setup installer for Windows distribution.
REM
REM Prerequisites:
REM   - Inno Setup 6.x installed (https://jrsoftware.org/isinfo.php)
REM   - Run build_windows.bat first to create dist\ResponseReportGenerator
REM
REM Usage:
REM   scripts\build_installer_inno.bat
REM ============================================================

title Building Response Report Generator Installer

echo.
echo ============================================================
echo   Building Response Report Generator Installer
echo ============================================================
echo.

REM Change to installer directory
cd /d "%~dp0..\installer"

REM Check if dist exists
if not exist "..\dist\ResponseReportGenerator\ResponseReportGenerator.exe" (
    echo ERROR: dist\ResponseReportGenerator not found!
    echo Please run scripts\build_windows.bat first.
    pause
    exit /b 1
)

REM Try to find Inno Setup
set ISCC=

REM Check common locations
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set ISCC=C:\Program Files ^(x86^)\Inno Setup 6\ISCC.exe
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe
)

REM Check if ISCC was found
if "%ISCC%"=="" (
    echo.
    echo Inno Setup not found in standard locations.
    echo.
    echo Please install Inno Setup 6 from:
    echo   https://jrsoftware.org/isdl.php
    echo.
    echo Or compile manually:
    echo   1. Open installer\ResponseReportGenerator.iss in Inno Setup
    echo   2. Click Build ^> Compile
    echo.
    pause
    exit /b 1
)

REM Create output directory
if not exist "..\dist\installer" mkdir "..\dist\installer"

REM Compile the installer
echo Compiling installer with Inno Setup...
echo.
"%ISCC%" ResponseReportGenerator.iss

if errorlevel 1 (
    echo.
    echo ERROR: Installer build failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   INSTALLER BUILD SUCCESSFUL!
echo ============================================================
echo.
echo Installer created at:
echo   dist\installer\ResponseReportGenerator_Setup.exe
echo.
echo This installer:
echo   - Installs to Program Files (or user's choice)
echo   - Creates Start Menu shortcuts
echo   - Stores user data in AppData folders
echo   - Does NOT require admin rights to run after install
echo.
echo ============================================================

pause
