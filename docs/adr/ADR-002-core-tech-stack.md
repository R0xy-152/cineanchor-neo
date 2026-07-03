# ADR-002: Core Tech Stack — Web → FastAPI → Project JSON → Blender Eevee → FFmpeg → MP4, Local-First

Decided: project inception (pre-2026-06-23).
Documented: 2026-07-03 (retroactive — backfills the ADR-001~003 numbering gap; the decision predates this record).

Status: Accepted (retroactively documented).

## Context

Given the positioning (ADR-001: controllable game-ops video generator), the product needed a rendering and orchestration stack that could deliver the four hard criteria (controllable / no-distortion / logical / frame-to-frame consistent) fastest, for a solo developer, without cloud dependencies.

Candidate render approaches: (a) deterministic 3D rendering (Blender), (b) generative AI video (diffusion / commercial APIs), (c) 2D-only motion-graphics tooling. Candidate deployment: local-first vs cloud/SaaS.

## Decision

Adopt this stack as the core path:

**Web UI → FastAPI → Project JSON → Blender Eevee (headless) → FFmpeg → MP4**, orchestrated in **Python**. Inputs: user-uploaded **PNG / GLB**. Deployment: **local-first, serial render, no cloud / SaaS / accounts**.

- **Blender Eevee (headless)** = primary render engine: fast, deterministic, fully controllable geometry/camera/lighting; projects the same geometry along a camera path every frame → no hallucination, inherent temporal consistency.
- **FFmpeg** = frame→MP4 encode + any color/LUT/filter post; also the boundary for text/subtitle compositing.
- **FastAPI + Project JSON** = the request/description boundary (JSON detailed in ADR-003).
- **Python** = single orchestration language across web, render scripts, and tests.

## Reasons

1. **Deterministic rendering natively satisfies the four criteria; generative AI natively endangers them** (elaborated in ADR-004 / ADR-005). Blender wins the quality bar by construction.
2. **Fastest to portfolio for a solo dev** — the Web→FastAPI→Blender→FFmpeg→MP4 chain is standard, debuggable, and mostly reusable; no research-grade AI integration on the critical path.
3. **Local-first removes cloud cost, latency, data-egress, and account/SaaS complexity** at this stage — appropriate for a solo, pre-product project (see `docs/scope.md` non-goals).
4. **Eevee over Cycles** — real-time-oriented rasterizer is fast enough for stylized promo output and keeps iteration cheap; path-traced realism is not the product need.
5. **GLB + PNG inputs** match real game assets ops teams already own (ADR-001 asset premise).

## Consequences

- The Blender deterministic data layer (RGB frames, optional EXR depth, camera JSON) is the canonical render substrate; if any bounded AI layer is ever activated (ADR-007 / ADR-010) it composits over this substrate, not replaces it.
- Serial, local render is accepted as a throughput limit for now; batch/parallel/cloud are explicit non-goals until later.
- Render-backend specialization is allowed per template without breaking this stack: ADR-009 later dispatches character_birthday to a Pillow 2D compositor while legacy/showcase templates stay on Blender Eevee — an extension of, not a departure from, this decision.
- FFmpeg remains the final encode + safe locus for text compositing (keeps text out of any AI/render instability, per ADR-004).
