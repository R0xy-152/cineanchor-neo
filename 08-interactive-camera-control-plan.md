# 08 — Interactive Camera Control — Plan

> Author: Andy (product/architecture brain) · Approver/Merger: 启鸣 · Executor: CC (local)
> Language: English (tech doc). Upstream: `08-interactive-camera-control-requirements.md` (locked 2026-06-29) / `07-camera-trajectory-engine-{plan,acceptance}.md`.
> Status: **Andy implementation plan for CC to execute. CC: flag any item that fights the real codebase before coding — do not silently deviate.**

## 0. Verdict / framing

Loop 07 shipped the offline engine (`camera_math.py` Catmull-Rom + SLERP, pure-python, 8 presets). Loop 08 puts a **browser hand on it**: a Three.js viewport where 启鸣 flies the camera (keyboard+mouse), **records a take** (left=record / right=pause, hard cuts allowed), and the recording is **fitted down to sparse `CameraSpec` keyframes** that the *existing* Blender path renders. JSON stays the single source of truth; render backend is **untouched**.

The make-or-break is **parity**: what the browser shows ≈ what Blender renders. Everything else is plumbing around that.

## 1. Architecture (reuse vs new)

```
Three.js viewport (PERSP preview)
  ── input controller (WASD/Space/Ctrl/Shift/mouse-look/scroll, L=rec R=pause)
  ── recorder: dense per-frame pose samples, segmented by hard cuts
  ── fitter: dense samples ─▶ sparse CameraSpec keyframes (per shot)  ◀── tolerance
        │
        ▼  serialize
  CameraSpec JSON  (07 schema: keyframes + preset; +shot/cut boundary)   ← SINGLE TRUTH
        │
        ▼  unchanged
  FastAPI ─▶ render_project.py ─▶ Blender Eevee ─▶ FFmpeg ─▶ MP4
```

- **Reuse:** `camera_math.py` interpolation semantics, `three_to_blender_pose()` coordinate bridge, `CameraSpec` schema, `add_keyframed_camera` render path.
- **New (frontend):** `web/src/camera_math.js` (port), `web/src/viewport.js` (Three.js), `web/src/input_controller.js`, `web/src/recorder.js`, `web/src/fitter.js`, serialize-to-CameraSpec glue.
- **New (backend, minimal):** an endpoint to persist a recorded `CameraSpec` into a project JSON (reuse existing project IO if present — do NOT invent a parallel store).

## 2. Phases

### Phase 1 — Port interpolation to JS + cross-check (foundation, de-risks parity #1)
- Port `camera_math.py` → `web/src/camera_math.js`: `catmullRom`, `slerp`, `interpolateKeyframes`, `threeToBlenderPose`, `targetFromQuat`. Pure functions, no Three.js/DOM dependency.
- **Parity unit test (the gate for this phase):** feed identical keyframe inputs to JS and python; compare interpolated poses value-by-value across a dense t-grid. Tolerance: position/quaternion components within float epsilon (≥ ~1e-6 agreement). This is the contract that makes "preview == render" possible.
- Deliver a small fixture set shared by both test suites so drift is caught mechanically.

### Phase 2 — Three.js viewport, PERSP only
- Load the **same asset** the renderer uses (GLB; PNG-plane fallback) and the same lighting intent enough to judge framing (framing parity is what matters, not full shading match).
- Single PERSP camera; FOV/lens mapping must match Blender's `camera.data.lens` ↔ FOV exactly (this is a known parity trap — derive from sensor width + focal, same formula both ends).
- Render current pose live. Show an aspect-correct frame guide matching render output dimensions.

### Phase 3 — Input controller (locked mapping)
- Pointer-lock for mouse-look (capture on left-click-into-viewport / a click-to-focus affordance — reconcile with "left = record"; see Risk R4).
- Mapping: `W/A/S/D`=translate fwd/left/back/right (camera-local), `Space`=up, `Ctrl`=down, `Shift` held = scale **translation** speed down only (mouse-look sensitivity unchanged), mouse move = yaw/pitch, wheel = dolly (forward axis).
- Frame-rate-independent movement (delta-time scaled) so recording is smooth regardless of client FPS.

### Phase 4 — Recorder + fitter + serialize
- **Recorder:** left-click starts; sample pose at the project's target fps; right-click pauses. Re-record (left again after pause) starts a **new shot** at current pose → records a **hard cut** boundary (no interpolation across it).
- **Fitter:** dense samples → sparse keyframes per shot, within a position/orientation tolerance (decimation or curve-fit). Goal: minimal keyframes that the 07 engine re-interpolates back to the recorded path within tolerance. Keep JSON sparse/diffable (moat T3).
- **Hard-cut representation:** segment the keyframe list into shots; mark shot boundaries so `interpolateKeyframes` (both JS preview and python render) never blends across a cut. CC: pick the minimal schema addition (e.g. a `cut: true` flag on the boundary keyframe or a `shots[]` grouping) and document it in `docs/project_json_schema.md`.
- **Serialize:** write into `CameraSpec` (07 schema). JSON round-trip must be lossless (req §四.2).

