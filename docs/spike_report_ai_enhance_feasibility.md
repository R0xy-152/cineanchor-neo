# AI Enhancement Feasibility Gate Report

Date: 2026-06-24

Branch: `spike/ai-enhance-feasibility-gate`

Final decision: FAIL

## Goal

Determine whether CineAnchor can produce visibly better AI-enhanced output than
raw Blender Eevee output while preserving subject stability, text stability, and
acceptable local processing time.

## Why This Gate Exists

The product owner clarified that the core product value is AI enhancement. The
existing V0.1 path already validates Web -> FastAPI -> Project JSON -> Blender
Eevee -> FFmpeg -> MP4, but that is not enough if the product promise depends on
clear AI visual lift.

This gate intentionally does not harden production code. It tests whether the AI
direction is worth continuing before any production integration.

## Previous Route 3A / 3B Results

- Route 3A direct full-frame img2img over final frames: FAIL. ComfyUI processed
  frames, but rendered subtitle text was corrupted.
- Route 3B conservative ComfyUI reference plus FFmpeg enhancement: PARTIAL.
  Stable and text-safe, but visual lift was weak.

This feasibility gate changes the order: render without text, run AI on no-text
frames, then add deterministic text after AI.

## Experiment Setup

- Source assets:
  - `spikes/render_json/input/hero.png`
  - `spikes/render_json/input/model.glb`
- Isolated spike code:
  - `spikes/ai_enhance_feasibility/render_no_text.py`
  - `spikes/ai_enhance_feasibility/video_ops.py`
  - `spikes/ai_enhance_feasibility/run_comfy_feasibility.py`
  - `spikes/ai_enhance_feasibility/workflows/sdxl_img2img_api.json`
- Generated artifacts are under `spikes/ai_enhance_feasibility/output/` and are
  ignored by Git.
- No production Web/FastAPI route was modified.

## Workflow And Checkpoint Details

| Field | Value |
|---|---|
| ComfyUI URL | `http://127.0.0.1:8188` |
| ComfyUI version | `0.25.0` |
| Workflow | `spikes/ai_enhance_feasibility/workflows/sdxl_img2img_api.json` |
| Workflow type | SDXL img2img on no-text frames |
| Checkpoint | `RealVisXL_V5.0_Lightning_fp16.safetensors` |
| Steps | 8 |
| CFG | 1.6 |
| Denoise sweep | `0.25`, `0.35`, `0.50` |
| Continuous test denoise | `0.25` |
| Positive prompt | `polished mobile game promotional keyframe, cinematic lighting, richer color, clean highlights, crisp edges, premium game ad still, preserve exact subject silhouette, preserve exact pose, preserve exact composition, no text` |
| Negative prompt | `text, watermark, logo, deformed subject, changed face, changed costume, changed product geometry, extra limbs, extra objects, melted edges, blur, flicker, oversaturated, noisy artifacts, layout change` |

Machine / GPU notes:

- GPU: NVIDIA GeForce RTX 5070 Ti
- VRAM: 16303 MB
- ComfyUI startup required system Python
  `C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe`.
  Starting it with the repo venv failed with missing `sqlalchemy`.
- ComfyUI retained about 9.3 GB VRAM after runs, so Blender and ComfyUI should
  not run concurrently without an explicit GPU policy.

## Experiment 1: No-Text Render + Post Text Overlay

Outputs:

- `spikes/ai_enhance_feasibility/output/character_intro/raw_no_text.mp4`
- `spikes/ai_enhance_feasibility/output/character_intro/final_with_text_overlay.mp4`

Results:

| Check | Result |
|---|---|
| Blender no-text render | PASS: 96 frames, 720x1280, 24 fps |
| Render duration | 48.213s |
| FFmpeg raw MP4 | PASS |
| Deterministic post text overlay | PASS |
| Text stability | PASS: title/subtitle are stable because they are not AI-generated |

## Experiment 2: Stronger Keyframe AI Enhancement

Character output paths:

- `spikes/ai_enhance_feasibility/output/character_intro/keyframes_ai/denoise_0_25/`
- `spikes/ai_enhance_feasibility/output/character_intro/keyframes_ai/denoise_0_35/`
- `spikes/ai_enhance_feasibility/output/character_intro/keyframes_ai/denoise_0_50/`
- `spikes/ai_enhance_feasibility/output/character_intro/comparisons/denoise_grid/`

Product output paths:

- `spikes/ai_enhance_feasibility/output/product_orbit/keyframes_ai/denoise_0_25/`
- `spikes/ai_enhance_feasibility/output/product_orbit/keyframes_ai/denoise_0_35/`
- `spikes/ai_enhance_feasibility/output/product_orbit/keyframes_ai/denoise_0_50/`
- `spikes/ai_enhance_feasibility/output/product_orbit/comparisons/denoise_grid/`

