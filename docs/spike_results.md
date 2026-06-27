# CineAnchor Neo Spike Results

## V0.1 Start Decision

Status: STARTED

All major Spike routes are complete enough to start V0.1 official development.
The V0.1 core path is Web -> FastAPI -> Project JSON -> Blender Eevee -> FFmpeg
-> MP4.

Route 3 remains PARTIAL and optional. Full-frame AI video regeneration stays
forbidden for V0.1, and ComfyUI is not required for standard rendering.

## AI Enhancement Feasibility Gate 2: Structure Control

Status: FAIL

Goal question: Can structure-controlled AI enhancement make Blender output visibly better while preserving subject identity, product shape, text stability, and temporal stability?

Conclusion: FAIL for product feasibility. Canny ControlNet, unique raw/control uploads, and subject-protected compositing improved stability compared with plain img2img. Text remains stable because it is post-overlaid. However, the best stable output is only mildly better than raw Blender, stronger settings introduce artifacts/detail drift, and no non-developer reviewer preference was collected.

| Field | Result |
|---|---|
| Commands run | Created isolated `spikes/ai_enhance_gate2`; parsed PowerShell; compiled Python; started/probed ComfyUI; rendered no-text RGB and masks; generated Canny maps; ran plain img2img denoise sweep; ran Canny ControlNet denoise sweep; fixed raw/control upload filename collision; generated subject-protected composites; processed 48 continuous frames; recomposed MP4s; ran ffprobe; ran optional product keyframe check. |
| Input assets | `spikes/render_json/input/hero.png`, `spikes/render_json/input/model.glb` |
| Output artifacts | `spikes/ai_enhance_gate2/output/character_intro/before_after_2s.mp4`, `control_canny_fixed_2s_denoise_0_35.mp4`, `protected_canny_fixed_2s_denoise_0_35.mp4`, keyframe grids under `output/*/keyframes/comparisons/` |
| Structural maps | RGB raw frames and subject masks generated. Canny maps generated through FFmpeg. Blender 5.1.2 Z/Normal pass flags exist, but reliable depth/normal export was not practical because the compositor/file-output API changed and `OPEN_EXR_MULTILAYER` was unavailable in this build. |
| Render duration | character_intro RGB: 54.952s for 96 frames; character_intro mask: 14.508s; product_orbit RGB: 31.882s for 48 frames; product_orbit mask: 11.327s |
| Workflow | `sdxl_img2img_api.json` baseline; `sdxl_controlnet_img2img_api.json` with `SetUnionControlNetType` |
| Checkpoint / Control model | `RealVisXL_V5.0_Lightning_fp16.safetensors`; `diffusion_pytorch_model_promax.safetensors` |
| Denoise result | Plain img2img: `0.25` weak, `0.35`/`0.45` drift details. Canny ControlNet fixed: `0.35` best tradeoff, still modest lift; `0.45` begins artifacts. |
| Continuous-frame result | 48 character frames at Canny ControlNet `0.35`, avg 3.354s/frame, peak sampled VRAM 12973 MB; recomposed `before_after_2s.mp4` successfully. |
| Product shape stability | Optional product keyframe test at `0.35`: outline mostly stable, but material/detail changes; protected composite restores original product pixels. |
| Text stability | PASS: text is post-overlaid after AI. |
| Subject stability | PARTIAL: ControlNet improves stability; subject-protected composite preserves identity best. |
| Flicker | PARTIAL: no catastrophic flicker in spot-check stills, but per-frame AI variation remains a risk. |
| Visual lift | FAIL: not strong enough to justify AI as the core product value. |
| Non-developer feedback | Not collected |
| Pass / Fail | FAIL |
| Blocking errors | Initial ComfyUI API unreachable until local server was started. Initial ControlNet outputs collapsed to edge maps because raw and control images shared filenames with `overwrite=true`; fixed by unique upload names. |
| Next decision | Pause/pivot AI-enhanced product positioning unless a stronger video-aware or better-masked method is validated. Keep ComfyUI out of production Web/FastAPI path. |

