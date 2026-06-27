# Route 4 Spike Report: Web To Local Render Chain

Status: PASS

Branch: `spike/web-local-render-chain`

Goal question: Can a minimal Web UI call FastAPI, trigger Blender JSON rendering, run FFmpeg composition, poll task status, and download the final MP4?

## Implementation

- Added a FastAPI app in `server/app.py`.
- Added a static local UI in `apps/web/`.
- Added `server/smoke_web_chain.py` to run a repeatable HTTP smoke check.
- Reused `spikes/render_json/render_project.py` and `spikes/render_json/make_video.ps1`.
- Used in-memory task state only.
- Generated per-task Project JSON files under `spikes/render_json/output/web/<task_id>/project.json`.

## API Endpoints

- `POST /api/render`
- `GET /api/render/{task_id}`
- `GET /api/render/{task_id}/download`

## Commands Run

```powershell
git status --short --branch
git stash list
git stash show --stat --include-untracked 'stash@{0}'
git stash show --stat --include-untracked 'stash@{1}'
git add spikes/render_json docs/spike_results.md docs/spike_report_json.md
git commit -m "spike: validate json-driven rendering"
git add .gitignore
git commit -m "chore: ignore local render artifacts"
git switch -c spike/web-local-render-chain
```

```powershell
.\.venv\Scripts\python.exe -m py_compile server\app.py server\smoke_web_chain.py
.\.venv\Scripts\python.exe server\smoke_web_chain.py
```

```powershell
E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,duration,nb_frames -of default=noprint_wrappers=1 E:\cineanchor\spikes\render_json\output\web\5e056af9c3294a8c8f91954e9a47b58f\final.mp4
E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,duration,nb_frames -of default=noprint_wrappers=1 E:\cineanchor\spikes\render_json\output\web\73f8c80da1394e2bacb4cc4d3f0d4fc1\final.mp4
```

## Smoke Results

```text
ROUTE4_PAGE_STATUS=200
ROUTE4_INVALID_TEMPLATE_STATUS=400 error_code=UNSUPPORTED_TEMPLATE
ROUTE4_CREATED template=character_intro task_id=5e056af9c3294a8c8f91954e9a47b58f
ROUTE4_STATUS task_id=5e056af9c3294a8c8f91954e9a47b58f status=RENDERING
ROUTE4_STATUS task_id=5e056af9c3294a8c8f91954e9a47b58f status=COMPOSITING
ROUTE4_STATUS task_id=5e056af9c3294a8c8f91954e9a47b58f status=DONE
ROUTE4_TASK template=character_intro task_id=5e056af9c3294a8c8f91954e9a47b58f status=DONE output=spikes\render_json\output\web\5e056af9c3294a8c8f91954e9a47b58f\final.mp4 blender_seconds=51.68 ffmpeg_seconds=0.65
ROUTE4_DOWNLOAD template=character_intro status=200 bytes=459085
ROUTE4_CREATED template=product_orbit task_id=73f8c80da1394e2bacb4cc4d3f0d4fc1
ROUTE4_STATUS task_id=73f8c80da1394e2bacb4cc4d3f0d4fc1 status=RENDERING
ROUTE4_STATUS task_id=73f8c80da1394e2bacb4cc4d3f0d4fc1 status=COMPOSITING
ROUTE4_STATUS task_id=73f8c80da1394e2bacb4cc4d3f0d4fc1 status=DONE
ROUTE4_TASK template=product_orbit task_id=73f8c80da1394e2bacb4cc4d3f0d4fc1 status=DONE output=spikes\render_json\output\web\73f8c80da1394e2bacb4cc4d3f0d4fc1\final.mp4 blender_seconds=20.95 ffmpeg_seconds=0.5
ROUTE4_DOWNLOAD template=product_orbit status=200 bytes=359468
```

## Output Artifacts

| Template | MP4 | Render | FFmpeg |
|---|---|---:|---:|
| `character_intro` | `spikes/render_json/output/web/5e056af9c3294a8c8f91954e9a47b58f/final.mp4` | 51.68s | 0.65s |
| `product_orbit` | `spikes/render_json/output/web/73f8c80da1394e2bacb4cc4d3f0d4fc1/final.mp4` | 20.95s | 0.50s |

## ffprobe

`character_intro`:

```text
codec_name=h264
width=720
height=1280
r_frame_rate=24/1
duration=4.000000
nb_frames=96
```

`product_orbit`:

```text
codec_name=h264
width=1280
height=720
r_frame_rate=12/1
duration=4.000000
nb_frames=48
```

## Acceptance

- User can open the local page: PASS (`/web/` returned 200 during smoke).
- User can select `character_intro` and generate MP4: PASS.
- User can select `product_orbit` and generate MP4: PASS.
- Frontend/API status changes are observable: PASS (`RENDERING`, `COMPOSITING`, `DONE`).
- Final MP4 can be downloaded: PASS.
- No manual Blender or FFmpeg command is required after clicking Generate: PASS.
- Failure returns readable `error_code`: PASS (`UNSUPPORTED_TEMPLATE`).

## Known Risks

- The task store is in memory and disappears on restart.
- The Spike has no queue, cancellation, retry, database, or multi-user isolation.
- `BLENDER_PATH` and `FFMPEG_PATH` must be configured per machine.
- Runtime sample assets are ignored by Git and must exist locally.
- Persistent background uvicorn launch from this Codex shell was unreliable because of Windows process/environment handling; foreground uvicorn and in-process HTTP smoke validation worked.
- The Project JSON schema remains provisional for Spike validation.

## Decision

Route 4 passes. The Web-to-local-render chain is viable for a local Spike and can call the existing JSON render path without manual Blender or FFmpeg commands.
