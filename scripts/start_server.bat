@echo off
REM CineAnchor V0.1 — Start the local render server
REM Requires BLENDER_PATH and FFMPEG_PATH environment variables.
REM Copy .env.example to .env and adjust paths, or set them before running.

cd /d "%~dp0\.."

IF "%BLENDER_PATH%"=="" set BLENDER_PATH=C:\Program Files\Blender Foundation\Blender 5.1\blender.exe
IF "%FFMPEG_PATH%"=="" set FFMPEG_PATH=%~dp0\..\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe

echo CineAnchor V0.1 Local Server
echo Blender: %BLENDER_PATH%
echo FFmpeg:  %FFMPEG_PATH%
echo.
echo Web UI:  http://127.0.0.1:8000/web/
echo API:     http://127.0.0.1:8000/docs
echo Health:  http://127.0.0.1:8000/health
echo.
echo Press Ctrl+C to stop.
echo ----------------------------------------

.venv\Scripts\python.exe -m uvicorn server.main:app --host 127.0.0.1 --port 8000
