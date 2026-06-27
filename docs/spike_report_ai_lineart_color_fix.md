# Spike Report: AI Lineart ControlNet Color Fix

**Date:** 2026-06-24
**Branch:** `spike/ai-lineart-color-fix`
**Timebox:** ~2 hours (well within 4-hour limit)
**Decision:** PARTIAL (improving toward PASS)

## 1. Goal

Determine whether Lineart ControlNet output can be meaningfully improved through prompt engineering and color correction — fixing the saturation loss and flicker issues found in the previous ControlNet Structure Enhancement spike.

## 2. Why This Spike Exists

The previous ControlNet spike (`spike/ai-enhance-gate2-structure-control`) found:
- Lineart ControlNet is the best structure-control method
- But visual lift was only mild to moderate
- Character output suffered saturation loss (−0.059 to −0.066 vs raw)
- 2-second videos showed visible frame-to-frame variation

This spike tests whether prompt engineering + fixed seed + post-AI color correction can fix these issues without requiring a new checkpoint or complex workflow changes.

## 3. Previous ControlNet PARTIAL Summary

| Issue | Severity | Root Cause |
|---|---|---|
| Saturation loss | Moderate (−0.059) | "Cinematic" prompt biases RealVisXL toward desaturated look |
| Flicker | Mild (CV 0.056) | Per-frame seed variation adds inconsistency |
| Weak visual lift | MAE 4.13 | Safe denoise (0.35) limits how much AI changes |

## 4. Timebox Used

~2 hours total:
- Prompt variant keyframe sweep: ~80s GPU
- 2s continuous temporal test: 155s GPU
- Product sanity check: 13s GPU
- Color correction + video generation: ~30s
- Metrics + report writing: ~20 min

## 5. Prompt Variants Tested

Three variants on character keyframes (4 frames each, denoise 0.30 and 0.35):

| Variant | Approach | Key Prompt Features | Sat Delta (d=0.35) | Verdict |
|---|---|---|---|---|
| **A** | Game promo vivid | "vivid saturated colors, game art style, no cinematic" | **−0.0531** | **Winner** |
| B | Color preservation | "preserve original hue and saturation, no color shift" | −0.0627 | Worse than baseline |
| C | Minimal lift | "no color shift, no saturation change, subtle only" | −0.0689 | Worst |
| (Prev) | Cinematic | "cinematic lighting, richer color" | −0.0585 | Baseline |

**Key finding:** Explicit "game art style" and negative prompting against "cinematic/filmic" reduces saturation loss. Generic "preserve original colors" prompts are ineffective — the model needs specific stylistic direction.

## 6. Fixed Seed Discovery

Changing from `--seed-mode frame` (varying seed per frame) to `--seed-mode fixed` (same base seed for all frames) dramatically improved temporal consistency:

| Metric | Frame-varying seed | Fixed seed | Improvement |
|---|---|---|---|
| Frame-to-frame MeanDiff | 0.0127 | **0.0036** | **72% reduction** |
| Per-frame MAE std | 0.389 | **0.151** | **61% reduction** |

Fixed seed means the AI applies the same "style" to every frame, eliminating seed-induced variation between frames. This is the single biggest improvement in this spike.

## 7. Color Correction Results

Applied FFmpeg `eq=saturation=1.25:contrast=1.05` to Variant A denoise 0.35 output:

| Metric | Raw | Prev Lineart | Variant A | Variant A + cc |
|---|---|---|---|---|
| Saturation | 0.2704 | 0.2090 | 0.2230 | **0.2405** |
| Delta vs raw | — | −0.0615 | −0.0475 | **−0.0299** |

Saturation loss reduced by 51% compared to previous Lineart. Color correction is deterministic, costs zero GPU time, and can be tuned per-template.

## 8. Best Setup

| Parameter | Value |
|---|---|
| Method | Lineart ControlNet (Union ControlNet) |
| Checkpoint | RealVisXL_V5.0_Lightning_fp16 |
| Preprocessor | LineartStandardPreprocessor |
| Control strength | 0.75 |
| Denoise | 0.35 |
| Steps / CFG / Sampler | 8 / 1.6 / euler normal |
| Seed | Fixed (20260624) |
| Prompt | Variant A — Game promo vivid |
| Post-processing | FFmpeg eq saturation=1.25, contrast=1.05 |

## 9. 2-Second Temporal Test

48 continuous frames processed with fixed seed + Variant A at denoise 0.35:

- **Flicker:** Essentially eliminated. MeanDiff 0.0036 (2.6× raw camera motion, vs 9× for previous)
- **Saturation:** 0.2230 without cc, 0.2405 with cc (raw: 0.2704)
- **Subject stability:** No deformation detected
- **Processing:** 155s for 48 frames (3.2s/frame)
- **Estimated 8s:** ~620s (~10.3 min)

## 10. Product Sanity Check

4 product keyframes with Variant A at denoise 0.35:
- Saturation: +0.0369 gain (14% more than previous Canny's +0.0323)
- Product shape: stable
- Material identity: preserved
- Suitable for product advertising: Yes (adds color without deforming geometry)

## 11. Scorecard Summary

| Dimension | Previous | This Spike | Improvement |
|---|---|---|---|
| Saturation preservation | 2/5 | **4/5** | ++ |
| Flicker | 4/5 | **5/5** | + |
| Visual lift | 3/5 | 3-4/5 | + |
| Subject stability | 4/5 | 4/5 | = |
| Product stability | 4/5 | 4/5 | = |
| Text safety | PASS | PASS | = |

## 12. Final Decision

**PARTIAL** — improving toward PASS. Major technical issues (flicker, saturation) are solved. Visual lift is the remaining question — requires human reviewer confirmation.

## 13. Product Recommendation

**Submit for human review.** The technical quality is now production-grade. The decision hinges on whether humans perceive the AI-enhanced output as "clearly better" than raw Blender.

**Decision tree:**
- If ≥ 2 reviewers prefer AI + colorfix → **PASS** → proceed with ControlNet integration
- If reviewers are split or indifferent → one more narrow cycle (checkpoint test)
- If reviewers prefer raw → **close ControlNet**, move to Layered Subject Protection

**Key files for review:**
- `spikes/ai_lineart_color_fix/output/videos/raw_vs_A_0.35_colorfix_2s.mp4` — Raw vs Enhanced (best)
- `spikes/ai_lineart_color_fix/output/videos/prev_vs_A_0.35_2s.mp4` — Old vs New comparison
- `spikes/ai_lineart_color_fix/output/videos/enhanced_A_0.35_colorfix_2s.mp4` — Enhanced standalone
