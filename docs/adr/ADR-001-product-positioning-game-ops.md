# ADR-001: Product Positioning — Controllable Game-Ops Video Generator (toB), Not toC, Not a Free Editor

Decided: project inception (pre-2026-06-23).
Documented: 2026-07-03 (retroactive — backfills the ADR-001~003 numbering gap; the decision predates this record).

Status: Accepted (retroactively documented).

## Context

CineAnchor Neo generates vertical (9:16) game-promo / game-operations videos. Before any tech or architecture choice, the founding product question was *who is this for and what is it*. Two forks were available:

- **toC consumer** — a video toy/app for individual players (AI effects, meme/novelty clips, one-tap "make it cinematic").
- **toB game-operations** — a production tool for game marketing/ops teams that must ship on-brand promo material on a cadence (new skin, new character, event, patch).

The product also had to avoid two adjacent traps (see `V0.2-vision-and-architecture.md` §三): becoming a low-配 剪映 (generic free timeline editor) or a low-配 AI-video experiment.

## Decision

CineAnchor is positioned as a **controllable, template/JSON-driven game-ops (toB) video generator**. It is explicitly **not** a toC consumer app, and **not** a free/timeline editor.

- User flow is template-fill: **pick template → fill assets → fill copy → pick theme color → export** — not free multi-subject placement, manual camera/FOV, or timeline editing.
- Founding goal (V0.1): portfolio-first — "fastest path to a portfolio-ready video demo AND best video quality" (see ADR-005). Evolution: V0.1 tech demo → V0.2 templated production MVP; positioning continuous, not overturned.

## Why game-ops and NOT toC

The choice is forced by the product's own quality bar and design, not a market whim:

1. **The four hard criteria demand a market that requires correctness.** Our bar is controllable / no-distortion / logical / frame-to-frame consistent (ADR-005). toC video toys tolerate distortion and randomness because their value is novelty, fun, and virality. Game-ops material cannot: a warped weapon skin or a wrong character face is unusable as official marketing. The deterministic-over-generative bet only pays off where correctness is mandatory — that is game-ops, not toC.
2. **Template-fill fits a repeatable operational need, not a consumer one.** Ops teams produce many promo videos on a cadence and need fast, stable, on-brand, reproducible output from structured inputs (asset + copy + theme color). toC users want either full creative freedom (→ a free editor, which we reject) or one-tap generative novelty (→ AI that breaks the criteria). Our design serves neither consumer mode — it is intrinsically an ops production tool.
3. **Reproducibility + versioning is a feature for ops, invisible to toC.** Seeded, versioned, re-renderable output (competitive-analysis tripwire T3) lets ops tweak-and-re-render and maintain a consistent series look. Consumers don't value this.
4. **The asset premise presupposes a professional user.** The pipeline requires real game assets — pre-matted transparent PNG / GLB (V0.2 §4.3). Game-ops teams have these production assets; toC consumers do not.
5. **Focus and defensibility for a solo dev.** toC is crowded, low-ARPU, virality- and CAC-dependent, and distribution-hard for one developer. Game-ops is a focused, reachable, higher-willingness-to-pay wedge where the moat (a controllable deterministic engine) is exactly what the buyer needs.

## Consequences

- Every downstream decision optimizes for controllability/reproducibility over creative freedom or generative novelty (grounds ADR-002 stack, ADR-003 JSON-single-truth, ADR-005 deterministic route).
- Features that only make sense for toC (one-tap AI restyle, meme effects, free editing) are out of scope; features that serve ops (templates, theme-color drive, versioned re-render, brand-safe determinism) are in.
- The product story is "a controllable game-promo video generator for ops," told by the deterministic pipeline itself.
- Re-open this ADR only if the target buyer changes; a toC pivot would invalidate the four-criteria bet and much of ADR-002/003/005.