### Denoise Comparison

| Asset | Denoise | Avg seconds/frame | Peak VRAM MB | Visual result | Decision |
|---|---:|---:|---:|---|---|
| character_intro | 0.25 | 4.277 | 11698 | Safest subject stability, but lift is modest and details are smoothed/redrawn. | Usable only as a stability candidate |
| character_intro | 0.35 | 3.219 | 11730 | Stronger redraw; face/body details and highlights change visibly. | Reject |
| character_intro | 0.50 | 3.258 | 11694 | Subject silhouette/details change; unacceptable deformation risk. | Reject |
| product_orbit | 0.25 | 3.225 | 11750 | Product outline mostly preserved; slight surface cleanup. | Usable only as a stability candidate |
| product_orbit | 0.35 | 3.214 | 11784 | Product material and seed/edge details change more visibly. | Reject |
| product_orbit | 0.50 | 3.218 | 11767 | Adds spots/texture changes and alters edges. | Reject |

Conclusion: there is no denoise range that gives both obvious visual lift and
acceptable subject stability. `0.25` is the only plausible stability setting,
but its improvement is too weak for the core product claim.

## Experiment 3: 2-Second Continuous-Frame AI Enhancement

Best candidate used: denoise `0.25`.

Outputs:

- `spikes/ai_enhance_feasibility/output/character_intro/raw_no_text_2s.mp4`
- `spikes/ai_enhance_feasibility/output/character_intro/ai_enhanced_2s.mp4`
- `spikes/ai_enhance_feasibility/output/character_intro/ai_enhanced_2s_with_text.mp4`
- `spikes/ai_enhance_feasibility/output/character_intro/before_after_2s.mp4`
- Spot-check stills:
  - `spikes/ai_enhance_feasibility/output/character_intro/before_after_2s_t05.png`
  - `spikes/ai_enhance_feasibility/output/character_intro/before_after_2s_t15.png`

Timing:

| Frames | Avg seconds/frame | Min | Max | Total observed command time | Peak VRAM MB |
|---:|---:|---:|---:|---:|---:|
| 48 | 2.678 | 2.140 | 3.257 | about 132.4s | 11809 |

Assessment:

| Check | Result |
|---|---|
| Recomposition | PASS: 48-frame MP4 generated |
| Text overlay after AI | PASS: text remains readable and stable |
| Subject stability | PARTIAL: no catastrophic deformation at `0.25`, but details are redrawn and not identical |
| Flicker | PARTIAL: no catastrophic flicker found in spot checks, but per-frame AI detail changes remain visible risk |
| Visual lift | FAIL: improvement over raw is weak |
| Processing time | PARTIAL: about 2.7s/frame is plausible for local spike use, but an 8s/192-frame clip would project to about 8.6 minutes of ComfyUI time before overhead |

## Optional Experiment 4: Product GLB Test

The product keyframe test was run.

Results:

- `0.25` mostly preserves product outline, with mild surface cleanup.
- `0.35` and `0.50` increasingly alter material, seed detail, background spots,
  and edge shape.

Acceptance result: PARTIAL for product keyframes only. Product output is not
enough to rescue the gate because the lift remains mild at the only stable
setting.

## FFprobe Results

| Output | Resolution | FPS | Duration | Frames |
|---|---:|---:|---:|---:|
| `character_intro/raw_no_text.mp4` | 720x1280 | 24 | 4.0s | 96 |
| `character_intro/final_with_text_overlay.mp4` | 720x1280 | 24 | 4.0s | 96 |
| `character_intro/raw_no_text_2s.mp4` | 720x1280 | 24 | 2.0s | 48 |
| `character_intro/ai_enhanced_2s.mp4` | 720x1280 | 24 | 2.0s | 48 |
| `character_intro/ai_enhanced_2s_with_text.mp4` | 720x1280 | 24 | 2.0s | 48 |
| `character_intro/before_after_2s.mp4` | 1440x1280 | 24 | 2.0s | 48 |
| `product_orbit/raw_no_text.mp4` | 1280x720 | 12 | 4.0s | 48 |

Full ffprobe JSON:

- `spikes/ai_enhance_feasibility/output/ffprobe_report.json`

## Commands Run

```powershell
git switch -c spike/ai-enhance-feasibility-gate
```

Result: PASS.

```powershell
$files = @('spikes\ai_enhance_feasibility\run_feasibility.ps1')
foreach ($file in $files) {
  [System.Management.Automation.Language.Parser]::ParseFile(...)
}
```

Result: PASS.

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  spikes\ai_enhance_feasibility\render_no_text.py `
  spikes\ai_enhance_feasibility\video_ops.py `
  spikes\ai_enhance_feasibility\run_comfy_feasibility.py
