@echo off
REM ============================================================================
REM  Run the test suite. Double-click to check the platform is working after a
REM  change, or after pulling a new version.
REM
REM  Everything runs against a temporary in-memory database, so this never
REM  touches your machines, fields or lines.
REM ============================================================================
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   Run start.bat first - it sets up the environment the tests need.
    echo.
    pause
    exit /b 1
)

echo.
echo   Running the test suite...
echo.
".venv\Scripts\python.exe" -m pytest tests -q
echo.
if errorlevel 1 (
    echo   Some tests FAILED. The output above says which.
) else (
    echo   All tests passed.
)
echo.
pause
