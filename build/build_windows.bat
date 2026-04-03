@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: build_windows.bat — Build the Second Conflict Windows installer
::
:: Requirements (must be on PATH or detected automatically):
::   - Python 3.11+  (with pip)
::   - PyInstaller   (installed automatically if missing)
::   - Inno Setup 6  (optional; installer is compiled if found)
::
:: Run from the project root:
::   build\build_windows.bat
:: ============================================================

echo.
echo ====================================================
echo  Second Conflict — Windows Build
echo ====================================================
echo.

:: Move to project root (script lives in build\)
cd /d "%~dp0.."

:: ----------------------------------------------------------
:: 1. Ensure PyInstaller is installed
:: ----------------------------------------------------------
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller not found. Installing...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause & exit /b 1
    )
)

:: ----------------------------------------------------------
:: 2. Clean previous build artefacts
:: ----------------------------------------------------------
echo [INFO] Cleaning previous build output...
if exist "dist\Second Conflict" rmdir /s /q "dist\Second Conflict"
if exist "build\Second Conflict"  rmdir /s /q "build\Second Conflict"

:: ----------------------------------------------------------
:: 3. Run PyInstaller
:: ----------------------------------------------------------
echo [INFO] Running PyInstaller...
python -m PyInstaller build\second_conflict.spec --distpath dist --workpath build\pyinstaller_work --noconfirm

if errorlevel 1 (
    echo [ERROR] PyInstaller failed. See output above.
    pause & exit /b 1
)
echo [OK] PyInstaller completed. App is in dist\Second Conflict\

:: ----------------------------------------------------------
:: 4. Compile the Inno Setup installer (if iscc.exe is available)
:: ----------------------------------------------------------
set ISCC=
for %%p in (
    "%ProgramFiles(x86)%\Inno Setup 6\iscc.exe"
    "%ProgramFiles%\Inno Setup 6\iscc.exe"
) do (
    if exist %%p set ISCC=%%p
)

if defined ISCC (
    echo [INFO] Inno Setup found at %ISCC%
    echo [INFO] Compiling installer...
    %ISCC% build\installer.iss
    if errorlevel 1 (
        echo [ERROR] Inno Setup compilation failed.
        pause & exit /b 1
    )
    echo [OK] Installer created: build\Output\SecondConflict-Setup.exe
) else (
    echo.
    echo [WARN] Inno Setup not found — skipping installer compilation.
    echo        Install Inno Setup 6 from https://jrsoftware.org/isdl.php
    echo        then re-run this script, or compile build\installer.iss manually.
    echo.
    echo        The standalone app folder is ready at:
    echo          dist\Second Conflict\
)

echo.
echo Done.
pause