# CineAnchor Neo Spike Results

## Route 2: JSON-Driven Template Rendering

Status: PASS

Goal question: Can one JSON file drive template, asset path, camera motion, duration, fps, aspect ratio, title, and subtitle?

Conclusion: PASS for the current Spike scope. One Project JSON now drives `character_intro` from PNG and `product_orbit` from GLB using Blender Eevee plus FFmpeg.

| Field | Result |
|---|---|
| Commands run | Blender headless rendered `projects/character_intro.json` and `projects/product_orbit.json`; FFmpeg composed both MP4 files; ffprobe validated both outputs. |
| Input assets | `spikes/render_json/input/hero.png`, `spikes/render_json/input/model.glb` |
| Output artifacts | `spikes/render_json/output/character_intro/final.mp4`, `spikes/render_json/output/product_orbit/final.mp4` |
| Render duration | character_intro: 45.58s; product_orbit: 19.18s |
| FFmpeg duration | character_intro: 0.34s; product_orbit: 0.23s |
| Machine / GPU notes | Blender 5.1.2, Eevee (`BLENDER_EEVEE`). |
| JSON fields supported | `template`, `asset.type`, `asset.path`, `camera.motion`, `duration`, `fps`, `output.width`, `output.height`, `output.frames_dir`, `output.video_path`, `text.title`, `text.subtitle` |
| asset.path switch | PASS: PNG and GLB project files render different subjects without code changes. |
| text.title switch | PASS: rendered titles come from JSON (`New Hero Arrival`, `Product Orbit`). |
| aspect ratio switch | PASS: ffprobe confirmed 720x1280 and 1280x720 outputs. |
| duration / fps switch | PASS: 4s at 24fps produced 96 frames; 4s at 12fps produced 48 frames. |
| camera.motion switch | PASS: `dolly_in` and front-arc `orbit` camera animation were exercised. |
| ffprobe | PASS: both outputs are h264 MP4 files with expected resolution, duration, fps, and frame count. |
| Pass / Fail | PASS |
| Blocking errors | None. |
| Next decision | Route 2 is viable as a Spike. Keep the JSON shape provisional until more templates are validated. |

Known risks:

- `product_orbit` currently uses a front-arc orbit, not full 360-degree orbit, to keep the fixed stage and text readable.
- `prop_showcase` is outside this task's current scope.
- This Spike JSON is not the production schema.
- Render inputs and outputs are local runtime artifacts and are intentionally ignored by Git.

## Route 4: Web To Local Render Chain

Status: PASS

Goal question: Can a minimal web UI call FastAPI, trigger Blender JSON rendering, run FFmpeg composition, poll task status, and download the final MP4?

Conclusion: PASS for the current Spike scope. A static local page calls a FastAPI app, which generates a Route 2 Project JSON, runs Blender Eevee headless, runs FFmpeg composition, exposes task status, and returns the MP4 through a download endpoint.

| Field | Result |
|---|---|
| Commands run | Installed FastAPI/uvicorn into `.venv`; compiled `server/app.py` and `server/smoke_web_chain.py`; ran `server/smoke_web_chain.py`; ran ffprobe on both Web-generated MP4s. |
| Input assets | `spikes/render_json/input/hero.png`, `spikes/render_json/input/model.glb` |
| Output artifacts | `spikes/render_json/output/web/5e056af9c3294a8c8f91954e9a47b58f/final.mp4`, `spikes/render_json/output/web/73f8c80da1394e2bacb4cc4d3f0d4fc1/final.mp4` |
| Render duration | character_intro: 51.68s; product_orbit: 20.95s |
| FFmpeg duration | character_intro: 0.65s; product_orbit: 0.50s |
| Machine / GPU notes | Blender 5.1.2, Eevee (`BLENDER_EEVEE`), FFmpeg 8.1.1 Gyan build. |
| API endpoints | `POST /api/render`, `GET /api/render/{task_id}`, `GET /api/render/{task_id}/download` |
| Status transitions | PASS: poll observed `RENDERING -> COMPOSITING -> DONE` for both templates. |
| Download | PASS: API download returned MP4 bytes for both templates. |
| Failure response | PASS: invalid template returned HTTP 400 with `error_code=UNSUPPORTED_TEMPLATE`. |
| ffprobe | PASS: character output is h264 720x1280, 24fps, 4s, 96 frames; product output is h264 1280x720, 12fps, 4s, 48 frames. |
| Pass / Fail | PASS |
| Blocking errors | None for the web-to-render chain. Persistent background server launch from this Codex shell was unreliable; foreground uvicorn and in-process HTTP smoke validation worked. |
| Next decision | Route 4 is viable as a Spike. Keep the task store in-memory until production queue requirements are validated. |

