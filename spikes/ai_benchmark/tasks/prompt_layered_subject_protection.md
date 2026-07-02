# Task: Layered Subject Protection Enhancement

## Assignment

- **Target branch:** `spike/ai-layered-subject-protection`
- **Task type:** R&D spike — AI enhancement method search
- **Method #:** 4 (from method matrix)
- **Depends on:** `spikes/ai_benchmark/` (benchmark package)

## Background

Gate 2 tested a basic form of subject-protected compositing: Canny ControlNet
AI enhancement on the full frame, then paste the original subject back using
the Blender-rendered mask. The result was stable but visual lift was mild —
likely because the test scene had a simple gradient background that didn't
benefit much from AI enhancement.

This task explores a more deliberate approach: intentionally direct the AI
to enhance ONLY the background, lighting, and atmosphere, while the subject
mask ensures the character or product remains 100% original. This is a
different philosophy from structure control — instead of constraining the AI
to preserve the subject, we remove the subject from the AI process entirely.

## Goal

Determine whether AI-only background/atmosphere enhancement with subject mask
compositing can produce a visually compelling result, while guaranteeing zero
subject deformation.

## Approach Options

### Option A: Inpaint/Outpaint Background Only

1. Use subject mask to create an inpaint mask (invert: mask background, not subject).
2. Run ComfyUI img2img with the inpaint mask — AI only modifies background pixels.
3. Composite: use original subject pixels, AI-enhanced background pixels.
4. Edge blend: slight feather/blur on mask edge to avoid hard seams.

### Option B: Full-Frame Enhance + Subject Restoration

1. Run AI enhancement on the full frame (AI touches everything).
2. Use subject mask to paste original subject back over the AI output.
3. Edge blend to avoid visible cut lines.
4. This is what Gate 2 did — the key difference here is optimizing the AI
   prompt and settings specifically for *background* enhancement rather than
   trying to preserve the subject through ControlNet.

### Option C: Separate Background Generation

1. Use subject mask to extract background-only image (subject area blacked out).
2. Run AI enhancement on the background-only image.
3. The AI sees only the background and can fill/modify it more aggressively.
4. Composite original subject back on top of the enhanced background.
5. This is the most aggressive variant — the AI doesn't see the subject at all.

### Option D: Depth-Aware Background Enhancement

1. Use depth map (ComfyUI preprocessor) to identify foreground vs background.
2. Apply stronger enhancement to background depth layers, weaker to foreground.
3. Composite with per-pixel blending weights based on depth.
4. This is a softer version of Option C — gradual rather than binary mask.

## Requirements

### 1. Understand the benchmark

Read `spikes/ai_benchmark/README.md`. The text-handling rule is especially
important here — text is post-AI overlay, which naturally complements the
layered compositing approach.

### 2. Use existing masks

Subject masks are already rendered by Gate 2:
- Character: `spikes/ai_enhance_gate2/output/character_intro/mask/`
- Product: `spikes/ai_enhance_gate2/output/product_orbit/mask/`

Use these masks. If needed, regenerate with:
```powershell
.\.venv\Scripts\python.exe spikes\ai_enhance_gate2\render_structural.py `
  --template character_intro --asset-path samples/assets/hero.png `
  --output <dir> --duration 2 --fps 24 --no-text
```

### 3. Character experiments

Use the no-text character benchmark inputs:
- 2s video: `spikes/ai_enhance_gate2/output/character_intro/raw_no_text_2s.mp4`
- RGB frames: `spikes/ai_enhance_gate2/output/character_intro/rgb/`
- Mask frames: `spikes/ai_enhance_gate2/output/character_intro/mask/`

Test at least 2 of the 4 approach options (A/B/C/D above).

For each approach:
- Process 4 keyframes at multiple denoise levels (start at 0.30, try 0.40, 0.50).
- Since the subject is protected by compositing, higher denoise on the
  background is acceptable and even desirable.
- Pick the best settings and process 48 continuous frames (2s).
- Generate before/after keyframe comparisons and before/after 2s videos.
- Check edge seams carefully — document any visible compositing artifacts.

### 4. Product experiments (if character shows promise)

If character results look promising (visual lift ≥ 3 with zero subject
deformation), test on product orbit keyframes using the product masks.

### 5. Edge blending quality

Pay special attention to the subject-background edge:
- Test different mask feather/blur radii (0px, 2px, 5px, 10px).
- Document which radius produces the most natural edge.
- If edges are visible in video, note this as a limitation.

### 6. Fill out the scorecard

Complete `spikes/ai_benchmark/evaluation/scorecard_template.md` for each
tested approach. Note that subject stability should be 5 by construction
(subject is original), but edge quality may reduce the effective score.

## Output

All output goes under `spikes/ai-layered-subject-protection/output/`:

```
output/
├── character/
│   ├── approach_a/        # (or b/c/d as tested)
│   │   ├── keyframes/
│   │   ├── continuous/
│   │   ├── comparisons/
│   │   ├── *.mp4
│   │   └── *_report.json
│   ├── approach_b/
│   │   └── ...
│   └── edge_blend_tests/  # Mask edge radius comparison
├── product/               # (if tested)
│   └── ...
└── scorecard.md           # Completed scorecard
```

## Acceptance Criteria

- [ ] ≥ 2 approach variants tested on character benchmark.
- [ ] Continuous 2s character video generated at best settings.
- [ ] Edge blend quality assessed and documented.
- [ ] Before/after comparison assets produced.
- [ ] Scorecard filled out with all metrics and assessments.
- [ ] Subject confirmed unchanged (pixel-identical where mask = 1.0).
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
- Use existing masks from Gate 2 — do NOT re-render unless necessary.

## Reference Files

- `spikes/ai_benchmark/README.md` — benchmark rules and inputs
- `spikes/ai_benchmark/evaluation/method_matrix.md` — method context
- `spikes/ai_benchmark/evaluation/scorecard_template.md` — evaluation template
- `spikes/ai_benchmark/controls/character/mask/PLACEHOLDER.md` — mask details
- `spikes/ai_enhance_gate2/output/` — existing masks and RGB frames
- `spikes/ai_enhance_gate2/video_ops.py` — compositing helpers (`composite_protected()`)
- `spikes/ai_enhance_gate2/render_structural.py` — mask render script
