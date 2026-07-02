# 11 — Weapon Skin Showcase — Review & Rework Checklist (for CC)

> Author: Andy (plan-review of CC's loop 11 first render). Base: `11-weapon-skin-showcase-template-plan.md` + `ADR-009` + 启鸣's visual verdict 2026-07-02.
> Verdict: **NOT accepted — rework required.** The output reads as "model test render", not "skin promo". Root cause is deterministic execution not landing, NOT a deterministic-method ceiling. Do not introduce AI into the auto path to paper over these bugs.
> Language: English. Status: actionable rework list; re-run the visual gate before re-submitting.

---

## 0. Framing — read this first

The five defects below are **execution bugs in the deterministic path** (framing, camera-preset wiring, material/light override, particle method, text layout). None of them proves "确定性粒子上限太低". The first-version sparks being "太廉价太假" is a **method-quality problem, fixable within ADR-006 determinism** — not a hard ceiling. AI stays out of the auto template pipeline (V0.2 §4.2, ADR-007 keeps AI spark manual/optional/off-path). Fix the determinism first; re-judge only after.

## 1. Defect triage (all P0/P1 — blocking sign-off)

| # | Symptom (启鸣) | Root-cause class | Priority |
|---|---|---|---|
| D1 | Weapon too small; frame mostly pure black;枪在中上部; reads as "model test render" | **Framing / composition params** — camera distance, weapon scale + centering, stage/background not built | P0 |
| D2 | Orbit 没成立 — weapon stays side-profile, only grows (static side + slow dolly/scale-in) | **Camera preset/keyframe not executing orbit** — the loop 07-09 engine can orbit; it degraded to dolly → the `weapon_skin_showcase` dispatch is not wiring the orbit preset | P0 |
| D3 | Fire element基本没出现; theme color 没覆盖氛围 (still AK-47 Vulcan's own blue/white skin) | **Particle not triggered + material/light override not applied** — `theme_color` must drive key light + particle base color; `element_theme=fire` must emit | P0 |
| D4 | Text mispositioned / cropped out of frame; VULCAN / AVAILABLE NOW too low & clipped; **AK-47 / Legendary / Factory New not shown** | **Text-positioning visual-gate failure (the预判 long pole #4) + missing schema fields** (weapon_name / rarity / series not rendered) | P0 |
| D5 | No "宣传片阶段感" | **7-段 structure not landing** — aggregate of D1–D4 | P1 (falls out once D1–D4 fixed) |

## 2. Rework items

### RW-1 (D1) — Framing & stage
- Reframe so the weapon fills a promo-appropriate portion of the 9:16 frame (target: weapon长边占画面 ~55–70%, centered or rule-of-thirds — NOT中上部floating in black).
- Build a **stage**, not empty black: floor/gradient/vignette + theme-color ambient so it reads as a lit set, not a void. Deterministic (ADR-006 background methods).
- Verify framing holds for **both** GLB (real mesh bbox) and PNG-2.5D (plane bounds) — auto-fit camera distance to asset bbox, don't hardcode.

### RW-2 (D2) — Orbit camera must actually orbit
- The `side_showcase`/orbit段 must execute a **real orbit** (azimuth sweep around the weapon), reusing `camera_presets` orbit — not a dolly/scale substitute.
- This template is the first to exercise the camera engine (moat). **Any coordinate-space change MUST extend the golden-pose oracle before merge (ADR-008 permanent guardrail).** Confirm the orbit preset produces the expected transform via the oracle, not just "looks like it moves".
- Deliverable proof: a mid-orbit frame showing a clearly different azimuth than the opening frame.

### RW-3 (D3) — theme_color + element_theme must drive the frame
- `theme_color` drives **key light color + particle base color + stage ambient** — the frame's dominant mood must shift with it, not stay the asset's native skin palette.
- `element_theme=fire` must actually emit the fire particle system in `element_burst` (7–9s). Confirm each of the 6 element presets emits.
- Acceptance proof: two renders with different `theme_color` produce visibly different ambient/lighting.

### RW-4 (D3, particle method) — upgrade the deterministic particle, do NOT delete or AI it
The first version's sparks were "太廉价太假" → **improve the method, still deterministic (ADR-006), still seeded by project_id.** Concrete upgrades:
- Real spark/ember **sprite texture**, not flat dots.
- **Additive / screen blending** (the cheap look comes mostly from plain alpha compositing).
- **Motion**: velocity + lifetime decay + upward heat drift + trail — not static blinking.
- **Color-link** to `theme_color` / `element_theme` (fire=warm ember, ice=cold shard, etc.).
- Pair with `light_sweep` glow/heat-haze for local atmosphere.
- Two renders must stay **pixel-identical** (WI determinism preserved).
> If, after these upgrades, the fire still lacks atmosphere, that is the ONLY point that might touch a real ceiling — flag it back to Andy/启鸣 then. Do NOT reach for AI before this.

### RW-5 (D4) — Text-positioning visual gate (the long pole) + missing fields
- Render **all required text**: `weapon_name` (AK-47), `skin_name` (Vulcan), `rarity` (Legendary), `series`/`Factory New`, `cta` (AVAILABLE NOW). Currently rarity/series missing → check schema→render wiring.
- Fix layout: nothing clipped or off-frame; safe-margins respected; long strings auto-shrink/wrap (same discipline as birthday WI-2).
- **Mandatory human visual gate on text positioning** across the diverse-asset set — this is the blocking milestone; green unit tests ≠ visually correct (loop 03/04/07 lesson).

### RW-6 (D5) — Stage feel
- Once D1–D4 land, verify the 7 段 read as a promo arc (dark_ignite → reveal → sweep → showcase → burst → title → cta). Produce a contact sheet at 段 boundaries for the gate.

## 3. Re-submission gate (all must pass)
1. Both-path end-to-end: one **GLB** + one **PNG** asset each export 9:16 12s MP4.
2. Orbit visibly orbits (mid-orbit frame proof) + **golden-pose oracle green**.
3. theme_color + element_theme visibly drive lighting/particles (two-color proof).
4. Upgraded fire particle — deterministic (pixel-diff) + not "廉价".
5. All text present (AK-47/Vulcan/Legendary/Factory New/CTA), nothing cropped — **text visual gate passed**.
6. Legacy + birthday zero-regression.
7. Contact sheet + sample videos (GLB + PNG) for 启鸣 sign-off.

## 4. Explicit non-goal for this rework
- **No AI in the auto path.** AI (ADR-007) stays manual/optional/off-pipeline. If deterministic fire proves insufficient AFTER RW-4, that triggers an Andy/启鸣 decision (candidate ADR-010: bounded offline AI *layer* — local, seeded, versioned, never per-frame regen, never in realtime preview) — NOT a unilateral CC change.
