# 04 — Particle Visibility Fix — Plan (Andy-reviewed)

> Author: Claude Code (draft) · Reviewed & finalized by: Andy · Status: APPROVED for execution
> Source of truth: `04-particle-visibility-fix-requirements.md` + `ADR-006` (incl. 2026-06-27 dated update), both Accepted on Andy branch.
> Review gate: `00-workflow-rules.md` §4 step 5 — Andy vets the plan (启鸣 does not review plans).

---

## Andy review verdict

CC's draft is a strong root-cause plan: it correctly traces the black ember layer to `hide_render=True` + HALO-removed-in-5.1 + sub-pixel particle size, and the filter-wash to `screen` ignoring alpha (`premultiply` fix) + a clipping/skin-overlapping default color. Dual non-black validation (generation-time + pre-composite), the real escalation gate, and the brightness-floor schema validator all directly satisfy the 04 acceptance table. **Approved with four adjustments**, folded into the phases below. ADJ-1 is a correctness blocker — the other three are completeness gaps.

- **ADJ-1 (BLOCKER) — Phase 6 color derivation must not re-create defect 2.** The filter-wash happened *because* ember color was auto-derived from the subject and collapsed into the subject's tone. Phase 6 wires `derive_ember_color()` to **override** the JSON color with a subject-derived value — taken literally, this re-introduces the exact wash we are fixing. Per the ADR-006 update, ember color must be **same hue family but high-saturation / high-luminance with a contrast check against the subject.** So the derivation contract is: derive the subject **hue family only**, then force saturation and luminance up, then verify contrast vs. the subject; if the derived color fails contrast or the brightness floor, fall back to `#F5A623`. The derived color MUST also pass the Phase 5b luminance guard. "Derive verbatim and override" is rejected; "derive hue → boost → contrast-check → guarded fallback" is required.
- **ADJ-2 — Bloom mechanism for Blender 5.1 EEVEE Next.** Legacy `eevee.use_bloom` was removed in EEVEE Next (same version family that removed HALO, which this very plan acknowledges). Setting a non-existent struct attribute will raise, not no-op. So: (a) verify the correct 5.1 glow mechanism (likely a compositor Glare node, not `eevee.use_bloom`); (b) **guard it** so a missing/renamed API cannot crash generation; (c) ember visibility must NOT depend on bloom — the hide_render + OBJECT-instance + emissive-material + size fixes are what make embers visible; bloom is additive glow only.
- **ADJ-3 — Add the 03 regression to Verification.** The plan's "full suite passes" does not cover the visual regression that acceptance #6 demands. Add explicit checks: subject pixel-diff = 0 vs the pre-04 baseline (mask-based), camera trajectory unchanged, and a frame-to-frame no-flicker check on the new ember + bloom output.
- **ADJ-4 — Rebalance bokeh/vignette to subordinate (acceptance #5).** The plan makes embers visible but does not dial back bokeh/vignette. After embers are visible, confirm embers are the **dominant** visible particle effect and bokeh/vignette are subordinate (ADR-006 "must not overpower the subject"). If embers still don't dominate, reduce bokeh opacity / vignette strength.

Everything else in CC's plan stands as written.

---

## Root causes (from CC, confirmed)

**Defect 1 — black ember overlay (`generate_overlays.py`):** `emitter.hide_render=True` suppresses the particle modifier in 5.1 EEVEE; `HALO` render type removed in 5.1; `particle_size=0.04` is sub-0.1% frame coverage; no glow.

**Defect 2 — filter-like composite (`ffmpeg_service.py`):** `blend=all_mode=screen` ignores alpha (opacity sliders are dead code); `colorchannelmixer=rr=1.0` clips red to white at ember centers; default `#FF8C2E` spectrally overlaps skin tones; `derive_ember_color()` never wired.

---

## Implementation

**Phase 1 — Fix ember generation (`blender/scripts/generate_overlays.py`)**
- 1a. `emitter.hide_render=False`; transparent material (alpha=0, BLEND) on emitter mesh; ember material on the particle instance object.
- 1b. Replace `render_type="HALO"` with `OBJECT`: UV sphere (radius=0.005, segments=8) as `instance_object`, orange emissive material on it, hide the instance object itself from render.
- 1c. `particle_size` 0.04 → 0.25.
- 1d. **Glow — per ADJ-2:** verify the 5.1 EEVEE-Next mechanism (compositor Glare node, not `eevee.use_bloom`); guard the call so a missing API cannot crash generation; visibility must not depend on it.
- 1e. `_validate_non_black()` via FFmpeg `signalstats` YAVG across all frames; raise `RuntimeError` if mean < 8/255.

**Phase 2 — Regenerate overlay MP4s.** Run `blender --background --python blender/scripts/generate_overlays.py`; non-black validation runs inline.

**Phase 3 — Fix FFmpeg compositing (`server/services/ffmpeg_service.py`)**
- 3a. Add `premultiply=inplace=1` to ember AND bokeh chains before `screen` blend (`shortest=1`) so alpha/opacity actually modulate RGB.
- 3b. `validate_overlay_non_black()` static method — checks overlay brightness via `signalstats` before compositing; raises `CineAnchorError(OVERLAY_IS_BLACK)` if mean YAVG < 5.
- 3c. `derive_ember_color()` default return `#FF8C2E` → `#F5A623`. **Per ADJ-1**, the derivation body must: derive subject hue family → force high saturation + luminance → contrast-check vs subject → guarded fallback to `#F5A623`; output must pass the Phase 5b floor.

**Phase 4 — Error code (`server/services/errors.py`).** Add `OVERLAY_IS_BLACK` to `ErrorCode`.

**Phase 5 — Schema (`server/schemas/project.py`)**
- 5a. Default `particles.color` `#FF8C2E` → `#F5A623`.
- 5b. `@field_validator("color")` rejecting luminance < 60/255 (no black/near-black → invisible embers). Applies to derived colors too (ADJ-1).

**Phase 6 — Wire color derivation (`server/routes/render.py`).** Call `derive_ember_color(asset_path, asset_type)` in `_execute_render()`. **Per ADJ-1**, treat the result as a *hue-family-derived, boosted, contrast-checked* color with guarded fallback — NOT a verbatim subject-color override.

**Phase 7 — Real A→B escalation gate.** `validate_overlay_non_black()` returns brightness; store `overlay_mean_brightness` on the task; a black layer after regeneration increments `particle_attempts` and fails with `OVERLAY_IS_BLACK` instead of producing an empty-effect video. (A black layer is a Method-A generation defect to fix in A, not a trigger to jump to B — per ADR-006 update.)

**Phase 8 — Tests.** `test_project_schema.py`: default color assertion + dim-color rejection. `test_ffmpeg_service.py`: `compose_mp4_with_effects()` asserts `premultiply=inplace=1` present, particles-disabled path, non-black validation. `test_golden_path.py`: particles-enabled golden path.

---

## Verification (with ADJ-3 / ADJ-4 added)

1. `py_compile` all modified files.
2. `unittest tests/backend/test_project_schema.py -v`.
3. `unittest tests/backend/test_ffmpeg_service.py -v`.
4. `unittest discover -s tests` — full suite.
5. Run `generate_overlays.py` → `embers_default.mp4` is **visibly non-black** (acceptance #1).
6. Run `compose_mp4_with_effects()` → embers appear as **discrete spark-like points**, brighter than subject, not a wash (acceptance #3/#4).
7. **(ADJ-3)** Subject pixel-diff = 0 vs pre-04 baseline (mask-based); camera trajectory unchanged; frame-to-frame no-flicker check (acceptance #6).
8. **(ADJ-4)** Confirm embers dominate; bokeh/vignette subordinate (acceptance #5).
9. Reverse-test the guard: feed a deliberately black layer → generation/compositing FAILS with the new error (acceptance #2).
10. Output BOTH the standalone ember layer and the final composite file paths for 启鸣's human acceptance (acceptance #8).

---

## Acceptance mapping (to `04-*-requirements.md` §四)

| # | Criterion | Covered by |
|---|-----------|-----------|
| 1 | Ember layer visible | Phase 1 + Verify 5 |
| 2 | Non-black auto-guard | Phase 1e + 3b + 4 + Verify 9 |
| 3 | Embers pop in final | Phase 3a + Verify 6 |
| 4 | Color consistent but not washed | Phase 3c + 5 + ADJ-1 + Verify 6 |
| 5 | Not overpowering | ADJ-4 + Verify 8 |
| 6 | 03 standards not regressed | ADJ-3 + Verify 7 |
| 7 | End-to-end real run | Phase 2 + Verify 5/6 |
| 8 | Local dual output | Verify 10 |
