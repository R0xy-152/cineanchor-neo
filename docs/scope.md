# CineAnchor Neo — Scope & Boundaries

> Consolidated from `AGENTS.md`, `.claude/CLAUDE.md`, and `README.md`.
> One-page reference for what is in-scope, out-of-scope, and deferred.
> Regenerate when product scope changes.

## In scope (V0.1)

### Input
- One transparent PNG character image → `character_intro` template
- One GLB 3D model → `product_orbit` template
- Title + subtitle text strings
- Configurable: duration (4–20s), FPS (24 locked), aspect ratio (9:16 / 16:9 / 1:1), resolution (1080p)
- Model transform (location / rotation / scale) via `scene.model_transform`
- Per-light overrides (position / energy / color / size) via `scene.lighting_overrides`
- Camera params (height / start_distance / end_distance / focal_length) now wired to Blender
- Stage elements toggle: ring, glints, cloth texture via `scene.background_enhance`

### Pipeline
- **Web UI** → static HTML/CSS/JS (zero-build, Chinese)
- **FastAPI** → `server.main:app` (primary); legacy `server/app.py` for reference only
- **Project JSON** → Pydantic v2 schema (`server/schemas/project.py`)
- **Blender Eevee** → headless 5.1.2, `blender/scripts/render_project.py`
- **FFmpeg** → compose PNG frames → MP4 (h264 yuv420p, 1080p)
- **AI enhancement** → optionally enabled (`ai_enhance.enabled`), post-FFmpeg only; ComfyUI NOT part of standard path

### Output
- MP4 video: 1080p, 8–15 seconds, 24fps, h264 yuv420p
- Debug artifacts under `storage/` (gitignored)

### Templates
- `character_intro` — dolly-in camera (tunable via camera params), PNG subject with alpha, stage + lights + text
- `product_orbit` — dolly-in or orbit camera (tunable), GLB subject, stage + lights + text

### Infrastructure
- Local-only: no cloud, no Docker, no Redis, no Celery
- In-memory task store (lost on restart — acceptable for V0.1)
- Single-threaded rendering (one task at a time)
- `unittest` framework (NOT pytest), 72+ tests

## Out of scope (never, unless explicitly rescoped)

- Cloud rendering / SaaS deployment
- Account system / user management
- Multiplayer collaboration
- Template marketplace
- Ecommerce batch generation
- Unreal Engine backend
- Frame-by-frame AI video redraw (see ADR-004)
- WYSIWYG preview parity (Three.js vs Blender)
- Celery + Redis queues
- CI/CD pipeline / Docker / containerization

## Deferred (V0.2+)

- `subject_scale` parameter
- BGM upload
- User accounts or project history
- GLB decimation (large models may time out)
- Automatic background removal for non-transparent PNGs
- Real-time 3D preview
- Web UI mounted on `server.main:app` (available via legacy `server/app.py`)

## Hard rules (never bypass)

1. **Text must never be processed by AI.** Title/subtitle/CTA must be composited after AI stage.
2. **AI enhancement default is off.** `ai_enhance.enabled` defaults to `false`.
3. **Full-frame AI video regeneration is forbidden.** See ADR-004.
4. **Production code is read-only during AI R&D.** AI spikes live under `spikes/ai_*`.
5. **No new dependencies without documentation.**
6. **Secrets never committed.**

## Branch strategy

| Branch | Who writes | Merge to main |
|--------|-----------|---------------|
| `main` | Nobody directly | 启鸣 merges PRs |
| `Andy` | Andy only (docs) | Never auto |
| `spike/*` | CC | Via PR if promoted |
| `feature/*` | CC | Via PR |
| `docs/*` | CC or Andy | Via PR |

## Current strategic state

V0.1 RC **passed functional verification** (72 tests, golden smoke). Standard render path stable. Parameter decoupling complete: model transform, lighting overrides, camera params now configurable via JSON. Loop-06 mass production (3 weapons × ≥2 camera moves) complete — base videos with Seedance prompts ready for 2b generality validation. AI enhancement is the current R&D focus.
