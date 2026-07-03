# ADR-003: Project JSON As The Single Source of Truth

Decided: project inception (pre-2026-06-23).
Documented: 2026-07-03 (retroactive — backfills the ADR-001~003 numbering gap; the decision predates this record).

Status: Accepted (retroactively documented).

## Context

With a controllable game-ops positioning (ADR-001) and a Blender/FFmpeg stack (ADR-002), the product needed one authoritative representation of "what video to produce" that both the Web UI and the render backend agree on — and that keeps output reproducible as templates, backends, and features evolve.

The risk to avoid: logic and state scattered across UI code, render scripts, and ad-hoc parameters, which would make output non-reproducible and every new template a backend rewrite.

## Decision

A declarative **Project JSON** is the single source of truth for every video.

- The JSON fully describes the video: assets, template, text/copy, theme color, timeline/stages, camera, effects.
- **Render backends are pure functions of the Project JSON** — same JSON (+ same seed) → same output. Backends read the JSON; they do not hold hidden state.
- **Templates are JSON *generators*, not backend variants.** A template turns a small template-fill form (asset + copy + theme color) into a valid Project JSON; the backend does not change for a template.
- Schema evolves **backward-compatibly** — new template/asset/timeline structures must never break existing templates (e.g. `character_intro` / `product_orbit`).

## Reasons

1. **Reproducibility** — a single declarative artifact makes "same input → same video" enforceable and auditable; it is the substrate the determinism guarantees (ADR-005) stand on.
2. **Template scalability without backend churn** — because templates only *generate* JSON, adding templates does not fork the renderer; the moat (deterministic engine) is written once and reused.
3. **Clean UI/render boundary** — the Web UI produces JSON; the backend consumes JSON; they can evolve independently.
4. **Versionability** — a JSON artifact can be stored, diffed, and version-pinned, enabling tweak-and-re-render for ops (ADR-001 reason 3) and, if ever needed, version-pinned generated assets under the bounded-AI layer (ADR-010).

## Consequences

- Every later architectural decision treats JSON as the contract: ADR-008 (interactive camera) writes camera data back into the JSON; ADR-009 (backend dispatch) has each template *declare its backend in the JSON*, no implicit default; ADR-010 (bounded offline AI) stores/version-pins generated artifacts in the JSON.
- Determinism must be verified **per backend** against the same JSON (Blender golden-pose oracle for the 3D path; pixel-diff for the 2D path) — the JSON is the shared fixture.
- Any feature that would require hidden, JSON-external state (e.g. per-frame live generation, non-reproducible randomness) is rejected by default; state that matters must live in the JSON.
- Schema changes carry a hard back-compat obligation and a regression gate on legacy templates.
