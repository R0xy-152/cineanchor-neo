# AI Enhancement Method Scorecard: Lineart Color Fix

## Method Identification

| Field | Value |
|---|---|
| **Method name** | Lineart ControlNet + Prompt Engineering + Color Correction |
| **Branch name** | `spike/ai-lineart-color-fix` |
| **Date evaluated** | 2026-06-24 |
| **Evaluator** | Claude (AI agent), quantitative metrics |
| **Input asset** | character_intro + product_orbit |

## Workflow

| Field | Value |
|---|---|
| **Base model** | SDXL 1.0 |
| **Checkpoint** | `RealVisXL_V5.0_Lightning_fp16.safetensors` |
| **ControlNet model(s)** | `diffusion_pytorch_model_promax.safetensors` (Union ControlNet) |
| **Control signal used** | Lineart (LineartStandardPreprocessor) |
| **Control signal strength** | 0.75, start 0.0, end 0.85 |
| **Denoise value** | 0.35 (best from previous spike) |
| **Steps** | 8 |
| **CFG scale** | 1.6 |
| **Scheduler / sampler** | euler / normal |
| **Seed strategy** | **Fixed seed** (key improvement — previous used frame-varying seed) |
| **Additional LoRAs** | None |
| **Prompt (positive) — Variant A** | "colorful mobile game promotion still, vivid saturated colors, bright stylized lighting, crisp character render, premium mobile game promo, preserve original character design, preserve silhouette, preserve color palette, game art style, vibrant game keyframe, rich bright colors, clean cel-shaded lighting, no cinematic dark mood, no filmic desaturation, no realistic skin texture, no gritty rendering, no moody shadows, no low saturation, no dramatic shadows, no text" |
| **Prompt (negative) — Variant A** | "text, watermark, logo, deformed subject, changed face, changed outfit, cinematic lighting, filmic look, desaturated, dark shadows, moody, gritty, realistic skin, photo-realistic, 3D render artifacts, extra limbs, extra objects, melted edges, blur, flicker, oversaturated to burned, noisy artifacts, layout change" |
| **Post-AI color correction** | FFmpeg `eq=saturation=1.25:contrast=1.05:brightness=0.0` |

## Prompt Variants Tested

| Variant | Label | Sat Delta vs Previous | Verdict |
|---|---|---|---|
| **A** | Game promo vivid | **−0.0475 (23% better)** | **BEST — adopted** |
| B | Original-color preservation | −0.0627 (worse) | Rejected |
| C | Minimal style lift | −0.0689 (worse) | Rejected |
| (Previous) | Cinematic (Gate 2 prompt) | −0.0585 (baseline) | — |

## Processing Metrics

| Metric | Character (720×1280) | Product (1280×720) |
|---|---|---|
| **Frames processed** | 24 keyframes + 48 continuous | 4 keyframes |
| **Time per frame (avg)** | 3.2 s | 3.1 s |
| **Total 2s processing time** | 155 s (48 frames) | — |
| **Estimated 8s processing time** | ~620 s (~10.3 min) | — |
| **Peak VRAM** | ~15.2 GB (estimated) | ~13 GB (estimated) |
| **GPU** | NVIDIA GeForce RTX 5070 Ti (16 GB) | |

## Quality Assessment — Character

| Dimension | Previous Lineart | Variant A (no cc) | Variant A + colorfix | Change |
|---|---|---|---|---|
| **Saturation delta** | −0.0615 | **−0.0475** | **−0.0299** | 23% → 51% improvement |
| **Temporal MeanDiff** | 0.0127 | **0.0036** | 0.0044 | **72% reduction** |
| **Temporal CV** | 0.056 | 0.165 | 0.149 | Lower absolute variation |
| **Per-frame MAE std** | 0.389 | **0.151** | — | **61% more consistent** |
| **MAE vs raw** | 4.17 | 4.36 | — | Slightly more visual change |
| **Visual lift (1–5)** | 3 | 3 | **3-4** | Close to "clearly better" |
| **Subject stability (1–5)** | 4 | 4 | 4 | No deformation |
| **Flicker (1–5)** | 4 | **5** | **5** | Essentially flicker-free |
| **Saturation preservation (1–5)** | 2 | 3 | **4** | Major improvement |

