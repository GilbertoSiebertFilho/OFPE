@echo off
REM ============================================================================
REM  OFPE Field Data Platform - start here.
REM
REM  Double-click this file. It sets everything up the first time and just
REM  starts the app every time after that.
REM
REM  Everything it installs goes into a .venv folder next to this script, so it
REM  cannot break any other Python you have on this machine.
REM ============================================================================
setlocal
cd /d "%~dp0"

echo.
echo   OFPE Field Data Platform
echo   ------------------------
echo.

REM --- Find a usable Python --------------------------------------------------
REM  "py" is the Windows launcher and is the more reliable of the two, because
REM  "python" on a machine without Python opens the Microsoft Store instead of
REM  reporting an error.
set "PY_CMD="
py -3 --version >nul 2>&1 && set "PY_CMD=py -3"
if not defined PY_CMD (
    python --version >nul 2>&1 && set "PY_CMD=python"
)

if not defined PY_CMD (
    echo   Python is not installed, or it is not on your PATH.
    echo.
    echo   Install it from:  https://www.python.org/downloads/
    echo   On the first screen of the installer, TICK
    echo   "Add python.exe to PATH" before pressing Install.
    echo.
    echo   Then double-click this file again.
    echo.
    pause
    exit /b 1
)

REM --- First run: build a private environment --------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo   First run. Creating a private Python environment...
    %PY_CMD% -m venv .venv
    if errorlevel 1 goto venv_failed
    echo   Installing the packages it needs. This takes a minute or two,
    echo   once, and only the first time.
    echo.
    ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
    if errorlevel 1 goto install_failed
    echo   Setup finished.
    echo.
)

REM --- Start, and open the browser -------------------------------------------
echo   Starting. Your browser will open in a moment.
echo   Leave this window open while you use the app.
echo.
".venv\Scripts\python.exe" run.py --open
goto :eof

:venv_failed
echo.
echo   Could not create the Python environment.
echo   Try running this in a Command Prompt to see the full error:
echo       %PY_CMD% -m venv .venv
echo.
pause
exit /b 1

:install_failed
echo.
echo   Could not install the required packages. The usual cause is no
echo   internet connection, or a company proxy blocking pip.
echo.
echo   To see the full error, open a Command Prompt here and run:
echo       .venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
pause
exit /b 1
