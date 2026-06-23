@echo off
REM CineAnchor V0.1 — Golden path smoke script
REM Validates character_intro and product_orbit end-to-end if sample assets exist.
REM Skips with clear messages if assets are missing — does NOT fail cryptically.

cd /d "%~dp0\.."

IF "%BLENDER_PATH%"=="" set BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 5.1\blender.exe
IF "%FFMPEG_PATH%"=="" set FFMPEG_PATH=%~dp0\..\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe

echo === CineAnchor V0.1 Golden Path Smoke ===
echo.

REM Check sample assets
set SAMPLE_PNG=samples\assets\hero.png
set SAMPLE_GLB=samples\assets\model.glb

if not exist "%SAMPLE_PNG%" (
    echo [SKIP] Sample PNG not found at %SAMPLE_PNG%
    echo   Place a transparent PNG character image at %SAMPLE_PNG% for character_intro test.
    set PNG_MISSING=1
) else (
    echo [OK] Sample PNG found: %SAMPLE_PNG%
)

if not exist "%SAMPLE_GLB%" (
    echo [SKIP] Sample GLB not found at %SAMPLE_GLB%
    echo   Place a GLB model at %SAMPLE_GLB% for product_orbit test.
    set GLB_MISSING=1
) else (
    echo [OK] Sample GLB found: %SAMPLE_GLB%
)

echo.
echo Press any key to start smoke tests (or Ctrl+C to abort)...
pause >nul

echo.
echo Starting server...
start "CineAnchor-Smoke" /B .venv\Scripts\python.exe -m uvicorn server.main:app --host 127.0.0.1 --port 8765 > storage\logs\smoke-server.log 2>&1

REM Wait for server
ping -n 5 127.0.0.1 >nul

echo Running integration smoke tests...
.venv\Scripts\python.exe -m unittest discover -s tests\smoke -v

echo.
echo Stopping smoke server...
taskkill /FI "WINDOWTITLE eq CineAnchor-Smoke*" /F >nul 2>&1

echo.
echo === Smoke complete ===