Known risks:

- The result is based on local visual inspection and generated comparison artifacts; required non-developer preference feedback was not collected.
- Processing projects to about 10.7 minutes of ComfyUI time for 8s/192 frames before other overhead.
- ComfyUI peak sampled VRAM reached 13.394 GB during the optional product keyframe test.
- Depth/normal structural output still needs a Blender 5.1-specific export path if those controls become required.

## AI Enhancement Feasibility Gate

Status: FAIL

Goal question: Can CineAnchor achieve visibly better AI-enhanced output than raw Blender Eevee while preserving subject stability, text stability, and acceptable processing time?

Conclusion: FAIL. Rendering without text and adding deterministic FFmpeg text after AI solves the text corruption failure mode, but the AI enhancement itself does not pass the product gate. Denoise `0.25` is the only plausible stability range, yet visual lift is weak. Denoise `0.35` and `0.50` provide a stronger AI look but visibly change character/product details and increase deformation risk.

| Field | Result |
|---|---|
| Commands run | Created isolated `spikes/ai_enhance_feasibility`; parsed PowerShell; compiled Python; checked ComfyUI API; rendered no-text character/product samples; extracted keyframes; ran ComfyUI denoise sweep at `0.25`, `0.35`, `0.50`; processed 48 continuous character frames at `0.25`; recomposed MP4s; ran ffprobe; generated comparisons. |
| Input assets | `spikes/render_json/input/hero.png`, `spikes/render_json/input/model.glb` |
| Output artifacts | `spikes/ai_enhance_feasibility/output/character_intro/raw_no_text.mp4`, `final_with_text_overlay.mp4`, `ai_enhanced_2s.mp4`, `ai_enhanced_2s_with_text.mp4`, `before_after_2s.mp4`, keyframe comparison PNGs under `output/*/comparisons/` |
| Render duration | character_intro no-text: 48.213s for 96 frames; product_orbit no-text: 19.510s for 48 frames |
| ComfyUI checkpoint | `RealVisXL_V5.0_Lightning_fp16.safetensors` |
| Workflow | `spikes/ai_enhance_feasibility/workflows/sdxl_img2img_api.json`; SDXL img2img, `steps=8`, `cfg=1.6` |
| Denoise result | `0.25`: stable but weak lift; `0.35`: visible subject/detail changes; `0.50`: unacceptable deformation/shape changes |
| Continuous-frame result | 48 character frames at `0.25`, avg 2.678s/frame, peak sampled VRAM 11809 MB; recomposed 2s MP4 successfully |
| Machine / GPU notes | NVIDIA GeForce RTX 5070 Ti, 16303 MB VRAM; ComfyUI 0.25.0; model remained resident around 9.3 GB after runs |
| Text stability | PASS: text is post-overlaid and readable |
| Subject stability | PARTIAL: acceptable only at weak `0.25`; stronger denoise alters subject/product details |
| Visual lift | FAIL: weak at stable denoise |
| Non-developer feedback | Not collected |
| Pass / Fail | FAIL |
| Blocking errors | Repo venv could not start ComfyUI because `sqlalchemy` was missing; system Python 3.12 started ComfyUI successfully. One Windows report-write permission issue happened after all 48 continuous frames were generated; script was patched with retry logic. |
| Next decision | Pause/pivot the AI-enhanced product direction unless a different AI method can show obvious lift without subject changes. Keep ComfyUI out of the production Web/FastAPI path. |

Known risks:

- The result is based on local visual inspection and generated comparison artifacts; non-developer preference feedback still needs separate collection if the direction is retried.
- The 48-frame run shows technical feasibility but not product-level value.
- The measured rate projects to roughly 8.6 minutes of ComfyUI time for an 8-second/192-frame character clip before overhead.
- ComfyUI VRAM residency remains a production scheduling risk.

