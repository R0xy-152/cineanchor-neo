# CineAnchor Neo

Generate 8-15 second game promotion videos from PNG images or GLB models.

**Stage:** Spike Technical Validation

## What is CineAnchor?

CineAnchor helps mobile game and indie game operators create promotional short videos without 3D art skills. Upload a character image or GLB model, choose a template, type your title, and get a 1080p MP4 ready for TikTok / Xiaohongshu / Steam.

## Tech Stack (Planned)

| Layer | Technology |
|---|---|
| Frontend | Static HTML/CSS/JS for Spike; Next.js later if needed |
| 3D Preview | React Three Fiber |
| Backend | Python FastAPI |
| 3D Render | Blender 5.1.2 Headless (tested) |
| AI Enhance | ComfyUI + SDXL |
| Video | FFmpeg |

## Current Status

- [x] Route 0: 3D Render Loop
- [x] Route 1: PNG 2.5D Video
- [x] Route 2: JSON-Driven Template Rendering
- [ ] Route 3: ComfyUI AI Enhancement
- [x] Route 4: Web To Local Render Chain

See `docs/spike_results.md` for detailed validation results.

## Route 4 Local Web Spike

Install the local web spike dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
```

Configure local tool paths, then run the server:

```powershell
$env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/web/`.

Run the Route 4 smoke check:

```powershell
$env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
.\.venv\Scripts\python.exe server\smoke_web_chain.py
```

## Development

Read `AGENTS.md` before contributing. This project is AI-agent-first: all tasks are designed to be executed by AI agents following the rules in AGENTS.md.

## License

[to be determined]
