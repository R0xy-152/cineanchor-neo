# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

- **Repo:** R0xy-152/cineanchor-neo
- **Goal:** Generate 8-15 second game promo videos from PNG images or GLB models
- **Core chain:** Web → FastAPI → Project JSON → Blender Eevee → FFmpeg → MP4
- **Agent Rules:** `AGENTS.md` (read this first — task template, merge rules, change report format)
- **Primary Docs:** `CineAnchor_可行性操作文档.md`, `README.md`

## Current Phase: V0.1 Phase A (Post-Spike)

Spike is essentially complete: Route 0/1/2/4 passed, Route 3 is PARTIAL. V0.1 Phase A has started — building the backend foundation, formal Project JSON schema, error model, and in-memory task acceptance. The render execution pipeline (Blender + FFmpeg) is not yet wired in the formal `server/` code — services are placeholders.

Route 3 ComfyUI enhancement is optional. `ai_enhance.enabled` defaults to `false`. Full-frame AI video regeneration is forbidden for V0.1 (see `docs/adr/ADR-004-no-full-frame-ai-video-regeneration.md`).

## Architecture: Dual Server Setup

There are TWO FastAPI apps — know which to use:

| | Spike App | Formal App |
|---|---|---|
| **Module** | `server.app:app` | `server.main:app` |
| **Routes** | Defined inline in `server/app.py` | Modular under `server/routes/render.py` |
| **Schema** | Inline Pydantic model | Pydantic v2 in `server/schemas/project.py` |
| **Rendering** | Actually runs Blender + FFmpeg | Placeholder services (returns 501 for download) |
| **Task store** | Inline dict in `app.py` | `server/services/task_queue.py` (InMemoryTaskStore) |
| **Error model** | Ad-hoc | `server/services/errors.py` (ErrorCode enum + CineAnchorError) |
| **Web UI** | Serves `apps/web/` via StaticFiles | Not mounted yet |
| **Use for** | End-to-end demos, smoke checks | Schema validation, API contract development |

The formal app's services (`server/services/blender_service.py`, `server/services/ffmpeg_service.py`, `server/services/comfy_service.py`) are placeholders that raise `NotImplementedError`. The spike app in `server/app.py` is the working render pipeline.

## Environment Setup

Python virtual environment is at `.venv/`. All Python commands use `.\.venv\Scripts\python.exe`.

Required environment variables:

```powershell
$env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
```

Additional env vars used by the spike app: `CINEANCHOR_RENDER_JSON_DIR`, `CINEANCHOR_RENDER_SCRIPT`, `CINEANCHOR_MAKE_VIDEO_SCRIPT`, `CINEANCHOR_RENDER_TIMEOUT_SECONDS`, `POWERSHELL_PATH`.

## Common Commands

### Lint / Compile Check

```powershell
.\.venv\Scripts\python.exe -m py_compile server\main.py server\config.py server\routes\render.py server\services\errors.py server\schemas\project.py
```

### Run Unit Tests (schema, config, errors — no hardware needed)

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests\backend
```

### Run Smoke Tests (ASGI integration, golden path — no hardware needed)

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests\smoke
```

### Run All Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

### Run Formal V0.1 Server (schema-only, no rendering)

```powershell
.\.venv\Scripts\python.exe -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

### Run Spike Web Server (with Blender rendering + Web UI)

```powershell
$env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/web/` for the UI.

### Run End-to-End Smoke Check (Route 4 — needs Blender + FFmpeg)

```powershell
$env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
.\.venv\Scripts\python.exe server\smoke_web_chain.py
```

### Git Diff Check

```powershell
git diff --check
```

## Key Files and Directories

| Path | Purpose |
|---|---|
| `server/main.py` | V0.1 formal FastAPI entry point |
| `server/app.py` | Spike FastAPI app (working render pipeline) |
| `server/config.py` | Settings dataclass, env var reading, path resolution |
| `server/schemas/project.py` | Pydantic v2 ProjectJSON schema (the contract) |
| `server/routes/render.py` | V0.1 render API routes (POST + GET status + GET download) |
| `server/services/errors.py` | ErrorCode enum, CineAnchorError, error_payload |
| `server/services/task_queue.py` | InMemoryTaskStore + RenderTask dataclass |
| `server/services/*_service.py` | Placeholder service classes (not wired yet) |
| `apps/web/` | Static HTML/CSS/JS frontend (served by spike app) |
| `blender/scripts/render_project.py` | Placeholder — real script is `spikes/render_json/render_project.py` |
| `spikes/render_json/` | Route 2 spike: JSON-driven Blender rendering scripts |
| `spikes/comfy_enhance/` | Route 3 spike: direct img2img attempt (FAILED for text) |
| `spikes/comfy_lut_enhance/` | Route 3 spike: conservative ComfyUI reference + FFmpeg (PARTIAL) |
| `tests/backend/` | Unit tests (schema, config, errors) — run without hardware |
| `tests/smoke/` | ASGI integration tests — run without hardware |
| `docs/spike_results.md` | Detailed Route 2/3/4 results with performance data |
| `docs/adr/` | Architecture Decision Records |
| `storage/` | Runtime output (gitignored) |
| `.tools/` | Bundled FFmpeg (gitignored) |

## Task Status State Machine

```
PENDING → RENDERING → COMPOSITING → (ENHANCING) → DONE
            ↓              ↓              ↓
          FAILED         FAILED         FAILED
```

ENHANCING is only entered when `ai_enhance.enabled=true` (not in standard V0.1 path).

## Key Constraints

- Blender 5.1.2 headless confirmed working, Eevee is default (not Cycles)
- FFmpeg 8.1.1 Gyan build confirmed working
- ComfyUI must NOT be called by the standard V0.1 render path — `ComfyService.enhance` is a fire alarm if triggered
- Serial execution only: Blender then ComfyUI (never concurrently — will OOM on 12GB VRAM)
- ComfyUI full-frame img2img is forbidden — it corrupts rendered text (see ADR-004)
- Local-only, no cloud, no Redis, no Celery
- Target output: 1080p, 8-15 seconds, 24fps, MP4 (h264 yuv420p)
- In-memory task store is lost on server restart (acceptable for V0.1 local-first)

## Change Report Format

Every completed task must output a change report in this exact format:

```md
Changed:

files_modified:
- path/to/file

behavior_changed:
- summary

api_changed: yes/no
schema_changed: yes/no

tests_added:
- path/to/test

commands_run:
- command and result

known_risks:
- risk summary
```

This is mandatory — do not skip or abbreviate it.

## Project JSON Schema (V0.1 Formal)

Defined by `ProjectJSON` in `server/schemas/project.py`. Key rules:
- `version` must be `"0.1"`
- Exactly one asset with `id="main_subject"`
- `character_intro` template requires asset `type=image`
- `product_orbit` template requires asset `type=glb`
- `ai_enhance.enabled` defaults to `false`
- `fps` is locked to `24` (Literal type)
- Aspect ratios: `9:16`, `16:9`, `1:1`; resolution: only `1080p`
