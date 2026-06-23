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

## Route 3: ComfyUI Conservative AI Enhancement

Status: PARTIAL

Goal question: Can Route 3 be included in V0.1 as conservative AI enhancement without subject deformation, text corruption, flicker, or unacceptable processing time?

Conclusion: PARTIAL. Direct full-frame img2img over final frames failed because it corrupted rendered subtitle text. Conservative ComfyUI reference plus FFmpeg enhancement works end-to-end and final MP4s remain stable because ComfyUI frames are not used as final frames. Text and subject/product shape are stable. However, the visual improvement is light, so Route 3 should be treated as an optional V0.1 preset rather than a core selling point.

### Previous direct full-frame img2img: FAIL

Direct full-frame SDXL img2img processed extracted keyframes successfully, but corrupted the `character_intro` subtitle in 4 of 4 reviewed frames. This validates the V0.1 decision to exclude full-frame AI video regeneration and to keep text-bearing final frames in Blender/FFmpeg output.

### Conservative ComfyUI reference + FFmpeg enhancement: PARTIAL

| Field | Result |
|---|---|
| Commands run | Created `spike/comfy-lut-enhance`; parsed PowerShell scripts; compiled Python scripts; extracted keyframes; ran ComfyUI reference workflow; analyzed color parameters; applied FFmpeg enhancement; generated comparisons; ran ffprobe on enhanced MP4s. |
| Input assets | `spikes/render_json/output/web/5e056af9c3294a8c8f91954e9a47b58f/final.mp4`, `spikes/render_json/output/web/73f8c80da1394e2bacb4cc4d3f0d4fc1/final.mp4` |
| Output artifacts | `spikes/comfy_lut_enhance/output/character_intro/enhanced_ffmpeg.mp4`, `spikes/comfy_lut_enhance/output/product_orbit/enhanced_ffmpeg.mp4`, raw/reference/comparison images under `spikes/comfy_lut_enhance/output/*/`, `spikes/comfy_lut_enhance/output/color_params.json` |
| ComfyUI URL | `http://127.0.0.1:8188` |
| Workflow | `spikes/comfy_lut_enhance/workflows/conservative_sdxl_reference_api.json` |
| Model / checkpoint notes | ComfyUI checkpoint `RealVisXL_V5.0_Lightning_fp16.safetensors`; workflow settings `steps=6`, `cfg=1.4`, `denoise=0.08`. |
| Per-frame processing time | character_intro: 2.500s, 2.160s, 2.177s, 2.191s; product_orbit: 2.143s, 2.150s, 2.199s, 2.191s. |
| Machine / GPU notes | NVIDIA GeForce RTX 5070 Ti, 16303 MB VRAM; about 8989 MB used before ComfyUI reference run; sampled peak 9306 MB; about 8944 MB after run. |
| Color parameters | character_intro: brightness 0.0024, contrast 0.986, saturation 0.95, gamma 0.9988; product_orbit: brightness 0.0035, contrast 0.9806, saturation 1.0197, gamma 0.9982. |
| FFmpeg filters | `eq` plus `unsharp=5:5:0.32:3:3:0.12`; exact filter strings are recorded in `docs/spike_report_comfy_lut.md`. |
| ffprobe | PASS: character output is h264 720x1280, 24fps, 4s, 96 frames; product output is h264 1280x720, 12fps, 4s, 48 frames. |
| Visual review | Final FFmpeg output preserves text and subject/product shape. Improvement is mostly subtle sharpening and slight color adjustment. |
| Pass / Fail | PARTIAL |
| Blocking errors | One script bug in PowerShell JSON array loading was fixed; no remaining blocker in the conservative Route 3 chain. |
| Next decision | Keep full-frame AI video regeneration excluded from V0.1. Keep conservative FFmpeg/LUT enhancement as an optional preset only. |

Known risks:

- This is not a true LUT solver; it estimates broad video-wide parameters.
- ComfyUI reference images can still corrupt text and must not become final frames.
- Visual lift is too mild to position as a core V0.1 AI feature or portfolio selling point.
- ComfyUI retains GPU memory and may conflict with Blender if run concurrently.
- Non-developer feedback for conservative Route 3 has not been collected yet; manual review remains pending.