## AI Enhancement Method Search (2026-06-24)

Status: ACTIVE — Method search R&D phase

After AI Enhancement Gate 1 (FAIL) and Gate 2 (FAIL), production hardening is
**paused**. The core dilemma remains unresolved: higher denoise produces more
visual lift but less stability, and no approach to date has broken this trade-off.

Next step: Structured multi-method search using a shared benchmark framework.

- Benchmark package created: `spikes/ai_benchmark/`
- Three method search spikes prepared:
  - `spike/ai-controlnet-structure-enhance` — ControlNet Depth/Normal/Canny
  - `spike/ai-layered-subject-protection` — AI background-only + subject compositing
  - `spike/ai-atmosphere-overlay` — AI-generated atmosphere/lighting overlay layer
- Full plan: `docs/ai_enhance_method_search_plan.md`
- Evaluation: Unified scorecard at `spikes/ai_benchmark/evaluation/scorecard_template.md`

Decision framework: If any method PASSES → proceed as AI-enhanced product.
If only PARTIAL → downgrade AI to auxiliary feature. If ALL FAIL → pause or
pivot CineAnchor's AI direction.

## AI ControlNet Structure Enhancement Spike (Method #3)

Status: PARTIAL (2026-06-24)

- **Branch:** `spike/ai-enhance-gate2-structure-control`
- **Goal:** Determine whether Canny/Depth/Normal/Lineart structure-controlled AI enhancement can make Blender output visibly better while preserving subject stability
- **Methods tested:** Canny (ComfyUI preprocessor), Depth (DepthAnythingV2), Normal (BAE), Lineart (LineartStandard), Plain img2img baseline — all at denoise 0.25/0.35/0.45
- **Checkpoint:** `RealVisXL_V5.0_Lightning_fp16.safetensors`; ControlNet: `diffusion_pytorch_model_promax.safetensors` (Union)
- **Key findings:**
  - **Lineart ControlNet is the best method** (new discovery): best edge preservation (edge ratio 1.046), best saturation retention, best temporal consistency (CV 0.056), same speed as Canny (3.3s/frame)
  - Depth/Normal ControlNet tested for first time via ComfyUI preprocessors (previous Gate 2 could not test them)
  - Structure control WORKS — edge ratio ≥ 1.02 for all methods vs 0.99 for plain img2img at denoise 0.45
  - Temporal consistency is excellent — both Canny (CV 0.070) and Lineart (CV 0.056) have smooth frame-to-frame transitions
  - **Saturation loss on character input is the primary blocker** — all methods reduce saturation by −0.04 to −0.07 vs raw Blender. The "cinematic" prompt mutes already-vibrant colors
  - Product behaves differently — AI ADDS saturation (+0.03 to +0.05) to desaturated GLB model scenes. Enhancement value is template-dependent
- **Result:** PARTIAL — Technical pipeline works; structure control prevents deformation; but visual lift is not strong enough for PASS. The saturation loss on character input undermines visual quality.
- **Decision:** PARTIAL
- **Recommendation:** Run one more narrow R&D cycle targeting prompt engineering to fix saturation loss; test Lineart on product. Hard timebox: 4 hours. If no improvement → downgrade AI to auxiliary feature.
- **Report:** `docs/spike_report_ai_controlnet_structure.md`
- **Scorecard:** `spikes/ai_controlnet_structure_enhance/scorecard_controlnet_structure.md`
- **Artifacts:** Comparison grids under `spikes/ai_controlnet_structure_enhance/output/*/comparisons/`; 2s videos under `output/videos/`; metrics scripts and report JSONs in spike directory

## AI Lineart Color Fix Spike (Prompt Engineering + Fixed Seed)

Status: PARTIAL — improving toward PASS (2026-06-24)

