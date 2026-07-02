# ADR-008: Interactive Camera Control — Recording-Take Model, Dense→Sparse Fitting, Same-Source Interpolation, and the Golden-Pose Oracle

Date: 2026-07-02

Status: Accepted

Relates to: `ADR-005` (four hard criteria + route ranking), `ADR-004`/`ADR-006` (render-backend / JSON-single-truth integrity). Extends the loop-07 trajectory engine (`camera_math.py` Catmull-Rom + SLERP) into a hand-driven authoring surface.

## Context

Loop 07 shipped a trajectory engine — the system could *compute* camera paths from presets/keyframes. But the user could not *hand-fly* a shot; there was no surface where a human摆 (poses by hand) equals what renders. That surface is the product moat (competitive analysis T2 — precise camera input): a browser fly-cam whose live preview is render-faithful, plus a way to turn continuous flight into a small keyframe set the loop-07 engine reproduces exactly.

Two design forks had to be resolved, and one hard failure had to be diagnosed. This ADR records both.

## Decision

Four coupled decisions define the interactive camera architecture:

**1. Recording-take model with hard cuts.** Authoring is a recording session: left-click = record, right-click = pause/resume. Interpolation is **segment-internal only** — a keyframe carrying `cut: true` hard-clamps the Catmull-Rom window so no interpolation ever crosses a cut. This mirrors real editing (a video is a sequence of shots), and prevents nonsensical smoothing across scene changes. Keyframes without `cut` remain backward-compatible.

**2. Dense-sample → sparse-keyframe fitter (RDP + quaternion angle filter).** Live flight is captured densely, then simplified: Ramer-Douglas-Peucker on position, a quaternion-angle filter on rotation → a small keyframe set. The JSON stays the single source of truth and the render backend is untouched; the fitter produces exactly the `CameraSpec.keyframes` the existing engine already knows how to render.

**3. Same-source interpolation (JS ≡ Python).** The browser preview and the Blender render MUST interpolate identically, so `camera_math` is ported to pure-JS (`camera_math.js`) and cross-checked against `camera_math.py` frame-by-frame (29 parity tests, position ≤1e-4, quaternion angle ≤1e-3 rad). The preview is not an approximation of the render — it *is* the render's math, running in the browser.

**4. The golden-pose oracle as a permanent regression.** Math-parity green proves the two ends interpolate *identically*; it does **not** prove the Three.js (Y-up) → Blender (Z-up) coordinate transform is *correct* — both ends can be **identically wrong** (coordinate handedness). A hand-computed **golden-pose oracle** (6 axis-aligned poses with ground-truth Blender quaternions) anchors correctness and MUST remain in `tests/parity/`.

## Evidence (why decision 4 is not optional)

Gate 4 (visual parity, the make-or-break) was blocked by exactly the handedness risk the oracle was built to catch — the model was in-frame but camera orientation was wrong, while all 29 math-parity tests were green. The oracle localized 2 exact bugs:

1. `camera_presets.py::_quat_from_look` — matrix-trace sign error: used `R00 + R11 − R22` where quaternion extraction requires `+ R22`.
2. `render_project.py::_adapt_user_keyframes` — forced the camera to look at scene-center, **discarding the recorded quaternion orientation** (also missing the `scene_center` offset the preset adapter had, and not using the actual camera distance).

After fixing both (commits `02216d6`, `2bc3dec`, `210b7b5`, `4604384`): 154 tests green including the 4→6 oracle cases; 启鸣 human-confirmed preview ≈ render **indistinguishable** (2026-07-02).

## Consequences

- **Positive:** the interactive hand-flown camera is now render-faithful. The moat — browser 60fps flight *feel* + zero-install web demoability — is real, and parity is a **one-time cost now permanently closed by the oracle**, not a recurring tax.
- **Guardrail promoted to a rule:** *"math-parity green ≠ transform correct."* Any future coordinate-space change (new axis convention, a different preview engine) MUST add or extend oracle cases before merge. The oracle is a truth-anchor, not a convenience test.
- **Honest boundary:** the final visual verdict is human "indistinguishable" (ADJ-3 practical pass), backed by a landmark ≤2% check measured on a **clean silhouette / bounding-box** — NOT auto offset-detection on fully-lit noisy Eevee frames (that method proved unreliable and is deliberately not pursued).
- **Deferred (loop 09):** gamepad input; 3D trajectory drag-edit; and a dedicated **spike** on whether to drive the live preview with Blender natively (parity would then be free, but the moat is the browser flight feel — keep Three.js for now; this is a real T2-architecture question, not a mid-loop pivot).
- **Relationship to prior ADRs:** preserves `ADR-005`'s four hard criteria — deterministic, same-source interpolation favors controllability and frame-to-frame consistency; JSON-single-truth + untouched render backend preserve `ADR-004`/`ADR-006` integrity (authoring adds keyframes, it does not regenerate structure).
- **Revert path:** if the recording-take model proves too coarse for fine authoring, the sparse-keyframe JSON it emits is still hand-editable and engine-compatible; nothing about the render path is locked to the interactive surface.

## Acceptance evidence reference

`08-interactive-camera-control-acceptance.md` (repo root) — all 8 criteria met; Gate 4 human-confirmed by 启鸣 2026-07-02. Branch `feature/loop08-interactive-camera` HEAD `4604384`, 154 tests green, oracle in `tests/parity/test_three_to_blender_oracle.py`.
