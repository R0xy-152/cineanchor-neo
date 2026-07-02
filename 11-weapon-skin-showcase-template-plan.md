# 11 — Weapon Skin Showcase Template — Plan

> Author: Andy (execution plan for CC) · Base: `11-weapon-skin-showcase-template-requirements.md` (accepted) + `ADR-009` (render-backend dispatch) + 启鸣's scope change 2026-07-02 (GLB + PNG both required).
> Language: English (plan). Status: ready for CC execution, subject to the requirements-sync note in §0.

---

## 0. Scope change locked by 启鸣 (2026-07-02) — GLB **and** PNG both in-scope

Requirements §二.1 / §三 / §七 deferred the GLB 3D path ("PNG 2.5D 优先；GLB 明确后置，本 loop 可只留 schema 占位"). **启鸣 now requires BOTH the GLB (3D) and PNG (2.5D) paths in this loop.** This supersedes the deferral. Loop 11 delivers both.

> **Requirements-sync note (needs 启鸣 one-line OK):** requirements §二.1 (GLB 后置), §三 (PNG 优先 / GLB schema 占位), §七 no longer match scope. On OK I will patch those lines to "GLB + PNG both delivered this loop." The plan below already assumes both.

## 1. Approach decision (plan-review of CC's A/B/C)

**Endorse Approach A (inline dispatch, no premature abstraction)** — with a sharpening.

