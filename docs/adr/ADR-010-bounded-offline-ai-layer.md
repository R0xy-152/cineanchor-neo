# ADR-010 — Bounded Offline AI Layer

- **Status:** Proposed (DRAFT — recorded per 启鸣 2026-07-03 "先落成草案，不落实"). NOT accepted, NOT implemented.
- **Date:** 2026-07-03
- **Deciders:** Andy (drafts) + 启鸣 (sole approver). Activation is a joint decision, never unilateral CC.
- **Supersedes / relates:** extends ADR-006 (deterministic particles), ADR-007 (bounded AI spark — manual/optional/off-path). Sits under the V0.2 §4.2 "no new AI in auto path" line and the four hard criteria (ADR-005: controllable / no-distortion / logical / frame-to-frame consistent).

## Context

Across loop 10 (birthday particles below production standard) and loop 11 (weapon-skin fire "太廉价太假" then, after rework, not visible at all), the recurring question surfaced: are CC-authored deterministic particles fundamentally quality-capped, and should a commercial AI model be introduced?

Andy's standing position: most defects are deterministic-execution bugs, not a ceiling — hence loop 12 exists to prove a properly-built deterministic FX system can reach the production bar BEFORE any AI is considered. This ADR pre-defines the boundary so that IF loop 12 (or a V0.3 feature) genuinely needs AI, we already know where AI is allowed to sit — and where it is forbidden.

## The core distinction

The single judgment that decides whether an AI use breaks our four hard criteria:

> **Pre-render static-artifact AI** — AI produces a static, human-reviewable, versioned artifact ONCE, before the deterministic render → **ALLOWED (bounded).**
> **Per-frame pixel AI** — AI generates or regenerates pixels during the render, or runs in realtime preview → **FORBIDDEN** (breaks frame-to-frame consistency + invites distortion; ADR-004/005).

Frame-to-frame consistency is preserved because a static artifact, reused deterministically across frames, cannot flicker or drift.

## Decision (DRAFT — the boundary, if/when activated)

An AI use is admissible into the pipeline ONLY IF it satisfies ALL of:

1. **Offline / pre-render** — runs before the deterministic render step, never inside the per-frame loop, never in realtime preview.
2. **Static output** — emits a fixed artifact: image, texture/sprite sheet, short looping frame sequence, text string, or audio clip. NOT a live generator called during rendering.
3. **Seeded + reproducible** — same input + same seed → same artifact; artifact is cached.
4. **Versioned** — the generated artifact is stored and version-pinned in the Project (so re-renders are byte-stable and the artifact is auditable).
5. **Human-reviewable** — a human can inspect/approve/replace the artifact before it enters the render (e.g. crop the generated asset sheet, edit the generated line, swap the voice clip).
6. **Off the default auto-path unless explicitly promoted** — like ADR-007, defaults to manual/optional; promotion to a template's default pipeline is a per-feature joint decision recorded here.

Forbidden regardless: per-frame image regen, full-frame AI restyle (ADR-004), realtime-preview AI, any use that makes two renders of the same JSON differ.

## Candidate activations (NOT yet approved — placeholders)

| Trigger | Use | Admissible under this ADR? | Status |
|---|---|---|---|
| loop 12 deterministic FX misses production bar | AI-generated static fire sprite / short loop sequence, composited deterministically | Yes (offline, static, seeded, versioned) | pending loop 12 outcome |
| V0.3 scene-adaptive fonts | AI recognizes subject → generates a croppable asset sheet, human crops | Yes (pre-render, human-reviewed static artifact) | deferred, deterministic font-library version first |
| V0.3 AI dialogue | AI drafts lines from character bio, human edits | Yes (static text, human-reviewable) | deferred |
| V0.3 AI voiceover | AI voice clone; user-upload has no AI | Yes for clone (static clip); user-upload trivially safe | deferred, user-upload first |

## Consequences

- Gives us a principled "yes" lane for AI without breaching frame consistency — the boundary, not a blanket ban.
- Keeps determinism as the default; AI is the escalation, entered only by joint decision and only in the pre-render layer.
- Requires Project schema to store/version generated artifacts when any activation is approved (deferred until first activation).

## Open questions (to resolve at activation, not now)

- Which model / local-vs-hosted for each activation (licensing, reproducibility).
- Artifact storage + version-pin mechanism in Project JSON.
- Cost / offline-batch workflow.
