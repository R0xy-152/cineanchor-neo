# 10 — Character Birthday Template — Plan

> Author: Andy (execution plan for CC) · Base: `10-character-birthday-template-requirements.md` (accepted) + codex/v0.2 demo review + ADR-009.
> Language: English (plan). Status: ready for CC execution, subject to 启鸣 final sign-off on the acceptance amendment in §3.

---

## 0. Starting point (what already exists)

codex built a working foundation on branch `codex/v0.2` (HEAD `1835f48`):
- Schema extension: `character_birthday` added to `server/schemas/project.py` with conditional validation; legacy `character_intro` / `product_orbit` rules untouched (back-compat holds).
- Deterministic Pillow 2D compositor: `server/services/birthday_renderer.py` (`BirthdayFrameRenderer`) — 6-段 timeline, seeded particles, no AI, no network.
- Reference analysis (`docs/reference_analysis/`), template design doc, sample project, backend + frontend tests.

启鸣's verdict: video "勉强能接受" (barely acceptable), validated on **one** asset. This plan **adopts the foundation and closes the review gaps** to pass loop 10 acceptance — it does not rebuild from scratch.

## 1. Architecture decision adopted (ADR-009)

- **Render backend is dispatched per template.** `character_birthday` → Pillow 2D compositor; `character_intro` / `product_orbit` → Blender Eevee (unchanged).
- **The camera engine (loops 07-09) is NOT used by 2D poster templates.** It is reserved for 3D / spatial-showcase templates (loop 11 weapon-skin GLB path). "缓推 / 轻移" for the poster page = deterministic 2D scale/pan keyframes inside the compositor.
- The `camera` block stays required in schema for API-contract stability but is ignored by the 2D renderer.
- Full rationale + boundary in `docs/adr/ADR-009-templated-render-backend-dispatch.md`.

## 2. Work items (mapped to loop 10 acceptance #1–#8)

| WI | Work | Feeds acceptance |
|----|------|------------------|
| WI-1 | **Adopt codex foundation.** Rebase `codex/v0.2` onto latest main; resolve conflicts; verify legacy schema validators untouched. | #1, #7 |
| WI-2 | **Multi-asset generalization + text-positioning visual gate (the long pole).** | #2, #3 |
| WI-3 | **Externalize font config** — remove hardcoded OS font paths. | #3, #5 |
| WI-4 | **2D-path determinism regression** (pixel-diff). | #4 |
| WI-5 | **Missing-optional robustness.** | #5 |
| WI-6 | **Legacy zero-regression** (full test + pixel-diff on the two old templates). | #6 |
| WI-7 | **Schema validation + dispatched-backend render** (see §3 amendment). | #7 |
| WI-8 | **Sample video + usage doc.** | #8 |

### WI-2 detail (do NOT skip — this is where sign-off lives)

The demo passed on ONE asset; the renderer's layout is heavily proportional-hardcoded (date font `width*0.31`, fixed ribbon polygons, fixed positions). Run **≥4 diverse asset sets**:
- (a) long CJK name (4–6 汉字), (b) long Latin name, (c) wide/short character art, (d) tall/narrow art;
- crossed with a **dark** theme-color pair and a **light** pair.

For each set, **human visual gate**: date card / name card / ribbon title / subtitle must not overflow, clip, or misalign; text must be readable. Produce contact sheets at 段 boundaries. Fix layout that breaks — long strings must auto-shrink / wrap gracefully rather than overflow.

> This is the loop-03/04/07 blood lesson: **green unit tests ≠ visually correct.** No sign-off on unit tests alone; the visual gate is mandatory and separate (V0.2 §6).

### WI-3 detail

Move `font_preset` → font-file resolution out of hardcoded paths (`C:/Windows/Fonts/...`) into an editable config map (same externalization principle as loop 09 gamepad params — no hardcoding). Ship a documented fallback chain + a **licensing note**: production must bundle licensed fonts, must not depend on arbitrary machine fonts.

### WI-4 detail

Two full renders of the same project → **pixel-identical** (seeded particles). Add the pixel-diff test to the suite. Note: the Blender golden-pose oracle (ADR-008) does **not** cover the 2D path — the 2D path needs its **own** determinism regression. Do not conflate the two.

### WI-5 detail

no subtitle / no support image / no logo (→ title-text fallback) / no theme color (→ default preset) / no BGM → still exports, no crash. Unit + spot render.

## 3. Acceptance amendment (needs 启鸣 nod)

Loop 10 requirements acceptance **#7** currently reads "JSON schema 校验通过，新模板可被 **Blender** 原样渲染". ADR-009 dispatches `character_birthday` to **Pillow**, not Blender. Reword #7 to:

> "JSON schema 校验通过，新模板经其分派后端（Pillow 2D compositor）正确渲染。"

This is a direct consequence of the backend-dispatch decision 启鸣 approved. Flagging explicitly so the acceptance table stays honest.

## 4. Non-goals (unchanged from requirements)

No camera engine for this template; no auto-matting (transparent PNG hard prereq); no BGM; GLB deferred; no free editing / manual timeline.

## 5. Sequencing / timebox

1. WI-1 rebase/adopt → 2. WI-3 font externalize (cheap, unblocks portability) → 3. **WI-2 multi-asset visual gate (the blocking milestone)** → 4. WI-4 / WI-5 determinism + robustness → 5. WI-6 legacy full regression → 6. WI-8 sample + doc.

Everything else can be green while WI-2 still fails — WI-2 is the gate, weight the timebox there.

## 6. Open risks

- **Two-pipeline maintenance surface** (Pillow 2D + Blender Eevee) — accepted per ADR-009, but every future template MUST declare its backend in the ADR dispatch table.
- **codex authored this, not CC** — the merged result must pass the project's own gate (TDD + git hook + visual gate + 启鸣 sign-off), not inherit codex's self-assessment. CC owns the integrated code.
