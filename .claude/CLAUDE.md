# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

- **Repo:** R0xy-152/cineanchor-neo
- **Goal:** Generate 8-15 second game promo videos from PNG images or GLB models
- **Core chain:** Web → FastAPI → Project JSON → Blender Eevee → FFmpeg → MP4
- **Agent Rules:** `AGENTS.md` (read this first — task template, merge rules, change report format)
- **Primary Docs:** `CineAnchor_可行性操作文档.md`, `README.md`

## Current Phase: Loop 08 — Interactive Camera Control ✅ COMPLETE

Loop 08 is complete. All gates passed, 启鸣签收 2026-07-02.

**Bug fixes delivered:**
1. `_quat_from_look` trace formula: `R00+R11-R22` → `R00+R11+R22` (both Python and JS)
2. Quaternion component order: `[x,y,z,w]` → `(w,x,y,z)` for Blender's `rotation_quaternion` — in BOTH `_persp_camera_from_frames` and `add_keyframed_camera`

**Critical lesson — Blender quaternion convention:**
`Object.rotation_quaternion` expects `(w, x, y, z)`. Our internal convention is `[x, y, z, w]`. ALWAYS convert when crossing the Blender boundary. Affected functions: `_persp_camera_from_frames`, `add_keyframed_camera`.

**Gate results:**
| Gate | Status |
|------|--------|
| 4. Visual parity | ✅ User confirmed |
| 6. Default-path regression | ✅ Orbit/dolly/preset all PASS |
| 7. PERSP+title carry-forward | ✅ PASS |

**Test count:** 154 tests green (was 150, added 4 oracle tests)

**Diagnostic scripts created (for future debugging):**
- `scripts/parity_diagnostic.py` — single-frame pipeline math trace
- `scripts/e2e_pipeline_trace.py` — API→Blender full pipeline
- `scripts/side_by_side_diag.py` — orbit vs keyframed camera comparison
- `scripts/gate6_regression.py` — default-path regression test

## Architecture: Dual Server Setup

There are TWO FastAPI apps — know which to use:

| | Spike App | Formal App |
|---|---|---|
| **Module** | `server.app:app` | `server.main:app` |
| **Routes** | Defined inline in `server/app.py` | Modular under `server/routes/render.py` |
| **Schema** | Inline Pydantic model | Pydantic v2 in `server/schemas/project.py` |
| **Rendering** | Runs Blender + FFmpeg | Runs Blender + FFmpeg (services wired) |
| **Task store** | Inline dict in `app.py` | `server/services/task_queue.py` (InMemoryTaskStore) |
| **Error model** | Ad-hoc | `server/services/errors.py` (ErrorCode enum + CineAnchorError) |
| **Web UI** | Serves `apps/web/` via StaticFiles | Serves `apps/web/` via StaticFiles |
| **Use for** | End-to-end demos, smoke checks | Production — schema validation, API contract, render pipeline |

Use `server.main:app` for production. The spike app (`server/app.py`) is the legacy pipeline.

## Environment Setup

Python virtual environment at `.venv/`. All Python commands use `.\.venv\Scripts\python.exe`.

```powershell
$env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
```

Verify: `.\.venv\Scripts\python.exe scripts\check_env.py`

Additional env vars used by the spike app: `CINEANCHOR_RENDER_JSON_DIR`, `CINEANCHOR_RENDER_SCRIPT`, `CINEANCHOR_MAKE_VIDEO_SCRIPT`, `CINEANCHOR_RENDER_TIMEOUT_SECONDS`, `POWERSHELL_PATH`.

## Common Commands

### Lint / Compile Check

```powershell
.\.venv\Scripts\python.exe -m py_compile server\main.py server\config.py server\routes\render.py server\services\errors.py server\schemas\project.py server\services\blender_service.py server\services\ffmpeg_service.py server\services\task_queue.py
```

### Run Tests (unittest — NOT pytest)

