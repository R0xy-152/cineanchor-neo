# AI Enhancement Method Matrix

Priority-ordered survey of AI enhancement approaches for CineAnchor.
Each method is assessed for expected visual lift potential and stability risk.

## Priority Ranking

Methods are ordered by expected visual effect potential (highest first).

### Tier 1: High Visual Potential (but higher risk/cost)

| # | Method | Expected Visual Lift | Stability Risk | Setup Cost | Status |
|---|---|---|---|---|---|
| 1 | **Commercial video-to-video / external AI upper-bound** | Very High | Medium | LOW (API) | NOT STARTED |
| 2 | **Temporal video-to-video** (SVD, AnimateDiff, etc.) | High | Medium | High | NOT STARTED |

### Tier 2: Structural Control (medium visual, controlled stability)

| # | Method | Expected Visual Lift | Stability Risk | Setup Cost | Status |
|---|---|---|---|---|---|
| 3 | **ControlNet / Depth / Canny / Normal structure-controlled enhancement** | Medium-High | Low-Medium | Medium | **TASK READY** → `tasks/prompt_controlnet_structure.md` |
| 4 | **Layered render: AI only enhances background/lighting/atmosphere** | Medium | Low | Medium | **TASK READY** → `tasks/prompt_layered_subject_protection.md` |
| 5 | **AI-generated atmosphere / lighting overlay** | Medium | Low | Medium | **TASK READY** → `tasks/prompt_atmosphere_overlay.md` |

### Tier 3: Baselines and References

| # | Method | Expected Visual Lift | Stability Risk | Setup Cost | Status |
|---|---|---|---|---|---|
| 6 | **2-second frame-by-frame repaint upper-bound test** | Very High | High (per-frame inconsistency) | Low | NOT STARTED |
| 7 | **Real LUT / color transfer / curves** | Low-Medium | Very Low | Very Low | NOT STARTED |
| 8 | **Plain SDXL img2img baseline** | Low-Medium | High | Low | COMPLETED (Gate 1) — FAIL |
| 9 | **FFmpeg eq + unsharp fallback** | Low | Very Low | Very Low | COMPLETED (Comfy LUT) — PARTIAL |

## Method Details

### 1. Commercial Video-to-Video (Upper Bound)

**What:** Send benchmark videos to a commercial video-to-video API (Runway Gen-3,
Pika, Kling, etc.) and observe what SOTA external models can achieve.

**Purpose:** Establish an upper bound for what "good" looks like. If even commercial
APIs cannot meaningfully enhance the CineAnchor benchmark inputs, the problem may
be the input quality rather than the enhancement method.

**Risk:** Cost, external dependency, not integratable into local product.
This is a research benchmark only — not a product integration target.

### 2. Temporal Video-to-Video

**What:** Use video-aware diffusion models (SVD, AnimateDiff, Video Crafter, etc.)
to enhance the full 2-second sequence with temporal consistency baked into the model.

**Purpose:** Test whether native video models solve the flicker/stability problem
that per-frame img2img approaches suffer from.

**Risk:** High VRAM, complex ComfyUI workflows, may over-smooth or hallucinate motion.
Many video models are trained on real footage, not Blender renders.

### 3. ControlNet Structure-Controlled Enhancement

**What:** Use Canny, Depth, or Normal ControlNet to lock the structure of each frame
while allowing the diffusion model to enhance color, lighting, and texture.

**Current status from Gate 2:**
- Canny ControlNet at strength 0.75 + denoise 0.35 improved frame-to-frame stability
  compared to plain img2img.
- Best stable output was only mildly better than raw Blender.
- Canny at strength 0.30 did not constrain structure enough.
- Depth and Normal not yet tested (blocked by Blender 5.1 limitation).

**Next step:** `tasks/prompt_controlnet_structure.md`

### 4. Layered Subject Protection

**What:** Use subject masks to composite the original Blender subject back over an
AI-enhanced background. AI only touches the background, lighting, and atmosphere.
The subject (character or product) stays 100% original.

**Current status from Gate 2:**
- Protected compositing was implemented in `video_ops.py`.
- Canny ControlNet + protected compositing was tested but visual lift was mild —
  likely because the background in the test scene was simple and didn't benefit much.

**Next step:** `tasks/prompt_layered_subject_protection.md`

### 5. AI Atmosphere / Lighting Overlay

**What:** Generate a separate AI layer (light rays, fog, particles, bloom, color
grading) and composite it over the Blender original. The original frame is untouched;
the AI layer adds cinematic atmosphere.

**Purpose:** Achieve visual lift with zero subject risk. If the overlay looks bad,
the render falls back to the Blender original — no quality regression.

**Next step:** `tasks/prompt_atmosphere_overlay.md`

### 6. Frame-by-Frame Repaint Upper Bound

**What:** Push denoise very high (0.60–0.85) on every single frame, accepting
inconsistency, to see what the diffusion model *wants* the scene to look like
if unconstrained by structure or temporal consistency.

**Purpose:** Upper bound for per-frame potential. If even this looks bad, the
base model/checkpoint is wrong for the task.

### 7. Real LUT / Color Transfer

**What:** Extract color statistics from reference game trailers or promotional
videos and apply them as 3D LUTs. No AI generation at runtime.

**Purpose:** Cheapest possible "enhancement" that might get 60% of the visual
lift with 0% of the stability risk.

### 8. Plain SDXL img2img

**What:** Per-frame SDXL img2img with no control signals, no temporal model.
The simplest AI enhancement baseline.

**Result:** FAIL (Gate 1). denoise 0.25 too weak, denoise 0.35+ caused deformation.

### 9. FFmpeg eq + unsharp

**What:** Pure FFmpeg post-processing: equalizer, unsharp mask, slight saturation
boost. No AI, no GPU.

**Result:** PARTIAL. Stable and works but visual improvement is very light.

## Evaluation Protocol

All methods share the same:
1. **Inputs** — benchmark videos and keyframes (see benchmark README)
2. **Scorecard** — `evaluation/scorecard_template.md`
3. **Decision rules** — PASS / PARTIAL / FAIL (see benchmark README)

## Multi-Agent Branch Plan

| Method # | Branch Name | Task Prompt | Status |
|---|---|---|---|
| 3 | `spike/ai-controlnet-structure-enhance` | `tasks/prompt_controlnet_structure.md` | READY |
| 4 | `spike/ai-layered-subject-protection` | `tasks/prompt_layered_subject_protection.md` | READY |
| 5 | `spike/ai-atmosphere-overlay` | `tasks/prompt_atmosphere_overlay.md` | READY |
| 1 | `spike/ai-commercial-upper-bound` | (future) | NOT READY |
| 2 | `spike/ai-temporal-video` | (future) | NOT READY |
| 6 | `spike/ai-repaint-upper-bound` | (future) | NOT READY |
| 7 | `spike/ai-lut-color-transfer` | (future) | NOT READY |

## Final Decision Framework

After all method agents report back:

- **If any method is PASS:** Proceed with CineAnchor as an AI-enhanced product.
  Integrate the winning method into the production pipeline.
- **If only PARTIAL results:** Either downgrade AI to an auxiliary feature
  (color correction only) or run one more narrow R&D round targeting the
  specific gap (e.g., stronger checkpoint, better prompt engineering).
- **If ALL methods FAIL:** Pause CineAnchor or pivot away from AI enhancement
  as core positioning. Consider repositioning as a pure Blender template product.
