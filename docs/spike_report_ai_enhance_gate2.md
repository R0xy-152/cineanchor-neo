# AI Enhancement Feasibility Gate 2 Report

Date: 2026-06-24

Branch: `spike/ai-enhance-gate2-structure-control`

Final decision: FAIL

## Goal

Determine whether structure-controlled AI enhancement can make CineAnchor's
Blender output visibly better while preserving subject identity, product shape,
text stability, temporal stability, and plausible local processing time.

## Why Gate 2 Exists

Gate 1 showed that plain SDXL img2img could either stay stable with weak visual
lift or produce stronger changes with unacceptable subject/detail drift. Because
the product owner clarified that AI enhancement is the core product value, Gate
2 retested the direction with structure control and subject-protected
compositing instead of plain full-frame img2img.

This spike is isolated from production. It does not modify the Web/FastAPI
render path and does not integrate ComfyUI into the API.

## Summary Of Gate 1 Failure

- Direct full-frame img2img over final frames failed because it corrupted text.
- Rendering without text and adding text after AI solved text corruption.
- Denoise `0.25` was stable but visually weak.
- Denoise `0.35` and `0.50` gave stronger AI changes but altered subject/product
  details.
- Gate 1 failed because the enhancement was not strong and stable enough to
  justify AI as the core product direction.

## Experiment Setup

Source assets:

- `spikes/render_json/input/hero.png`
- `spikes/render_json/input/model.glb`

Isolated Gate 2 code:

- `spikes/ai_enhance_gate2/render_structural.py`
- `spikes/ai_enhance_gate2/video_ops.py`
- `spikes/ai_enhance_gate2/run_comfy_gate2.py`
- `spikes/ai_enhance_gate2/run_gate2.ps1`
- `spikes/ai_enhance_gate2/workflows/sdxl_img2img_api.json`
- `spikes/ai_enhance_gate2/workflows/sdxl_controlnet_img2img_api.json`

Generated artifacts are under `spikes/ai_enhance_gate2/output/` and are ignored
by Git.

Machine / GPU:

- GPU: NVIDIA GeForce RTX 5070 Ti
- VRAM: 16303 MB
- Blender: 5.1.2
- FFmpeg: 8.1.1 essentials build
- ComfyUI: 0.25.0
- Python for ComfyUI: system Python 3.12.10

## Structural Maps Generated

Character `character_intro`:

| Map | Result |
|---|---|
| RGB raw frames | PASS: 96 frames, `spikes/ai_enhance_gate2/output/character_intro/rgb/` |
| Subject mask frames | PASS: 96 frames, `spikes/ai_enhance_gate2/output/character_intro/mask/` |
| Canny maps | PASS: generated with FFmpeg for keyframes and 2s continuous frames |
| Depth / Z pass | NOT PRACTICAL in this run |
| Normal pass | NOT PRACTICAL in this run |

Blender 5.1.2 exposes `use_pass_z` and `use_pass_normal`, but the previous
compositor API no longer exposes `scene.node_tree`, and this build does not
offer `OPEN_EXR_MULTILAYER` in `scene.render.image_settings.file_format`.
Because of that, reliable headless depth/normal pass export was not completed
within the spike. RGB and subject masks were available and used.

Optional product `product_orbit`:

- RGB raw frames: 48
- Subject mask frames: 48
- Canny keyframes: generated with FFmpeg

## ComfyUI Workflow Details

Plain baseline:

- Workflow: `spikes/ai_enhance_gate2/workflows/sdxl_img2img_api.json`
- Checkpoint: `RealVisXL_V5.0_Lightning_fp16.safetensors`
- Steps: `8`
- CFG: `1.6`
- Denoise sweep: `0.25`, `0.35`, `0.45`

Structure-control workflow:

- Workflow: `spikes/ai_enhance_gate2/workflows/sdxl_controlnet_img2img_api.json`
- Checkpoint: `RealVisXL_V5.0_Lightning_fp16.safetensors`
- Control model: `diffusion_pytorch_model_promax.safetensors`
- Control method used: Canny
- Union control type: `canny/lineart/anime_lineart/mlsd`
- Control strength: `0.75`
- Control range: `0.0` to `0.85`
- Steps: `8`
- CFG: `1.6`

