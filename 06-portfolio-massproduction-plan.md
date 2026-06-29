# 06 — Semi-manual Mass Production + Parameter Decoupling — Plan (Andy-reviewed)

> Author: Claude Code (draft) · Reviewed & finalized by: Andy · Status: APPROVED for execution with adjustments
> Source of truth: `06-portfolio-massproduction-requirements.md` (repo root).
> Review gate: `00-workflow-rules.md` §4 step 5 — Andy vets the plan (启鸣 does not review plans).
> Upstream: `ADR-007` (bounded AI spark enhancement, already accepted). This loop is execution + generality validation; NO new ADR.

---

## Andy review verdict

CC's plan correctly maps the three goals (fill portfolio / validate 2b generality / expose a JSON parameter face). The render-side mechanism is sound: the JSON channel already exists (`blender_service` passes the full ProjectJSON), so the work is wiring `render_project.py`'s hardcoded constants to read-JSON-with-fallback. `render_defaults.py` as a single source of truth (CC's 1.5) is a good idea and is endorsed.

**However, one item must be removed (ADJ-2 — it collides with work already on the Andy branch), and the decoupling scope must be reined in (ADJ-1) to avoid churning a 725-line render script for parameters this loop does not use.** Seven adjustments below; ADJ-1/2/3 are blocking, ADJ-4..7 are quality/handoff fixes. Everything else in CC's plan stands.

- **ADJ-1 (scope discipline — blocking).** CC expands decoupling to model transform + lighting + camera **+ full stage/background (ring radius/emission, glints sub-params, cloth noise) + text font_style**. Trim it. This loop's bases are **glints-off, particle-free, text-free** — so `stage_overrides` (rings/glints/cloth) and `font_style` would render nothing observable yet, while adding regression surface across a 725-line hardcoded script. **In scope: `ModelTransformSpec` (location/rotation/scale), `LightingOverridesSpec`, and CameraSpec wiring.** These are exactly what mass-producing different weapons under different camera moves needs. **Defer** `StageOverridesSpec` and `font_style` wiring to a later loop — the comprehensive parameter face belongs with the eventual frontend, built against a surface *validated by this loop's actual production use*, not guessed now. (This also resolves requirements §七 Q2: scope = transform + lighting + camera.)
- **ADJ-2 (remove WS5 — blocking, file collision + role boundary).** ADR-007 **already exists on the Andy branch**: `docs/adr/ADR-007-bounded-ai-spark-enhancement-seedance.md` (authored by Andy, commit `bc46e29`), and `ADR-006` is already amended to point at it. CC's WS5 ("新建 docs/adr/ADR-007-seedance-spark-enhancement.md") would create a **second, colliding ADR-007** with a different filename and content. ADR authoring is Andy's responsibility (workflow), not CC's. **Delete WS5 entirely.** The generality conclusion from this loop will be appended to the existing ADR-007 **by Andy** after 启鸣's acceptance (requirements §六).
- **ADJ-3 (default-path regression — blocking, the key safety net).** A "hardcode → JSON-with-fallback-default" refactor's #1 failure mode is silent default drift. Before declaring WS1 done: render an existing project (e.g. `character_intro`) with **NO overrides** and assert the output is **pixel-identical (diff = 0)** against a pre-refactor render. `render_defaults.py` single-source (1.5) is endorsed precisely to prevent two-source drift; this regression test proves it worked. Green unittests alone are NOT sufficient (loop 03/04 lesson).
- **ADJ-4 (real diverse weapons + camera verified, not "experimental").** Per 启鸣's note, GLB assets exist at `E:\asset\AK` — **CC self-selects 3 genuinely different weapons** (different shape / volume / main color) and drops the single-`model.glb`-variants fallback. Span **≥2 distinct camera moves** (e.g. dolly-in + orbit), since "different camera moves" is a core generality dimension (requirements §四). The `CameraSpec`→Blender mapping (CC's Risk #2) cannot ship as untested "experimental": it must be **verified visually** to produce correct, visibly distinct moves on the actual bases. Scope the camera wiring to the params the 3 configs actually exercise.
- **ADJ-5 (visual sanity gate per base — 03/04 lesson).** Tests green ≠ deliverable correct (loop 03 shipped a black layer with 58/58 passing). Each of the 3 bases must pass a **visual** check before handoff to 启鸣: subject present & undistorted, **NO text, NO particles, glints off**, correct camera move, format compliant. Do not rely on unittest/smoke alone for the visual deliverable.
- **ADJ-6 (text stays deterministic; not a deliverable this loop).** Bases remain text-free. **Deterministic text re-composite onto Seedance output C is NOT required this loop** — 启鸣 is judging 2b generality (subject / sparks / flicker), not final-with-text. Relaxing `TextSpec.title` to allow empty is endorsed, but keep text-free gated by the explicit `text_overlay=false` flag (don't overload `title=""` as the only signal), and add a test that `text_overlay=false` yields no text regardless of `title`.
- **ADJ-7 (prompt language + structure).** English is the canonical copy-paste prompt for Seedance (per loop-05 plan); Chinese only as annotation for 启鸣. Each prompt keeps the `ADR-007` three-part structure: **state baked-in content to preserve** (subject identity, camera motion, rim light, cloth backdrop, NO sparks, NO text) → **enhance what's already there** (atmosphere/grade) → **add only the genuinely absent** (sparks/embers).

---

## In-scope work (WS1–WS4, WS5 removed)

### WS1 — Parameter decoupling: schema + Blender wiring (trimmed per ADJ-1)

Add optional-override Pydantic models in `server/schemas/project.py` (all optional → fallback to defaults → backward compatible):
- `ModelTransformSpec`: `location (x,y,z)`, `rotation (rx,ry,rz deg)`, `scale (>0, default = auto 2.55/max_dim)`.
- `LightDefSpec` + `LightingOverridesSpec`: per-light override (key / rim_left / rim_right / back / silhouette_rim) — `enabled / location / energy / color / size`.
- `SceneSpec` gains `model_transform` + `lighting_overrides` (NOT `stage_overrides` — deferred, ADJ-1).
- `CameraSpec`: unchanged fields, but **wire it into the render** (currently ignored).
- `TextSpec.title`: relax to allow empty (ADJ-6).

Blender wiring (`blender/scripts/render_project.py`), each as read-JSON-then-fallback:
- model load (`import_glb` / `make_png_plane`): transform overrides (scale override on top of existing auto-scale default).
- `add_lighting()`: per-light override from `lighting_overrides.<name>`.
- camera (`add_dolly_camera` / `add_orbit_camera`): read `camera.speed/start_distance/end_distance/height/focal_length` → derive ortho_scale/position/orbit params (ADJ-4, verify visually).
- **Defer**: `add_stage()` ring/glints, `_add_cloth_texture()`, `add_text_overlay()` font_style.

`render_defaults.py` (new): single source for all in-scope defaults; both schema `Field(default=...)` and the render script `.get(key, DEFAULT)` reference it (ADJ-3).

Files: `server/schemas/project.py` (transform + lighting models, SceneSpec ext, TextSpec.title), `blender/scripts/render_defaults.py` (new, in-scope defaults only), `blender/scripts/render_project.py` (model + lighting + camera functions only), `tests/backend/test_project_schema.py` (valid/invalid cases for the in-scope specs). `blender_service.py` unchanged.

### WS2 — Parameter table (`docs/parameters.md`)

Per in-scope parameter: JSON path · meaning (中文) · range/unit · default (from `render_defaults.py`) · example value. Sections: Model Transform → Lighting → Camera. (Stage/text sections omitted this loop, ADJ-1.) Correct location: `docs/` = CC technical artifacts.

### WS3 — Produce 3 base videos

Format: 1080p (1920×1080), 24fps, 4s (96f), H.264 MP4 (libx264, yuv420p, crf 18, +faststart), text-free, particle-free, glints off.
Assets: 3 different real GLBs from `E:\asset\AK`, ≥2 camera moves (ADJ-4). New `scripts/base_configs.json` (3 differentiated configs) + `scripts/mass_produce_base.py` → `BlenderService.render_project()` → `FFmpegService.compose_mp4()` (no effects path) → `storage/exports/mass_produce/{weapon}/`, print each output path. Each base passes the visual sanity gate (ADJ-5).

### WS4 — Seedance prompts (`docs/seedance_prompts.md`)

One copy-paste English prompt per base (Chinese annotation alongside), three-part structure per ADJ-7 / ADR-007. Self-contained for direct paste into Seedance.

---

## Verification

1. `py_compile` modified files (`project.py`, `render_defaults.py`, `render_project.py`).
2. `unittest discover -s tests\backend` + `tests\smoke` — no regressions (optional overrides default-off preserve old behavior).
3. **Default-path pixel regression (ADJ-3):** render an existing project with no overrides → pixel-diff = 0 vs pre-refactor render.
4. **Controllability (acceptance #2):** change one value (e.g. `lighting_overrides.key.energy`, or a camera param) → re-render → frame changes accordingly.
5. **Per-base visual sanity gate (ADJ-5):** each of 3 bases — subject present/undistorted, NO text, NO particles, glints off, correct camera move, format compliant (1080p/24fps/H.264).
6. Output all file paths for 启鸣 retrieval (acceptance #7).
7. **Seedance generality (acceptance #6, 启鸣 external):** feed each base + prompt → judge subject drift / flicker per clip. Andy appends the conclusion to the existing ADR-007 afterward (ADJ-2).

---

## Acceptance mapping (to `06-*-requirements.md` §五)

| # | Criterion | Covered by |
|---|-----------|-----------|
| 1 | Decoupling complete (pos/dir/rot/light via JSON) | WS1 transform + lighting + camera wiring (scope per ADJ-1) |
| 2 | JSON edits take effect | Verification #4 controllability check |
| 3 | Parameter table complete | WS2 `docs/parameters.md` |
| 4 | 3 bases, text/particle-free, format-compliant, paths output | WS3 + ADJ-5 visual gate + Verification #5 |
| 5 | Each base has a compliant prompt | WS4 + ADJ-7 structure |
| 6 | **2b generality (core)** | WS3 diverse assets (ADJ-4) + WS4 prompts → 启鸣 external per-clip judgement |
| 7 | All file paths output | Verification #6 |

Plus a non-functional guard not in the requirements table but mandated by review: **default-path pixel regression (ADJ-3)** — the refactor must not change default output.

---

## Note on outcome (requirements §六)

No new ADR this loop. After 启鸣's per-clip acceptance, **Andy** appends a dated update to the existing `ADR-007`:
- Generality holds across diverse assets → confirm 2b is generalizable (paves the way for later engineering / frontend).
- Some assets flicker / drift → record as a known limitation (which asset classes fail, fallback strategy); ADR-007 body still stands.
