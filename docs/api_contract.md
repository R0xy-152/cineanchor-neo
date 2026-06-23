# CineAnchor V0.1 API Contract

This contract covers the Phase A backend foundation. The API accepts and
validates formal Project JSON but does not need to execute Blender rendering yet.

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

Phase A behavior:

- validates Project JSON with Pydantic
- rejects invalid templates and invalid asset/template combinations
- creates an in-memory task
- returns `PENDING`
- does not call Blender yet
- does not call ComfyUI
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
| `ENHANCING` | Optional AI enhancement is running. Only valid when `ai_enhance.enabled=true`. |
| `DONE` | MP4 output is ready. |
| `FAILED` | Task failed and exposes `error_code` plus `message`. |

Default standard path:

```text
PENDING -> RENDERING -> COMPOSITING -> DONE
```

## Download

`GET /api/render/{task_id}/download`

The endpoint is reserved for the render execution phase. During Phase A it
returns a readable `OUTPUT_NOT_READY` error unless a future render service marks
the in-memory task as `DONE`.

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

- `ASSET_NOT_FOUND`
- `INVALID_PROJECT_JSON`
- `ASSET_IMPORT_FAILED`
- `UNSUPPORTED_TEMPLATE`
- `BLENDER_RENDER_FAILED`
- `FFMPEG_COMPOSE_FAILED`
- `COMFY_ENHANCE_FAILED`
- `RENDER_TIMEOUT`

`COMFY_ENHANCE_FAILED` is reserved for a future optional enhancement path. It
must be treated as a warning/fallback condition and must not fail the standard
Blender + FFmpeg render path.