Important implementation note: an initial ControlNet attempt collapsed into
edge-map-like output because the raw frame and Canny control image had the same
filename and ComfyUI upload used `overwrite=true`. The runner now uploads raw
and control images with unique names. Only the fixed `control_canny_fixed`
outputs are used for assessment.

## Denoise Comparison

Character keyframes:

| Method | Denoise | Avg sec/frame | Peak VRAM MB | Result |
|---|---:|---:|---:|---|
| Plain img2img | 0.25 | 6.725 | 12531 | Slight smoothing and color change; visual lift weak |
| Plain img2img | 0.35 | 6.160 | 12375 | More visible change; character detail starts drifting |
| Plain img2img | 0.45 | 6.528 | 11944 | Stronger change but subject details deform |
| Canny ControlNet fixed | 0.25 | 3.271 | 12971 | Stable, but visual lift very weak |
| Canny ControlNet fixed | 0.35 | 3.235 | 13047 | Best tradeoff; shape mostly preserved, lift still modest |
| Canny ControlNet fixed | 0.45 | 3.252 | 12961 | More background change but visible artifacts begin |

Comparison grids:

- `spikes/ai_enhance_gate2/output/character_intro/keyframes/comparisons/canny_fixed_denoise_0_25/`
- `spikes/ai_enhance_gate2/output/character_intro/keyframes/comparisons/canny_fixed_denoise_0_35/`
- `spikes/ai_enhance_gate2/output/character_intro/keyframes/comparisons/canny_fixed_denoise_0_45/`

## Control Method Comparison

Only Canny was exercised as the actual structure-control method because the
local ControlNet directory exposed one ProMax model and no clearly named depth,
normal, or lineart-specific model. ComfyUI does expose depth, normal, and
lineart preprocessor nodes, but without matching known-good ControlNet model
coverage this spike used the safest identifiable structure route: Canny plus
the union control type selector.

Result: Canny control improved shape stability compared with plain img2img, but
it did not create a strong enough visual upgrade.

## Mask / Subject-Protection Result

Subject protection works technically:

- The original Blender subject can be composited back over the AI-enhanced
  background with a thresholded subject mask.
- This prevents subject identity drift in the protected output.
- Text is added after all AI processing.

Limitations:

- The current mask protects the character/product subject, not every related
  scene element such as rings or stage props.
- Protected output is more stable, but the visual lift becomes even milder
  because the main subject remains raw.

Key paths:

- Full AI keyframes: `spikes/ai_enhance_gate2/output/character_intro/keyframes/control_canny_fixed/`
- Protected keyframes: `spikes/ai_enhance_gate2/output/character_intro/keyframes/protected_canny_fixed/`
- Final with text: `spikes/ai_enhance_gate2/output/character_intro/protected_canny_fixed_2s_denoise_0_35_with_text.mp4`

## Timing And VRAM Data

Blender structural render:

| Case | RGB frames | Mask frames | RGB render sec | Mask render sec |
|---|---:|---:|---:|---:|
| character_intro | 96 | 96 | 54.952 | 14.508 |
| product_orbit | 48 | 48 | 31.882 | 11.327 |

ComfyUI timing:

| Test | Frames | Avg sec/frame | Min | Max | Peak VRAM MB |
|---|---:|---:|---:|---:|---:|
| Character plain keyframes 0.25 | 4 | 6.725 | 5.372 | 8.752 | 12531 |
| Character plain keyframes 0.35 | 4 | 6.160 | 5.390 | 6.441 | 12375 |
| Character plain keyframes 0.45 | 4 | 6.528 | 5.382 | 7.070 | 11944 |
| Character Canny keyframes 0.35 | 4 | 3.235 | 3.228 | 3.248 | 13047 |
| Character Canny continuous 0.35 | 48 | 3.354 | 3.206 | 3.640 | 12973 |
| Product Canny keyframes 0.35 | 4 | 3.317 | 3.244 | 3.422 | 13394 |

Projection: at 3.354 seconds per frame, a 192-frame / 8-second clip would take
about 10.7 minutes for ComfyUI alone, before Blender, FFmpeg, upload/download,
and compositing overhead. This is borderline for local production use.

