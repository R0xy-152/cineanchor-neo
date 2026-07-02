@echo off
REM CineAnchor V0.1 — Clean runtime artifacts
REM Removes generated renders, exports, projects, logs, and uploaded assets.
REM Does NOT remove source code, samples README, or configuration.

cd /d "%~dp0\.."

echo CineAnchor V0.1 Runtime Cleanup
echo.

set STORAGE=storage

if not exist "%STORAGE%" (
    echo Storage directory not found — nothing to clean.
    exit /b 0
)

echo Cleaning...

if exist "%STORAGE%\projects" (
    rmdir /s /q "%STORAGE%\projects" 2>nul
    echo   [OK] storage\projects
)
if exist "%STORAGE%\renders" (
    rmdir /s /q "%STORAGE%\renders" 2>nul
    echo   [OK] storage\renders
)
if exist "%STORAGE%\exports" (
    rmdir /s /q "%STORAGE%\exports" 2>nul
    echo   [OK] storage\exports
)
if exist "%STORAGE%\logs" (
    rmdir /s /q "%STORAGE%\logs" 2>nul
    echo   [OK] storage\logs
)
if exist "%STORAGE%\assets" (
    rmdir /s /q "%STORAGE%\assets" 2>nul
    echo   [OK] storage\assets
)

echo.
echo Runtime artifacts cleaned.
echo Source code, samples README, and configuration are untouched.
