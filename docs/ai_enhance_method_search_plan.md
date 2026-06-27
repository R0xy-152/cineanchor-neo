# AI Enhancement Method Search Plan

**Date:** 2026-06-24
**Status:** Active
**Phase:** Post-V0.1 Phase A — R&D Method Search

## 1. Why This Method Search

CineAnchor V0.1 can render 8–15 second game promo videos through a working
pipeline: Web → FastAPI → Project JSON → Blender Eevee → FFmpeg → MP4.
This pipeline is stable and produces clean renders.

However, the product's stated core value proposition is **AI enhancement** —
not just Blender rendering. If AI enhancement cannot produce a visually
compelling result that is clearly superior to the Blender raw output, while
maintaining subject stability and temporal consistency, then the product
direction may need to pause or pivot.

The previous AI enhancement attempts have systematically eliminated the
simplest approaches without finding a clear winner. The remaining approaches
require more deliberate exploration — and a structured benchmark framework
to ensure results are comparable.

## 2. Previous AI Enhancement Results (Summary of Failures)

### Attempt 1: Direct Full-Frame img2img (Route 3 Spike)

- **Result:** FAIL
- **Why:** SDXL img2img at any denoise above ~0.12 corrupted rendered text.
  At conservative settings (denoise 0.12) that preserved text, the visual
  improvement was negligible.
- **Key Learning:** Text must never pass through AI processing.

### Attempt 2: Conservative ComfyUI Reference + FFmpeg (Route 3)

- **Result:** PARTIAL
- **Why:** Extracted color/style reference from ComfyUI keyframe enhancement,
  applied as FFmpeg `eq` + `unsharp` filters to the full video. Visually
  stable but improvement is very light — closer to color correction than
  "AI enhancement."
- **Key Learning:** FFmpeg-only post-processing is insufficient. If the product
  claims AI enhancement, actual AI must contribute visible value.

### Attempt 3: AI Enhancement Feasibility Gate 1

- **Result:** FAIL
- **Why:** Systematic denoise sweep (0.25, 0.35, 0.50) on plain SDXL img2img.
  - denoise 0.25: Stable but visual lift is weak.
  - denoise 0.35: Stronger lift but subject/details begin to deform.
  - denoise 0.50: Unacceptable deformation.
  - Text stability was solved by post-AI text overlay (deterministic FFmpeg drawtext).
  - Non-developer feedback was not collected.
- **Key Learning:** Post-AI text overlay solves the text corruption problem.
  But plain img2img cannot simultaneously achieve strong visual lift AND
  subject stability. Structure control is needed.

### Attempt 4: AI Enhancement Feasibility Gate 2 — Structure Control

- **Result:** FAIL
- **Why:** Canny ControlNet + subject-protected compositing tested across
  multiple strengths and configurations.
  - Canny ControlNet improved frame-to-frame stability vs plain img2img.
  - Best stable output (Canny strength 0.75, denoise 0.35) was only mildly
    better than raw Blender.
  - Depth and Normal passes could not be generated (Blender 5.1.2 lacks
    OPEN_EXR_MULTILAYER output format).
  - Non-developer feedback was not collected.
- **Key Learning:** Canny alone is not enough. Depth and Normal control were
  not tested. Subject-protected compositing works technically but didn't
  help because the background was already simple.

### Pattern Across All Attempts

| Approach | Visual Lift | Stability | Text Safety | Verdict |
|---|---|---|---|---|
| Direct img2img (denoise 0.12) | Too weak | OK | FAIL (text corrupted) | FAIL |
| Direct img2img (denoise 0.35) | Medium | FAIL (deformation) | FAIL (text corrupted) | FAIL |
| FFmpeg eq+unsharp | Very weak | OK | OK | PARTIAL |
| Post-AI text overlay + denoise 0.25 | Weak | OK | OK | FAIL |
| Post-AI text overlay + denoise 0.35 | Medium | FAIL | OK | FAIL |
| Canny ControlNet + protected composite | Weak-Medium | OK | OK | FAIL |

The core dilemma remains: **higher denoise = more visual lift but less stability.**
All approaches to date have failed to break this trade-off.