- **Branch:** `spike/ai-lineart-color-fix`
- **Goal:** Fix saturation loss and flicker from previous ControlNet spike through prompt engineering + fixed seed + color correction
- **Timebox:** ~2 hours (within 4-hour limit)
- **Methods tested:** 3 prompt variants (A: Game promo vivid, B: Color preservation, C: Minimal lift) × denoise 0.30/0.35 on character keyframes; fixed seed for temporal consistency; FFmpeg color correction at sat=1.25
- **Key findings:**
  - **Fixed seed eliminated flicker**: frame-to-frame MeanDiff dropped 72% (0.0127 → 0.0036)
  - **Variant A prompt reduced saturation loss 23%** (−0.0585 → −0.0475 baseline, −0.0615 → −0.0475 on continuous)
  - **Color correction halved saturation loss** (−0.0615 → −0.0299 with sat=1.25)
  - Variants B and C made saturation WORSE — generic "preserve colors" prompts are ineffective
  - Product sanity check passed — Lineart adds more saturation than previous Canny (+0.0369 vs +0.0323)
  - Processing: 3.2s/frame, 155s for 2s, estimated 10.3 min for 8s
- **Result:** PARTIAL — Technical quality is now production-grade (flicker solved, saturation recoverable). Decision hinges on human reviewer preference.
- **Decision:** PARTIAL (submit for human review; if ≥ 2 prefer AI version → upgrade to PASS)
- **Recommendation:** If reviewers prefer AI + colorfix → proceed with ControlNet integration. If not → close ControlNet, move to Layered Subject Protection.
- **Report:** `docs/spike_report_ai_lineart_color_fix.md`
- **Scorecard:** `spikes/ai_lineart_color_fix/scorecard_lineart_color_fix.md`
- **Artifacts:** Comparison videos under `spikes/ai_lineart_color_fix/output/videos/`; keyframe outputs under `output/*/keyframes/`

## Route 2: JSON-Driven Template Rendering

Status: PASS

Goal question: Can one JSON file drive template, asset path, camera motion, duration, fps, aspect ratio, title, and subtitle?

Conclusion: PASS for the current Spike scope. One Project JSON now drives `character_intro` from PNG and `product_orbit` from GLB using Blender Eevee plus FFmpeg.

| Field | Result |
|---|---|
| Commands run | Blender headless rendered `projects/character_intro.json` and `projects/product_orbit.json`; FFmpeg composed both MP4 files; ffprobe validated both outputs. |
| Input assets | `spikes/render_json/input/hero.png`, `spikes/render_json/input/model.glb` |
| Output artifacts | `spikes/render_json/output/character_intro/final.mp4`, `spikes/render_json/output/product_orbit/final.mp4` |
| Render duration | character_intro: 45.58s; product_orbit: 19.18s |
| FFmpeg duration | character_intro: 0.34s; product_orbit: 0.23s |
| Machine / GPU notes | Blender 5.1.2, Eevee (`BLENDER_EEVEE`). |
| JSON fields supported | `template`, `asset.type`, `asset.path`, `camera.motion`, `duration`, `fps`, `output.width`, `output.height`, `output.frames_dir`, `output.video_path`, `text.title`, `text.subtitle` |
| asset.path switch | PASS: PNG and GLB project files render different subjects without code changes. |
| text.title switch | PASS: rendered titles come from JSON (`New Hero Arrival`, `Product Orbit`). |
| aspect ratio switch | PASS: ffprobe confirmed 720x1280 and 1280x720 outputs. |
| duration / fps switch | PASS: 4s at 24fps produced 96 frames; 4s at 12fps produced 48 frames. |
| camera.motion switch | PASS: `dolly_in` and front-arc `orbit` camera animation were exercised. |
| ffprobe | PASS: both outputs are h264 MP4 files with expected resolution, duration, fps, and frame count. |
| Pass / Fail | PASS |
| Blocking errors | None. |
| Next decision | Route 2 is viable as a Spike. Keep the JSON shape provisional until more templates are validated. |

