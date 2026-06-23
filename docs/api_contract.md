# CineAnchor V0.1 API Contract

This contract covers the V0.1 backend with render execution. The API validates
formal Project JSON and executes Blender + FFmpeg rendering to produce
downloadable MP4 files.

## Health

`GET /health`

Response:

```json
{
  "status": "ok"
}
```

## Create Render Task

`POST /api/render`

Request body: formal Project JSON as documented in `docs/project_json_schema.md`.

Behavior:

- validates Project JSON with Pydantic
- rejects invalid templates and invalid asset/template combinations
- creates an in-memory task
- returns `PENDING` immediately
- starts a background thread that executes Blender → FFmpeg → DONE
- does not call ComfyUI (standard path)
- does not require a database

Success response:

```json
{
  "task_id": "1f2d3c4b5a6e7890",
  "status": "PENDING"
}
```

Invalid Project JSON response:

```json
{
  "error_code": "INVALID_PROJECT_JSON",
  "message": "Project JSON is invalid",
  "detail": "..."
}
```

## Task Status

`GET /api/render/{task_id}/status`

Success response:

```json
{
  "task_id": "1f2d3c4b5a6e7890",
  "project_id": "demo-character-intro",
  "status": "PENDING",
  "error_code": null,
  "message": "Queued",
  "output_path": null,
  "created_at": 1782180000.0,
  "updated_at": 1782180000.0
}
```

Task status values:

| Status | Meaning |
|---|---|
| `PENDING` | Task accepted and waiting. |
| `RENDERING` | Blender render is running. |
| `COMPOSITING` | FFmpeg composition is running. |
| `ENHANCING` | Optional AI enhancement. Defined in schema but not entered in V0.1 — `ai_enhance.enabled=true` is logged as a warning and standard MP4 is returned. |
| `DONE` | MP4 output is ready. `output_path` is set. |
| `FAILED` | Task failed and exposes `error_code` plus `message`. |

Standard path:

```text
PENDING → RENDERING → COMPOSITING → DONE
```

On failure at any step:

```text
→ FAILED (with error_code and message)
```

If `ai_enhance.enabled=true`: a warning is logged and the standard path
completes to DONE without AI enhancement. The render is not failed.

## Download

`GET /api/render/{task_id}/download`

Behavior:

- Task not found → HTTP 404, `TASK_NOT_FOUND`
- Task exists but status is not DONE → HTTP 409, `OUTPUT_NOT_READY`
- Task is DONE but output file missing → HTTP 404, `OUTPUT_NOT_FOUND`
- Task is DONE with output file present → HTTP 200, `video/mp4` FileResponse

## Error Model

All application errors use this shape:

```json
{
  "error_code": "INVALID_PROJECT_JSON",
  "message": "Project JSON is invalid",
  "detail": "..."
}
```

Required V0.1 error codes:

- `ASSET_NOT_FOUND` — asset path in Project JSON does not exist on disk
- `INVALID_PROJECT_JSON` — Pydantic validation failure
- `ASSET_IMPORT_FAILED` — Blender could not load the asset (reserved)
- `UNSUPPORTED_TEMPLATE` — template not recognized (reserved)
- `BLENDER_RENDER_FAILED` — Blender subprocess exited non-zero or not found
- `FFMPEG_COMPOSE_FAILED` — FFmpeg subprocess exited non-zero or not found
- `COMFY_ENHANCE_FAILED` — reserved for future optional enhancement (must not fail standard path)
- `RENDER_TIMEOUT` — Blender render exceeded 900s timeout
- `TASK_NOT_FOUND` — task ID not found in the in-memory store
- `OUTPUT_NOT_READY` — download attempted before task reached DONE
- `OUTPUT_NOT_FOUND` — task is DONE but MP4 file is missing on disk

`COMFY_ENHANCE_FAILED` is reserved for a future optional enhancement path. It
must be treated as a warning/fallback condition and must not fail the standard
Blender + FFmpeg render path.
