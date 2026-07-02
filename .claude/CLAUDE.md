# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

- **Repo:** R0xy-152/cineanchor-neo
- **Goal:** Generate 8-15 second game promo videos from PNG images or GLB models
- **Core chain:** Web → FastAPI → Project JSON → Blender Eevee → FFmpeg → MP4
- **Docs:** `README.md` (overview), `AGENTS.md` (task rules), `docs/codemap.md` (module map)

## Current Phase: Loop 08 — Interactive Camera Control ✅

Loop 08 complete. All gates (4, 6, 7) closed. 启鸣签收 2026-07-02.

**Critical lesson — Blender quaternion convention:**
`Object.rotation_quaternion` expects `(w, x, y, z)`. Our `_quat_from_look()` returns `[x, y, z, w]`. Always convert with `(q[3], q[0], q[1], q[2])` when assigning to Blender objects. This bug cost days of debugging.

## Environment

```powershell
$env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
```

Python venv at `.venv/`. Verify: `python scripts\check_env.py`

## Essential Commands

```powershell
# Run server
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000

# Run all tests (unittest — NOT pytest)
python -m unittest discover -s tests
```

## Key Constraints

- Blender 5.1.2 headless, FFmpeg 8.1.1
- Node.js required for parity tests (JS↔Python cross-check)
- `python-multipart` required for asset upload
- Serial execution only (no concurrent Blender/ComfyUI — OOM risk)
- Local-only: no cloud, no Redis, no Celery. In-memory task store lost on restart.
- ComfyUI must NOT be called by standard render path
- `unittest` framework (NOT pytest)

## Architecture

Two FastAPI apps. Use `server.main:app` for production. See `docs/codemap.md` for full directory layout, call flow diagram, and module descriptions.

## CC Execution Rules

1. **TDD 铁律：先写测试，确认 FAIL，再写实现，跑到 PASS。** 不允许先写实现再补测试。
2. **每个 task 完成前自检：** tests 全绿，py_compile 通过，视觉输出无黑帧/花帧。
3. **遇到阻塞或偏离 plan 时，停下来报告 Andy，不自行改 plan。**
4. **CC 不修改 Requirements、不审批自己的 plan、不做 ADR。**

## CLAUDE.md 维护规则

- 写入与删除需克制，防止上下文臃肿
- 信息优先放在 README / `docs/codemap.md` / `AGENTS.md`，CLAUDE.md 只放"新会话必须知道"的内容
- 每个 Loop 结束后清理过时内容，不堆积历史