## 3. Why Production Hardening Is Paused

The V0.1 formal server architecture (`server/main.py`, modular routes,
schema validation, error model) is structurally sound but the services are
placeholders. Before investing in wiring the Blender + FFmpeg execution
pipeline into the formal server:

1. We need to know whether AI enhancement can work at all.
2. If the answer is no, the product scope shrinks to "Blender template renderer"
   — which changes the architecture significantly (no ComfyUI integration,
   no async enhancement queue, different error model).
3. If the answer is yes, we need to know which method to integrate so the
   service architecture can be designed correctly from the start.

**Production hardening resumes when:** at least one AI enhancement method
achieves PASS on the benchmark scorecard.

## 4. Benchmark Inputs

All methods use the same no-text benchmark inputs for fair comparison.

| Input | Source |
|---|---|
| Character 2s no-text video (48 frames, 720×1280, 24fps) | `spikes/ai_enhance_gate2/output/character_intro/raw_no_text_2s.mp4` |
| Character keyframes (4) | `spikes/ai_enhance_gate2/output/character_intro/keyframes/` |
| Character continuous frames (48) | `spikes/ai_enhance_gate2/output/character_intro/continuous_raw/` |
| Product keyframes (4) | `spikes/ai_enhance_gate2/output/product_orbit/keyframes/` |
| Character subject masks | `spikes/ai_enhance_gate2/output/character_intro/mask/` |
| Product subject masks | `spikes/ai_enhance_gate2/output/product_orbit/mask/` |
| Character Canny edge maps | `spikes/ai_enhance_gate2/output/character_intro/keyframes/canny/` |

See `spikes/ai_benchmark/README.md` for regeneration commands if Gate 2 outputs
are unavailable.

## 5. Method Priority Ranking

Methods are ranked by expected visual effect potential.

| Priority | Method | Expected Lift | Risk | Branch | Status |
|---|---|---|---|---|---|
| 1 | Commercial video-to-video (upper bound) | Very High | Medium | (future) | NOT STARTED |
| 2 | Temporal video-to-video | High | High | (future) | NOT STARTED |
| 3 | **ControlNet / Depth / Canny / Normal** | Medium-High | Low-Medium | `spike/ai-controlnet-structure-enhance` | **TASK READY** |
| 4 | **Layered subject protection** | Medium | Low | `spike/ai-layered-subject-protection` | **TASK READY** |
| 5 | **AI atmosphere / lighting overlay** | Medium | Low | `spike/ai-atmosphere-overlay` | **TASK READY** |
| 6 | Frame-by-frame repaint upper bound | Very High | High | (future) | NOT STARTED |
| 7 | Real LUT / color transfer | Low-Medium | Very Low | (future) | NOT STARTED |
| 8 | Plain SDXL img2img | Low-Medium | High | — | COMPLETED — FAIL |
| 9 | FFmpeg eq + unsharp | Low | Very Low | — | COMPLETED — PARTIAL |

Methods 3, 4, and 5 have prepared task prompts in `spikes/ai_benchmark/tasks/`
and are ready to be assigned to spike agents.

## 6. Evaluation Scorecard

All methods are evaluated using the unified scorecard at
`spikes/ai_benchmark/evaluation/scorecard_template.md`.

**Key dimensions:**
- Visual lift (1–5)
- Subject / product shape stability (1–5)
- Flicker / temporal consistency (1–5)
- Text safety (PASS/FAIL — must be post-AI overlay)
- Processing time and VRAM
- Setup complexity (LOW / MEDIUM / HIGH)
- Reviewer preference (if collected)

**Decision rules:**
- **PASS:** Visual lift ≥ 4, stability ≥ 4, flicker ≥ 4, text = PASS.
  If reviewer feedback collected: ≥ 2 prefer AI version.
- **PARTIAL:** Works for one template but not both; OR good lift but flicker;
  OR stable but not visually stunning.
- **FAIL:** Weak lift, unacceptable deformation, obvious flicker, or setup
  too complex for current product stage.

## 7. Multi-Agent Branch Plan

Three method search spikes can run in parallel (they are independent):

