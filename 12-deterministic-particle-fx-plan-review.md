# 12 — Deterministic Particle/FX — Andy Plan-Review (of codex's plan)

> Gate: Andy vets plans (启鸣 only reviews requirements). Base: `12-deterministic-particle-fx-requirements.md`, ADR-006/008/010, four hard criteria.
> **Verdict: ENDORSE — strong plan, proceed to execute AFTER the P0 fixes below.** Language: English.

## Why endorse (lock these in — do NOT regress)

- **Closed-form per-frame position, no global `random`, no prev-frame state, no Blender particle cache** → determinism by construction. This is exactly right and directly fixes loop 11's "seed not actually in sim" failure. Keep.
- **Quantitative acceptance gates** (coverage 0.2–4% / 0.4–8%, P95 brightness ≥12/≥18, hue within 30° of preset + ≥20° shift on theme swap, centroid-displacement motion proof, ≥50% end-alpha decay) → this operationalizes "visible" and "not cheap" and "theme-driven" into MEASURABLE bars. This is the correct response to loop 11's "technically present but invisible". Excellent — keep all of it.
- **fx_manifest.json** (version + seed + presets + asset checksums) → versioned, auditable artifact. Keep — this also pre-figures the ADR-010 artifact-versioning pattern if we ever activate it.
- **Fail-loud** (missing FX asset → `FFMPEG_COMPOSE_FAILED` / `deterministic_fx`, no silent skip) → keep.
- **Exit condition honored exactly** (§4: if all deterministic methods done and still below human bar → stop patching, record failure samples+metrics, submit ADR-010 activation, never self-add AI) → this matches requirements §五 precisely. Keep.
- **Golden-pose oracle + legacy pixel regression retained** (ADR-008 guardrail) → keep.
- **No schema churn** (reuse `style.particle_preset`/`primary_color`, `weapon_style.element_theme`/`theme_color`; template-FX priority over legacy `scene.particles`; old templates unchanged) → keep.
- Scoping OUT loop 11's camera/framing/text defects → correct decoupling.

## P0 — must fix before execute

1. **ADR-006 edit is a governance violation.** §4 says "更新 ADR-006 的实现状态". **ADRs are Andy-only (CC must not author/edit ADRs).** Put the implementation-status note in the **loop 12 execution doc** instead, and hand the ADR-006 amendment to Andy. Do not touch `docs/adr/`.

2. **2D FX must anchor to the projected 3D emitter, not screen-space.** The plan applies FX as a 2D pass over composited PNG frames *before* FFmpeg — for the **orbiting** weapon this is the single biggest visual risk. If particles emit at fixed screen coordinates, they will float in a static region while the gun rotates → reads as "pasted on / wrong". **Requirement:** for the weapon path the FX service MUST receive, per frame, the **projected 2D position (and ideally depth) of the 3D muzzle/emitter** from the Blender render, and anchor emission there so sparks track the weapon across the orbit. Confirm this data path exists before building. (Birthday is a 2D poster → static anchor is fine there.)

## P1 — must add to the visual gate / confirm

3. **"Pasted-on" test is now a first-class gate item.** The plan bets the whole architecture on 2D-composited-over-3D. That bet must be *gated, not assumed*: the weapon visual gate must explicitly confirm the FX layer reads as **integrated with the orbiting 3D weapon** (plausible depth/anchoring, additive embers sit believably), not a flat overlay. Add this as an explicit checkbox alongside "visible / not cheap / stage feel".

4. **Re-validate the quantitative thresholds at RELEASE resolution.** "Auto tests low-res for speed; visual gate 1080×1920" is a loop-11 trap in waiting: coverage-%, sprite pixel size, and additive brightness do NOT scale linearly with resolution — low-res green can become 1080p sparse/invisible. **Either prove the metric gates are resolution-invariant, or re-run the coverage/brightness gates at 1080p** before human sign-off. Green at 320p ≠ visible at 1080p.

5. **Uncommitted `render_project.py` provenance.** §1 imports the loop 11 rework as an **uncommitted** baseline. Untracked = irreproducible baseline. **Commit it (as the read-only loop-11 source and/or into the "pre-Loop 12 baseline" commit) before building on it**, so the baseline is fully reproducible and the change report has a real diff anchor.

## P2 — note (not blocking)

6. **Weapon "阶段感" judgment may be confounded by unfixed loop 11 orbit/framing (D1/D2/D4).** Particle visibility/quality/theme metrics are judgeable independently, but whole-video "stage feel" for the weapon reads cleaner if loop 11's orbit/framing/text rework lands first or in parallel. Not a blocker; sequence-aware — if the weapon sample still looks like "test render" for non-particle reasons, judge particles on the metric matrix + contact sheet, not the whole-video impression.

7. **Loop 12 does NOT satisfy loop 10's real-subject visual gate.** Loop 10 closeout (a) (rerun text-positioning on ≥4 real diverse subjects, not primitives) is separate and still open — loop 12 is particles only.

## Next
CC applies P0 #1–2 + confirms the muzzle-projection data path → executes TDD → runs auto gates + the hard human visual gate (with P1 #3–4 added) → submits samples + reports. If the deterministic bar is still missed after everything, that is the ADR-010 activation trigger (Andy/启鸣 joint), not a CC decision.
