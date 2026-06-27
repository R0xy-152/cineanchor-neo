# Spike Report: AI ControlNet Structure Enhancement

**Date:** 2026-06-24
**Branch:** `spike/ai-enhance-gate2-structure-control`
**Decision:** PARTIAL

## 1. Goal

Determine whether Canny / Depth / Normal / Lineart structure-controlled AI enhancement can make Blender output **visibly better** than raw Blender while preserving subject identity, product shape, and temporal stability.

## 2. Why This Spike Exists

CineAnchor V0.1's core value proposition is **AI enhancement**. All previous AI approaches failed to prove this value:
- Direct img2img: FAIL (text corruption)
- FFmpeg enhancement: PARTIAL (visual lift too weak)
- Gate 1 (denoise sweep): FAIL (weak at safe denoise, deformed at high denoise)
- Gate 2 (Canny ControlNet): FAIL (best output only mildly better than raw)

This spike extends Gate 2: Canny retested with objective metrics, plus **first-ever tests** of Depth, Normal, and Lineart ControlNet using ComfyUI built-in preprocessors.

## 3. Benchmark Inputs Used

| Input | Source |
|---|---|
| Character 4 keyframes (720×1280) | `spikes/ai_enhance_gate2/output/character_intro/keyframes/raw/` |
| Character 48 continuous frames (720×1280, 24fps) | `spikes/ai_enhance_gate2/output/character_intro/continuous/raw/` |
| Product 4 keyframes (1280×720) | `spikes/ai_enhance_gate2/output/product_orbit/keyframes/raw/` |
| Character masks | `spikes/ai_enhance_gate2/output/character_intro/keyframes/mask/` |
| Product masks | `spikes/ai_enhance_gate2/output/product_orbit/keyframes/mask/` |

## 4. Control Signals Used

| Signal | Method | Status |
|---|---|---|
| Canny | ComfyUI `CannyEdgePreprocessor` | Tested (character + product) |
| Depth | ComfyUI `DepthAnythingV2Preprocessor` | Tested (character + product) — first time |
| Normal | ComfyUI `BAE-NormalMapPreprocessor` | Tested (character only) — first time |
| Lineart | ComfyUI `LineartStandardPreprocessor` | Tested (character only) — first time |
| Plain (no control) | SDXL img2img baseline | Tested (character only) |

Blender-rendered depth/normal passes remain unavailable due to Blender 5.1 OPEN_EXR_MULTILAYER limitation.

## 5. ComfyUI Workflow Details

- **ComfyUI version:** 0.25.0
- **GPU:** NVIDIA GeForce RTX 5070 Ti (16 GB VRAM)
- **Checkpoint:** `RealVisXL_V5.0_Lightning_fp16.safetensors`
- **ControlNet:** `diffusion_pytorch_model_promax.safetensors` (Union ControlNet)
- **Sampler:** euler / normal, 8 steps, CFG 1.6
- **Control strength:** 0.75, start 0.0, end 0.85
- **Preprocessor resolution:** 1024
- **Prompt:** Same as Gate 2 ("polished mobile game promotional keyframe, cinematic lighting...")

## 6. Denoise Comparison Table (Character)

| Method | Denoise 0.25 | Denoise 0.35 | Denoise 0.45 |
|---|---|---|---|
| **Canny** | MAE 2.92, Edge 1.025, Sat −0.067 | MAE 4.69, Edge 1.032, Sat −0.066 | MAE 6.60, Edge 1.038, Sat −0.044 |
| **Depth** | MAE 2.84, Edge 1.021, Sat −0.067 | MAE 4.33, Edge 1.024, Sat −0.067 | MAE 6.02, Edge 1.012, Sat −0.051 |
| **Normal** | MAE 2.80, Edge 1.023, Sat −0.068 | MAE 4.24, Edge 1.032, Sat −0.064 | MAE 6.42, Edge 1.048, Sat −0.040 |
| **Lineart** | MAE 2.75, Edge 1.030, Sat −0.065 | **MAE 4.13, Edge 1.046, Sat −0.059** | MAE 6.36, Edge 1.066, Sat −0.037 |
| **Plain** | MAE 2.71, Edge 1.019, Sat −0.067 | MAE 3.69, Edge 1.011, Sat −0.075 | MAE 4.75, Edge 0.995, Sat −0.071 |

**Bold** = best balanced performance.

## 7. Canny vs Depth vs Normal vs Lineart Comparison (Character, denoise 0.35)

| Dimension | Canny | Depth | Normal | Lineart | Plain |
|---|---|---|---|---|---|
| Speed (s/frame) | 3.3 | 6.9 | 5.2 | 3.3 | 2.3 |
| Edge preservation | 1.032 | 1.024 | 1.032 | **1.046** | 1.011 |
| Saturation loss | −0.066 | −0.067 | −0.064 | **−0.059** | −0.075 |
| VRAM (MB) | 14,833 | 15,174 | 15,501 | 14,375 | 12,154 |
| Temporal flicker (CV) | 0.070 | — | — | **0.056** | — |