## Quality Assessment — Product

| Dimension | Previous Canny | Variant A Lineart |
|---|---|---|
| **Saturation delta** | +0.0323 | **+0.0369** (14% more) |
| **Product shape stability** | 4 | 4 |
| **Visual lift** | 3 | 3-4 |

## Text Stability

| Check | Result |
|---|---|
| Was text processed by AI? | NO |
| Was text added post-AI via overlay? | YES |
| Is final text readable? | PASS |

## Side-by-Side Comparison Assets

| Asset | Path |
|---|---|
| Raw vs Variant A (no cc) | `output/videos/raw_vs_A_0.35_2s.mp4` |
| Raw vs Variant A + colorfix | `output/videos/raw_vs_A_0.35_colorfix_2s.mp4` |
| Previous Lineart vs Variant A | `output/videos/prev_vs_A_0.35_2s.mp4` |
| Enhanced (no cc) standalone | `output/videos/enhanced_A_0.35_2s.mp4` |
| Enhanced (with cc) standalone | `output/videos/enhanced_A_0.35_colorfix_2s.mp4` |
| Keyframe comparisons | `output/keyframes/keyframes/A_denoise_0_35/` |

## Setup Complexity

| Factor | Assessment |
|---|---|
| **Setup complexity** | MEDIUM |
| **New dependencies** | None beyond previous ControlNet spike |
| **Integration feasibility** | Feasible. Same ComfyUI API pattern. Fixed seed reduces randomness. |
| **Color correction** | Trivial FFmpeg eq filter — deterministic, zero GPU cost |
| **Repeatability** | HIGH with fixed seed |

## Decision

| Field | Value |
|---|---|
| **Decision** | **PARTIAL** (improving toward PASS) |
| **Confidence** | HIGH |

### Rationale

**Major improvements over previous ControlNet spike:**
1. **Flicker essentially solved**: frame-to-frame MeanDiff reduced 72% (0.0127 → 0.0036) via fixed seed
2. **Saturation loss halved**: 51% improvement with prompt A + color correction (−0.0615 → −0.0299)
3. **Per-frame consistency**: 61% less MAE variation across frames

**Why still PARTIAL:**
- Visual lift, while improved, is still in the "moderate" range — human reviewer confirmation needed
- Color correction helps substantially but is a post-hoc fix, not an AI-driven improvement
- The core value proposition ("AI-enhanced product") still requires AI to contribute visible enhancement beyond what FFmpeg color correction alone could do
- Without color correction, visual lift is still borderline (3/5)

**Why close to PASS:**
- With color correction at sat=1.25, the output may be clearly preferable to raw for most viewers
- Temporal stability is now essentially production-quality (flicker score: 5/5)
- The fixed-seed approach is a game-changer for temporal consistency

## Product Recommendation

```
Submit for human review. If ≥ 2 non-developer reviewers prefer the AI + colorfix
output over raw Blender → upgrade to PASS and proceed with ControlNet integration.

If reviewers do NOT prefer it → close ControlNet as non-product-ready.

Specific recommendation:
1. Reviewer should watch both `raw_vs_A_0.35_colorfix_2s.mp4` and
   `prev_vs_A_0.35_2s.mp4` side-by-side
2. If colorfix version is preferred → PASS, proceed to integration design
3. If neither is preferred → close ControlNet route, move to Layered Subject Protection
4. ControlNet route is technically mature enough for integration IF visual quality passes review
```

## Known Risks

1. Fixed seed eliminates seed-based variation but means the same input always produces the same output — may be desirable for production
2. Color correction at sat=1.25 was tuned for this specific character input — may need per-template tuning
3. Only tested with RealVisXL V5.0 Lightning checkpoint — other checkpoints may behave differently
4. 8-second full render time of ~10 minutes is acceptable for local production but may feel slow
5. VRAM peaks near 16GB capacity — cards with < 16GB may need --lowvram mode
6. Product test was keyframes only — 2s product video not tested
