# 03 — Particle & Background Enhancement — Plan (Andy-reviewed)

> Author: Claude Code (draft) · Reviewed & finalized by: Andy · Status: APPROVED for execution
> Source of truth: `ADR-006-particles-background-deterministic-compositing.md` + `03-particle-background-requirements.md` (both Accepted on Andy branch).
> Review gate: per `00-workflow-rules.md` §4 step 5, Andy vets the plan after requirements approval (启鸣 does not review plans). This document is the vetted version.

---

## Andy review verdict

CC's draft plan is faithful to ADR-006 (decouple particles into a 2D overlay, AI rejected for both areas, background deterministic enhancement, landing order background→A→B). **Approved with three adjustments**, folded into the steps below:

- **ADJ-1 (vignette/gradient → FFmpeg only).** CC's draft put vignette in BOTH the Blender compositor (Step 1c) and FFmpeg (Step 2c). That double-applies vignette and adds fragile Blender-compositor code (CC's own note flagged it as fragile). Decision: **radial gradient + vignette live in the FFmpeg post step only.** This also serves acceptance #7 — keep as much background tuning in post as possible, no 3D re-render to retune vignette strength. Blender keeps only what *must* be 3D: rim light (1a) and backdrop texture (1b).
- **ADJ-2 (record the A→B escalation gate).** The plan must encode ADR-006's switch criterion so CC escalates instead of over-tuning A: **if within 3 attempts the 2D ember layer cannot reach "ember trail becomes a light streak" realism, stop and switch to Method B** (separate Blender particle pass). Do not silently keep iterating on A.
- **ADJ-3 (asset path naming, minor/non-blocking).** Draft stores ember/bokeh assets under `spikes/ai_layered_multipass_composite/assets/`. The `ai_` name is misleading — these assets are deterministic and ADR-006 explicitly rejects AI here. Prefer a neutral path (e.g. `assets/overlays/`). If reusing the existing spike dir is operationally simpler, that's acceptable, but add a one-line README note that the assets are deterministic, not AI-generated.

Everything else in CC's plan stands.

---

## Scope

- `blender/scripts/render_project.py` — background 3D enhancements only: rim light, backdrop cloth texture.
- `server/services/ffmpeg_service.py` — all post compositing: vignette + radial gradient, particle overlay, bokeh overlay.
- New assets: ember loop MP4, bokeh overlay (deterministic; neutral path per ADJ-3).
- `server/schemas/project.py` — only if new config keys are required for particle/background tuning (particles config already exists per CC; prefer reuse).

Templates: `character_intro` is the primary test target; `product_orbit` follows the same pattern.

---

## Implementation

### Step 1 — Background deterministic enhancement (Blender, 3D-baked)

**1a. Rim light on subject silhouette** — in `add_lighting()`:
- SPOT or AREA light, positioned behind-and-to-the-side of the subject (Y positive, Z ~subject center), narrow cone targeting the outline.
- Energy ~80–120, color configurable (cool cyan or warm gold).
- Only active for templates that have a background plane.

**1b. Cloth texture on backdrop** — in `add_stage()`, after `DarkBackdrop`:
- Procedural Noise Texture → ColorRamp → Base Color, very faint (large noise scale, mix factor ~0.05–0.10), OR a cloth PNG via Image Texture if available.

**1c. Vignette / radial gradient — REMOVED from Blender (see ADJ-1).** Handled in Step 2 (FFmpeg).

### Step 2 — Particle Method A: 2D overlay + all post compositing (FFmpeg)

**2a. Generate pure-particle render** — minimal Blender script, embers only on black:
- Simple plane emitter, PATH/OBJECT particles, orange emission, black world, no scene objects.
- 2-second loop, 24fps, 1080p → save to neutral overlay asset path (ADJ-3).

