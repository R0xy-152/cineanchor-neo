# AI ControlNet Structure Enhancement Spike

**Branch:** `spike/ai-enhance-gate2-structure-control`
**Date:** 2026-06-24
**Task:** Method #3 — ControlNet Structure-Controlled Enhancement
**Status:** IN PROGRESS

## Goal

Determine whether structure-controlled AI enhancement (Canny, Depth, Normal, Lineart ControlNet) can produce a visually compelling result while preserving subject stability.

## Experiment 1: Benchmark Inventory

### Available Benchmark Inputs

| Asset | Path | Status |
|---|---|---|
| Character 2s no-text video (48 frames, 720×1280, 24fps) | `spikes/ai_enhance_gate2/output/character_intro/raw_no_text_2s.mp4` | **Available** |
| Character keyframes (4) | `spikes/ai_enhance_gate2/output/character_intro/keyframes/raw/` | **Available** |
| Character continuous frames (48) | `spikes/ai_enhance_gate2/output/character_intro/continuous/raw/` | **Available** |
| Character subject masks (4 keyframe + 48 continuous) | `spikes/ai_enhance_gate2/output/character_intro/keyframes/mask/` + `continuous/mask/` | **Available** |
| Product keyframes (4) | `spikes/ai_enhance_gate2/output/product_orbit/keyframes/raw/` | **Available** |
| Product raw no-text MP4 (1280×720, 12fps, 4s) | `spikes/ai_enhance_gate2/output/product_orbit/raw_no_text.mp4` | **Available** |
| Product RGB frames (48) | `spikes/ai_enhance_gate2/output/product_orbit/rgb/` | **Available** |
| Product subject masks (4 keyframe) | `spikes/ai_enhance_gate2/output/product_orbit/keyframes/mask/` | **Available** |

### Available Control Signals

| Signal | Character | Product | Method |
|---|---|---|---|
| Subject mask | ✓ (Blender-rendered) | ✓ (Blender-rendered) | Blender material override |
| Canny edge map | ✓ (FFmpeg edgedetect) | ✓ (FFmpeg edgedetect) | Gate 2 video_ops.py |
| Depth map | ✗ (Blender 5.1 limitation) | ✗ (Blender 5.1 limitation) | Will use ComfyUI preprocessor |
| Normal map | ✗ (Blender 5.1 limitation) | ✗ (Blender 5.1 limitation) | Will use ComfyUI preprocessor |
| Lineart | Not pre-rendered | Not pre-rendered | Will use ComfyUI preprocessor |

### Available ComfyUI Resources

| Resource | Details |
|---|---|
| ComfyUI version | 0.25.0 |
| GPU | NVIDIA GeForce RTX 5070 Ti (16 GB VRAM) |
| PyTorch | 2.12.0 + CUDA 12.8 |
| Checkpoints | `RealVisXL_V5.0_Lightning_fp16.safetensors`, `sd_xl_base_1.0_0.9vae.safetensors` |
| ControlNet | `diffusion_pytorch_model_promax.safetensors` (Union ControlNet — supports Canny/Depth/Normal/Lineart) |
| Preprocessors | comfyui_controlnet_aux installed (DepthAnything, Zoe-Depth, BAE-Normal, LineArt, CannyEdge, etc.) |

### Existing Gate 2 Results (Canny only)

| Experiment | Control | Denoise | Result |
|---|---|---|---|
| Plain img2img | None | 0.25/0.35/0.45 | Baseline: weak at 0.25, deformed at 0.35+ |
| Canny ControlNet s=0.75 | FFmpeg Canny | 0.25/0.35/0.45 | Improved stability, mild visual lift |
| Canny ControlNet s=0.30 | FFmpeg Canny | 0.25/0.35/0.45 | Insufficient constraint → deformation |
| Canny ControlNet fixed seed | FFmpeg Canny | 0.25/0.35/0.45 | Best Gate 2 result: 0.35 denoise, mild lift |
| Protected composite | Canny + mask | 0.35 | Background-only enhancement, subject preserved |

### What's NEW in This Spike

1. **Depth ControlNet** via ComfyUI DepthAnything/Zoe preprocessor (FIRST TEST)
2. **Normal ControlNet** via ComfyUI BAE-Normal preprocessor (FIRST TEST)
3. **Lineart ControlNet** via ComfyUI LineArt preprocessor (FIRST TEST)
4. **Dual ControlNet** (Canny + Depth) if VRAM allows
5. **Product shape-preservation** test with best method (Gate 2 only tested character)
6. Stricter 5-point visual lift scoring with side-by-side comparisons

## Experiments

| # | Experiment | Input | Methods | Denoise |
|---|---|---|---|---|
| 2 | Canny ControlNet keyframes | Character 4 keyframes | Canny (ComfyUI preprocessor) | 0.25, 0.35, 0.45 |
| 3 | Depth/Normal/Lineart | Character 4 keyframes | Depth, Normal, Lineart | 0.25, 0.35, 0.45 |
| 4 | Product shape test | Product 4 keyframes | Best method from 2/3 | Best denoise |
| 5 | 2s temporal test | Character 48 frames | Best method + denoise | Best |
| 6 | Plain img2img baseline | Character 4 keyframes | No control | 0.25, 0.35, 0.45 |

## Directory Structure

```
spikes/ai_controlnet_structure_enhance/
├── README.md                          # This file
├── workflows/
│   ├── sdxl_controlnet_preprocessor_api.json   # Workflow with built-in preprocessor
│   └── sdxl_img2img_api.json                   # Plain img2img baseline
├── run_spike.py                       # Python runner for all experiments
├── output/
│   ├── character/
│   │   ├── keyframes/canny/           # Canny ControlNet keyframe outputs
│   │   ├── keyframes/depth/           # Depth ControlNet keyframe outputs
│   │   ├── keyframes/normal/          # Normal ControlNet keyframe outputs
│   │   ├── keyframes/lineart/         # Lineart ControlNet keyframe outputs
│   │   ├── keyframes/plain_img2img/   # Plain img2img baseline
│   │   ├── continuous/canny/          # 48-frame Canny output
│   │   ├── comparisons/               # Before/after grids
│   │   └── control_maps/              # Generated control maps
│   ├── product/
│   │   ├── keyframes/                 # Product keyframe outputs
│   │   └── comparisons/
│   └── videos/                        # Before/after MP4s
├── scorecard_controlnet_structure.md  # Completed scorecard
└── *_report.json                      # Per-run ComfyUI reports
```
