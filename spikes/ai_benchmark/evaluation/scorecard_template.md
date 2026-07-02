# AI Enhancement Method Scorecard

> Fill out one scorecard per method. Copy this template and replace all
> `[PLACEHOLDER]` values with actual measurements and observations.

---

## Method Identification

| Field | Value |
|---|---|
| **Method name** | `[PLACEHOLDER — e.g. Canny ControlNet img2img]` |
| **Branch name** | `[PLACEHOLDER — e.g. spike/ai-controlnet-structure-enhance]` |
| **Date evaluated** | `[PLACEHOLDER]` |
| **Evaluator** | `[PLACEHOLDER]` |
| **Input asset** | `[character_intro / product_orbit / both]` |

## Workflow

| Field | Value |
|---|---|
| **Base model** | `[PLACEHOLDER — e.g. SDXL 1.0, SD 1.5, SVD, etc.]` |
| **Checkpoint** | `[PLACEHOLDER — e.g. dreamshaperXL_v21, Juggernaut XL, etc.]` |
| **ControlNet model(s)** | `[PLACEHOLDER — e.g. control-lora-canny-sdxl, t2i-adapter-canny-sdxl, None]` |
| **Control signal used** | `[canny / depth / normal / mask / none / combination]` |
| **Control signal strength** | `[PLACEHOLDER — e.g. 0.75]` |
| **Denoise value** | `[PLACEHOLDER — e.g. 0.25, 0.35, sweep 0.20–0.40]` |
| **Steps** | `[PLACEHOLDER]` |
| **CFG scale** | `[PLACEHOLDER]` |
| **Scheduler / sampler** | `[PLACEHOLDER]` |
| **Additional LoRAs** | `[PLACEHOLDER — or None]` |
| **Prompt (positive)** | `[PLACEHOLDER]` |
| **Prompt (negative)** | `[PLACEHOLDER]` |

## Processing Metrics

| Metric | Character | Product |
|---|---|---|
| **Frames processed** | `[PLACEHOLDER]` | `[PLACEHOLDER]` |
| **Time per frame (avg)** | `[PLACEHOLDER] s` | `[PLACEHOLDER] s` |
| **Total processing time** | `[PLACEHOLDER] s` | `[PLACEHOLDER] s` |
| **Peak VRAM** | `[PLACEHOLDER] MB` | `[PLACEHOLDER] MB` |
| **GPU** | `[PLACEHOLDER — e.g. RTX 5070 Ti 12GB]` | |

## Quality Assessment

Rate each dimension 1–5 (1 = worst, 5 = best).

| Dimension | Character Score | Product Score | Notes |
|---|---|---|---|
| **Visual lift** (1–5) | `[PLACEHOLDER]` | `[PLACEHOLDER]` | Does it look noticeably better than Blender raw? |
| **Subject stability** (1–5) | `[PLACEHOLDER]` | N/A | Character shape preserved? No face/body distortion? |
| **Product shape stability** (1–5) | N/A | `[PLACEHOLDER]` | 3D model geometry preserved? No warping? |
| **Flicker** (1–5) | `[PLACEHOLDER]` | `[PLACEHOLDER]` | 5 = no flicker, 1 = severe temporal inconsistency |
| **Background improvement** (1–5) | `[PLACEHOLDER]` | `[PLACEHOLDER]` | Background noticeably better? Mood/atmosphere improved? |

## Text Stability

| Check | Result |
|---|---|
| Was text processed by AI? | YES / NO |
| Was text added post-AI via overlay? | YES / NO |
| Is final text readable and undistorted? | PASS / FAIL |

> **Rule:** If text was processed by AI → method is **INVALID**. Text MUST be
> added after AI processing. A FAIL on text stability means the compositing
> method has a bug (not an AI problem).

## Side-by-Side Comparison Assets

| Asset | Path |
|---|---|
| Before keyframe (raw Blender) | `[PLACEHOLDER]` |
| After keyframe (AI enhanced) | `[PLACEHOLDER]` |
| Before/after comparison grid | `[PLACEHOLDER]` |
| Before 2s video (raw) | `[PLACEHOLDER]` |
| After 2s video (AI enhanced) | `[PLACEHOLDER]` |
| Side-by-side video | `[PLACEHOLDER]` |

## Setup Complexity

| Factor | Assessment |
|---|---|
| **Setup complexity** | LOW / MEDIUM / HIGH |
| **New dependencies** | `[PLACEHOLDER — list any new models, checkpoints, or tools beyond current ComfyUI SDXL baseline]` |
| **Integration feasibility for V0.1** | `[PLACEHOLDER — how hard would this be to wire into the production pipeline?]` |
| **Repeatability** | `[PLACEHOLDER — can another developer reproduce these results with the same workflow?]` |
| **Documentation quality** | `[PLACEHOLDER — is the workflow/script well-documented enough for another agent to reproduce?]` |

## Reviewer Feedback (if collected)

| Reviewer | Role | Prefers AI? | Prefers Raw? | No Preference | Comments |
|---|---|---|---|---|---|
| Reviewer 1 | `[non-dev]` | ☐ | ☐ | ☐ | `[PLACEHOLDER]` |
| Reviewer 2 | `[non-dev]` | ☐ | ☐ | ☐ | `[PLACEHOLDER]` |
| Reviewer 3 | `[non-dev]` | ☐ | ☐ | ☐ | `[PLACEHOLDER]` |

**Reviewer preference collected:** YES / NO
**Preference ratio (AI : Raw):** `[PLACEHOLDER]`

## Decision

| Field | Value |
|---|---|
| **Decision** | PASS / PARTIAL / FAIL |
| **Confidence** | HIGH / MEDIUM / LOW |

### Decision Rules (from benchmark README)

**PASS** (all must be true):
- Visual lift is clearly noticeable (score ≥ 4).
- Subject / product shape stays stable (score ≥ 4).
- Text stability: PASS (text added post-AI).
- No obvious flicker over 2s video (score ≥ 4).
- Processing time is acceptable for local production use.
- If reviewer feedback collected: ≥ 2 non-dev reviewers prefer AI-enhanced version.

**PARTIAL** (any of):
- Character input works but product input fails.
- OR visual lift is strong but flicker is present.
- OR stable but visual effect is still not stunning.

**FAIL** (any of):
- Visual lift is still weak (score ≤ 2).
- OR subject / product deformation is unacceptable.
- OR flicker is obvious.
- OR setup complexity is too high for current product stage.

## Summary

```
[PLACEHOLDER — One paragraph summarizing the experiment, key findings,
and what was learned. What worked? What didn't? What would you try next?]
```

## Product Recommendation

```
[PLACEHOLDER — If PASS: recommend integration path.
If PARTIAL: recommend focused follow-up experiment.
If FAIL: recommend abandoning this approach and why.]
```

## Known Risks / Caveats

```
[PLACEHOLDER — Any risks, edge cases, or caveats that the decision doesn't capture.
E.g. "Only tested with one character image — may not generalize."
Or "VRAM peaks at 11.8 GB — may OOM on 8 GB GPUs."]
```