**2b. Auto-derive ember color from subject** (reuse dolly-ember color-pick logic):
- PNG: sample pixels in the alpha-bounded region, compute median hue.
- GLB: default warm orange `#FF8C2E`.
- Pass color into the overlay compositing step as a parameter.

**2c. FFmpeg composite** — single post chain in `FFmpegService.compose_mp4()` (or a new post step), in this order:
1. **Vignette + radial gradient** on the main render (`vignette` filter; center slightly above midpoint to track subject position). *(ADJ-1: this is the only place vignette lives.)*
2. **Particle overlay**, screen blend: `blend=all_mode=screen` with the ember loop, after applying speed (`setpts=PTS*{speed_factor}`), opacity (`format=rgba,colorchannelmixer=aa={opacity}`), and color tint (`lutrgb`/`colorchannelmixer` to the derived ember color).
3. **Bokeh overlay** — same 2D-overlay/screen-blend pipeline as particles (one shared mechanism handles both).

**2d. Configurability — no 3D re-render** (acceptance #7), tunable via project JSON / env:
- `particles.density` → number of stacked overlay layers
- `particles.speed` → `setpts` factor
- `particles.opacity` → alpha mix level
- `particles.color` → hex for LUT/colormix

**2e. A→B escalation gate (ADJ-2):** if 3 attempts of the 2D ember layer cannot reach "ember trail becomes a light streak" realism, STOP and switch to Method B (separate Blender particle pass composited in post). Record the attempt outcomes so the escalation is auditable.

### Step 3 — Integration & verification

**3a. Wire-in:** background = Blender render time (no API change); particle/bokeh/vignette = FFmpeg compose step. No schema change unless a new tuning key is genuinely needed.

**3b. Smoke test:** render `character_intro` 2s → confirm rim light + backdrop texture; apply FFmpeg post → confirm vignette + embers visible; confirm subject pixels unchanged (mask check); confirm no flicker (deterministic overlay).

**3c. Regression:** `dolly_in` and `orbit` subject pixels match pre-change baseline; camera trajectory unchanged (acceptance #1); existing tests pass.

---

## Files to modify

| File | Change |
|------|--------|
| `blender/scripts/render_project.py` | Rim light in `add_lighting()`; backdrop cloth texture in `add_stage()`. (No Blender vignette — ADJ-1.) |
| `server/services/ffmpeg_service.py` | Vignette/gradient + particle overlay (screen blend) + bokeh overlay; ember color tint/speed/opacity params. |
| `assets/overlays/` (neutral path, ADJ-3) | New: ember loop MP4, bokeh overlay (+ README noting deterministic, not AI). |
| `server/schemas/project.py` | Only if a new particle/background tuning key is required (prefer reuse). |

---

## Verification

1. `python -m py_compile blender/scripts/render_project.py server/services/ffmpeg_service.py`
2. `python -m unittest tests.backend.test_project_schema -v`
3. Blender render 2s `character_intro` → background has rim light + texture.
4. FFmpeg compose → vignette present, embers visible, no flicker.
5. Subject pixel diff vs baseline = 0 (mask-based) — guards acceptance #1 and #3.
6. Full suite: `python -m unittest discover -s tests`.
7. Output the local test video FILE PATH for 启鸣's human acceptance (workflow §4 step 7).

---

## Acceptance mapping (to `03-particle-background-requirements.md` §四)

| # | Criterion | Covered by |
|---|-----------|-----------|
| 1 | Camera unchanged | 3c regression + 5 (pixel diff) |
| 2 | Frame consistency | deterministic overlay (no AI), 3b flicker check |
| 3 | No distortion | 5 subject pixel diff = 0 |
| 4 | Ember look | 2a/2e + A→B gate |
| 5 | Color consistency | 2b auto-derive |
| 6 | Background layering | Step 1 (rim+texture) + 2c.1 (vignette/gradient) + bokeh |
| 7 | Debuggable w/o 3D re-render | 2d (all particle + vignette tuning in post) |
| 8 | Local video output | Verification step 7 |
