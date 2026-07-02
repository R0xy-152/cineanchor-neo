# ADR-009: Templated Render-Backend Dispatch — 2D Poster Compositor vs Blender Eevee, and the Camera-Engine Applicability Boundary

Date: 2026-07-02

Status: Accepted

Relates to: `ADR-004` / `ADR-006` (JSON single-truth, render-backend integrity, deterministic compositing), `ADR-005` (four hard criteria + route ranking), `ADR-008` (camera engine + golden-pose oracle). Extends V0.2 vision (`V0.2-vision-and-architecture.md` §4.1 camera-engine-internalized, §4.4 schema back-compat).

## Context

V0.2 introduces templates. The first, `character_birthday`, was prototyped on branch `codex/v0.2`. Its content is flat graphic design — date card, ribbon title, poster layout, subtitle, procedural petals, logo end card. The prototype renders these with a **deterministic Pillow 2D compositor** (`birthday_renderer.py`), NOT Blender Eevee, and NOT the loops 07-09 camera engine.

This forces a decision the V0.2 vision (§4.1 "camera engine internalized as template motion system") left unresolved: **does every template run through Blender + the camera engine, or can a template pick a cheaper backend?** The prototype answered by fact; this ADR decides it by intent.

## Decision

**1. Render backend is dispatched per template, not global.** `character_birthday` → Pillow 2D compositor. `character_intro` / `product_orbit` → Blender Eevee (unchanged). The service dispatch boundary routes by `Template` enum.

**2. The camera engine (loops 07-09) is NOT universal.** It is the motion system for **3D / spatial-showcase** templates (product orbit; weapon-skin GLB showcase, loop 11). For **flat 2D poster** templates, "camera" motion (缓推 / 轻移) is achieved with deterministic 2D scale/pan keyframes inside the compositor. The `camera` block stays required in schema for API-contract stability but is **ignored** by 2D renderers.

**3. JSON stays the single source of truth; each template declares its backend.** The schema extension is back-compat (version `0.1` / `0.2`; legacy `main_subject` rules untouched). No template gets an implicit default backend — the dispatch table below is authoritative.

**4. Determinism is proven per-backend.** Each backend owns its determinism regression. The Blender golden-pose **oracle (ADR-008) guards the 3D path ONLY**; the 2D path must carry its **own** pixel-diff determinism test. The two are never conflated.

## Reasons

- **Cost / fit (ADR-005 route ranking).** Rendering flat typography + masks through Blender adds font/stroke/render cost for zero visual gain. The 2D compositor is the least-powerful deterministic route that meets the four hard criteria for poster content — exactly what route-ranking prescribes.
- **Moat preserved, not diluted.** The camera engine is a real moat (competitive-analysis T2, precise camera input) for spatial templates. Forcing it onto 2D posters would not showcase it. Reserving it for 3D/showcase templates keeps its leverage where it matters (loop 11).
- **Determinism intact, no new AI (V0.2 §4.2).** Both backends are deterministic; seeded particles; no network.
- **Back-compat structurally enforced.** Legacy templates keep the exact Blender path; the dispatch boundary + schema validators make zero-regression a structural property, not a hope.

## Consequences

- **Positive:** the first template ships on the cheapest correct backend; the camera engine stays sharp for templates that actually need it; the schema stays one truth with an explicit per-template backend declaration.
- **Cost accepted:** two render pipelines now coexist (Pillow 2D + Blender Eevee); maintenance surface roughly doubles. **Mitigation:** every new template MUST add a row to the dispatch table below with an explicit backend — no implicit default.
- **Guardrail:** the 2D path does NOT inherit the oracle's guarantee. "Blender path is guarded" ⇏ "2D path is guarded." The 2D path needs its own pixel-diff determinism regression (loop 10 WI-4).
- **Acceptance amendment:** loop 10 requirements acceptance #7 ("新模板可被 Blender 原样渲染") is superseded — new templates render via their **dispatched** backend, not necessarily Blender. Rewording flagged to 启鸣 in the loop 10 plan §3.
- **Highest-risk area moves to text positioning:** 2D poster layout is proportional-hardcoded and over-fits to one asset unless verified. Visual gate on text positioning across diverse assets is mandatory (V0.2 §6 + loop-03/04/07 lesson).
- **Deferred:** loop 11 (weapon-skin) exercises the 3D/GLB + camera-engine path; the dispatch table gains its row then. Component abstraction (V0.2 §5) is evaluated **after** that second template, not now.
- **Revert path:** the JSON/schema is backend-agnostic — a template can be re-homed to another backend without changing its JSON. Nothing locks a template to a backend.

## Dispatch table (living — every new template adds a row)

| Template | Backend | Motion system | Determinism guard |
|---|---|---|---|
| `character_intro` | Blender Eevee | camera engine (presets / keyframes) | golden-pose oracle (`tests/parity/`) |
| `product_orbit` | Blender Eevee | camera engine (orbit) | golden-pose oracle |
| `character_birthday` | Pillow 2D compositor | 2D scale/pan keyframes | pixel-diff determinism test (loop 10 WI-4, to build) |
| `weapon_skin_showcase` (loop 11) | TBD — PNG 2.5D → 2D+; GLB 3D → Blender + camera engine | TBD | TBD |