## Flicker Assessment

Continuous output:

- `spikes/ai_enhance_gate2/output/character_intro/control_canny_fixed_2s_denoise_0_35.mp4`
- `spikes/ai_enhance_gate2/output/character_intro/protected_canny_fixed_2s_denoise_0_35.mp4`
- `spikes/ai_enhance_gate2/output/character_intro/before_after_2s.mp4`

Assessment: PARTIAL. The 48-frame MP4s compose and play at the expected
duration/fps. Spot-check stills did not show catastrophic flicker, and protected
compositing keeps the subject stable. However, independent per-frame AI
processing still creates subtle texture/lighting variation risk, especially in
the full-AI column.

## Subject Stability Assessment

PARTIAL.

- Plain img2img changes character details at `0.35` and especially `0.45`.
- Canny ControlNet preserves the silhouette better than plain img2img.
- Subject-protected compositing preserves the original subject identity best.
- The protected output is stable but visually less impressive because the
  subject itself remains raw Blender output.

## Product Stability Assessment

PARTIAL for one optional keyframe check.

At denoise `0.35`, the product outline mostly stays stable under Canny
ControlNet, but material/seed detail changes. Subject-protected compositing
restores the original product pixels and keeps shape stable, but again reduces
AI visual lift.

Comparison path:

- `spikes/ai_enhance_gate2/output/product_orbit/keyframes/comparisons/canny_fixed_denoise_0_35/`

## Text Stability Assessment

PASS.

No text is processed through AI. Title/subtitle are added by FFmpeg after the AI
stage. The final videos keep text readable and stable:

- `spikes/ai_enhance_gate2/output/character_intro/raw_2s_with_text.mp4`
- `spikes/ai_enhance_gate2/output/character_intro/control_canny_fixed_2s_denoise_0_35_with_text.mp4`
- `spikes/ai_enhance_gate2/output/character_intro/protected_canny_fixed_2s_denoise_0_35_with_text.mp4`
- `spikes/ai_enhance_gate2/output/character_intro/before_after_2s.mp4`

## Visual Lift Assessment

FAIL for product feasibility.

Structure control and masking improved stability, but the visual lift is still
not strong enough to justify CineAnchor as an AI-enhanced product. The best
candidate, protected Canny at denoise `0.35`, is cleaner and stable but only
mildly different from raw Blender. Stronger settings increase artifacts or
subject/detail drift.

No non-developer reviewer feedback was collected. Because PASS requires at
least two non-developer reviewers to prefer the AI-enhanced output, PASS is not
available from this evidence.

## FFprobe Outputs

Full ffprobe JSON:

- `spikes/ai_enhance_gate2/output/ffprobe_gate2_report.json`

Key validated outputs:

| Output | Resolution | FPS | Duration | Frames |
|---|---:|---:|---:|---:|
| `character_intro/raw_no_text.mp4` | 720x1280 | 24 | 4.0s | 96 |
| `character_intro/raw_no_text_2s.mp4` | 720x1280 | 24 | 2.0s | 48 |
| `character_intro/control_canny_fixed_2s_denoise_0_35.mp4` | 720x1280 | 24 | 2.0s | 48 |
| `character_intro/protected_canny_fixed_2s_denoise_0_35.mp4` | 720x1280 | 24 | 2.0s | 48 |
| `character_intro/before_after_2s.mp4` | 2160x1280 | 24 | 2.0s | 48 |

## Commands Run

```powershell
git switch -c spike/ai-enhance-gate2-structure-control
```

Result: PASS.

```powershell
[System.Management.Automation.Language.Parser]::ParseFile(
  (Resolve-Path 'spikes\ai_enhance_gate2\run_gate2.ps1'), ...
)
```

Result: PASS.

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  spikes\ai_enhance_gate2\render_structural.py `
  spikes\ai_enhance_gate2\video_ops.py `
  spikes\ai_enhance_gate2\run_comfy_gate2.py
```

Result: PASS.

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 10
```

Initial result: FAIL before ComfyUI startup. After starting ComfyUI from
`D:\ComfyUI\main.py`, result was PASS.

```powershell
Start-Process -FilePath `
  'C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe' `
  -ArgumentList @('main.py', '--listen', '127.0.0.1', '--port', '8188') `
  -WorkingDirectory 'D:\ComfyUI' -WindowStyle Hidden
