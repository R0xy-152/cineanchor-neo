# 05 — Seedance Spark Enhancement Spike — Plan (Andy-reviewed)

> Author: Claude Code (draft) · Reviewed & finalized by: Andy · Status: APPROVED for execution
> Source of truth: `05-seedance-spike-requirements.md` (approved on Andy branch).
> Review gate: `00-workflow-rules.md` §4 step 5 — Andy vets the plan (启鸣 does not review plans).
> Nature: Spike (exploratory, disposable). Keep it light. No ADR triggered (per §8 + the requirements doc).

---

## Andy review verdict

CC's draft is correctly scoped: CC produces only (1) a clean no-particle base video and (2) Seedance prompts; 启鸣 runs Seedance externally and does human acceptance on A/B/C. The glint-disable flag, the no-particles base, and the side-by-side baseline copy all match the requirements. **Approved with five adjustments**, folded into the steps below. ADJ-1 and ADJ-2 are quality-critical; ADJ-3/4/5 are practical handoff fixes.

- **ADJ-1 (text must NOT go through the AI) — quality-critical.** CC's base bakes in the text overlay and asks Seedance to "preserve text readability." AI video-to-video is notorious for garbling letters — this is a high-probability failure. **Render the Seedance base video text-free.** Provide the text as a separate deterministic overlay that 启鸣 (or a later step) composites back onto Seedance's output C. This both removes the garble risk and matches the real production pattern (structure+aesthetic via AI, text deterministic on top). If 启鸣 wants to see text-through-AI behavior for curiosity, that's a separate optional clip — not the primary base.
- **ADJ-2 (prompt ⇄ base consistency) — quality-critical.** The base bakes in rim light + cloth texture (deterministic bg enhancements), but CC's prompts tell Seedance to "ADD background atmosphere / texture / lighting" from scratch — contradictory instructions. The prompts must be written against what the base actually contains: **"enhance the existing rim-lit edges and cloth backdrop, add cinematic haze/depth"** and **"add sparks/embers"** (sparks are the only thing genuinely absent). Every prompt must state precisely what is already in the frame (subject, camera motion, rim light, cloth backdrop, occlusion — and NO sparks, NO text) so Seedance enhances rather than invents/conflicts.
- **ADJ-3 (Seedance-friendly output format).** Ensure the base video is in a format 启鸣 can upload without re-encoding surprises: standard resolution (1080p or 720p), standard fps (24 or 30), H.264 MP4, standard aspect ratio. An odd resolution/fps risks rejection or silent re-encode on the Seedance side.
- **ADJ-4 (clip length for flicker judgement).** 2s may be too short to judge spark frame-to-frame consistency — the #1 risk of 2b (acceptance #5). Render **3–5s** so 启鸣 can actually see whether AI sparks flicker.
- **ADJ-5 (document what's baked, offer a stripped variant only if cheap).** Recommendation: KEEP rim light + cloth texture in the base — they are structural/silhouette anchors that reduce AI drift (more for Seedance to hold onto). Do NOT strip them by default. But `prompts.md` must document exactly what is baked in (ties to ADJ-2). If render budget is trivial, optionally also output a minimal-structure variant so 启鸣 can A/B which base Seedance enhances better — optional, not required.

Everything else in CC's plan stands.

---

## Deliverable 1 — Clean structure base video (text-free)

Blender render of `character_intro` with:
- Subject + camera motion + lighting + shadows + occlusion (already working) — the structural truth Seedance must preserve.
- Background: rim light + cloth texture KEPT (ADJ-5, structural anchor).
- **NO particles** (no embers, no bokeh, no glints), **NO FFmpeg overlays**, **NO text** (ADJ-1).

Changes:
1. Add `glints: bool = True` to `BackgroundEnhanceSpec` in `server/schemas/project.py` (default True = no regression).
2. Gate the glint-sphere loop in `add_stage()` (`render_project.py` ~line 411) on `bg_enhance.get("glints", True)`.
3. Ensure the render path can emit a **text-free** clip (ADJ-1) — disable the text overlay for this base render (flag or a no-text project JSON), keep the text spec saved separately for later deterministic re-composite.
4. Write a minimal project JSON: `particles: null`, `glints: false`, text disabled, duration **3–5s** (ADJ-4).
5. Render → PNG frames → `compose_mp4()` (no effects) → `storage/spike_seedance/base_video.mp4`, in a Seedance-friendly format (ADJ-3).

---

## Deliverable 2 — Seedance prompts (`storage/spike_seedance/prompts.md`)

2–3 English, copy-paste-ready variants. Each prompt must (ADJ-2):
- **State what is already in the base** (preserve, do not alter): subject + identity, camera movement, rim-lit edges, cloth backdrop, occlusion/depth — and explicitly note NO sparks and NO text present.
- **Enhance** (already in base): rim lighting → dramatic cinematic rim; cloth backdrop → richer weave/atmosphere; overall → filmic grade, depth/haze, high contrast.
- **Add** (genuinely absent): spark/ember form — long streak trails ("light streaks"), bright splashing sparks, small discrete orange-gold glowing points.
- Cover 启鸣's four areas: spark form, background atmosphere, texture/material, cinematic lighting.
- Be self-contained (copy-paste directly into Seedance).

---

## Deliverable 3 — Side-by-side comparison setup

Place in `storage/spike_seedance/` for 启鸣:
- **A (baseline):** `particle_final.mp4` — loop 04 deterministic embers (copy).
- **B (base):** `base_video.mp4` — clean structure, no particles, no text.
- **C (Seedance):** produced by 启鸣 externally from B + a prompt.
- Plus the deterministic text overlay asset (ADJ-1) for re-compositing onto C later.

---

## Verification

1. `py_compile` modified files.
2. `unittest discover -s tests` — no regressions (glints default True preserves old behavior).
3. Render base: confirm glints absent, NO particles, **NO text** (ADJ-1), subject + camera + occlusion intact.
4. Confirm base format is Seedance-friendly: 1080p/720p, 24/30fps, H.264 MP4, 3–5s (ADJ-3/4).
5. Review `prompts.md`: each variant states what's baked (preserve), what to enhance, what to add; all 4 areas covered; consistent with the actual base contents (ADJ-2).
6. Output all file paths for 启鸣 retrieval.

---

## Acceptance mapping (to `05-*-requirements.md` §五)

| # | Criterion | Covered by |
|---|-----------|-----------|
| 1 | Overall look improves | 启鸣 judges A vs C externally; base quality (D1) + prompt quality (D2) set C's ceiling |
| 2 | Sparks meet expectation | D2 spark-form prompt + 启鸣 external judgement |
| 3 | Subject no drift | D1 structural anchors (rim+cloth kept, ADJ-5) + ADJ-2 preserve-instructions |
| 4 | Camera preserved | D1 base carries locked camera; ADJ-2 preserve-instructions |
| 5 | Spark frame consistency | ADJ-4 (3–5s clip lets 启鸣 see flicker) — the make-or-break of 2b |
| 6 | CC deliverables | D1 base video path + D2 prompts.md (+ text overlay asset, ADJ-1) |

---

## Note on outcome (per requirements §六)

- Spike passes (1/2 good, 3/4/5 no hard failures) → triggers a new ADR: bounded AI spark enhancement (deterministic base + AI aesthetic), amending/extending ADR-006.
- Spike fails (flicker hard failure or subject drift) → record "tried, not viable," revert to deterministic sparks, ADR-006 stands.
