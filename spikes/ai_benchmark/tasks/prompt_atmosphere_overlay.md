# Task: AI Atmosphere / Lighting Overlay Enhancement

## Assignment

- **Target branch:** `spike/ai-atmosphere-overlay`
- **Task type:** R&D spike — AI enhancement method search
- **Method #:** 5 (from method matrix)
- **Depends on:** `spikes/ai_benchmark/` (benchmark package)

## Background

All previous AI enhancement attempts modified the frame pixels directly
(img2img). This always carries risk: higher denoise = more visual lift but
also more subject deformation. The layered subject protection approach
(method #4) mitigates this by compositing the original subject back, but
can leave visible seams.

This task explores a fundamentally different approach: instead of modifying
the Blender output, generate a separate AI "atmosphere layer" and composite
it on top. The Blender original remains completely untouched. The AI layer
adds cinematic elements: light rays, fog, particles, bloom, color grading —
things that make a video look like a game trailer rather than a raw render.

The key insight: if the overlay looks bad, the output gracefully degrades
to the Blender original. There is no quality regression risk.

## Goal

Determine whether AI-generated atmosphere/lighting overlays can produce a
visually compelling result that looks like a game promotion video, while
guaranteeing zero subject deformation and zero flicker risk.

## Approach

### Concept

```
Blender raw frame  →  [untouched]  →  Final frame
                     ↗
AI atmosphere layer  →  blend mode (screen/add/overlay/soft-light)
```

### Layer Generation

1. **Input:** Raw Blender no-text frame (character or product).
2. **Process:** Generate a same-resolution "atmosphere" image using ComfyUI.
   The AI prompt describes only atmospheric elements (light rays, fog, glow,
   particles, cinematic color grade), NOT the subject.
3. **Composite:** Blend the atmosphere layer over the original frame using
   screen, add, overlay, or soft-light blend modes.
4. **Optional mask:** Apply subject mask to the atmosphere layer so atmosphere
   effects don't obscure the subject.

### Variants to Test

| Variant | Generation | Blend Mode | Subject Mask on Layer |
|---|---|---|---|
| A | txt2img (prompt-only, no input image) | Screen | No |
| B | txt2img (prompt-only) | Overlay | No |
| C | img2img at very high denoise (0.60–0.80) → extract difference | Screen | Yes |
| D | Empty latent + ControlNet (structure from edges) → atmosphere style | Screen | Yes |
| E | Generate light rays / god rays specifically | Screen / Add | Yes |

### ComfyUI Workflow Ideas

**Variant A/B (txt2img atmosphere):**
- Empty latent → SDXL with prompt like "cinematic game trailer atmosphere,
  volumetric light rays, golden hour lighting, dust particles, lens flare,
  dark moody background, 8K"
- No input image — the AI generates pure atmosphere.
- Composite with screen blend (bright areas add light, dark areas are transparent).

**Variant C (difference extraction):**
- SDXL img2img at denoise 0.70 on the Blender frame.
- Extract the difference between AI output and original.
- Use difference as the atmosphere layer.
- Composite with appropriate blend mode.

**Variant D (structure-guided atmosphere):**
- Extract Canny edges from Blender frame.
- Use ControlNet (Canny) to guide empty latent generation.
- The structure guides where light/shadow falls, but the AI generates
  atmosphere, not subject details.
- Composite with screen blend.

**Variant E (targeted effect generation):**
- Use ComfyUI with specific LoRAs or prompts for volumetric light, god rays,
  particle effects.
- Generate as separate RGBA layer (with transparency).
- Composite with add blend mode.

### Blending Implementation

FFmpeg can apply blend modes via the `blend` filter:

```python
# Screen blend (lightens, preserves blacks)
ffmpeg -i original.png -i atmosphere.png \
  -filter_complex "blend=all_mode=screen" output.png

# Overlay blend (contrast enhancement)
ffmpeg -i original.png -i atmosphere.png \
  -filter_complex "blend=all_mode=overlay" output.png
```

Or use Python/PIL for pixel-level blend control with subject mask.

## Requirements

### 1. Understand the benchmark

Read `spikes/ai_benchmark/README.md`. The text-handling rule applies here
too — text overlay is a separate compositing step after atmosphere blending.

### 2. Character experiments

Use the no-text character benchmark inputs:
- 2s video: `spikes/ai_enhance_gate2/output/character_intro/raw_no_text_2s.mp4`
- Keyframes: `spikes/ai_enhance_gate2/output/character_intro/keyframes/`

Test ≥ 3 variants from the table above on 4 keyframes.

For the best variant:
- Generate atmosphere layers for all 48 continuous frames.
- Compose the 2s video with atmosphere applied.
- Generate before/after comparisons.

### 3. Blend mode comparison

For the best variant, test at least 3 blend modes:
- Screen (lightens, good for light rays/glow)
- Overlay (contrast boost, good for mood)
- Soft-light (subtle, good for color grade)
- Add (additive light, good for particles/sparks)

Document which blend mode produces the best result.

### 4. Temporal consistency

Atmosphere layers generated independently per frame may flicker. Assess:
- Does the atmosphere layer itself flicker?
- Does the blend mode amplify or hide flicker?
- If flicker is present, try: fixed seed per-frame, lower denoise, or
  temporal smoothing (frame blending) on the atmosphere layers.

### 5. Product experiments (if character shows promise)

If character results look promising (visual lift ≥ 3, no flicker), test on
product orbit keyframes.

### 6. Fill out the scorecard

Complete `spikes/ai_benchmark/evaluation/scorecard_template.md` for each
tested variant. Note that:
- Subject stability = 5 by construction (original is untouched).
- Product shape stability = 5 by construction.
- Flicker score refers to atmosphere layer flicker, not subject flicker.

## Output

All output goes under `spikes/ai-atmosphere-overlay/output/`:

```
output/
├── character/
│   ├── variant_a/         # txt2img screen blend
│   │   ├── atmosphere/    # Generated atmosphere layers
│   │   ├── composited/    # Final composited frames
│   │   ├── comparisons/
│   │   ├── *.mp4
│   │   └── *_report.json
│   ├── variant_c/         # Difference extraction
│   │   └── ...
│   ├── variant_e/         # Targeted effects
│   │   └── ...
│   └── blend_comparison/  # Same variant, different blend modes
├── product/               # (if tested)
│   └── ...
└── scorecard.md           # Completed scorecard
```

## Acceptance Criteria

- [ ] ≥ 3 atmosphere generation variants tested on character benchmark.
- [ ] ≥ 3 blend modes compared for best variant.
- [ ] Continuous 2s character video generated at best settings.
- [ ] Temporal consistency assessed and documented.
- [ ] Before/after comparison assets produced.
- [ ] Subject confirmed unchanged (Blender original pixels untouched).
- [ ] Text is NOT processed by AI — confirmed in scorecard.
- [ ] Decision (PASS / PARTIAL / FAIL) with supporting evidence.
- [ ] All generated media is gitignored.
- [ ] Scripts, workflow JSON, and scorecard are committed.
- [ ] `git diff --check` passes.

## Constraints

- Do NOT modify production code.
- Do NOT integrate ComfyUI into the production API.
- Do NOT process text with AI.
- Do NOT commit generated media files.
- The Blender original frame must be recoverable (no destructive editing).

## Reference Files

- `spikes/ai_benchmark/README.md` — benchmark rules and inputs
- `spikes/ai_benchmark/evaluation/method_matrix.md` — method context
- `spikes/ai_benchmark/evaluation/scorecard_template.md` — evaluation template
- `spikes/ai_benchmark/controls/` — control signal status
- `spikes/ai_enhance_gate2/output/` — existing benchmark inputs
- `spikes/ai_enhance_gate2/video_ops.py` — FFmpeg helpers (may be useful for compositing)
