# CineAnchor Neo — Code Map

> One-page module map + call flow. Shallow — details in source.
> Regenerate when directory structure or call flow changes.

## Directory layout

```
cineanchor-neo/
├── server/                  # FastAPI backend (V0.1 production)
│   ├── main.py              #   Entry point: FastAPI app, route registration
│   ├── config.py            #   Settings dataclass, env-var → path resolution
│   ├── routes/
│   │   ├── render.py        #   POST /api/render, GET status/download
│   │   └── assets.py        #   POST /api/assets/upload
│   ├── schemas/
│   │   └── project.py       #   Pydantic v2 ProjectJSON schema (the contract)
│   └── services/
│       ├── blender_service.py   # Blender subprocess wrapper
│       ├── ffmpeg_service.py    # FFmpeg composition + AI enhancement
│       ├── comfy_service.py     # ComfyUI client (NOT wired — excluded from standard path)
│       ├── task_queue.py        # InMemoryTaskStore + RenderTask state machine
│       └── errors.py            # ErrorCode enum + CineAnchorError
├── blender/
│   └── scripts/
│       ├── render_project.py    # Production Blender script (Eevee, templates, layers)
│       └── render_defaults.py   # Single source of truth for hardcoded defaults
├── blender/
│   └── scripts/
│       ├── render_project.py    # Production Blender script (Eevee, templates, layers)
│       ├── render_defaults.py   # Single source of truth for hardcoded defaults
│       ├── camera_math.py       # Catmull-Rom + SLERP interpolation
│       └── camera_presets.py    # 8 cinematic camera presets
├── apps/
│   └── web/                     # Static frontend (zero-build HTML/CSS/JS, Chinese)
│       ├── index.html           #   Main UI
│       ├── viewport.html        #   Loop 08 interactive 3D viewport
│       └── src/
│           ├── camera_math.js   #   Catmull-Rom + SLERP (JS port)
│           ├── camera_presets.js#   8 cinematic presets (JS port)
│           ├── fitter.js        #   RDP + angle filter keyframe fitting
│           ├── input_controller.js # Keyboard/mouse flight input
│           ├── recorder.js      #   Keyframe recording + hard-cut support
│           └── viewport.js      #   Three.js scene + fly camera + recording
├── tests/
│   ├── backend/                 # Unit tests (unittest) — 106 tests
│   ├── frontend/                # Viewport JS unit tests — 20 tests
│   ├── parity/                  # JS vs Python cross-check — 15 tests
│   └── smoke/                   # ASGI integration tests — 13 tests
├── spikes/                      # R&D spike archives (read-only reference)
│   └── ai_benchmark/            #   AI method search benchmark package
├── docs/                        # Documentation
│   ├── adr/                     #   Architecture Decision Records
│   ├── api_contract.md          #   Full API endpoint contracts
│   ├── scope.md                 #   Scope & boundaries
│   ├── codemap.md               #   This file
│   ├── parameters.md            #   Parameter table (JSON → Blender)
│   └── seedance_prompts.md      #   Seedance prompts for mass-produced bases
├── scripts/                     # Helper scripts (mass production, pre-push smoke)
├── samples/                     # Sample assets (gitignored)
├── storage/                     # Runtime output (gitignored)
└── .claude/                     # Claude Code config
    └── CLAUDE.md                #   Agent guidance (this is read by CC)
```

## Call flow (standard render — no AI)

```
Browser                          FastAPI                         Blender              FFmpeg
  │                                │                               │                    │
  │  POST /api/render              │                               │                    │
  │  (Project JSON)                │                               │                    │
  ├───────────────────────────────►│                               │                    │
  │                                │  validate → InMemoryTaskStore │                    │
  │                                │  spawn daemon thread          │                    │
  │  200 {task_id, PENDING}        │                               │                    │
  │◄───────────────────────────────┤                               │                    │
  │                                │                               │                    │
  │  GET /api/render/{id}/status   │                               │                    │
  ├───────────────────────────────►│                               │                    │
  │  {status: "RENDERING"}         │                               │                    │
  │◄───────────────────────────────┤                               │                    │
  │                                │  BlenderService.render_project│                    │
  │                                ├──────────────────────────────►│                    │
  │                                │                               │ render_project.py  │
  │                                │                               │ output: PNG frames │
  │                                │◄──────────────────────────────┤                    │
  │                                │  FFmpegService.compose_mp4    │                    │
  │                                ├───────────────────────────────────────────────────►│
  │                                │                               │   compose → MP4   │
  │                                │◄───────────────────────────────────────────────────┤
  │                                │  task → DONE                  │                    │
  │                                │                               │                    │
  │  GET /api/render/{id}/download │                               │                    │
  ├───────────────────────────────►│                               │                    │
  │  200 video/mp4                 │                               │                    │
  │◄───────────────────────────────┤                               │                    │
```

## Task state machine

```
PENDING → RENDERING → COMPOSITING → (ENHANCING) → DONE
              ↓              ↓            ↓
            FAILED         FAILED       FAILED
```

- `ENHANCING` only entered when `ai_enhance.enabled=true` (default: false)
- On enhancement failure: fallback to standard MP4 with `AI_ENHANCE_SKIPPED` warning

## Project JSON schema (key types)

```
ProjectJSON
├── version: "0.1" (regex-locked)
├── project_id: str
├── template: character_intro | product_orbit
├── output: {duration, fps: 24, aspect_ratio, resolution}
├── assets: [exactly 1, id="main_subject", type=image|glb]
├── camera: {motion, speed, start_distance, end_distance, height, focal_length,
│           preset?, keyframes?, shots?}  # preset=preset camera, keyframes/shots=interactive
├── scene: {background, lighting, particles?, fog, background_enhance?,
│           model_transform?, lighting_overrides?}
├── text: {title?, subtitle?, font_style}
├── ai_enhance: {enabled?, mode?, workflow?}
└── scene.background_enhance: {rim_light?, rim_light_color?, rim_light_energy?,
                                cloth_texture?, cloth_mix?, glints?,
                                text_overlay?, stage_ring?}
```

## Key constraints

- Python 3.11+, FastAPI + uvicorn + python-multipart only (3 deps)
- No npm/JS build step — frontend is vanilla static files
- Blender 5.1.2 headless, Eevee engine, Filmic view transform
- FFmpeg 8.1 — h264, yuv420p
- Serial execution (Blender then FFmpeg — never concurrent to avoid OOM)
- 12GB VRAM budget (RTX 5070 Ti target)
- Windows-only (PowerShell scripts, Blender Windows build)
