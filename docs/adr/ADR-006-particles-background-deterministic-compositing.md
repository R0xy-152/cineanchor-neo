# ADR-006: Particles & Background via Deterministic Compositing, AI Rejected for Both

Date: 2026-06-27

Status: Accepted

## Context

Under the route locked by `ADR-005` (deterministic Blender render + post polish as the primary route), the camera work has passed acceptance and is locked. Two problems remained on route ①:

1. **Particles are persistently hard to debug.** Camera passed acceptance, but every particle parameter change required re-rendering the whole pipeline to see the result — iteration measured in minutes.
2. **The black-cloth background is "too dead"** — pure black is flat and gives no sense of space.

Root-cause analysis showed the particle difficulty is **not a wrong-tool problem but an over-coupling problem**: particles were rendered together with the 3D main scene, motion blur, and camera, so the variables were entangled and could not be iterated independently.

A tempting alternative was to hand particles to generative AI. This was rejected: among the four hard criteria (`ADR-005`), frame-to-frame consistency is the most critical, and particles (small + bright + fast-moving) are exactly the element generative AI is least stable on — per-frame regeneration makes small bright points jitter in position/count/brightness → flicker. Using AI to "fix" particles would trade away the very metric we care about most for something that can be deterministically locked.

The background being "too dead" is the easiest problem to solve deterministically and likewise needs no AI.

## Decision

**Both particles and background go through deterministic compositing; AI does not enter either of these two areas.** (AI stays where `ADR-005` placed it: isolated "wow" shot look-comparison only, never the core control path.)

**Particles — decouple into an independent layer:**
- **Method A (primary):** 2D ember overlay layer. Particles are rendered/sourced as an independent transparent-or-black-background looping layer; the 3D main render contains NO particles. Composite over the main render with FFmpeg `screen`/`add` blend. Ember color is auto-derived from the subject's main color (reusing the dolly-ember color-pick logic). Density / color / speed / opacity are tunable WITHOUT re-rendering the 3D scene → second-level iteration.
- **Method B (fallback):** render particles as a separate Blender pass and composite in post. Retains Blender physical realism but is slower and still needs physics tuning. Switch to B only if A's look is insufficient — concretely, if within 3 attempts stock/single-layer material cannot achieve the "ember trail becomes a light streak" realism.

**Background — deterministic enhancement, all four items adopted:**
1. Faint radial gradient + vignette (FFmpeg `vignette` or Blender world/compositor nodes).
2. Rim light on the subject silhouette (a spot/area light behind-and-to-the-side, lighting only the outline).
3. Very faint cloth texture or noise so the background is no longer a dead flat black.
4. Bokeh light spots as a 2D overlay layer (same approach as the particle layer).

Constraint: background enhancement must not overpower the subject — the weapon is always the subject; the background only adds layering and a sense of space.

## Alternatives Considered

- **Keep debugging particles inside the coupled main pipeline.** Rejected: the cost is structural (re-render per tweak), not a matter of more tuning effort.
- **Use generative AI for particles.** Rejected: directly endangers frame-to-frame consistency, the most critical of the four criteria; particles are AI's worst case.
- **Particle Method B as the primary path.** Deferred to fallback: higher physical fidelity but slower and still coupled to physics-parameter tuning; only justified if A cannot reach the target look.

## Consequences

- Particle look (density / color / speed) becomes tunable at second-level latency with zero 3D re-render, removing the iteration bottleneck that motivated this decision.
- Landing order: background deterministic enhancement first (small change, low risk, immediate effect) → particle Method A → Method B only if A's look fails the bar → no AI introduced at any point.
- Acceptance is governed by the 8-criterion table in `03-particle-background-requirements.md` (camera unchanged, frame consistency, no distortion, ember look, color consistency, background layering, debuggability without 3D re-render, local video output per the workflow rules). Final video acceptance remains a human (启鸣) decision.
- Consistent with `ADR-005` (AI confined to non-core polish) and `ADR-004` (no full-frame AI regeneration); this ADR extends that boundary to two specific elements (particles, background) without altering the route ordering.

## 2026-06-27 Update — Ember color-consistency clarified, and a visibility guard added

First execution (loop `03`) shipped but failed human acceptance: the ember overlay asset (`embers_default.mp4`) rendered pure black (embers invisible — screen-blending a black layer adds nothing), and the final composite read as "a filter over the subject" because the auto-derived ember color collapsed everything into one flat tone. The automated suite (58/58) passed while the actual visual deliverable was empty — code paths were tested, but not "does the layer contain visible embers."

This is an execution-correction loop (`04-particle-visibility-fix-requirements.md`), not a new method decision, so it is recorded here as a dated update rather than a new ADR. Two clarifications to the original Decision:

1. **Ember color-consistency refined (amends acceptance criterion #5).** "Ember color consistent with the weapon's style color" must NOT be taken as "identical color." Embers share the weapon's **hue family** but must be high-luminance / high-saturation and contrast against the subject, reading as discrete bright sparks — never collapsing the frame into a single flat tinted layer. Color-consistency ≠ washed-out monochrome.
2. **Visibility guard is now part of the deterministic-compositing contract.** Because a black/empty overlay can pass code-level tests silently, generation of any overlay asset must include an automated non-black / luminance self-check that FAILS generation when the layer is black or near-black. A green test suite is not sufficient evidence that the visual deliverable exists.

The Method A → B escalation gate is reaffirmed: a black ember layer is a Method-A generation defect to fix within A, not a trigger to jump to B. Escalate to B only if embers are visible but still cannot reach "ember trail becomes a light streak" realism.