Known risks:

- `product_orbit` currently uses a front-arc orbit, not full 360-degree orbit, to keep the fixed stage and text readable.
- `prop_showcase` is outside this task's current scope.
- This Spike JSON is not the production schema.
- Render inputs and outputs are local runtime artifacts and are intentionally ignored by Git.

## Route 4: Web To Local Render Chain

Status: PASS

Goal question: Can a minimal web UI call FastAPI, trigger Blender JSON rendering, run FFmpeg composition, poll task status, and download the final MP4?

Conclusion: PASS for the current Spike scope. A static local page calls a FastAPI app, which generates a Route 2 Project JSON, runs Blender Eevee headless, runs FFmpeg composition, exposes task status, and returns the MP4 through a download endpoint.

| Field | Result |
|---|---|
| Commands run | Installed FastAPI/uvicorn into `.venv`; compiled `server/app.py` and `server/smoke_web_chain.py`; ran `server/smoke_web_chain.py`; ran ffprobe on both Web-generated MP4s. |
| Input assets | `spikes/render_json/input/hero.png`, `spikes/render_json/input/model.glb` |
| Output artifacts | `spikes/render_json/output/web/5e056af9c3294a8c8f91954e9a47b58f/final.mp4`, `spikes/render_json/output/web/73f8c80da1394e2bacb4cc4d3f0d4fc1/final.mp4` |
| Render duration | character_intro: 51.68s; product_orbit: 20.95s |
| FFmpeg duration | character_intro: 0.65s; product_orbit: 0.50s |
| Machine / GPU notes | Blender 5.1.2, Eevee (`BLENDER_EEVEE`), FFmpeg 8.1.1 Gyan build. |
| API endpoints | `POST /api/render`, `GET /api/render/{task_id}`, `GET /api/render/{task_id}/download` |
| Status transitions | PASS: poll observed `RENDERING -> COMPOSITING -> DONE` for both templates. |
| Download | PASS: API download returned MP4 bytes for both templates. |
| Failure response | PASS: invalid template returned HTTP 400 with `error_code=UNSUPPORTED_TEMPLATE`. |
| ffprobe | PASS: character output is h264 720x1280, 24fps, 4s, 96 frames; product output is h264 1280x720, 12fps, 4s, 48 frames. |
| Pass / Fail | PASS |
| Blocking errors | None for the web-to-render chain. Persistent background server launch from this Codex shell was unreliable; foreground uvicorn and in-process HTTP smoke validation worked. |
| Next decision | Route 4 is viable as a Spike. Keep the task store in-memory until production queue requirements are validated. |

Known risks:

- In-memory task state is lost on server restart.
- No queue, cancellation, concurrency policy, or database exists in this Spike.
- Runtime sample assets and generated outputs are ignored by Git and must exist locally.
- `BLENDER_PATH` and `FFMPEG_PATH` must be configured per machine.
- The current Project JSON remains provisional Spike schema.

## Route 3: ComfyUI Conservative AI Enhancement

Status: PARTIAL

Goal question: Can Route 3 be included in V0.1 as conservative AI enhancement without subject deformation, text corruption, flicker, or unacceptable processing time?

Conclusion: PARTIAL. Direct full-frame img2img over final frames failed because it corrupted rendered subtitle text. Conservative ComfyUI reference plus FFmpeg enhancement works end-to-end and final MP4s remain stable because ComfyUI frames are not used as final frames. Text and subject/product shape are stable. However, the visual improvement is light, so Route 3 should be treated as an optional V0.1 preset rather than a core selling point.

### Previous direct full-frame img2img: FAIL

Direct full-frame SDXL img2img processed extracted keyframes successfully, but corrupted the `character_intro` subtitle in 4 of 4 reviewed frames. This validates the V0.1 decision to exclude full-frame AI video regeneration and to keep text-bearing final frames in Blender/FFmpeg output.

