# ADR-005: Deterministic Blender Rendering As Primary Route, AI Diffusion Deferred

Date: 2026-06-27

Status: Accepted

## Context

CineAnchor must produce game-promo videos for a portfolio. 启鸣 set the goal as "fastest path to a portfolio-ready video demo AND the best video quality," with four hard quality criteria for a "good" video:

1. Controllable picture (画面可控)
2. No subject distortion (画面不会扭曲)
3. Coherent / logical (有逻辑)
4. Frame-to-frame consistency (帧间一致)

A deep-research report (`deep-research-report (1).md`) evaluated an ambitious AI pipeline: depth-guided, multi-view-conditioned, camera-controllable video diffusion (Control-A-Video, CameraCtrl, MotionCtrl, CamI2V, ViewCrafter, MVGD, 3DGS, commercial APIs Veo/Sora/Runway). Its own conclusion: the pipeline is feasible only as a multi-stage research system, and "no single off-the-shelf commercial API should be the primary route" — public commercial APIs do not expose depth-video or per-frame camera matrices as first-class inputs.

The four criteria are intrinsically the strength of deterministic rendering, not generative AI. Deterministic 3D rendering projects the same geometry along a camera path every frame — no hallucination, so no distortion, inherent temporal consistency, full control. Generative AI introduces exactly the opposite risks (flicker, deformation, identity drift). `ADR-004` already excluded full-frame AI video regeneration for V0.1.

Given 启鸣's criteria, "fastest" and "best quality" do NOT conflict: the deterministic route wins both; the only thing sacrificed is the generative "cinematic AI" ceiling, which can be recovered via commercial APIs as a non-core polish layer.

## Decision

Adopt deterministic Blender rendering + post-processing as the **primary** route. Rank the implementation routes by recommendation:

1. **Primary (do now):** Blender deterministic render (Web → FastAPI → Blender Eevee → FFmpeg → MP4, the validated v0.1 chain) + post-processing polish (FFmpeg/LUT/compositing/particles/motion-blur, e.g. the dolly-ember enhancement). Scores full marks on all four criteria; fastest to portfolio; clean professional promo look.
2. **Polish layer (overlay on #1, not a standalone route):** Commercial APIs (Veo 3.1 / Sora / Runway) for a quality-ceiling comparison only. Feed structurally-correct keyframes from #1 as reference images (Veo accepts up to 3 ≈ tri-view). Uncontrollable (no depth/camera-matrix input) → fails "controllable/no-distortion"; restrict to isolated "wow" shots, never core control logic.
3. **Conditional (defer until #1 is solid):** Geometry-first hybrid (3DGS/multi-view → coarse render → conservative AI enhance on still frames only). Higher ceiling, more stable than pure depth-control; needs GPU + research integration. Consistent with ADR-004.
4. **Deferred (not now):** Control-first AI video diffusion (depth sequence + camera trajectory → Control-A-Video/CameraCtrl/CamI2V). Highest potential ceiling but research-grade, 256×256/16-frame, flicker + deformation risk, 3-7 days first version / 2-4 weeks to production. Directly conflicts with "fastest to portfolio" and threatens the four criteria.

## Reasons

1. The four hard criteria (controllable, no distortion, coherent, frame-consistent) are natively satisfied by deterministic rendering and natively endangered by generative AI.
2. "Fastest" and "best quality" align on the deterministic route — most of the v0.1 chain already exists.
3. The research report itself rejects any single commercial API as a primary route; commercial APIs expose no depth-video / camera-matrix inputs.
4. ADR-004 already excluded full-frame AI regeneration; routes #3/#4 stay within or beyond that boundary and are sequenced accordingly.
5. The portfolio story — "a controllable game-promo video generator" — is told by route #1 itself.

## Consequences

- The next requirement loop focuses on route #1: advance v0.1 + enhancements (e.g. dolly-ember) to produce portfolio video.
- Commercial-API polish (#2) is allowed only for isolated shots / comparison, never in the core control path.
- Geometry-first hybrid (#3) and control-first diffusion (#4) are recorded as "evaluated, deferred" — revisit per need once #1 meets the bar.
- The Blender deterministic data layer (EXR depth, PNG/EXR RGB, camera JSON) remains the canonical source if any AI route is later activated, so assets need not be re-rendered when model interfaces evolve.
- This ADR does not lock product architecture beyond route ordering; it sequences exploration, consistent with the project's still-in-selection stage.