```powershell
# Backend unit tests (no hardware needed)
.\.venv\Scripts\python.exe -m unittest discover -s tests\backend

# Smoke / integration tests (no hardware needed)
.\.venv\Scripts\python.exe -m unittest discover -s tests\smoke

# JS vs Python parity tests (needs Node.js)
.\.venv\Scripts\python.exe -m unittest tests.parity.test_camera_math_parity

# All tests
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

### Run Server

```powershell
.\.venv\Scripts\python.exe -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

### Run Spike Web Server

```powershell
$env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/web/` for the UI.

## Key Files and Directories

| Path | Purpose |
|---|---|
| `server/main.py` | V0.1 formal FastAPI entry point |
| `server/app.py` | Legacy spike FastAPI app |
| `server/config.py` | Settings dataclass, env var → path resolution |
| `server/schemas/project.py` | Pydantic v2 ProjectJSON schema (the contract) |
| `server/routes/render.py` | V0.1 render API: POST /api/render, GET status + download |
| `server/routes/assets.py` | Asset upload: POST /api/assets/upload |
| `server/services/errors.py` | ErrorCode enum, CineAnchorError, error_payload |
| `server/services/task_queue.py` | InMemoryTaskStore + RenderTask dataclass |
| `server/services/blender_service.py` | Blender headless subprocess wrapper |
| `server/services/ffmpeg_service.py` | FFmpeg composition + enhancement |
| `server/services/comfy_service.py` | ComfyUI stub — NOT in standard path |
| `apps/web/` | Static frontend (zero-build HTML/CSS/JS) |
| `apps/web/viewport.html` | Loop 08 interactive 3D viewport (standalone page) |
| `apps/web/src/camera_math.js` | Pure-JS port of Catmull-Rom + SLERP (G1: no DOM/Three.js) |
| `apps/web/src/camera_presets.js` | JS preset library — 8 cinematic presets (ported from Python) |
| `apps/web/src/viewport.js` | Three.js scene + fly camera + recording (Phase 2-4) |
| `blender/scripts/render_project.py` | Production Blender render script (JSON-driven) |
| `blender/scripts/render_defaults.py` | Single source of truth for hardcoded defaults |
| `blender/scripts/camera_math.py` | Catmull-Rom + SLERP interpolation (pure Python) |
| `blender/scripts/camera_presets.py` | 8 cinematic camera presets |
| `tests/backend/` | Unit tests — 103 tests |
| `tests/smoke/` | ASGI integration tests — 13 tests |
| `tests/parity/` | JS vs Python cross-check tests — 24 tests (needs Node.js) |
| `docs/` | codemap, scope, parameters, project_json_schema, adr/ |
| `spikes/` | R&D spike archives (read-only reference) |
| `storage/` | Runtime output (gitignored) |

## Task Status State Machine

```
PENDING → RENDERING → COMPOSITING → (ENHANCING) → DONE
            ↓              ↓              ↓
          FAILED         FAILED         FAILED
```

ENHANCING is only entered when `ai_enhance.enabled=true`.

## Project JSON Schema (V0.1 Formal)

Defined by `ProjectJSON` in `server/schemas/project.py`. Key rules:
- `version` must be `"0.1"`
- Exactly one asset with `id="main_subject"`
- `character_intro` template requires asset `type=image`
- `product_orbit` template requires asset `type=glb`
- `ai_enhance.enabled` defaults to `false`
- `fps` is locked to `24` (Literal type)
- Aspect ratios: `9:16`, `16:9`, `1:1`; resolution: only `1080p`
- Camera: `preset: str|None` (loop 07), `keyframes: list|None`, `shots: list|None` (loop 08)

## CC Role in the CineAnchor Workflow

CC is the **execution agent** in this workflow. The full pipeline is:

```
/clear → 需求 → Andy 收敛需求/整理方案 → Requirements → 启明审批
→ Andy 产出 plans + 验收策略 → CC / plan agent 细化执行 plan
→ Andy plan-review gate → CC 执行 → TDD → 实现
→ git hook (单测/lint/格式/类型检查) → 视觉闸门 → parity 闸门
→ 启明验收签收 → ADR (Andy-only) → 更新 CLAUDE.md/知识库 → push → /clear
```

### CC's Specific Responsibilities