### Conservative ComfyUI reference + FFmpeg enhancement: PARTIAL

| Field | Result |
|---|---|
| Commands run | Created `spike/comfy-lut-enhance`; parsed PowerShell scripts; compiled Python scripts; extracted keyframes; ran ComfyUI reference workflow; analyzed color parameters; applied FFmpeg enhancement; generated comparisons; ran ffprobe on enhanced MP4s. |
| Input assets | `spikes/render_json/output/web/5e056af9c3294a8c8f91954e9a47b58f/final.mp4`, `spikes/render_json/output/web/73f8c80da1394e2bacb4cc4d3f0d4fc1/final.mp4` |
| Output artifacts | `spikes/comfy_lut_enhance/output/character_intro/enhanced_ffmpeg.mp4`, `spikes/comfy_lut_enhance/output/product_orbit/enhanced_ffmpeg.mp4`, raw/reference/comparison images under `spikes/comfy_lut_enhance/output/*/`, `spikes/comfy_lut_enhance/output/color_params.json` |
| ComfyUI URL | `http://127.0.0.1:8188` |
| Workflow | `spikes/comfy_lut_enhance/workflows/conservative_sdxl_reference_api.json` |
| Model / checkpoint notes | ComfyUI checkpoint `RealVisXL_V5.0_Lightning_fp16.safetensors`; workflow settings `steps=6`, `cfg=1.4`, `denoise=0.08`. |
| Per-frame processing time | character_intro: 2.500s, 2.160s, 2.177s, 2.191s; product_orbit: 2.143s, 2.150s, 2.199s, 2.191s. |
| Machine / GPU notes | NVIDIA GeForce RTX 5070 Ti, 16303 MB VRAM; about 8989 MB used before ComfyUI reference run; sampled peak 9306 MB; about 8944 MB after run. |
| Color parameters | character_intro: brightness 0.0024, contrast 0.986, saturation 0.95, gamma 0.9988; product_orbit: brightness 0.0035, contrast 0.9806, saturation 1.0197, gamma 0.9982. |
| FFmpeg filters | `eq` plus `unsharp=5:5:0.32:3:3:0.12`; exact filter strings are recorded in `docs/spike_report_comfy_lut.md`. |
| ffprobe | PASS: character output is h264 720x1280, 24fps, 4s, 96 frames; product output is h264 1280x720, 12fps, 4s, 48 frames. |
| Visual review | Final FFmpeg output preserves text and subject/product shape. Improvement is mostly subtle sharpening and slight color adjustment. |
| Pass / Fail | PARTIAL |
| Blocking errors | One script bug in PowerShell JSON array loading was fixed; no remaining blocker in the conservative Route 3 chain. |
| Next decision | Keep full-frame AI video regeneration excluded from V0.1. Keep conservative FFmpeg/LUT enhancement as an optional preset only. |

Known risks:

- This is not a true LUT solver; it estimates broad video-wide parameters.
- ComfyUI reference images can still corrupt text and must not become final frames.
- Visual lift is too mild to position as a core V0.1 AI feature or portfolio selling point.
- ComfyUI retains GPU memory and may conflict with Blender if run concurrently.
- Non-developer feedback for conservative Route 3 has not been collected yet; manual review remains pending.

## AI Layered Multipass Composite Probe

Status: **PASS**

Branch: `spike/ai-layered-multipass-composite-probe`
Report: `docs/spike_report_ai_layered_multipass_composite.md`

Goal: Validate that CineAnchor can split frames into separate layers (background, subject, text) and protect subject/text pixels while modifying only the background — enabling safe AI background enhancement.

Conclusion: **PASS.** The mask-based approach works perfectly: render the full composite, then render subject-only and text-only passes to extract alpha masks. Use these masks to protect pixels during background modification. All subject and text pixels remain byte-identical (max_diff = 0.0) while background modifications are successfully applied.

