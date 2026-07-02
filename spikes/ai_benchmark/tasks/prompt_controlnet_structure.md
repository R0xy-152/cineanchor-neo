# Task: ControlNet Structure-Controlled Enhancement

## Assignment

- **Target branch:** `spike/ai-controlnet-structure-enhance`
- **Task type:** R&D spike — AI enhancement method search
- **Method #:** 3 (from method matrix)
- **Depends on:** `spikes/ai_benchmark/` (benchmark package)

## Background

Previous AI enhancement attempts (Gates 1 & 2) found that plain SDXL img2img at
denoise 0.35+ causes subject deformation, while denoise 0.25 is stable but too
weak to produce meaningful visual lift.

Gate 2 tested Canny ControlNet at various strengths and found:
- Canny strength 0.75 + denoise 0.35: improved stability vs plain img2img, but
  visual lift was still only mildly better than raw Blender.
- Canny strength 0.30: did not constrain structure enough — still deformed.
- Depth and Normal ControlNet were NOT tested (Blender 5.1 OPEN_EXR_MULTILAYER
  limitation prevented depth/normal pass rendering).

This task extends the Gate 2 Canny work AND explores whether depth/normal
ControlNet (via ComfyUI preprocessors) can achieve better results.

## Goal

Determine whether structure-controlled AI enhancement (Canny, Depth, or Normal
ControlNet) can produce a visually compelling result while preserving subject
stability, OR whether this approach should be abandoned.

## Requirements

### 1. Understand the benchmark

Read `spikes/ai_benchmark/README.md` for the text-handling rule, benchmark inputs,
and control signal status.

### 2. Study Gate 2 results

Review `spikes/ai_enhance_gate2/` — scripts, outputs, and reports — to understand
what was already tested and the failure modes. Do NOT re-run identical experiments.

### 3. Character experiments

Use the no-text character benchmark inputs:
- 2s video: `spikes/ai_enhance_gate2/output/character_intro/raw_no_text_2s.mp4`
- Keyframes: `spikes/ai_enhance_gate2/output/character_intro/keyframes/`
- Continuous frames (48): `spikes/ai_enhance_gate2/output/character_intro/continuous_raw/`

Test these variants (at minimum):

| Variant | Control Signal | Strength | Denoise | Notes |
|---|---|---|---|---|
| A | Canny (FFmpeg) | 0.60–0.80 sweep | 0.25–0.40 sweep | Extends Gate 2 with finer sweep |
| B | Depth (ComfyUI preprocessor) | 0.60–0.80 | 0.25–0.40 | First depth test |
| C | Normal (ComfyUI preprocessor) | 0.60–0.80 | 0.25–0.40 | First normal test |
| D | Canny + Depth (dual ControlNet) | 0.50–0.70 each | 0.25–0.40 | If VRAM allows |

For each variant:
- Process 4 keyframes first at 3 denoise levels (0.25, 0.30, 0.35, 0.40).
- Pick the best denoise/strength combo.
- Process 48 continuous frames (2s) at the best settings.
- Compose before/after keyframe comparisons and before/after 2s MP4s.

### 4. Product experiments (if character shows promise)

If any character variant scores visual lift ≥ 4 and stability ≥ 4 on the
scorecard, test the same variant on product orbit keyframes.

Use: `spikes/ai_enhance_gate2/output/product_orbit/keyframes/`

### 5. Use ComfyUI built-in preprocessors

Since Blender 5.1 cannot output depth/normal passes, use ComfyUI's built-in
preprocessors:
- **Depth:** `ControlNetPreprocessor` with `depth_anything` or `depth_leres++`
- **Normal:** `ControlNetPreprocessor` with `normal_bae` or equivalent

Reference: ComfyUI ControlNet Auxiliary Preprocessors node pack.

### 6. Fill out the scorecard

Complete `spikes/ai_benchmark/evaluation/scorecard_template.md` with all
measurements, observations, and comparisons for each tested variant.

## Output

All output goes under `spikes/ai-controlnet-structure-enhance/output/`:

```
output/
├── character/
│   ├── keyframes/         # Enhanced keyframes per variant
│   ├── continuous/        # 48-frame continuous enhancement
│   ├── comparisons/       # Before/after comparison grids
│   ├── *.mp4              # Before/after/side-by-side videos
│   └── *_report.json      # ComfyUI per-run reports
├── product/               # (if tested)
│   └── ...
└── scorecard.md           # Completed scorecard
```

## Acceptance Criteria

- [ ] Character keyframe experiments completed for ≥ 2 control signal types.
- [ ] Continuous 2s character video generated at best settings.
- [ ] Before/after comparison assets produced (keyframes + videos).
- [ ] Scorecard filled out with all metrics and assessments.
- [ ] Text is NOT processed by AI — confirmed in scorecard.
- [ ] Decision (PASS / PARTIAL / FAIL) with supporting evidence.
- [ ] All generated media is gitignored (no MP4/PNG in commit).
- [ ] Scripts, workflow JSON, and scorecard are committed.
- [ ] `git diff --check` passes.

## Constraints

- Do NOT modify `server/`, `apps/web/`, or production code.
- Do NOT integrate ComfyUI into the production API.
- Do NOT process text with AI — text must be post-AI overlay.
- Do NOT commit generated MP4, PNG frames, or model files.
- Use existing benchmark inputs — do NOT re-render unless Gate 2 outputs
  are unavailable.
- If Blender re-render is needed, use `spikes/ai_enhance_gate2/render_structural.py`
  with `--no-text` flag.

## Reference Files

- `spikes/ai_benchmark/README.md` — benchmark rules and input paths
- `spikes/ai_benchmark/evaluation/method_matrix.md` — method context
- `spikes/ai_benchmark/evaluation/scorecard_template.md` — evaluation template
- `spikes/ai_benchmark/controls/` — control signal status and placeholders
- `spikes/ai_enhance_gate2/` — previous Canny experiments
- `spikes/ai_enhance_gate2/render_structural.py` — no-text render script
- `spikes/ai_enhance_gate2/video_ops.py` — FFmpeg helpers (Canny gen, compositing, comparisons)
- `spikes/ai_enhance_gate2/workflows/` — ComfyUI workflow JSON templates
- `docs/adr/ADR-004-no-full-frame-ai-video-regeneration.md` — text handling ADR
