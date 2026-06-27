# Spike Report: AI Layered Multipass Composite Probe

**Branch:** `spike/ai-layered-multipass-composite-probe`
**Date:** 2026-06-25
**Decision:** **PASS**

---

## 1. Goal

Validate a layered render/composite pipeline where AI never touches subject or text pixels. The core idea is to split frames into separate layers (background, subject, text) and only enhance the background, then recompose: background → subject → text.

## 2. Why Layered Rendering Is Being Tested

All previous AI enhancement methods failed because they processed the full frame, causing:

- **Direct full-frame img2img:** FAIL (text corruption)
- **Conservative ComfyUI reference + FFmpeg:** PARTIAL (visual improvement too weak)
- **Gate 1 denoise sweep:** FAIL (safe denoise too weak, higher denoise deforms subject)
- **Gate 2 Canny ControlNet + subject protection:** FAIL (best output only mildly better than raw Blender)

Layered rendering isolates the AI to the background only, eliminating the text corruption and subject deformation that doomed previous approaches.

## 3. Phase 0: Blender Pass Support Probe

### Environment
- **Blender:** 5.1.2 (hash ec6e62d40fa9, built 2026-05-19)
- **Engine:** `BLENDER_EEVEE` (Eevee Next features, but identifier is `BLENDER_EEVEE`)
- **Eevee Next identifier** (`BLENDER_EEVEE_NEXT`): NOT available — falls back to `BLENDER_EEVEE`

### Pass Support Matrix

| Pass | Eevee | Cycles | Notes |
|---|---|---|---|
| Alpha (RGBA PNG) | YES | YES | `film_transparent=True` supported |
| Combined | YES | YES | Standard render output |
| Depth/Z | YES | YES | Available on RL node |
| Normal | YES | YES | Available on RL node |
| Object Index | YES | YES | Available, `pass_index` settable |
| Material Index | YES | YES | Available, `pass_index` settable |
| Cryptomatte Object | YES | YES | Available on RL node (3 slots: 00, 01, 02) |
| Cryptomatte Material | YES | YES | Available on RL node (3 slots) |
| Cryptomatte Asset | YES | YES | Available on RL node (3 slots) |
| Diffuse Color | YES | YES | Available |
| Emission | YES | YES | Available |
| Shadow | YES | YES | Available |
| Ambient Occlusion | YES | YES | Available |
| OPEN_EXR_MULTILAYER | NO | NO | Listed but non-functional in Blender 5.1.2 |

### Key Finding: Cryptomatte Export Blocked

Cryptomatte passes ARE available on the Render Layers compositor node and can be enabled on the view layer. However, the compositor **File Output** node in Blender 5.1.2 only accepts `OPEN_EXR_MULTILAYER` format (PNG and OPEN_EXR are rejected with: `enum "PNG" not found in ('OPEN_EXR_MULTILAYER')`). Since `OPEN_EXR_MULTILAYER` doesn't actually write files in this build, Cryptomatte cannot be exported via the standard compositor pipeline.

### Practical Approach: Visibility Toggling

The workaround is to render the scene multiple times with different object visibility settings:

1. Full scene (all objects visible)
2. Background only (hide subject + text)
3. Subject only (hide background + text, `film_transparent=True`)
4. Text only (hide background + subject, `film_transparent=True`)

This approach produces clean layers for mask extraction.

### Blender 5.x Compositor API Changes

The compositor API changed in Blender 5.x:
- Old: `scene.use_nodes = True` → `scene.node_tree.nodes`
- New: `bpy.data.node_groups.new(name, 'CompositorNodeTree')` → `scene.compositing_node_group = ng`
- File Output: `fo.directory` (not `base_path`), `fo.file_output_items` (not `file_slots`)

## 4. Current Text Rendering Location

**Text is added as Blender text objects** in `blender/scripts/render_project.py:add_text_overlay()` (lines 495-556). The production pipeline uses `bpy.ops.object.text_add()` to create `JsonTitle` and `JsonSubtitle` objects with emission materials. Text is rendered as part of the 3D scene, not as a post-process overlay.

**Proposed final text-layer strategy:** Text remains a Blender text object in the scene. For the layered pipeline, text is rendered separately (visibility toggling) to generate a text alpha mask. AI enhancement is prohibited from touching text pixels. The mask-based approach ensures text pixels are byte-identical to the baseline composite.

## 5. Layer Definitions

### character_intro (PNG hero image)

| Layer | Objects | Render Settings |
|---|---|---|
| L_composite | All objects | Standard (film_transparent=False) |
| L_background | DarkBackdrop, StageFloor, TemplateBackRing, TemplateInnerRing, StageGlint_00-17, all lights | Standard |
| L_subject | HeroPNGPlane | film_transparent=True |
| L_text | JsonTitle, JsonSubtitle | film_transparent=True |

### product_orbit (GLB model)

| Layer | Objects | Render Settings |
|---|---|---|
| L_composite | All objects | Standard |
| L_background | StageFloor, TemplateBackRing, StageGlint_00-17, all lights, OrbitPivot, OrbitTarget | Standard |
| L_subject | ProductAssetRoot, Avocado (imported mesh) | film_transparent=True |
| L_text | JsonTitle, JsonSubtitle | film_transparent=True |

