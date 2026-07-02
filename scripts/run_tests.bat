@echo off
REM CineAnchor V0.1 — Run the full unittest suite

cd /d "%~dp0\.."

echo === CineAnchor V0.1 Test Suite ===
echo.

echo [1/3] Backend unit tests...
.venv\Scripts\python.exe -m unittest discover -s tests\backend -v
IF %ERRORLEVEL% NEQ 0 (
    echo BACKEND TESTS FAILED
    exit /b 1
)

echo.
echo [2/3] Smoke / integration tests...
.venv\Scripts\python.exe -m unittest discover -s tests\smoke -v
IF %ERRORLEVEL% NEQ 0 (
    echo SMOKE TESTS FAILED
    exit /b 1
)

echo.
echo [3/3] Full suite...
.venv\Scripts\python.exe -m unittest discover -s tests
IF %ERRORLEVEL% NEQ 0 (
    echo FULL SUITE FAILED
    exit /b 1
)

echo.
echo === All tests passed ===
