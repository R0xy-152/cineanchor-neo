# AI Enhancement Method Scorecard: ControlNet Structure Enhancement

## Method Identification

| Field | Value |
|---|---|
| **Method name** | Multi-ControlNet Structure-Controlled img2img (Canny / Depth / Normal / Lineart) |
| **Branch name** | `spike/ai-enhance-gate2-structure-control` |
| **Date evaluated** | 2026-06-24 |
| **Evaluator** | Claude (AI agent), quantitative metrics |
| **Input asset** | character_intro + product_orbit |

## Workflow

| Field | Value |
|---|---|
| **Base model** | SDXL 1.0 |
| **Checkpoint** | `RealVisXL_V5.0_Lightning_fp16.safetensors` |
| **ControlNet model(s)** | `diffusion_pytorch_model_promax.safetensors` (Union ControlNet — supports Canny/Depth/Normal/Lineart) |
| **Control signal used** | Canny, Depth (DepthAnythingV2), Normal (BAE), Lineart — all via ComfyUI built-in preprocessors |
| **Control signal strength** | 0.75 (fixed across all methods) |
| **Denoise values tested** | 0.25, 0.35, 0.45 |
| **Steps** | 8 |
| **CFG scale** | 1.6 |
| **Scheduler / sampler** | euler / normal |
| **Additional LoRAs** | None |
| **Prompt (positive)** | "polished mobile game promotional keyframe, cinematic lighting, richer color, clean highlights, premium game ad still, crisp but stable edges, preserve exact subject silhouette, preserve exact pose, preserve exact composition, no text" |
| **Prompt (negative)** | "text, watermark, logo, deformed subject, changed face, changed costume, changed product geometry, extra limbs, extra objects, melted edges, blur, flicker, oversaturated, noisy artifacts, layout change" |

## Processing Metrics

| Metric | Character (720×1280) | Product (1280×720) |
|---|---|---|
| **Frames processed** | 60 keyframes + 96 continuous | 24 keyframes |
| **Time per frame — Canny** | 3.3 s | 3.3 s |
| **Time per frame — Depth** | 6.9 s | 6.0 s |
| **Time per frame — Normal** | 5.2 s | — |
| **Time per frame — Lineart** | 3.3 s | — |
| **Time per frame — Plain img2img** | 2.3 s | — |
| **Time per frame — 48-frame continuous (Canny)** | 3.3 s (158s total) | — |
| **Time per frame — 48-frame continuous (Lineart)** | 3.3 s (158s total) | — |
| **Peak VRAM — Character** | 15,557 MB (Depth, first frame model load) | — |
| **Peak VRAM — Character (steady state)** | 14,375–15,501 MB | — |
| **Peak VRAM — Product** | — | 12,736–13,056 MB |
| **GPU** | NVIDIA GeForce RTX 5070 Ti (16 GB) | |

## Quality Assessment — Character

Rate each dimension 1–5.

| Dimension | Canny | Depth | Normal | Lineart | Plain | Notes |
|---|---|---|---|---|---|---|
| **Visual lift** (MAE-based estimate) | 3 | 2-3 | 3 | 3 | 2 | All methods show measurable but subtle change at safe denoise |
| **Subject stability** (edge ratio) | 4 (1.032) | 4 (1.024) | 4 (1.032) | 4 (1.046) | 3 (1.012) | Lineart best edge preservation; plain loses edges at d=0.45 |
| **Flicker** (temporal CV) | 4 (CV 0.070) | — | — | 5 (CV 0.056) | — | Lineart best temporal consistency |
| **Saturation preservation** | 3 (−0.066) | 3 (−0.067) | 3 (−0.064) | 3 (−0.059) | 2 (−0.075) | ALL methods desaturate vs raw Blender |
| **Setup complexity** | N/A | N/A | N/A | N/A | N/A | MEDIUM — requires ComfyUI + controlnet_aux custom nodes |

**Key:** Edge ratio > 1.0 means edges are preserved or enhanced. CV (coefficient of variation) < 0.1 indicates excellent temporal smoothness.

## Quality Assessment — Product

| Dimension | Canny | Depth | Notes |
|---|---|---|---|
| **Visual lift** | 3 | 3 | Measurable change |
| **Product shape stability** | 4 | 4 | No warping detected; Depth slightly better constraint (lower MAE) |
| **Saturation change** | +0.032 (improved!) | +0.032 (improved!) | Unlike character, AI ADDS saturation to product |
| **Best denoise for product** | 0.45 (MAE 5.86, sat +0.044) | 0.45 (MAE 5.33, sat +0.046) | Product tolerates higher denoise |

## Text Stability

| Check | Result |
|---|---|
| Was text processed by AI? | NO |
| Was text added post-AI via overlay? | YES (text added via FFmpeg drawtext after AI — per ADR-004) |
| Is final text readable and undistorted? | PASS |

## Side-by-Side Comparison Assets