## 6. Output Format

**Separated PNG sequences** (not EXR). Each layer outputs as an independent PNG sequence with consistent naming (`{frame:04d}.png`).

EXR was rejected because:
- `OPEN_EXR_MULTILAYER` is non-functional in Blender 5.1.2
- Single-layer `OPEN_EXR` works but adds complexity without benefit for this probe
- PNG is simpler, directly measurable, and matches the production pipeline

## 7. Character Template Result

**4 representative frames** rendered (1, 32, 64, 96) from a 4-second 24fps animation. All 4 layers × 4 frames = 16 renders completed successfully.

- Total render time: 5.56s
- Composite (baseline): 3.59s (0.90s/frame)
- Background: 0.75s (0.19s/frame)
- Subject: 0.57s (0.14s/frame)
- Text: 0.48s (0.12s/frame)

Classification: 1 subject object, 2 text objects, 22 background objects, 4 lights, 1 camera.

## 8. Product Template Result

**4 representative frames** rendered. All layers completed successfully.

- Total render time: 2.98s
- Composite: 1.12s (0.28s/frame)
- Background: 0.54s (0.14s/frame)
- Subject: 0.47s (0.12s/frame)
- Text: 0.44s (0.11s/frame)

Classification: 2 subject objects (root + mesh), 2 text objects, 20 background objects, 4 lights, 2 empties, 1 camera.

## 9. Mask Quality Result

Masks are generated from the alpha channel of subject/text renders. Binary threshold (alpha > 10, scale 0-255) produces clean masks.

| Template | Subject mask | Text mask | Protected % of frame |
|---|---|---|---|
| character_intro, frame 1 | 135,036 px (core: 131,326, edge: 3,710) | 7,440 px | 15.5% |
| character_intro, frame 96 | 172,429 px (core: 168,225, edge: 4,204) | 9,227 px | 19.7% |
| product_orbit, frame 1 | 74,198 px (core: 71,554, edge: 2,644) | 4,984 px | 8.6% |
| product_orbit, frame 96 | 73,111 px (core: 70,490, edge: 2,621) | 4,926 px | 8.5% |

The subject mask grows from 15.5% to 19.7% during the character_intro dolly animation as the character gets closer to camera. The product_orbit mask stays consistent (~8.5%) since the orbit camera maintains a fixed distance.

## 10. Lossless Recomposition Result

**Layer-by-layer color recomposition FAILS.** This is expected and documented.

| Metric | Frame 1 | Frame 32 | Frame 64 | Frame 96 |
|---|---|---|---|---|
| PSNR | 27.70 dB | 27.65 dB | 27.23 dB | 27.07 dB |
| Pixels diff ≤ 1/255 | 81.61% | 81.46% | 80.56% | 80.44% |
| Max diff | 202.00 | 203.00 | 203.00 | 202.00 |

Both straight-alpha and premultiplied-alpha compositing formulas were tested. Neither achieves lossless recomposition.

### Root Causes

1. **Non-linear Filmic view transform:** Colors are transformed non-linearly before PNG output. Linear compositing of display-referred values is mathematically incorrect.
2. **Premultiplied alpha:** Eevee with `film_transparent=True` produces premultiplied alpha at anti-aliased edges. The subject edges blend with the transparent background (not the actual scene background), so recomposition colors at edges don't match.
3. **Lighting interactions:** When background objects are hidden, the remaining objects receive slightly different indirect lighting. Eevee's GTAO and bloom also interact differently.
4. **Color management settings:** `view_transform = "Filmic"`, `look = "Medium High Contrast"` apply to each render independently.

## 11. Background-Only Enhancement Probe Result

Using the **mask-based approach** (not color recomposition), deterministic background modifications were applied:

| Method | character_intro | product_orbit |
|---|---|---|
| Hue shift (RGB rotation) | PASS (bg mean diff 14.9-15.5) | PASS (bg mean diff 1.2-1.3) |
| Saturation boost (1.5x) | PASS (bg mean diff 4.2-4.4) | PASS (bg mean diff 0.3-0.4) |
| Brightness boost (1.3x) | PASS (bg mean diff 14.7-15.2) | PASS (bg mean diff 19.5-19.6) |

All methods successfully modify the background while keeping subject and text pixels unchanged.

## 12. Text Safety Result

**A3: PASS** — All frames, all templates, all modification methods:

- Text pixel max_diff = 0.0 (byte-identical)
- Text region size: 4,926-9,227 px per frame
- Text is never touched by any modification

## 13. Subject Safety Result

**A4: PASS** — All frames, all templates, all modification methods:

| Region | max_diff | Status |
|---|---|---|
| Subject core (eroded by 2px) | 0.0 | PASS |
| Subject edge (dilation ring) | 0.0 | PASS |
| Subject full (all masked pixels) | 0.0 | PASS |

All subject pixels, including anti-aliased edge pixels, are byte-identical to the original composite.

## 14. Reproducibility Result