| Phase | Owner | What CC Does |
|-------|-------|-------------|
| 需求收敛 | Andy | CC 不参与 — 等待 Andy 产出 Requirements |
| Requirements 审批 | 启明 | CC 不参与 |
| Plans + 验收策略 | Andy | CC 不参与 — 等待 Andy 产出 plan |
| **细化执行 plan** | **CC + plan agent** | 拿到 Andy 的 plan 后，用 plan agent 拆解为可执行的具体步骤，产出 task list |
| **Plan-review gate** | Andy | CC 提交细化后的 plan，等待 Andy 批准再继续 |
| **CC 执行** | **CC** | 按 approved plan 逐步执行，每步完成后自检 |
| **TDD 编写测试** | **CC** | 先写测试，确认测试 FAIL，再写实现 |
| **实现** | **CC** | 写代码，跑测试，修到绿 |
| **Git hook 闸门** | **CC** | 确保单测全绿 + lint 通过 + 格式正确 + 类型检查无报错 |
| **视觉闸门** | **CC** | 检查关键帧画面正确性、Blender 运行时无报错、输出 MP4 可播放 |
| **Parity 闸门** | **CC** | 前端预览 ≈ 实渲结果；如有偏差必须记录或修复 |
| 启明验收 | 启明 | CC 不参与 — 如驳回，回到执行/plan 修正 |
| ADR 决策记录 | Andy | CC 不参与 |
| 更新 CLAUDE.md / 沉淀 | **CC + Andy** | 将本轮经验写入 CLAUDE.md 和知识库 |

### CC Execution Rules

1. **必须先有 approved plan 再动手写代码。** 没有通过 Andy plan-review gate 的 task，CC 不执行实现。
2. **TDD 铁律：先写测试，确认 FAIL，再写实现，跑到 PASS。** 不允许先写实现再补测试。
   - **写前闸门：每次 Write/Edit 创建或修改源码文件前，必须确认对应的测试文件已存在且至少有一个会 FAIL 的测试用例。** 没有测试就动手 = 违反流程。
   - 唯一例外：纯文档文件（`*.md`）、配置文件（`*.json`）、HTML 模板。
3. **每个 task 完成后，自检以下闸门再报告：**
   - [ ] `python -m unittest discover -s tests` 全绿
   - [ ] `python -m py_compile` 目标文件通过
   - [ ] 视觉输出（如有渲染）：关键帧无黑帧/花帧/明显异常
   - [ ] Parity（如涉及前端）：预览参数 ≈ Blender 实渲参数
4. **遇到阻塞或偏离 plan 时，停下来报告 Andy，不自行改 plan。**
5. **变更报告格式** 遵循 `AGENTS.md` 的 Change Report Format — 每个完成的 task 报告 changed files / behavior / API / schema / tests / commands / risks。
6. **CC 不修改 Requirements、不审批自己的 plan、不做 ADR。** 这些是 Andy 或启明的职责。

### Before Marking a Task "Done"

CC must confirm ALL of these before handing off to 启明验收:

- [ ] All unit tests pass (`python -m unittest discover -s tests`)
- [ ] All smoke tests pass
- [ ] Parity tests pass (if JS/Python math is touched)
- [ ] No lint errors (py_compile clean on all changed files)
- [ ] Blender renders without errors (if rendering path touched)
- [ ] Output MP4 is playable and visually correct
- [ ] Keyframes inspected: no black frames, no geometry collapse, no texture corruption
- [ ] Frontend preview matches Blender output within tolerance (if camera/3D touched)
- [ ] Change report written (per AGENTS.md format)
- [ ] CLAUDE.md updated if new conventions/constraints discovered

## Key Constraints

- Blender 5.1.2 at `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`
- FFmpeg 8.1.1 at `E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe`
- Node.js required for parity tests (JS↔Python cross-check via `subprocess.run("node", ...)`)
- `python-multipart` required for asset upload route (install: `pip install python-multipart`)
- ComfyUI must NOT be called by the standard V0.1 render path
- Serial execution only (never Blender + ComfyUI concurrently — OOM on 12GB VRAM)
- Local-only, no cloud, no Redis, no Celery
- In-memory task store lost on restart
- `unittest` framework (NOT pytest)