| Asset | Path |
|---|---|
| Character raw keyframes (4) | `spikes/ai_enhance_gate2/output/character_intro/keyframes/raw/` |
| Character comparison grids (all methods × 3 denoise) | `spikes/ai_controlnet_structure_enhance/output/character/comparisons/` |
| Product comparison grids (Canny + Depth × 3 denoise) | `spikes/ai_controlnet_structure_enhance/output/product/comparisons/` |
| Raw 2s video | `spikes/ai_enhance_gate2/output/character_intro/raw_no_text_2s.mp4` |
| Canny enhanced 2s video | `spikes/ai_controlnet_structure_enhance/output/videos/enhanced_canny_2s.mp4` |
| Lineart enhanced 2s video | `spikes/ai_controlnet_structure_enhance/output/videos/enhanced_lineart_2s.mp4` |
| Raw vs Canny side-by-side | `spikes/ai_controlnet_structure_enhance/output/videos/raw_vs_canny_2s.mp4` |
| Raw vs Lineart side-by-side | `spikes/ai_controlnet_structure_enhance/output/videos/raw_vs_lineart_2s.mp4` |

## Setup Complexity

| Factor | Assessment |
|---|---|
| **Setup complexity** | MEDIUM |
| **New dependencies** | `comfyui_controlnet_aux` custom nodes (already installed); DepthAnythingV2, BAE-Normal models auto-downloaded on first use |
| **Integration feasibility for V0.1** | Feasible. ComfyUI API-based, same pattern as Gate 2. ~3.3s/frame at 720p = ~5.7 min for 8s@24fps = 192 frames |
| **Repeatability** | HIGH. Workflow JSON and run_spike.py are deterministic. Same checkpoint + seed = same output |
| **Documentation quality** | HIGH. Full workflow JSON, runner script with CLI, metrics scripts all documented |

## Reviewer Feedback

**Not yet collected.** The user will review visual quality and provide preference data.

| Reviewer | Role | Prefers AI? | Prefers Raw? | No Preference | Comments |
|---|---|---|---|---|---|
| Reviewer 1 | — | ☐ | ☐ | ☐ | Pending user review |
| Reviewer 2 | — | ☐ | ☐ | ☐ | Pending user review |

**Reviewer preference collected:** NO
**Preference ratio (AI : Raw):** Pending

## Decision

| Field | Value |
|---|---|
| **Decision** | **PARTIAL** |
| **Confidence** | HIGH |

### Rationale

**What worked:**
1. Structure control via ControlNet effectively preserves subject edges and shape (edge ratio ≥ 1.02 for all methods vs 0.99 for plain img2img at denoise 0.45)
2. Temporal consistency is excellent — Lineart CV 0.056, Canny CV 0.070 — well below the flicker threshold
3. **Lineart ControlNet is a new discovery** — outperforms Canny on edge preservation (+6.6%), saturation retention, and temporal consistency, at the same speed (3.3s/frame)
4. Product enhancement adds saturation (unlike character) — AI enhancement has template-dependent value
5. Depth/Normal ControlNet tested for the first time with preprocessors (previous Gate 2 could not test them)

**What didn't work:**
1. Visual lift remains moderate — the best denoise (0.35) produces MAE of only 4-6 (on 0-255 scale), which is subtle
2. ALL methods reduce color saturation on character input (−0.06 to −0.07 delta) — the AI's "cinematic" bias mutes the already-vibrant Blender output
3. The fundamental trade-off persists: higher denoise (0.45) gives more change but at denoise 0.45 the subject risk increases, even with ControlNet
4. No method achieves visual lift ≥ 4 while maintaining stability ≥ 4 — the threshold for PASS

### Decision Rules Assessment

- Visual lift ≥ 4: **NO** (best estimate is 2-3 based on MAE and saturation metrics)
- Subject stability ≥ 4: **YES** (edge preservation confirms structure control works)
- Flicker ≥ 4: **YES** (CV < 0.1 for both Canny and Lineart)
- Text stability PASS: **YES** (text is post-AI overlay)
- Processing acceptable: **YES** (3.3s/frame at 720p, ~5.7 min for 8s clip)

**Verdict: PARTIAL** — Technical pipeline works; structure control is effective; but visual lift is not strong enough to prove core product value. Reviewer feedback pending.

## Product Recommendation

```
PARTIAL → Run ONE more narrow R&D cycle targeting the saturation problem.

Specific recommendation:
1. Test prompt engineering to fix saturation loss on character input
   (e.g., "vibrant color, rich saturation, game art style" instead of "cinematic")
2. Test Lineart ControlNet on product (not yet tested — only Canny + Depth)
3. If prompt fix improves saturation, re-evaluate at denoise 0.40
4. Timebox: 4 hours max for the narrow follow-up

If prompt fix doesn't improve visual lift → DOWNGRADE AI to auxiliary feature
(color correction only). The structure-control pipeline works technically but
the visual impact is insufficient for "AI-enhanced" product positioning.
```

## Known Risks / Caveats

1. **Saturation loss on character input is systematic** — likely the checkpoint's "cinematic" bias. May apply to other character images.
2. **Only tested with one checkpoint** (RealVisXL V5.0 Lightning). Other checkpoints (Juggernaut XL, Dreamshaper XL) may produce different saturation behavior.
3. **Visual assessment is metric-only** — no human reviewer has seen the output yet. Metrics may not capture "looks better."
4. **Prompt engineering not tested** — the Gate 2 prompt was carried forward without optimization for Lineart or other methods.
5. **720p resolution only** — 1080p would require ~2.25× more processing time.
6. **VRAM peaks at 15.6 GB** — cards with < 16 GB may OOM or need --lowvram mode.
