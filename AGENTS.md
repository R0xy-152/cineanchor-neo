# CineAnchor Neo Agent Guide

## Project Stage

CineAnchor Neo is currently in the **Spike validation stage**.

The goal of Spike is to answer whether the technical chain can work, not to build the production application. Spike code may be temporary and disposable.

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

Use this minimal Project JSON only for Spike:

```json
{
  "template": "character_intro",
  "asset_type": "image",
  "asset_path": "input/hero.png",
  "camera_motion": "dolly_in",
  "duration": 8,
  "fps": 24,
  "aspect_ratio": "9:16",
  "title": "New Hero Arrival",
  "subtitle": "Limited Event"
}
```

Pass criteria:

- changing `asset_path` switches input without code changes
- changing `camera_motion` changes camera behavior
- changing `aspect_ratio` changes output dimensions
- three template names can be exercised: `character_intro`, `product_orbit`, `prop_showcase`

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