Key findings:
- Layer-by-layer color recomposition is NOT lossless (PSNR ~35 dB vs 45 dB target) due to Eevee's non-linear Filmic transforms, premultiplied alpha, and lighting interactions — this is expected and documented
- Mask-based pixel protection IS lossless — subject and text max_diff = 0.0 for all frames, both templates, all modification methods
- Cryptomatte is available in Eevee but cannot be exported via compositor (File Output node restricted to OPEN_EXR_MULTILAYER which is non-functional in Blender 5.1.2)
- Visibility toggling is the practical workaround for mask generation
- Eevee is sufficient — no Cycles needed
- Rendering is 100% deterministic (pixel-identical across runs)
- Performance overhead: +29% for character_intro (in budget ≤50%), +81% for product_orbit (over budget but low absolute overhead of +44s for 8s render)
- Text safety (A3): PASS — zero-diff in all text pixels
- Subject safety (A4): PASS — zero-diff in all subject pixels including edges

Product recommendation: **PROCEED to background AI enhancement testing.** The mask-based infrastructure is validated. Wire AI enhancement (ComfyUI, ControlNet, etc.) to the background region only, using subject+text masks for protection.

| Field | Result |
|---|---|
| Templates tested | character_intro (PNG), product_orbit (GLB) |
| Pass support | Alpha: YES, Object mask: PARTIAL (Cryptomatte export blocked, visibility toggling works), Depth/Z: YES, Normal: YES |
| Recomposition (color) | FAIL — non-linear transforms prevent lossless layer compositing |
| Recomposition (mask) | PASS — 100% pixel-identical protection |
| A3 Text safety | PASS |
| A4 Subject safety | PASS |
| A5 Reproducibility | PASS — 100% pixel-identical across runs |
| A6 Performance | PARTIAL — character_intro +29%, product_orbit +81% |
| Final decision | PASS |
| Link to report | `docs/spike_report_ai_layered_multipass_composite.md` |

## Dolly Out Camera + Ember Particles

Status: **PARTIAL** (camera PASS, particles FAIL)

Branch: (on `spike/ai-layered-multipass-composite-probe`, to be separated)
Plan/Report: `docs/cineanchor_dolly_ember_plan.md`

### Dolly Out Camera: ✅ PASS

Backward-zooming camera (`motion: "dolly_out"`) with configurable speed (0.1–3.0). Constant-speed via LINEAR interpolation on both `camera` and `camera.data` keyframes. Backward-compatible — old `dolly_in`/`orbit` output 100% pixel-identical.

### Ember Particles: ❌ FAIL

Attempted to add fire-spark particles rising/floating around the subject. Four iterations tried:
- A. OBJECT mode tiny spheres → coverage 0.04% (invisible)
- B. OBJECT mode larger spheres → coverage 0.07% (still invisible — likely occluded/out-of-frame)
- C. PATH mode high-speed → coverage 0.2% (particles zip through frame in 5-6 frames)
- D. PATH mode slow-speed → coverage 3-5% (pixels present but visual effect underwhelming)

**Root cause:** Eevee ortho camera fundamentally limits particle visibility — no perspective scaling, PATH rendering produces uniform-thin lines without glow falloff, motion blur on particle paths is not functional in Blender 5.1.2, and bloom cannot differentiate particles from scene highlights.

**Recommendation:** Do not pursue Eevee particle-based embers further. If embers are needed, use Cycles for the particle layer or FFmpeg sprite-sheet overlay.

| Field | Result |
|---|---|
| Camera dolly_out | PASS |
| Camera regression | PASS — 100% pixel-identical |
| Particles visibility | FAIL — max 5% coverage, no streak effect |
| Motion blur streaks | FAIL — not functional on PATH particles in Eevee |
| Schema changes | DONE — `CameraMotion.dolly_out`, `ParticlesSpec` added |
| Tests added | 4 schema tests PASS |
| Final decision | Camera: PASS / Particles: FAIL — record only |
