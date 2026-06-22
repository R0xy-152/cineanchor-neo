# CineAnchor Neo — Claude Project Guide

## Project Identity

- **Repo:** R0xy-152/cineanchor-neo
- **Stage:** Spike Technical Validation (14 days, started 2026-06-22)
- **Goal:** Validate 5 technical routes before committing to product architecture
- **Primary Doc:** `CineAnchor_可行性操作文档.md` (feasibility doc in repo root)
- **Agent Rules:** `AGENTS.md` (read this first — it governs all AI agent work)

## Current Phase: Spike

We are validating whether the technical chain works:

1. **Route 0** (Day 1-2): GLB → Blender orbit render → FFmpeg → MP4
2. **Route 1** (Day 3-4): Transparent PNG → 2.5D video with camera motion
3. **Route 2** (Day 5-7): JSON-driven template rendering (3 templates)
4. **Route 3** (Day 8-10): ComfyUI keyframe enhancement
5. **Route 4** (Day 11-14): Web → FastAPI → Blender → MP4 full chain

## Rules During Spike

- **ALL** Spike code goes under `spikes/<route_name>/` — never in root or `apps/` / `server/`
- **DO NOT** create `apps/`, `server/`, `blender/`, `comfy/`, `docs/ADR/` directory trees yet
- **DO NOT** lock API contracts, database schema, or Project JSON schema
- **DO** record all results in `spike_results.md`
- **DO** use `spike/*` branches for Spike work
- **DO** treat Spike code as disposable — it exists to answer questions, not to ship

## When Starting a Task

1. Read `AGENTS.md` first — it has the task template, merge rules, and change report format
2. Determine if this is Spike or product work
3. If Spike: work in `spikes/<route>/`, use `spike/<name>` branch
4. Record evidence in `spike_results.md`

## Key Technical Constraints

- Blender 4.x headless, prefer Eevee for MVP (Cycles is too slow)
- ComfyUI: conservative mode only (keyframe enhance, NOT per-frame redraw)
- Serial execution: Blender first, then ComfyUI (avoid GPU OOM on 12GB VRAM)
- Local-only, no cloud, no Redis, no Celery
- Target: 1080p, 8-15 seconds, 24fps, MP4 output

## Environment

- Windows 11 Pro
- GPU: RTX 5070Ti (12GB VRAM) — to be confirmed
- Blender: to be installed/verified
- FFmpeg: to be installed/verified
- ComfyUI: to be installed/verified
- Python: to be verified