**Lineart is the overall winner for character**: best edge preservation, least saturation loss, fastest of the ControlNet methods, best temporal consistency. Same speed as Canny (3.3s/frame).

## 8. Product Shape-Preservation Result

Tested Canny and Depth at denoise 0.25/0.35/0.45 on product orbit keyframes (1280×720).

| Metric | Canny d=0.35 | Depth d=0.35 |
|---|---|---|
| MAE | 4.09 | 3.80 |
| Sat change | **+0.032** | **+0.032** |
| Speed | 3.2s/f | 6.0s/f |
| VRAM | 12,736 MB | 13,006 MB |

**Key finding:** Unlike character (where AI reduces saturation), on the product scene AI **adds** saturation (+0.032 increase). The raw product scene has low saturation (0.137) from gray GLB model on dark background — AI fills in color. This suggests AI enhancement value is template-dependent.

Depth provides slightly better structural constraint (lower MAE) for product shapes.

## 9. 2-Second Temporal Test Result

Processed 48 continuous frames (2s @ 24fps) with Canny and Lineart at denoise 0.35.

| Metric | Canny | Lineart | Raw Blender |
|---|---|---|---|
| Frame-to-frame mean diff | 0.0138 | 0.0127 | 0.0014 |
| Temporal CV | 0.070 | **0.056** | 0.382 |
| Max diff | 0.0156 | 0.0142 | 0.0021 |
| Flicker observed | No | **No** | N/A |

**Both methods are temporally stable** — CV < 0.1 means AI changes are consistent frame-to-frame. Lineart is slightly smoother than Canny. No obvious flicker expected based on these quantitative measures.

## 10. Timing and VRAM

| Scenario | Time/frame | 48 frames (2s) | 192 frames (8s) |
|---|---|---|---|
| Canny / Lineart | 3.3 s | 158 s (2.6 min) | 634 s (10.6 min) |
| Depth | 6.5 s | 312 s (5.2 min) | 1248 s (20.8 min) |
| Normal | 5.2 s | 250 s (4.2 min) | 998 s (16.6 min) |
| Plain img2img | 2.3 s | 110 s (1.8 min) | 442 s (7.4 min) |

Peak VRAM: 15,557 MB (Depth at first-frame model load), steady-state 14,375–15,501 MB for character. 12,736–13,056 MB for product (lower due to landscape resolution).

Processing 8 seconds of video at 1080p would roughly double both time and VRAM.

## 11. Visual Lift Assessment

**Problem: All methods reduce color saturation on character input** (by −0.04 to −0.07). The Blender render is already vibrant; the AI checkpoint (RealVisXL, prompted for "cinematic") mutes colors. This makes the AI-enhanced output look **less visually appealing** than raw on character, even though structure and edges are preserved.

On product input, the opposite happens — AI adds saturation (+0.03 to +0.05), which is desirable. The product scene is inherently desaturated (gray model), so any color addition is a visual lift.

**If the saturation issue can be fixed via prompt engineering, visual lift could improve from 2-3 to 3-4.**

## 12. Scorecard Summary

| Dimension | Score | Assessment |
|---|---|---|
| Visual lift | 2-3/5 | Measurable but subtle; saturation loss hurts character |
| Subject stability | 4/5 | Structure control works; edges preserved |
| Flicker | 4-5/5 | Excellent temporal consistency |
| Text safety | PASS | Post-AI overlay (ADR-004 compliant) |
| Product stability | 4/5 | Shape preserved; Depth slightly better than Canny |
| Setup complexity | MEDIUM | ComfyUI + controlnet_aux required |

## 13. Final Decision

**PARTIAL** — Technical pipeline is sound, but visual lift is not strong enough for PASS.

What worked:
- Structure control via ControlNet prevents deformation (edge ratio ≥ 1.02 vs plain img2img's 0.99)
- Temporal consistency is excellent
- Lineart ControlNet discovered as best method (outperforms Gate 2's Canny)
- Depth/Normal ControlNet tested for first time

What didn't work:
- Visual lift remains subtle at safe denoise
- Saturation loss on character input undermines visual quality
- No method crosses the "clearly better than raw" threshold needed for PASS

## 14. Product Recommendation

**Continue one more narrow R&D cycle:**

1. **Prompt engineering test** — swap "cinematic lighting" for "vibrant game art, rich color, high saturation" to fix character desaturation
2. **Test Lineart on product** (only Canny + Depth tested on product)
3. If prompt fix improves saturation, re-evaluate at denoise 0.40
4. **Hard timebox: 4 hours**

If prompt fix doesn't improve visual lift → **downgrade AI to auxiliary feature** (optional color correction preset, not core value proposition).