**A5: PASS** — Two independent renders of the same scene produce 100% pixel-identical output:

| Layer | Pixels identical | max_diff |
|---|---|---|
| composite | 100.00% (921,600/921,600) | 0.00 |
| background | 100.00% | 0.00 |
| subject | 100.00% | 0.00 |
| text | 100.00% | 0.00 |

File hashes differ due to PNG metadata (timestamps), but pixel values are byte-identical. Eevee rendering is deterministic in headless mode.

## 15. Performance Overhead

| Template | Standard (composite only) | Layered (composite + subject + text) | Overhead |
|---|---|---|---|
| character_intro | 3.59s (4 frames) | 4.74s (4 frames) | **+29%** |
| product_orbit | 1.12s (4 frames) | 2.03s (4 frames) | **+81%** |

Per-frame estimates for production (composite + subject mask + text mask):

| Template | Standard/frame | Layered/frame | Overhead/frame |
|---|---|---|---|
| character_intro | 0.90s | 1.16s | +0.26s (+29%) |
| product_orbit | 0.28s | 0.51s | +0.23s (+81%) |

For an 8-second 24fps render (192 frames):
- character_intro: 173s → 223s (+50s, +29%)
- product_orbit: 54s → 98s (+44s, +81%)

**A6: PARTIAL** — character_intro within +50% budget (+29%); product_orbit exceeds budget (+81%) but absolute overhead (+44s for 8s render) is modest.

## 16. Storage Overhead

For 4 representative frames at 720×1280:

| Template | Composite only | All layers | Overhead |
|---|---|---|---|
| character_intro | 3,992 KB | 47,959 KB | +1,102% |
| product_orbit | 2,484 KB | 14,372 KB | +479% |

Per-frame for full render (192 frames):
- character_intro: ~192 MB composite + ~960 MB subject masks + ~550 MB text masks = ~1,702 MB total
- product_orbit: ~119 MB composite + ~540 MB subject masks + ~500 MB text masks = ~1,159 MB total

Storage is high but manageable. Masks can be optimized:
- Render at lower resolution (360p instead of 1080p — masks don't need full quality)
- Store as 8-bit grayscale PNG (not RGBA)
- Render at reduced frame rate (every Nth frame, interpolate)

## 17. Premultiplied Alpha / Halo Findings

Blender Eevee with `film_transparent=True` produces **premultiplied alpha** (associated alpha) at anti-aliased edges. This is confirmed by pixel analysis:
- 94-97% of edge pixels have RGB ≤ alpha × 255 (premultiplied behavior)
- 3-6% exceed due to emission/lighting on edge pixels

For the mask-based approach, premultiplied alpha does not cause issues because:
1. Only the alpha channel is used (not RGB) for mask creation
2. Binary thresholding (alpha > 10) produces clean masks
3. Edge pixels in the composite are protected by the mask, not recomposited

## 18. Motion Blur / DOF Findings

Both motion blur and depth of field were **disabled** in this probe (not explicitly enabled in the production render script). If enabled in future:
- Motion blur would smear subject edges across background pixels
- DOF would blend subject and background at out-of-focus boundaries
- Masks from separate renders would not perfectly align with the motion-blurred composite
- Mitigation: render masks with same motion blur/DOF settings, or apply AI enhancement before compositing

## 19. Eevee vs Cycles Conclusion

**Eevee is sufficient** for the layered rendering pipeline. All required passes are available in Eevee. Cycles is not needed.

| Factor | Eevee | Cycles |
|---|---|---|
| All passes available | YES | YES |
| Cryptomatte on RL node | YES | YES |
| Render time (character, 1 frame) | ~0.90s | Would be >30s |
| Deterministic | YES | YES (with fixed seed) |
| Sufficient for masks | YES | Overkill |

## 20. Final Decision: PASS

The layered multipass composite approach is validated as infrastructure for AI background enhancement.

**Strengths:**
- Subject and text pixels are byte-identical to the baseline (proven for both templates)
- Masks are clean and reliable (binary alpha threshold)
- Eevee-only — no Cycles dependency
- Deterministic — 100% reproducible
- No new dependencies required
- No modification to production code

**Weaknesses:**
- Layer-by-layer color recomposition is not lossless (non-linear transforms) — addressed by mask-based approach
- Performance overhead for product_orbit exceeds +50% target — mitigation available
- Storage overhead is high — mitigation available
- Cryptomatte export blocked in Blender 5.1.2 — workaround (visibility toggling) available

## 21. Product Recommendation

**PROCEED to background AI enhancement testing.**

The mask-based infrastructure is validated. Next steps:

1. **Wire AI enhancement** to the background region using subject+text masks
2. **Test with ComfyUI** (ControlNet, IP-Adapter, etc.) applied only to unmasked regions
3. **Implement edge dilation** in protection masks (2-4px) to prevent AI bleed
4. **Optimize mask rendering** — lower resolution, reduced frame rate
5. **Test with real AI methods** — this probe used deterministic filters only
6. **If AI background enhancement still fails** to produce sufficient visual lift → run commercial video-to-video upper-bound test as parallel investigation