```

Result: PASS.

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 10
```

Initial result: FAIL before ComfyUI startup. After starting ComfyUI with system
Python 3.12, result was PASS.

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
  --background --python .\spikes\ai_enhance_feasibility\render_no_text.py `
  -- --case character_intro
```

Result: PASS, 96 frames in 48.213s.

```powershell
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\video_ops.py compose-raw --case character_intro
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\video_ops.py overlay-text --case character_intro --input output/character_intro/raw_no_text.mp4 --output output/character_intro/final_with_text_overlay.mp4
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\video_ops.py extract-keyframes --case character_intro --count 4
```

Result: PASS.

```powershell
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\run_comfy_feasibility.py `
  --case character_intro --experiment keyframes `
  --input-dir output/character_intro/keyframes_raw `
  --output-dir output/character_intro/keyframes_ai `
  --report output/character_intro/comfy_keyframes_report.json `
  --denoise 0.25 --denoise 0.35 --denoise 0.50
```

Result: PASS, 12 keyframe outputs.

```powershell
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\video_ops.py make-keyframe-comparisons --case character_intro --denoise 0.25 --denoise 0.35 --denoise 0.50
```

Result: PASS.

```powershell
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\video_ops.py extract-continuous --case character_intro --seconds 2
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\run_comfy_feasibility.py `
  --case character_intro --experiment continuous_2s `
  --input-dir output/character_intro/continuous_raw `
  --output-dir output/character_intro/continuous_ai `
  --report output/character_intro/comfy_continuous_2s_report.json `
  --seed-mode fixed --denoise 0.25
```

Result: 48 AI frames generated. The command returned nonzero after the last
frame because Windows denied the final report rewrite once; the script was
patched with a retry loop. The report contains all 48 frame timing entries.

```powershell
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\video_ops.py compose-ai-2s --case character_intro --denoise 0.25
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\video_ops.py make-before-after-2s --case character_intro --denoise 0.25
```

Result: PASS.

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
  --background --python .\spikes\ai_enhance_feasibility\render_no_text.py `
  -- --case product_orbit
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\video_ops.py compose-raw --case product_orbit
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\video_ops.py extract-keyframes --case product_orbit --count 4
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\run_comfy_feasibility.py `
  --case product_orbit --experiment keyframes `
  --input-dir output/product_orbit/keyframes_raw `
  --output-dir output/product_orbit/keyframes_ai `
  --report output/product_orbit/comfy_keyframes_report.json `
  --denoise 0.25 --denoise 0.35 --denoise 0.50
```

Result: PASS after rerunning keyframe extraction serially. The first extraction
attempt raced MP4 composition and failed because the MP4 was not ready yet.

```powershell
.\.venv\Scripts\python.exe .\spikes\ai_enhance_feasibility\video_ops.py ffprobe ...
```

Result: PASS.

```powershell
git diff --check
```

Result: PASS, with existing line-ending warnings for edited Markdown files.

## Text Stability Assessment

PASS. Text is deterministic FFmpeg overlay after AI. It is readable and stable in
`final_with_text_overlay.mp4`, `ai_enhanced_2s_with_text.mp4`, and
`before_after_2s.mp4`.

## Subject Stability Assessment

PARTIAL.

- Character: `0.25` avoids catastrophic deformation, but still smooths/redraws
  character detail. `0.35` and `0.50` visibly alter face/body details and
  silhouette.
- Product: `0.25` mostly preserves outline; `0.35` and `0.50` alter texture,
  seed detail, background, and edges.

## Flicker Assessment

PARTIAL. The 48-frame `0.25` continuous output recomposes and is playable. Spot
checks did not show catastrophic flicker, but per-frame AI detail variation is
still present risk. This is not strong enough to pass a product feasibility
gate.

## Non-Developer Feedback

Not collected in this run. Because PASS requires at least two non-developer
reviewers to prefer the enhanced result, PASS is not available from this
evidence even if the technical checks were stronger.

## Final Decision

FAIL.

Reasons:

- Stable text is solved by post overlay, but that only removes the text
  corruption failure mode.
- The only stable denoise range (`0.25`) produces weak visual lift.
- Stronger denoise values (`0.35`, `0.50`) produce the more obvious AI look but
  change subject/product details too much.
- Continuous-frame processing is technically possible, but the output does not
  provide enough product value to justify making AI enhancement the core
  direction.
- Non-developer preference feedback was not collected.

## Product Recommendation

Pause the CineAnchor direction as an AI-enhanced product unless a different AI
method is chosen and validated. Continue only if the product is repositioned as
a deterministic local Blender/FFmpeg promo renderer, or pivot the AI work to a
video-aware / temporally consistent / masked enhancement method that can deliver
obvious lift without changing the subject.