Known risks:

- In-memory task state is lost on server restart.
- No queue, cancellation, concurrency policy, or database exists in this Spike.
- Runtime sample assets and generated outputs are ignored by Git and must exist locally.
- `BLENDER_PATH` and `FFMPEG_PATH` must be configured per machine.
- The current Project JSON remains provisional Spike schema.

## Route 3: ComfyUI Keyframe Enhancement

Status: FAIL for Route 3 acceptance.

Goal question: Can ComfyUI improve Blender output without subject deformation, text corruption, or severe flicker?

Conclusion: FAIL for the current Route 3 acceptance. The isolated keyframe extraction and ComfyUI API client scripts worked, 4 keyframes per input video were enhanced, and side-by-side comparisons were generated. However, direct full-frame SDXL img2img corrupted the `character_intro` subtitle in 4/4 reviewed frames.

| Field | Result |
|---|---|
| Commands run | Checked ComfyUI with `D:\ComfyUI\comfyui_client.py`; extracted keyframes with FFmpeg; ran ComfyUI API client; generated side-by-side comparisons; compiled Python script. |
| Input assets | `spikes/render_json/output/web/5e056af9c3294a8c8f91954e9a47b58f/final.mp4`, `spikes/render_json/output/web/73f8c80da1394e2bacb4cc4d3f0d4fc1/final.mp4` |
| Output artifacts | Raw keyframes under `spikes/comfy_enhance/output/*/keyframes_raw/`; enhanced frames under `spikes/comfy_enhance/output/*/keyframes_enhanced/`; comparisons under `spikes/comfy_enhance/output/*/comparisons/`; `spikes/comfy_enhance/output/comfy_run_report.json` |
| ComfyUI URL | `http://127.0.0.1:8188`; script now also reads `COMFYUI_API_URL` |
| Workflow | `spikes/comfy_enhance/workflows/conservative_sdxl_img2img_api.json` |
| Model / checkpoint notes | ComfyUI `0.25.0`; checkpoint `RealVisXL_V5.0_Lightning_fp16.safetensors`; 1116 nodes available. |
| Per-frame processing time | character_intro: 7.444s, 3.306s, 3.237s, 3.222s; product_orbit: 3.234s, 3.233s, 3.257s, 3.192s. |
| Machine / GPU notes | NVIDIA GeForce RTX 5070 Ti, 16303 MB VRAM; about 2124 MB used before run; sampled peak about 11421 MB; about 8902 MB used after run because ComfyUI kept the model resident. |
| Visual review | Subject shape mostly preserved; product frames acceptable; character subtitle corrupted in 4/4 enhanced frames. |
| Pass / Fail | FAIL |
| Blocking errors | None after ComfyUI was started. Acceptance failed because text corruption is unacceptable. |
| Next decision | Do not integrate ComfyUI into the Web render chain yet. Retry only with pre-text enhancement or masked text preservation. |

Known risks:

- Direct full-frame img2img over rendered text is unsafe; rendered text should be applied after enhancement or protected by a mask.
- ComfyUI retains GPU memory after processing and may conflict with Blender unless GPU access is serialized or the model is unloaded.
- Low-denoise SDXL img2img can still alter UI/text details; manual side-by-side review remains required.
- This spike intentionally processes keyframes only, not all video frames.