| Branch | Method | Task Prompt | Dependencies |
|---|---|---|---|
| `spike/ai-controlnet-structure-enhance` | #3 ControlNet structure control | `spikes/ai_benchmark/tasks/prompt_controlnet_structure.md` | Gate 2 outputs |
| `spike/ai-layered-subject-protection` | #4 Layered subject protection | `spikes/ai_benchmark/tasks/prompt_layered_subject_protection.md` | Gate 2 masks |
| `spike/ai-atmosphere-overlay` | #5 Atmosphere overlay | `spikes/ai_benchmark/tasks/prompt_atmosphere_overlay.md` | Benchmark inputs |

If all three fail, methods 1, 2, 6, and 7 may be explored in a second round.

### Spike Agent Rules

Each agent must:
- Work ONLY within its assigned `spike/ai-*` directory.
- Use benchmark inputs from `spikes/ai_benchmark/` or Gate 2 outputs.
- Fill out the scorecard with measurements and observations.
- NOT modify production code (`server/`, `apps/web/`).
- NOT commit generated media (MP4, PNG, models).
- NOT process text with AI.

## 8. Final Decision Framework

After all method agents report back:

### If Any Method Is PASS

→ **Proceed** with CineAnchor as an AI-enhanced product.

Next steps:
1. Select the winning method.
2. Design the service architecture for that method.
3. Wire the method into the production pipeline.
4. Resume production hardening of `server/main.py`.
5. Collect non-developer feedback on the enhanced output.

### If Only PARTIAL Results

→ **Downgrade** AI to an auxiliary feature OR run one more narrow R&D round.

Option A: Downgrade
- Keep AI enhancement as an optional post-processing preset.
- Position CineAnchor as a "Blender template renderer" with optional AI color grade.
- Remove "AI enhancement" from core value proposition.

Option B: Narrow R&D
- Identify the specific gap (checkpoint too weak? prompt engineering? resolution?)
- Run one more focused round targeting that gap.
- Set a hard timebox (1 week) for the narrow round.

### If ALL Methods FAIL

→ **Pause or pivot** CineAnchor's AI enhancement direction.

Options:
1. Pause development and reassess after upstream AI model improvements.
2. Pivot to pure Blender template product (no AI claims).
3. Pivot to a different AI approach entirely (e.g., fine-tuned model on
   game trailer data — but this requires training infrastructure beyond
   current scope).

## 9. Text Handling Rule (IMMUTABLE)

> **Text must NEVER be processed by AI.**

This is a hard architectural rule, validated by multiple failed experiments:
- Titles, subtitles, and all text overlays must be added via deterministic
  FFmpeg `drawtext` or equivalent AFTER the AI processing stage.
- Any method that requires AI to see, process, or generate text pixels is
  automatically INVALID.
- The benchmark inputs intentionally omit text so every method starts from
  the same clean base.

This rule is documented in:
- `spikes/ai_benchmark/README.md` (benchmark rules)
- `docs/adr/ADR-004-no-full-frame-ai-video-regeneration.md` (ADR)
- All three task prompts (explicit constraint)

## 10. Timeline

| Phase | Duration | Outcome |
|---|---|---|
| Benchmark preparation | 1 day (this task) | Benchmark package, scorecard, task prompts |
| Method search spikes (parallel) | 3–5 days | 3 scorecards with PASS/PARTIAL/FAIL decisions |
| Results synthesis | 1 day | Decision on product direction |
| **Total** | **5–7 days** | Go / No-Go for AI-enhanced CineAnchor |

## References

- `spikes/ai_benchmark/README.md` — Benchmark package documentation
- `spikes/ai_benchmark/evaluation/method_matrix.md` — Full method ranking and details
- `spikes/ai_benchmark/evaluation/scorecard_template.md` — Evaluation rubric
- `spikes/ai_benchmark/tasks/` — Three follow-up task prompts
- `docs/spike_results.md` — Previous AI enhancement results
- `docs/adr/ADR-004-no-full-frame-ai-video-regeneration.md` — Text handling ADR
- `spikes/ai_enhance_gate2/` — Most recent AI enhancement experiments
