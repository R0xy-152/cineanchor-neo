# ADR-001: Product Positioning — Controllable Game-Ops Video Generator (toB), Not toC, Not a Free Editor

Decided: project inception (pre-2026-06-23).
Documented: 2026-07-03 (retroactive — backfills the ADR-001~003 numbering gap; the decision predates this record).

Status: Accepted (retroactively documented).

## Context

CineAnchor Neo generates vertical (9:16) game-promo / game-operations videos. The founding decision — made *before* any tech, architecture, or quality bar existed — was **who is this for**. Target-customer selection is the first move; the project (its four criteria, its stack, its constraints) is then built to serve that customer. The causal arrow runs **customer → project**, never the reverse.

Two forks were available:

- **toC consumer** — a video toy/app for individual players (AI effects, meme/novelty clips, one-tap "make it cinematic").
- **toB game-operations** — a production tool for game marketing/ops teams that must ship on-brand promo material on a cadence (new skin, new character, event, patch).

The product also had to avoid two adjacent traps (see `V0.2-vision-and-architecture.md` §三): becoming a low-配 剪映 (generic free timeline editor) or a low-配 AI-video experiment.

## Decision

CineAnchor is positioned as a **controllable, template/JSON-driven game-ops (toB) video generator**. It is explicitly **not** a toC consumer app, and **not** a free/timeline editor.

- User flow is template-fill: **pick template → fill assets → fill copy → pick theme color → export** — not free multi-subject placement, manual camera/FOV, or timeline editing.
- Founding goal (V0.1): portfolio-first — "fastest path to a portfolio-ready video demo AND best video quality" (see ADR-005). Evolution: V0.1 tech demo → V0.2 templated production MVP; positioning continuous, not overturned.

## Why game-ops and NOT toC

These are the reasons that stood **at inception — before the project had any technical characteristics**. They are grounded in market, buyer need, and solo-dev strategy alone. They are *prior to* and *cause* the quality bar; they are not derived from it.

1. **Market defensibility and reachability for a solo dev.** toC video is crowded, low-ARPU, virality- and CAC-dependent, and distribution-hard for one person. toB game-ops is a focused, reachable wedge with a nameable buyer, real budget, and higher willingness to pay — a go-to-market a single developer can actually serve.
2. **A real, repeatable operational need to build a product around.** Game marketing/ops teams must ship on-brand promo material on a cadence (new skin / character / event / patch). That recurring, structured demand is a durable business to serve; toC's "make me a fun clip" is an occasional, unstructured want with no cadence to anchor a product.
3. **A defined buyer with a clear value exchange.** An ops buyer has an explicit pain (produce many on-brand videos fast and reproducibly) and pays to remove it, so value can be captured *without* mass-market scale. toC monetizes only at distribution scale a solo dev cannot fund.
4. **Portfolio-first founding fit.** V0.1's goal was the fastest path to a portfolio-ready demo of *controllable quality*. A focused toB use-case with a demanding buyer showcases engineering depth far better than one more entry in the crowded toC toy category.

## Why the project follows the customer — not the reverse

Having chosen game-ops as the buyer, that choice **imposes** the project's defining characteristics. These are *consequences* of the positioning, not independent reasons for it — listing them as reasons to pick the customer would be circular, because they exist only because the customer was already chosen:

- The buyer's material must be brand-safe → the **four hard criteria** (controllable / no-distortion / logical / frame-to-frame consistent, ADR-005): a warped weapon skin or a wrong character face is unusable as official marketing.
- The four criteria → the **deterministic-over-generative bet** (ADR-005) and the **core tech stack** (ADR-002).
- The reproducible-cadence need → **Project JSON as single source of truth + seeded, versioned re-render** (ADR-003).
- A professional buyer already owns production assets → the **pre-matted transparent PNG / GLB** input premise.

The arrow is customer → four criteria → deterministic engine → stack/JSON/asset premise. These downstream properties **reinforce and stay consistent with** the choice, but they did not motivate it.

## Consequences

- Every downstream decision optimizes for controllability/reproducibility over creative freedom or generative novelty (grounds ADR-002 stack, ADR-003 JSON-single-truth, ADR-005 deterministic route).
- Features that only make sense for toC (one-tap AI restyle, meme effects, free editing) are out of scope; features that serve ops (templates, theme-color drive, versioned re-render, brand-safe determinism) are in.
- The product story is "a controllable game-promo video generator for ops," told by the deterministic pipeline itself.
- Re-open this ADR only if the **target buyer** changes; a toC pivot would invalidate the four-criteria bet and much of ADR-002/003/005. (Consistent with the customer→project direction: change the customer, and the project's characteristics must be re-derived.)
