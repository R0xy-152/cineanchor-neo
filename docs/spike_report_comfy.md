# Route 3 Spike Report: ComfyUI Keyframe Enhancement

Date: 2026-06-23

Branch: `spike/comfy-keyframe-enhance`

Status: FAIL for Route 3 acceptance. ComfyUI processing succeeded, but text corruption was observed.

## Goal

Validate whether ComfyUI can enhance Blender-rendered keyframes without subject deformation, text corruption, or severe flicker.

## Scope

This spike is isolated from the Web/FastAPI render path. It does not modify `server/app.py`, `apps/web/`, Route 2 renderer code, or Route 4 code.

## Workflow Used

- ComfyUI URL: `http://127.0.0.1:8188`
- ComfyUI version: `0.25.0`
- Workflow file: `spikes/comfy_enhance/workflows/conservative_sdxl_img2img_api.json`
- Workflow type: SDXL img2img, low-denoise conservative enhancement
- Settings used: `steps=8`, `cfg=1.6`, `denoise=0.12`
- Checkpoint used: `RealVisXL_V5.0_Lightning_fp16.safetensors`
- Checkpoint choices exposed by ComfyUI:
  - `RealVisXL_V5.0_Lightning_fp16.safetensors`
  - `sd_xl_base_1.0_0.9vae.safetensors`

The workflow was submitted through ComfyUI REST endpoints and the run report was written to `spikes/comfy_enhance/output/comfy_run_report.json`.

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

Generated comparison images:

- `spikes/comfy_enhance/output/character_intro/comparisons/frame_01_comparison.png`
- `spikes/comfy_enhance/output/character_intro/comparisons/frame_02_comparison.png`
- `spikes/comfy_enhance/output/character_intro/comparisons/frame_03_comparison.png`
- `spikes/comfy_enhance/output/character_intro/comparisons/frame_04_comparison.png`
- `spikes/comfy_enhance/output/product_orbit/comparisons/frame_01_comparison.png`
- `spikes/comfy_enhance/output/product_orbit/comparisons/frame_02_comparison.png`
- `spikes/comfy_enhance/output/product_orbit/comparisons/frame_03_comparison.png`
- `spikes/comfy_enhance/output/product_orbit/comparisons/frame_04_comparison.png`

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

The retry after ComfyUI was started succeeded:

```powershell
$env:COMFYUI_API_URL="http://127.0.0.1:8188"
.\.venv\Scripts\python.exe D:\ComfyUI\comfyui_client.py
```

Result: PASS, ComfyUI `0.25.0` reachable, 1116 nodes available.

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

Initial result: FAIL, API unavailable.

```powershell
$env:COMFYUI_API_URL="http://127.0.0.1:8188"
.\.venv\Scripts\python.exe .\spikes\comfy_enhance\run_comfy_enhance.py --timeout-seconds 1200
```

Retry result: PASS for processing, 8 enhanced frames saved.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\spikes\comfy_enhance\make_comparisons.ps1
```

Result: PASS, 8 side-by-side comparison images generated.

```powershell
.\.venv\Scripts\python.exe -m py_compile spikes\comfy_enhance\run_comfy_enhance.py
```

Result: PASS.

## Per-Frame Timing

| Case | Frame | ComfyUI seconds | GPU peak used MB |
|---|---:|---:|---:|
| character_intro | 1 | 7.444 | 9263 |
| character_intro | 2 | 3.306 | 11328 |
| character_intro | 3 | 3.237 | 11421 |
| character_intro | 4 | 3.222 | 11364 |
| product_orbit | 1 | 3.234 | 11334 |
| product_orbit | 2 | 3.233 | 11336 |
| product_orbit | 3 | 3.257 | 11353 |
| product_orbit | 4 | 3.192 | 11334 |

Total ComfyUI script wall time was about 31.1 seconds.

## GPU Memory Notes

- GPU: NVIDIA GeForce RTX 5070 Ti
- Total VRAM: 16303 MB
- Memory before ComfyUI script: about 2124 MB used
- Highest sampled during-processing memory: about 11421 MB used
- Memory after ComfyUI script: about 8902 MB used
- Current memory after visual review: about 8947 MB used

ComfyUI kept the model resident after processing. This is a likely GPU scheduling conflict with Blender if both are run at the same time.

## Manual Visual Check

Manual review was performed against all 8 side-by-side comparison images.

| Check | Result |
|---|---|
| Subject deformation | PASS for this run: character and product silhouettes stayed recognizable. |
| Text corruption | FAIL: `character_intro` subtitle was corrupted in 4/4 enhanced frames. |
| Severe flicker | Not fully validated; keyframes only. Product background texture changed slightly across frames, so flicker risk remains. |
| Promo quality improvement | Mixed: product frames look cleaner, character frames are not usable because subtitle text is damaged. |

## Acceptance

| Criterion | Result |
|---|---|
| ComfyUI API is reachable | PASS |
| 4 character_intro keyframes processed | PASS |
| 4 product_orbit keyframes processed | PASS |
| Enhanced frames saved | PASS |
| Side-by-side comparisons generated | PASS |
| Processing time recorded | PASS |
| Subject deformation documented | PASS |
| Text corruption documented | FAIL: subtitle text was corrupted in `character_intro`. |
| Pass/fail decision written | PASS |

## Known Risks

- Full-frame img2img over rendered text is not safe enough for the current template output.
- AI enhancement should happen before text overlay, or the text region must be masked/restored from the original render.
- ComfyUI remains resident in VRAM after the run; Blender and ComfyUI need serialized GPU access or explicit unload behavior.
- The default workflow is conservative SDXL img2img, but it still altered text.
- Full-frame video enhancement is intentionally out of scope for this spike.

## Decision

Route 3 fails acceptance in this run. The ComfyUI keyframe chain works technically, but direct full-frame SDXL img2img corrupted rendered subtitle text, so it is not acceptable as the current enhancement strategy for text-bearing final frames.

Recommended next decision: keep ComfyUI out of the Web render chain for now. If Route 3 is retried, enhance pre-text Blender frames or use a mask/post-composite step that preserves original text pixels.
