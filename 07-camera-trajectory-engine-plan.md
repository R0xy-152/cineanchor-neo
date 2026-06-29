# 07 — Camera Trajectory Engine Migration — Plan (Andy-reviewed)

> Author: Claude Code (4-phase draft) · Reviewed & finalized by: Andy · Status: APPROVED for execution with adjustments.
> Source of truth: `07-camera-trajectory-engine-requirements.md` (repo root, approved by 启鸣 2026-06-29).
> Review gate: `00-workflow-rules.md` §4 step 5 — Andy vets the plan (启鸣 only reviews requirements).
> Legacy source: `R0xy-152/CineAnchor` (local `D:\CineAnchor`). NO new ADR this loop.

---

## Andy review verdict

CC's 4-phase plan is sound and — importantly — already honors two of the hard constraints unprompted:
1. `camera_math.py` is **pure python, MUST NOT import bpy** (CC's own Phase-1 note) → the interpolation engine is testable without Blender, and the trajectory stays *our data*, not a Blender-session artifact.
2. **Frame-by-frame generation is NOT migrated** — only the interpolation math + preset data come over. This is exactly the requirements §三 boundary ("搬控制/数据层，不搬生成基质").

The phasing (pure-python lib → preset data → Blender wiring) gives clean safe stops. **Approved with seven adjustments. ADJ-1..3 are blocking; ADJ-4..7 are gates/guardrails.** Everything else in CC's plan stands.

- **ADJ-1 (scope trim — blocking).** CC's Phase 4 proposes a preset dropdown in `apps/web/app.js`. **Remove it.** Requirements defer the user-facing opercontrol layer (keyboard/mouse/gamepad/trajectory-drag) to the **next** loop, and treat the 8 presets as **demo, not a product feature**, this loop. Building a UI now starts the moat-feature prematurely and on the wrong substrate. **Trim Phase 4 to docs-only**: note the optional `preset` field + the 8 preset names in `docs/parameters.md` and `docs/project_json_schema.md`. No `app.js` work.
- **ADJ-2 (default-path pixel-zero regression — blocking, the key safety net).** CC says "existing tests must not break" and the preset path is additive — necessary but NOT sufficient. Before Phase 3 is done: render an existing project on **both** `dolly_in` AND `orbit` with **no preset** → assert **pixel-diff = 0** vs a pre-change render. Green unittests alone are not enough (loop 03/04 lesson; loop 06 ADJ-3). Acceptance #3.
- **ADJ-3 (reproducibility = the moat made measurable — blocking).** CC's plan has no reproducibility test. This is the criterion that turns "precise camera = moat" into something provable: render the **same preset/trajectory twice → identical output**. Acceptance #5 (= competitive-analysis top-3 Camera Reproducibility). Must be an explicit verification step, not implied.
- **ADJ-4 (PERSP no-distortion visual gate).** Phase 3 introduces a PERSP camera (requirements §四 #4 accepts perspective for cinematic feel). Tests green ≠ visually correct (loop 03 shipped a black layer at 58/58). Visually verify a **representative subset (≥3 presets spanning move types** — e.g. `nolan_orbit` orbit / `dolly_reveal` dolly / `drone_ascend` or `god_eye` aerial / `whip_pan` fast-pan): subject present, perspective acceptable, **NO geometric distortion / collapse**. Acceptance #6. (All 8 must still pass unit-level keyframe validity per acceptance #2 — only the *visual* gate is sub-setted, since presets are demo and visual-checking all 8 PERSP renders is disproportionate effort.)
- **ADJ-5 (guardrails — affirm).** `camera_math.py` MUST NOT import bpy (CC's note — endorsed). Frame-by-frame generation MUST NOT be migrated. No Blender/UE5 native-editor embedding, no UE5 (requirements §三). These are non-negotiable boundaries, restated so they cannot drift mid-execution.
- **ADJ-6 (scene_center/radius helper tested on both asset types).** CC's own Risk #2: scene_center/scene_radius computation differs between projects. Make `_compute_scene_center_radius(subject)` a **required, tested** unit on **both** PNG (`character_intro`) and GLB (`product_orbit`) — preset positions are parameterized by scene_radius, so a wrong radius silently throws the camera off-stage.
- **ADJ-7 (default = ORTHO unchanged — affirm CC's additive design).** `preset = null` path stays ORTHO + existing 2-KF Bezier behavior, byte-for-byte. PERSP is created **only** on the preset branch. The preset branch is a new `if`, never a rewrite of `add_dolly_camera` / `add_orbit_camera`.

---

## In-scope work (Phase 1–3 + trimmed Phase 4)

### Phase 1 — Port interpolation engine (pure python, no Blender) — per CC
`blender/scripts/camera_math.py` (new): `catmull_rom`, `slerp` (short-path flip + near-parallel fallback), `interpolate_keyframes`, `three_to_blender_pose`, `target_from_quat`. **No bpy import** (ADJ-5).
Tests `tests/backend/test_camera_math.py`: catmull_rom (identity/linear/curved), slerp (identity/90°/short-path/near-parallel), interpolate_keyframes (2-KF count, 4-KF pass-through, FOV interp), three_to_blender_pose (known + origin), edges (zero-duration, single KF, duplicate KFs).

### Phase 2 — Port preset library (no Blender, JSON-consumable) — per CC
`blender/scripts/camera_presets.py` (new): `_quat_from_look` (Z-up), the 8 presets (nolan_orbit / anime_closeup / dolly_reveal / drone_ascend / hero_tracking / suspense_pan / god_eye / whip_pan), `apply_preset` (uses `camera_math.interpolate_keyframes`), `list_presets`. **Presets = demo/validation material, not a committed product feature** (requirements).
Tests `tests/backend/test_camera_presets.py`: all 8 IDs → valid KF lists (≥3 KF, fields t/pos/quat/fov, position within reasonable range of scene_center), `list_presets()` → 8 entries, unknown preset → KeyError.

### Phase 3 — Wire presets into Blender render — per CC + gates
`blender/scripts/render_project.py`: add `add_keyframed_camera()` (PERSP on preset branch; per-frame location + rotation_quaternion from `interpolate_keyframes`; optional TRACK_TO to subject); add `_compute_scene_center_radius(subject)` helper tested on PNG+GLB (ADJ-6); `build_scene()` gains a preset branch — `if preset in PRESETS: add_keyframed_camera(...)` else existing `orbit`/`dolly` paths **unchanged** (ADJ-7).
`server/schemas/project.py`: `CameraSpec.preset: str | None = None` (optional; when set, overrides motion/distances/height; when null, behavior 100% unchanged).
`blender/scripts/render_defaults.py`: preset-camera defaults if any (most are parameterized in-preset).
**Gates before Phase 3 done**: pixel-zero regression on dolly_in + orbit (ADJ-2); reproducibility same-preset-twice (ADJ-3); PERSP visual no-distortion on representative subset (ADJ-4).

### Phase 4 — Docs only (trimmed, ADJ-1)
`docs/parameters.md`: add the optional `preset` field (JSON path, meaning, the 8 names) under the Camera section. `docs/project_json_schema.md`: add `preset` field. **No `apps/web/app.js` UI** (deferred to the interactive-control loop).

---

## Verification

1. `py_compile` changed files (`camera_math.py`, `camera_presets.py`, `render_project.py`, `render_defaults.py`, `project.py`).
2. `unittest` camera_math + camera_presets — pure python, no Blender env.
3. `unittest test_project_schema` — `preset` optional, default-off preserves old behavior.
4. **Default-path pixel regression (ADJ-2)**: dolly_in + orbit, no preset → pixel-diff = 0 vs pre-change render.
5. **Reproducibility (ADJ-3)**: same preset rendered twice → identical output.
6. **PERSP visual no-distortion gate (ADJ-4)**: representative ≥3-preset subset spanning move types — subject present, acceptable perspective, no geometry collapse.
7. Output all new/changed file paths for 启鸣 retrieval.

Recommended execution order (CC's safe stops, endorsed): **Phase 1 + 2 first** (pure python + tests, no Blender) → review preset names → **Phase 3** (needs Blender, run the three gates) → **Phase 4 docs**.

---

## Acceptance mapping (to `07-*-requirements.md` §五)

| # | Criterion | Covered by |
|---|-----------|-----------|
| 1 | Interp engine ported, pure python (no bpy), unit-covered | Phase 1 + ADJ-5 |
| 2 | 8 presets → valid keyframes; list_presets → 8 | Phase 2 |
| 3 | Default-path zero regression (dolly_in/orbit unchanged) | Verification #4 (ADJ-2) |
| 4 | preset via JSON takes effect; non-preset unchanged | Phase 3 + ADJ-7 + Verification #3 |
| 5 | **Reproducibility (core)**: same trajectory twice → identical | Verification #5 (ADJ-3) |
| 6 | PERSP acceptable perspective, no subject distortion | Verification #6 (ADJ-4) |
| 7 | All file paths output | Verification #7 |

---

## Note on outcome (requirements §六)

No new ADR this loop. If PERSP becomes a common path, **Andy** appends a dated update re ADR-006: "PERSP allowed for cinematic moves; ORTHO remains the no-distortion default." The §三 architecture decision (JSON = source of truth / Blender = render backend / no DCC-UI embedding / no UE5) is recorded in the requirements; revisit for ADR status when the interactive-control layer is productized in a later loop.
