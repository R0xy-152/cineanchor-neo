# Layered Multipass Composite Probe

Branch: `spike/ai-layered-multipass-composite-probe`

## Goal

Validate that CineAnchor can split frames into separate layers (background, subject, text) and protect subject/text pixels while modifying only the background — enabling safe AI background enhancement.

## Quick Results

| Metric | Result |
|---|---|
| A1 Subject mask IoU (PNG) | TBD (needs ground truth alpha) |
| A2 Lossless recomposition | N/A (separate renders can't losslessly recombine due to Eevee non-linear transforms) |
| A3 Text safety | **PASS** — zero-diff in text region |
| A4 Subject safety | **PASS** — zero-diff in subject region (including edges) |
| A5 Reproducibility | **PASS** — 100% pixel-identical across runs |
| A6 Performance (character_intro) | +29% overhead (in budget) |
| A6 Performance (product_orbit) | +81% overhead (over budget) |
| Final decision | **PASS** |

## Approach

### Correct Pipeline (mask-based)

```
1. Render composite frame (all objects, standard render)
2. Render subject-only with film_transparent → extract alpha mask
3. Render text-only with film_transparent → extract alpha mask
4. Apply AI enhancement to background region only (masked by subject+text)
5. Keep subject and text pixels byte-identical to composite
```

### What Does NOT Work

- **Layer-by-layer recomposition** (background → subject → text) fails because:
  - Eevee uses non-linear Filmic view transform
  - Separate renders have different lighting interactions
  - Premultiplied alpha edges blend with different backgrounds
  - PSNR ~27-35 dB, far below 45 dB threshold

### What DOES Work

- **Mask-based protection**: Render subject/text separately to get alpha masks
- Use masks to protect pixels in the original composite frame
- Modify only background regions
- 100% byte-level safety for subject and text pixels

## Pass Support Probe Results

| Pass | Eevee | Notes |
|---|---|---|
| Alpha (RGBA PNG) | YES | film_transparent=True produces premultiplied alpha |
| Object mask (Cryptomatte) | PARTIAL | Available on RL node but can't export via File Output (format restriction) |
| Object Index | YES | Available but same export limitation |
| Depth/Z | YES | Available but same export limitation |
| Normal | YES | Available but same export limitation |
| OPEN_EXR_MULTILAYER | NO | Listed but not functional in Blender 5.1.2 |
| Eevee sufficient | YES | No Cycles needed |
| Cycles required | NO | All passes available in Eevee |

Key finding: Blender 5.1.2 identifies engine as `BLENDER_EEVEE` (not `BLENDER_EEVEE_NEXT`), but uses Eevee Next features. Cryptomatte is available on the Render Layers compositor node. The compositor File Output node only accepts `OPEN_EXR_MULTILAYER` format, which cannot actually write files in this Blender build — preventing Cryptomatte/Depth/Normal export via the compositor.

The practical workaround is **visibility toggling** (render scene multiple times with different object visibility) to generate masks.

## Files

| File | Purpose |
|---|---|
| `probe_pass_support.py` | Phase 0: Blender pass availability probe |
| `probe_pass_support_deep.py` | Phase 0b: Deep pass rendering test (Cryptomatte, formats, compositor API) |
| `render_layers.py` | Phases 1-2: Build scene, classify objects, render layers with visibility toggling |
| `composite_layers.py` | Phase 3: Attempt lossless recomposition (FAILED — documented why) |
| `measure_recompose.py` | Phases 4-5: Mask-based enhancement probe (PASSED) |
| `project_character_intro.json` | Character intro project config |
| `project_product_orbit.json` | Product orbit project config |

## Output Structure

```
output/
├── probe/                    # Phase 0 probe outputs
├── character_intro/          # Character intro render
│   ├── composite/            # Full scene composite frames
│   ├── background/           # Background-only frames
│   ├── subject/              # Subject-only frames (with alpha)
│   ├── text/                 # Text-only frames (with alpha)
│   └── report/               # Measurement reports + enhanced frames
├── product_orbit/            # Product orbit render
│   ├── composite/
│   ├── background/
│   ├── subject/
│   ├── text/
│   └── report/
├── character_intro_run2/     # Reproducibility verification
└── probe/                    # Phase 0/0b results
```

All media under `output/` is gitignored.

## Known Issues

1. **Alpha premultiplication**: Blender Eevee with `film_transparent=True` outputs premultiplied alpha at anti-aliased edges. Compositing must use premultiplied over operator.
2. **Halo risk**: If AI enhancement near subject edges bleeds into edge pixels, it could create halos. Use dilated protection masks.
3. **Motion blur / DOF**: Disabled in this probe. If enabled, they would mix subject and background at boundaries, requiring more sophisticated mask extraction.
4. **Color management**: Filmic view transform is non-linear. Layer colors cannot be linearly combined from separate renders.
5. **Performance on product_orbit**: Overhead exceeds +50% budget. Mitigation: render masks at lower resolution or at reduced frame rate.
