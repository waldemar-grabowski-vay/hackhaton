@echo off
REM ======================================================================
REM  Vay OBD Live — one-shot Windows build
REM
REM  Produces:
REM     dist\Vay_OBD_Live\Vay_OBD_Live.exe          (PyInstaller bundle, ready to run)
REM     dist_installer\Vay_OBD_Live-Setup-<v>.exe   (Inno Setup installer)
REM
REM  Prereqs:
REM     - Python 3.11 or 3.12 on PATH
REM     - Inno Setup 6 installed (ISCC.exe). Default location is checked
REM       below; override by setting ISCC env var to the full path.
REM ======================================================================
setlocal ENABLEDELAYEDEXPANSION

cd /d "%~dp0"

echo [1/5] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: python not found on PATH. Install Python 3.11+ and rerun.
    exit /b 1
)

echo [2/5] Creating venv .build_venv if needed...
if not exist ".build_venv\Scripts\python.exe" (
    python -m venv .build_venv
    if errorlevel 1 (
        echo ERROR: failed to create venv.
        exit /b 1
    )
)
call ".build_venv\Scripts\activate.bat"

echo [3/5] Installing build dependencies...
python -m pip install --upgrade pip wheel >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed.
    exit /b 1
)
python -m pip install "pyinstaller>=6.6"
if errorlevel 1 (
    echo ERROR: failed to install pyinstaller.
    exit /b 1
)

echo [4/5] Running PyInstaller...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist
pyinstaller --noconfirm packaging\ts_diag.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

echo [5/5] Building installer with Inno Setup...
set "ISCC_EXE=%ISCC%"
if "%ISCC_EXE%"=="" set "ISCC_EXE=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_EXE%" (
    echo.
    echo PyInstaller bundle is ready at: dist\Vay_OBD_Live\Vay_OBD_Live.exe
    echo.
    echo Inno Setup not found at "%ISCC_EXE%".
    echo Install Inno Setup 6 from https://jrsoftware.org/isdl.php
    echo or set the ISCC env var to ISCC.exe and rerun this script.
    exit /b 0
)

if exist dist_installer rmdir /s /q dist_installer
"%ISCC_EXE%" packaging\installer.iss
if errorlevel 1 (
    echo ERROR: Inno Setup compilation failed.
    exit /b 1
)

echo.
echo === BUILD OK ===
for %%F in (dist_installer\*.exe) do echo Installer: %%~fF
echo.
endlocal
exit /b 0