### Phase 5 — Parity gate + carry-forward closure (the acceptance core)
- **Parity gate:** take one recorded JSON, render it in Blender, and capture the matching preview frames; quantify landmark error (subject bounding box / frame center). Pass = human-indistinguishable (practical pass, ADJ-3 spirit) AND landmark error ≤ 2% of frame dimension (quantified backstop, no overclaim).
- **Carry-forward (loop 07):** render a PERSP preset/recording **with a non-empty `title`**; confirm text positioning under PERSP (FOV→view_height) is correct — not offset, not overflowing. Closes the loop-07 carry-forward.

### Phase 6 — Regression
- Default path (project with NO interactive/recorded keyframes) renders **bit-identical** to the loop-07 baseline (reuse ADJ-2 pixel-diff harness on dolly_in + orbit). Interactive feature must not perturb the existing path.

## 3. Guardrails (must hold; violation = stop and flag)
- **G1** `camera_math.js` is pure math — no Three.js/DOM imports — so it can be unit-tested headless and stays a faithful port.
- **G2** JSON (`CameraSpec`) remains the single source of truth. No parallel trajectory store; dense samples are transient and discarded after fitting.
- **G3** Render backend (`render_project.py` interpolation/render) is **not** modified except the minimal cut-boundary read; default path stays bit-identical.
- **G4** Interpolation stays **same-source**: any change to fit/interp logic updates both JS and python and re-runs the Phase-1 cross-check.
- **G5** No frame-by-frame, no generative AI in the control/render path (ADR-004/005/006/007). Recording produces keyframes; Blender renders deterministically.
- **G6** Preview = PERSP only; ORTHO remains the render default with its no-distortion guarantee (ADR-006 2026-06-29 update). Do not touch ORTHO.

## 4. Risks
- **R1 — FOV/lens parity (highest).** Browser FOV vs Blender focal/sensor must use the identical formula and aspect handling, or framing diverges. Mitigation: derive both from the same sensor+focal inputs; assert in Phase-1/Phase-5 tests.
- **R2 — Coordinate handedness.** Three.js (Y-up, right-handed) vs Blender (Z-up). `three_to_blender_pose` exists from loop 07 — reuse it; add a reverse if the preview needs Blender→Three. Cross-check in Phase 1.
- **R3 — Fit tolerance vs fidelity.** Too-aggressive decimation flattens the hand-recorded feel; too-loose bloats JSON. Make tolerance a tunable; Phase-5 parity judges the recorded-vs-reinterpolated error.
- **R4 — Mouse-button overload.** Left-click is both "record" and the usual pointer-lock trigger; right-click "pause" collides with the browser context menu. Mitigation: suppress context menu in viewport; define an explicit click-to-focus/lock affordance distinct from the record action. CC to settle UX in Phase 3.
- **R5 — Hard-cut schema.** Cut representation must be understood identically by JS preview and python render. Single source: document the chosen flag/grouping in `docs/project_json_schema.md`, test both readers.

## 5. Acceptance mapping (requirements §五)
1 viewport live → Phase 2 · 2 input mapping usable → Phase 3 (启鸣 hands-on) · 3 record/pause/scrub + fit-reinterp within tol + same-source → Phase 1+4 (unit cross-check + fit-error test) · **4 parity (core)** → Phase 5 visual gate · 5 JSON round-trip + Blender renders interactive keyframes → Phase 4+5 · 6 default path zero-regression → Phase 6 (ADJ-2) · 7 PERSP+title text → Phase 5 · 8 local artifacts + file list → CC report.

Visual gates are mandatory (loop 03/04/07 lesson: green unit tests ≠ visually correct). Final video acceptance = 启鸣.

## 6. Files (expected; CC adjust to real layout)
- New: `web/src/camera_math.js`, `web/src/viewport.js`, `web/src/input_controller.js`, `web/src/recorder.js`, `web/src/fitter.js`; `tests/frontend/test_camera_math_parity.*` (JS↔python cross-check), `tests/frontend/test_fitter.*`.
- Changed (minimal): project-save endpoint (reuse existing), `render_project.py` cut-boundary read only, `docs/project_json_schema.md` (cut/shot field), `docs/parameters.md` (input mapping reference).
- Gate artifacts: `storage/visual_gate/loop08_*` (parity pairs, PERSP+title render, regression pixel-diff).
