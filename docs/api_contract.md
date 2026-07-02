# CineAnchor V0.1 API Contract

This contract covers the V0.1 backend with render execution. The API validates
formal Project JSON and executes Blender + FFmpeg rendering to produce
downloadable MP4 files.

The Project JSON schema has been expanded in loop-06 with optional model
transform, lighting overrides, and stage element toggles. See
`docs/parameters.md` for the complete parameter table and
`docs/project_json_schema.md` for the formal schema definition.

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
  "standard_output_path": null,
  "enhanced_output_path": null,
  "warning_code": null,
  "warning_message": null,
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
| `ENHANCING` | Optional AI enhancement is running. Only entered when `ai_enhance.enabled=true`. Uses conservative FFmpeg filters (`eq` + `unsharp`). |
| `DONE` | MP4 output is ready. `output_path` is set. |
| `FAILED` | Task failed and exposes `error_code` plus `message`. |

Standard path (ai_enhance.enabled=false):

```text
PENDING → RENDERING → COMPOSITING → DONE
```

Enhancement path (ai_enhance.enabled=true):

```text
PENDING → RENDERING → COMPOSITING → ENHANCING → DONE
```

On failure at any step:

```text
→ FAILED (with error_code and message)
```

If `ai_enhance.enabled=true` and enhancement fails, the task still becomes
`DONE` with `warning_code=AI_ENHANCE_SKIPPED`. The standard MP4 is returned.
The render is never failed because of enhancement failure.

## Download

`GET /api/render/{task_id}/download`

Behavior:

- Task not found → HTTP 404, `TASK_NOT_FOUND`
- Task exists but status is not DONE → HTTP 409, `OUTPUT_NOT_READY`
- Task is DONE but output file missing → HTTP 404, `OUTPUT_NOT_FOUND`
- Task is DONE with output file present → HTTP 200, `video/mp4` FileResponse

Download priority: enhanced MP4 (`enhanced_output_path`) if available,
otherwise standard MP4 (`output_path` / `standard_output_path`).

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
- `AI_ENHANCE_SKIPPED` — enhancement failed, standard MP4 returned (warning, not error)
- `UNSUPPORTED_ASSET_FORMAT` — uploaded file format is not PNG or GLB

`COMFY_ENHANCE_FAILED` is reserved for a future optional enhancement path. It
must be treated as a warning/fallback condition and must not fail the standard
Blender + FFmpeg render path.

## AI Enhancement (V0.1)

The V0.1 enhancement path uses conservative FFmpeg filters only — no ComfyUI
is called. The preset `conservative_premium` applies `eq` (brightness/contrast/
saturation/gamma) and `unsharp` (sharpening) filters derived from Route 3 spike
color-reference analysis.

- Enhancement is **optional** — enabled by `ai_enhance.enabled=true` in Project JSON.
- Enhanced output is written to `storage/exports/{task_id}/enhanced.mp4`.
- If enhancement fails for any reason, the task still reaches `DONE` with
  `warning_code=AI_ENHANCE_SKIPPED` and the standard MP4 is returned.
- ComfyUI is **not** part of the V0.1 enhancement path; it is a future hook only.

## Keyframe Endpoints (Loop 08)

`POST /api/keyframes`

Receives recorded camera keyframes from the interactive 3D viewport. Body: array of shot objects.

```json
[{
  "index": 0,
  "keyframes": [
    {"t": 0.0, "pos": [0, -5, 2], "quat": [0, 0, 0, 1], "fov": 50}
  ],
  "cut": false
}]
```

Response: `{"status": "ok", "shots": 1, "keyframes": 4}`

---

`GET /api/keyframes`

Returns the most recently POSTed keyframes (in-memory only, lost on restart).

Response: `{"keyframes": [{...}]}`

---

## Asset Upload

`POST /api/assets/upload`

Request: `multipart/form-data` with a single `file` field.

The endpoint identifies the asset type by file extension:
- `.png` → `image`
- `.glb` → `glb`

Success response:

```json
{
  "asset_id": "a1b2c3d4e5f6",
  "path": "assets/a1b2c3d4e5f6/hero.png",
  "type": "image",
  "filename": "hero.png"
}
```

Error response (unsupported format):

```json
{
  "error_code": "UNSUPPORTED_ASSET_FORMAT",
  "message": "不支持的素材格式。",
  "detail": "File extension is not supported: file.txt. Supported formats: PNG, GLB."
}
```

Note: The upload endpoint does **not** validate template/asset-type coupling
(e.g., character_intro requires PNG). That validation is performed by
`POST /api/render` via the ProjectJSON schema validator.

## Web UI

The frontend is served by the same FastAPI process at `/web/`. Start the
server and open `http://127.0.0.1:8000/web/`.

### Render Flow (from the frontend perspective)

1. User selects template (character_intro or product_orbit)
2. User uploads an asset (PNG for character_intro, GLB for product_orbit)
3. User sets title, subtitle, aspect ratio (9:16 / 16:9), and optional parameter overrides
4. User chooses render mode: 快速版 (standard) or 精品版 (mild enhancement)
5. Frontend builds formal V0.1 Project JSON and POSTs to `/api/render`
6. Frontend polls `GET /api/render/{task_id}/status` every 3s (first 30s) then 10s
7. When status is DONE, frontend shows download button pointing to `/api/render/{task_id}/download`
8. If warning_code is set, a non-blocking warning banner is shown