- **Why A:** requirements §六.6 ("组件抽象在本 loop 收尾时评估") + V0.2 §5 ("先具体两次，再抽象一次"). Add the third template exactly the way `character_intro` / `product_orbit` were added; extract shared components only at loop end (acceptance #8). **B (strategy/plugin base class) = premature abstraction — correctly rejected** (we don't yet know the real shared shape birthday↔weapon). **C (separate module) = optional fallback** only if `render_project.py` grows unwieldy; default to A.
- **Sharpening / correction to CC's framing:** CC's A described only the Blender functions (`add_stage`/`add_lighting`/`add_text_overlay`/`build_scene`). Unlike `character_birthday` (Pillow 2D), **weapon-skin runs BOTH asset paths through Blender Eevee + the camera engine.** So the `weapon_skin_showcase` branch must **sub-dispatch on asset type**:
  - `AssetType.GLB` → import mesh, camera orbits real geometry;
  - `AssetType.IMAGE` (PNG 2.5D) → textured plane in the 3D scene, lit + camera light-sweep (genuine 2.5D, NOT flat Pillow compositing).
- **This fills the ADR-009 dispatch-table TBD row** and is the template that finally exercises the camera engine (the moat). ADR-009 updated accordingly.

## 2. Backend & dispatch (fills ADR-009 table)

- `weapon_skin_showcase` → **Blender Eevee + camera engine**, for **both** asset paths.
- Asset-type sub-dispatch lives inside the single template branch — only the geometry-load + framing differs (GLB mesh vs PNG plane); timeline, lighting, sweep, particles, text, end-card are shared across both paths.

## 3. Schema extension (back-compat — must NOT break the three existing templates)

- Add `Template.WEAPON_SKIN_SHOWCASE = "weapon_skin_showcase"`.
- Asset ids (conditional-validated): `weapon` **required** (type `glb` OR `image`), `logo` optional. Reject unknown ids.
- `TextSpec` additions (reuse where possible): `weapon_name` **required**, `skin_name` **required**, `rarity` optional, `series` optional, `cta` optional.
- New style block (mirror `BirthdayStyleSpec` pattern): `theme_color` **required** (drives lighting + particle base), `element_theme` **required** enum ∈ {`fire`,`ice`,`lightning`,`venom`,`cyber`,`gold_black`}.
- New timeline (7 段, `for_duration(12)` default, scales like birthday): `dark_ignite` / `silhouette_reveal` / `light_sweep` / `side_showcase` / `element_burst` / `skin_title` / `brand_cta`.
- Conditional validators mirror birthday: version `0.2`, aspect `9:16`, required-field checks, missing-optional → no crash / still exports.
- **Zero-touch** to `character_intro` / `product_orbit` / `character_birthday` validation — verified by full legacy regression.

## 4. Rendering — 7 段, deterministic (ADR-006), camera engine internal

| 段 | Time | Camera (internal engine) | Deterministic effects |
|----|------|--------------------------|-----------------------|
| dark_ignite | 0–1s | static / slow push | dark stage; theme-color key light ramps up |
| silhouette_reveal | 1–3s | preset slow reveal | weapon emerges from dark (exposure/lighting ramp) |
| light_sweep | 3–5s | slight dolly | deterministic light sweep across surface (moving area/emission band) |
| side_showcase | 5–7s | preset side profile (orbit/dolly) | full weapon lit |
| element_burst | 7–9s | hold / subtle | element particle system (ADR-006 seeded) per `element_theme` |
| skin_title | 9–10.5s | hold | text overlay: skin_name / rarity / series — **text-positioning visual gate** |
| brand_cta | 10.5–12s | end-card framing | logo + CTA |

- **GLB path:** real mesh; camera orbits geometry; light sweep on real surface.
- **PNG 2.5D path:** PNG on a plane facing camera (slight tilt allowed); light sweep = moving light over the plane; optional subtle parallax — **stay deterministic**. If the flat sweep reads weak vs GLB, add a subtle normal/tilt, not AI.
- Camera motion = loops 07-09 presets/keyframes; **user touches no camera params** (requirements §二.3).

## 5. Determinism & no AI (铁律 + V0.2 §4.2)

- Lighting / light-sweep / element particles all deterministic → **two renders pixel-identical** (pixel-diff test). Element particles seeded by `project_id` (same discipline as birthday). **No AI anywhere in the path.**

## 6. Camera engine reuse — the moat, oracle-guarded

- Reuse `camera_math` / `camera_presets`. Because this template renders through Blender + the camera transform, **any coordinate-space change MUST extend the golden-pose oracle before merge** (ADR-008 permanent guardrail). Unlike birthday (2D, no oracle coverage), weapon-skin motion IS oracle-guarded.

## 7. Acceptance mapping (requirements §五 #1–#9) + GLB/PNG addition

- #1 端到端导出 9:16 12s MP4 — **verify on BOTH a GLB asset AND a PNG asset** (two end-to-end runs).
- #2 7-段结构 — visual, both paths.
- #3 theme-color drives lighting/particles; element_theme → correct effect.
- #4 **文字定位正确** (skin_name/rarity/CTA) — **visual gate + 启鸣, the long pole, blocking.**
- #5 lighting/sweep/particles deterministic — pixel-diff (both paths).
- #6 missing-optional still exports.
- #7 **zero regression on old 2 templates + `character_birthday`** — full test + pixel-diff.
- #8 **component-abstraction assessment report** — at loop end, list real shared shapes birthday↔weapon (Date/Title/Subtitle/Particle/Logo-EndCard/Light-Sweep) → extract-or-not recommendation (Andy review).
- #9 sample video + usage doc — **one GLB sample + one PNG sample.**

## 8. Work-item sequence

1. Schema + validators + tests (back-compat). → 2. GLB path render (mesh import + camera + lighting + sweep). → 3. PNG-2.5D path (textured plane). → 4. Element particles (6 deterministic presets, one per `element_theme`). → 5. Text overlay (skin_title + CTA) + **visual gate**. → 6. Determinism pixel-diff (both paths). → 7. Legacy + birthday zero-regression full run. → 8. Sample videos (GLB + PNG) + doc. → 9. Component-abstraction assessment (#8).

**Blocking milestones:** text-positioning visual gate (#4) + both-path end-to-end (#1). Everything else can be green while these fail — weight the timebox there.

## 9. Non-goals / boundaries

- Transparent PNG hard prereq, no auto-matting. No AI. No user-facing camera params. No free multi-subject / timeline editing. Component library NOT pre-built (extract at loop end, #8). Advanced GLB (PBR material authoring, skeletal animation) beyond a static lit showcase = deferred.

## 10. Risks

- **Two asset paths in one template = more surface.** Mitigate: share 段/timeline/lighting/text logic; sub-dispatch only geometry-load + framing.
- **6 element presets** — scope each as a single deterministic preset; do NOT expose per-particle control.
- **PNG-2.5D light sweep may read flatter than GLB** — visual gate must confirm both acceptable; fix with subtle tilt/normal, never AI.
- **codex vs CC ownership** — this loop is CC's; ensure the integrated result passes the project's own gate (TDD + hook + visual gate + 启鸣 sign-off).
