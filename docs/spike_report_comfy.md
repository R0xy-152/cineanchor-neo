# Route 3 Spike Report: ComfyUI Keyframe Enhancement

Date: 2026-06-23

Branch: `spike/comfy-keyframe-enhance`

Status: FAIL for this run, blocked by ComfyUI API availability.

## Goal

Validate whether ComfyUI can enhance Blender-rendered keyframes without subject deformation, text corruption, or severe flicker.

## Scope

This spike is isolated from the Web/FastAPI render path. It does not modify `server/app.py`, `apps/web/`, Route 2 renderer code, or Route 4 code.

## Workflow Used

- ComfyUI URL attempted: `http://127.0.0.1:8188`
- Workflow file: `spikes/comfy_enhance/workflows/conservative_sdxl_img2img_api.json`
- Workflow type: SDXL img2img, low-denoise conservative enhancement
- Settings in script defaults: `steps=8`, `cfg=1.6`, `denoise=0.12`
- Checkpoint selection: automatic via ComfyUI `/object_info`, preferring `RealVisXL`, `Lightning`, then SDXL names
- Local checkpoint files observed on disk:
  - `D:\ComfyUI\models\checkpoints\RealVisXL_V5.0_Lightning_fp16.safetensors`
  - `D:\ComfyUI\models\checkpoints\sd_xl_base_1.0_0.9vae.safetensors`

The checkpoint was not confirmed through the ComfyUI API because the API was not reachable.

## Input Paths

The extractor found existing Route 4 Web MP4 outputs and extracted 4 keyframes from each:

- `spikes/render_json/output/web/5e056af9c3294a8c8f91954e9a47b58f/final.mp4`
- `spikes/render_json/output/web/73f8c80da1394e2bacb4cc4d3f0d4fc1/final.mp4`

## Output Paths

Generated raw keyframes:

- `spikes/comfy_enhance/output/character_intro/keyframes_raw/frame_01.png`
- `spikes/comfy_enhance/output/character_intro/keyframes_raw/frame_02.png`
- `spikes/comfy_enhance/output/character_intro/keyframes_raw/frame_03.png`
- `spikes/comfy_enhance/output/character_intro/keyframes_raw/frame_04.png`
- `spikes/comfy_enhance/output/product_orbit/keyframes_raw/frame_01.png`
- `spikes/comfy_enhance/output/product_orbit/keyframes_raw/frame_02.png`
- `spikes/comfy_enhance/output/product_orbit/keyframes_raw/frame_03.png`
- `spikes/comfy_enhance/output/product_orbit/keyframes_raw/frame_04.png`

Generated manifest:

- `spikes/comfy_enhance/output/keyframes_manifest.json`

ComfyUI run report:

- `spikes/comfy_enhance/output/comfy_run_report.json`

Expected enhanced output directories, not populated in this run:

- `spikes/comfy_enhance/output/character_intro/keyframes_enhanced/`
- `spikes/comfy_enhance/output/product_orbit/keyframes_enhanced/`

Expected comparison directories, skipped because enhanced frames were unavailable:

- `spikes/comfy_enhance/output/character_intro/comparisons/`
- `spikes/comfy_enhance/output/product_orbit/comparisons/`

Generated outputs are ignored by Git.

## Commands Run

```powershell
git switch -c spike/comfy-keyframe-enhance
```

Result: branch created.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8188/system_stats" -TimeoutSec 5
```

Result: failed, remote server refused the connection.

```powershell
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader,nounits
```

Result: `NVIDIA GeForce RTX 5070 Ti, 16303, 1803`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\spikes\comfy_enhance\extract_keyframes.ps1
```

Result: PASS, extracted 8 raw keyframes total.

```powershell
.\.venv\Scripts\python.exe .\spikes\comfy_enhance\run_comfy_enhance.py
```

Result: FAIL, `ComfyUI is not reachable at http://127.0.0.1:8188`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\spikes\comfy_enhance\make_comparisons.ps1
```

Result: PASS as a safe no-op, comparison generation skipped because enhanced frames were missing.

```powershell
.\.venv\Scripts\python.exe -m py_compile spikes\comfy_enhance\run_comfy_enhance.py
```

Result: PASS.

## Per-Frame Timing

ComfyUI did not process any frames because the API was unreachable.

| Case | Frame | ComfyUI seconds |
|---|---:|---:|
| character_intro | 1 | not run |
| character_intro | 2 | not run |
| character_intro | 3 | not run |
| character_intro | 4 | not run |
| product_orbit | 1 | not run |
| product_orbit | 2 | not run |
| product_orbit | 3 | not run |
| product_orbit | 4 | not run |

The ComfyUI script failed during API reachability check after about 2.14 seconds.

## GPU Memory Notes

- GPU: NVIDIA GeForce RTX 5070 Ti
- Total VRAM: 16303 MB
- Memory before ComfyUI script: about 1901 MB used
- Memory after failed ComfyUI script: about 1854 MB used
- During-processing peak: not available because no ComfyUI job ran

## Manual Visual Check

Not completed in this run because no enhanced frames were produced.

| Check | Result |
|---|---|
| Subject deformation | Not checked |
| Text corruption | Not checked |
| Severe flicker | Not checked; keyframes only, no full-frame video processing |
| Promo quality improvement | Not checked |

## Acceptance

| Criterion | Result |
|---|---|
| ComfyUI API is reachable | FAIL |
| 4 character_intro keyframes processed | FAIL |
| 4 product_orbit keyframes processed | FAIL |
| Enhanced frames saved | FAIL |
| Side-by-side comparisons generated | FAIL |
| Processing time recorded | FAIL for frames; connection failure duration recorded |
| Subject deformation documented | FAIL; no enhanced output |
| Text corruption documented | FAIL; no enhanced output |
| Pass/fail decision written | PASS |

## Known Risks

- ComfyUI environment is not yet a managed project dependency.
- `D:\ComfyUI` exists and has checkpoints, but no running API process was found.
- The current workspace `.venv` does not include `torch` or `aiohttp`, so it cannot launch the local ComfyUI source tree.
- The default workflow is conservative SDXL img2img, but it still may alter text or subject details; visual review is required after the API is available.
- Full-frame video enhancement is intentionally out of scope for this spike.

## Decision

Route 3 fails for this run because the ComfyUI API is not reachable. The isolated extraction and API client scripts are ready; rerun the spike after starting ComfyUI or providing a reachable `COMFYUI_URL`.