```

Result: PASS.

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
  --background --python .\spikes\ai_enhance_gate2\render_structural.py `
  -- --case character_intro
```

Result: PASS for RGB and mask frames; depth/normal pass export not practical in
this run.

```powershell
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\video_ops.py compose-raw --case character_intro
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\video_ops.py extract-keyframes --case character_intro --count 4
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\video_ops.py extract-continuous --case character_intro --seconds 2
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\video_ops.py make-canny ...
```

Result: PASS.

```powershell
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\run_comfy_gate2.py `
  --mode plain --case character_intro --experiment keyframes_plain `
  --input-dir output/character_intro/keyframes/raw `
  --output-dir output/character_intro/keyframes/plain_img2img `
  --report output/character_intro/comfy_keyframes_plain_report.json `
  --denoise 0.25 --denoise 0.35 --denoise 0.45
```

Result: PASS, 12 keyframe outputs.

```powershell
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\run_comfy_gate2.py `
  --mode control --control-method canny --case character_intro `
  --experiment keyframes_control_canny_fixed `
  --input-dir output/character_intro/keyframes/raw `
  --control-dir output/character_intro/keyframes/canny `
  --output-dir output/character_intro/keyframes/control_canny_fixed `
  --report output/character_intro/comfy_keyframes_control_canny_fixed_report.json `
  --denoise 0.25 --denoise 0.35 --denoise 0.45
```

Result: PASS, 12 fixed ControlNet keyframe outputs.

```powershell
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\video_ops.py composite-protected ...
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\video_ops.py make-keyframe-grid `
  --case character_intro --method canny_fixed `
  --denoise 0.25 --denoise 0.35 --denoise 0.45
```

Result: PASS.

```powershell
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\run_comfy_gate2.py `
  --mode control --control-method canny --case character_intro `
  --experiment continuous_2s_control_canny_fixed `
  --input-dir output/character_intro/continuous/raw `
  --control-dir output/character_intro/continuous/canny `
  --output-dir output/character_intro/continuous/control_canny_fixed `
  --report output/character_intro/comfy_continuous_2s_control_canny_fixed_report.json `
  --seed-mode fixed --denoise 0.35
```

Result: PASS, 48 AI frames generated.

```powershell
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\video_ops.py compose-frames ...
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\video_ops.py make-before-after-2s `
  --case character_intro --method canny_fixed --denoise 0.35
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\video_ops.py ffprobe ...
```

Result: PASS.

Optional product commands:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
  --background --python .\spikes\ai_enhance_gate2\render_structural.py `
  -- --case product_orbit --skip-data-passes
.\.venv\Scripts\python.exe .\spikes\ai_enhance_gate2\run_comfy_gate2.py `
  --mode control --control-method canny --case product_orbit `
  --experiment keyframes_control_canny_fixed `
  --input-dir output/product_orbit/keyframes/raw `
  --control-dir output/product_orbit/keyframes/canny `
  --output-dir output/product_orbit/keyframes/control_canny_fixed `
  --report output/product_orbit/comfy_keyframes_control_canny_fixed_report.json `
  --denoise 0.35
```

Result: PASS for optional product keyframe generation.

## Final Decision

FAIL.

Gate 2 produced useful technical evidence:

- Canny ControlNet runs through ComfyUI.
- Subject-protected compositing works.
- Text stability is solved by post-overlay.
- A 48-frame / 2-second output can be generated and recomposed.

But the product feasibility question is still not answered positively:

- Visual lift remains too weak at stable settings.
- Stronger settings start introducing artifacts or detail drift.
- Protected compositing preserves identity but makes the AI improvement milder.
- Processing time projects to roughly 10.7 minutes of ComfyUI time for an
  8-second / 192-frame clip before other overhead.
- No non-developer reviewer preference was collected.

## Product Recommendation

Pause CineAnchor as an AI-enhanced product direction unless a stronger,
video-aware or better-masked enhancement method is validated. The deterministic
Blender/FFmpeg template renderer can continue as a 3D template tool, but it
should not be positioned as an AI-enhanced product based on Gate 2 evidence.
