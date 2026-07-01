# CineAnchor Neo Agent Guide

## Project Stage

CineAnchor Neo is currently in **V0.1 — Loop 06 Complete**.

Spike validation (Routes 0–4) is finished: Routes 0/1/2/4 PASS, Route 3 PARTIAL.
Loop 06 (parameter decoupling + semi-manual mass production) is complete:
model transform, lighting overrides, camera params, and stage toggles are now
configurable via Project JSON. 3 base videos with Seedance prompts ready for 2b
generality validation. 72 tests pass (59 backend + 13 smoke).

Do not build the full product architecture before the Spike conclusions are recorded.

## Product Positioning

CineAnchor helps mobile game and indie game operators generate 8-15 second promotional videos from either:

- one transparent PNG character image, or
- one GLB model,
- plus title copy and optional BGM.

The MVP target output is a 1080p MP4 that looks like a game promotion clip, not a PPT-style screenshot.

## Non-Goals Before V1.0

Do not implement:

- cloud rendering or SaaS deployment
- account system
- multiplayer collaboration
- template marketplace
- ecommerce batch generation
- Unreal Engine backend
- frame-by-frame AI video redraw
- perfect WYSIWYG preview parity between Three.js and Blender
- Celery + Redis queue

## Branch Strategy

| Branch | Rule |
|---|---|
| main | Stable only. No direct pushes. |
| develop | Integration branch after Spike. |
| spike/* | Spike validation branches. Disposable. Do not merge temporary code into main. |
| feature/* | Product feature branches after Spike. |
| docs/* | Documentation and portfolio material. |

During Spike, use `spike/render-pipeline`, `spike/png-25d`, `spike/json-template`, `spike/comfyui`, and `spike/web-local-render` style branches.

## Spike Rules

Spike allows:

- one-off scripts
- temporary code
- minimal tests or smoke checks
- direct local scripts
- hardcoded sample paths inside Spike-only folders when needed
- minimal dependency use

Spike forbids:

- merging temporary code into main
- designing the full product architecture early
- adding large dependencies without recording why
- implementing beyond the validation target
- treating Spike success as production readiness
- locking API contracts, database schema, or Project JSON schema before validation

## Required Spike Evidence

Every Spike route must record results in `spike_results.md`.

Each entry must include:

- goal question
- commands run
- input asset used
- output artifact path
- render duration
- machine / GPU notes when relevant
- pass / fail result
- blocking errors
- next decision

## Validation Routes

### Route 0: 3D Render Loop

Question: Can Blender import a GLB, animate an orbit camera, render frames, and export MP4 through FFmpeg?

Pass criteria:

- Blender headless runs without errors
- 192 frames are generated for 8 seconds at 24 fps
- no black frames
- FFmpeg creates playable MP4
- total render time is recorded
- if render time exceeds 10 minutes, rerun with Eevee

Kill criterion:

- If an 8-second video cannot be produced within 15 minutes, reassess Blender as the rendering backend.

### Route 1: PNG 2.5D Video

Question: Can a transparent PNG become a promotional-looking video instead of a static PPT-like clip?

Pass criteria:

- PNG alpha channel renders correctly
- character stays in frame during camera motion
- output MP4 is playable
- 2 out of 3 non-developers agree it looks closer to a promotional clip than a PPT screenshot

Kill criterion:

- If the subject is severely distorted or visually unusable, reassess support for image-only users.

### Route 2: JSON-Driven Template Rendering

Question: Can one JSON file drive template, asset path, camera motion, duration, fps, aspect ratio, title, and subtitle?

Current V0.1 Project JSON schema (see `server/schemas/project.py` for full definition):

```json
{
  "version": "0.1",
  "project_id": "demo",
  "template": "character_intro",
  "output": {"duration": 8, "fps": 24, "aspect_ratio": "9:16", "resolution": "1080p"},
  "assets": [{"id": "main_subject", "type": "image", "path": "storage/assets/hero.png"}],
  "camera": {"motion": "dolly_in", "speed": 1.0, "start_distance": 7.2, "end_distance": 5.8, "height": 0.25, "focal_length": 1.0},
  "scene": {"background": "dark_stage", "lighting": "rim_back", "particles": null, "fog": false},
  "text": {"title": "New Hero", "subtitle": "Limited Event", "font_style": "bold_game"}
}
```

Optional fields (loop 06): `scene.model_transform`, `scene.lighting_overrides`,
`scene.background_enhance` (rim_light, cloth_texture, glints, text_overlay, stage_ring).

Pass criteria:

- changing `asset_path` switches input without code changes
- changing `camera.motion` / `camera.height` / `camera.start_distance` changes camera behavior
- changing `aspect_ratio` changes output dimensions
- two template names are supported: `character_intro`, `product_orbit`

### Route 3: ComfyUI AI Enhancement

Question: Can ComfyUI improve Blender output without subject deformation or flicker?

MVP strategy:

- enhance keyframes only
- apply color / contrast / sharpening style to full video through FFmpeg
- do not use frame-by-frame AI redraw

Pass criteria:

- Python script calls ComfyUI API through `POST /prompt`
- enhanced output is visibly better in side-by-side review
- subject is not deformed
- no obvious flicker
- per-frame ComfyUI time is recorded
- GPU memory conflict with Blender is recorded

### Route 4: Web To Local Render Chain

Question: Can a minimal web UI call FastAPI, trigger Blender, and return MP4?

Pass criteria:

- upload saves asset into local storage
- backend generates Project JSON
- backend calls Blender headless
- status can move from pending to rendering to done
- frontend can poll status
- final MP4 download link works

## Merge Rules After Spike

A branch must not be merged if:

- it changes files outside the assigned scope
- it modifies API behavior without documentation
- it modifies Project JSON structure without documentation
- tests or smoke checks were not run
- it deletes existing tests
- it introduces unexplained dependencies
- it hardcodes production absolute paths
- it breaks the golden path after V0.1 exists

## Change Report Format

Every completed task must report:

```md
Changed:

files_modified:
- path/to/file

behavior_changed:
- summary

api_changed: yes/no
schema_changed: yes/no

tests_added:
- path/to/test

commands_run:
- command and result

known_risks:
- risk summary
```

## Loop 08 Change Report (CC — 2026-07-01)

```md
Changed:

files_modified:
- apps/web/src/camera_math.js (hard-cut boundary support: k0/k3 clamped at cut KFs)
- blender/scripts/camera_math.py (hard-cut boundary support: same logic, parity with JS)
- apps/web/src/viewport.js (refactored: extracted input/recorder/fitter to sub-modules)
- docs/project_json_schema.md (cut field + Camera Keyframes + Hard-Cut Semantics sections)
- AGENTS.md (this report)
- .claude/CLAUDE.md (loop-08 status + CC rules update)

files_created:
- apps/web/src/input_controller.js (keyboard/mouse flight, speed HUD — THREE injected)
- apps/web/src/recorder.js (recording state machine, pure JS, testable without browser)
- apps/web/src/fitter.js (RDP + angle filter, pure JS, dense→sparse keyframes)
- tests/frontend/test_fitter.py (8 tests: RDP, angle filter, cut boundaries, serialization)
- tests/frontend/test_recorder.py (12 tests: state machine, sample capture, module structure)
- scripts/visual_gate_loop08.py (Blender + FFmpeg parity verification script)

files_not_touched (per G3 guardrail):
- blender/scripts/render_project.py (no changes — already supported keyframes/shots)
- server/services/blender_service.py (no changes)
- server/routes/render.py (no changes)
- server/schemas/project.py (no changes — keyframes/shots already in schema)

behavior_changed:
- interpolateKeyframes (JS+Python): cut:true keyframes prevent Catmull-Rom window
  from crossing shot boundaries. Backward-compatible: KFs without cut behave same.
- viewport.js: recording now delegates to recorder.js + fitter.js modules
- fitter: placeholder Nth-sample replaced with RDP + angle filter

api_changed: no
schema_changed: no (CameraSpec.keyframes/shots already existed; new cut field is optional bool)

tests_added:
- tests/frontend/test_fitter.py (8 tests)
- tests/frontend/test_recorder.py (12 tests)
- tests/parity/test_camera_math_parity.py HardCutTests (5 tests)
- tests/backend/test_project_schema.py (3 tests: keyframes/shots/cut schema)
- tests/smoke/test_golden_path.py (2 tests: render with keyframes, render with shots)

commands_run:
- python -m unittest discover -s tests: 150 tests, OK
- All parity tests pass (JS↔Python cross-check including cut boundaries)

known_risks:
- R4 (mouse-button overload): recording uses keyboard L/R, not mouse left/right.
  Per Andy plan: CC settled on keeping keyboard L/R (decision A1).
- Visual parity gate (Task 5): script ready, actual visual inspection pending 启鸣 review.
  Human must compare Three.js preview vs Blender render screenshots.
```
