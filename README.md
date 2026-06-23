# CineAnchor Neo

Generate 8-15 second game promotion videos from PNG images or GLB models.

**Stage:** V0.1 Official Development / Phase A

## What is CineAnchor?

CineAnchor helps mobile game and indie game operators create promotional short videos without 3D art skills. Upload a character image or GLB model, choose a template, type your title, and get a 1080p MP4 ready for TikTok / Xiaohongshu / Steam.

## Tech Stack (Planned)

| Layer | Technology |
|---|---|
| Frontend | Static HTML/CSS/JS for Spike; Next.js later if needed |
| 3D Preview | React Three Fiber |
| Backend | Python FastAPI |
| 3D Render | Blender 5.1.2 Headless (tested) |
| AI Enhance | Optional ComfyUI reference + FFmpeg/LUT-style filters |
| Video | FFmpeg |

## Current Status

- [x] Route 0: 3D Render Loop
- [x] Route 1: PNG 2.5D Video
- [x] Route 2: JSON-Driven Template Rendering
- [x] Route 3: Conservative AI Enhancement (FFmpeg-based conservative_premium preset; ComfyUI is future hook)
- [x] Route 4: Web To Local Render Chain
- [x] V0.1 Phase A started: backend foundation and formal Project JSON schema

See `docs/spike_results.md` for detailed validation results.

## V0.1 Backend Foundation

V0.1 official development has started. The backend foundation is complete:
- Formal Project JSON schema with Pydantic v2 validation
- FastAPI app with `/health`, `POST /api/render`, `GET /api/render/{task_id}/status`, `GET /api/render/{task_id}/download`
- Blender headless render execution via `blender/scripts/render_project.py`
- FFmpeg MP4 composition (H.264, yuv420p, CRF 18)
- CineAnchorError exception hierarchy with 12 error codes
- In-memory task store with threading (no database dependency)
- Optional AI enhancement: FFmpeg `conservative_premium` preset (eq + unsharp)
- Enhancement fallback: standard MP4 returned if enhancement fails (warning, not error)
- Config via environment variables + `server/config.py`

The core V0.1 value:

```text
Web → FastAPI → Project JSON → Blender Eevee → FFmpeg → MP4
```

Route 3 AI enhancement is PARTIAL and optional. `ai_enhance.enabled` defaults to
`false`; ComfyUI is not called by the standard V0.1 render path.

Run backend checks:

```powershell
.\.venv\Scripts\python.exe -m py_compile server\main.py server\config.py server\routes\render.py server\services\errors.py server\schemas\project.py server\services\blender_service.py server\services\ffmpeg_service.py server\services\task_queue.py blender\scripts\render_project.py
.\.venv\Scripts\python.exe -m unittest discover -s tests\backend
.\.venv\Scripts\python.exe -m unittest discover -s tests\smoke
.\.venv\Scripts\python.exe -m unittest discover -s tests
git diff --check
```

## Run V0.1 Formal Server

Configure local tool paths, then run the formal V0.1 backend:

```powershell
$env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
.\.venv\Scripts\python.exe -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

POST formal Project JSON to `http://127.0.0.1:8000/api/render`, then poll
`/api/render/{task_id}/status`. When status is `DONE`, download from
`/api/render/{task_id}/download`.

## Route 4 Local Web Spike (Legacy)

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

## Route 3 Direct Img2Img Spike

This historical spike is isolated from the Web/FastAPI render chain. It extracts 4 keyframes from existing MP4 outputs, sends them to ComfyUI, and creates side-by-side comparison images.

```powershell
$env:COMFYUI_API_URL="http://127.0.0.1:8188"
$env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
$env:FFPROBE_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe"
powershell -NoProfile -ExecutionPolicy Bypass -File .\spikes\comfy_enhance\run_spike.ps1
```

Route 3 uses `COMFYUI_API_URL` first, then falls back to `COMFYUI_URL` and `http://127.0.0.1:8188`.

Direct full-frame img2img decision: FAIL. The ComfyUI keyframe chain works, but direct full-frame img2img corrupted rendered subtitle text. Do not integrate direct frame replacement into the Web render path.

## V0.1 AI Enhancement Decision

- Direct full-frame AI video regeneration is excluded.
- Conservative ComfyUI reference plus FFmpeg enhancement was validated as PARTIAL.
- It keeps text and subjects stable because final frames are not replaced.
- Visual improvement is light, so it is an optional premium preset, not the core product selling point.
- The core V0.1 value remains: Web -> FastAPI -> Project JSON -> Blender Eevee -> FFmpeg -> MP4.

Route 3 conservative AI enhancement generates only keyframe color/style references with ComfyUI, then applies conservative video-wide FFmpeg filters to the original MP4.

```powershell
$env:COMFYUI_API_URL="http://127.0.0.1:8188"
powershell -NoProfile -ExecutionPolicy Bypass -File .\spikes\comfy_lut_enhance\extract_keyframes.ps1
.\.venv\Scripts\python.exe .\spikes\comfy_lut_enhance\run_comfy_reference.py --timeout-seconds 1200
.\.venv\Scripts\python.exe .\spikes\comfy_lut_enhance\analyze_color_reference.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\spikes\comfy_lut_enhance\apply_ffmpeg_enhance.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\spikes\comfy_lut_enhance\make_comparisons.ps1
```

Current Route 3 decision: PARTIAL. The final FFmpeg-enhanced videos preserve text and subject shape, but the visual lift is mild.

## Development

Read `AGENTS.md` before contributing. This project is AI-agent-first: all tasks are designed to be executed by AI agents following the rules in AGENTS.md.

## License

[to be determined]
