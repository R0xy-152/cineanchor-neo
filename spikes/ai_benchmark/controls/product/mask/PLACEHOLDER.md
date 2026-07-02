# Subject Mask — Product

## Status

**Available** from Gate 2: `spikes/ai_enhance_gate2/output/product_orbit/mask/`

Product masks were rendered by Gate 2's `render_structural.py` using the same
material override approach as character masks.

## Generation Method

Same as character: `spikes/ai_enhance_gate2/render_structural.py` overrides all
materials to white emissive with black background.

```powershell
.\.venv\Scripts\python.exe spikes\ai_enhance_gate2\render_structural.py `
  --template product_orbit `
  --asset-path samples/assets/model.glb `
  --output <output_dir> `
  --duration 2 --fps 24 --no-text
```

## Expected Format

- PNG, same resolution as input (1280×720 for product)
- White (255,255,255) = product pixels
- Black (0,0,0) = background / non-product pixels

## Notes for Product Orbit

Unlike the character which is a flat plane, the product is a 3D GLB model.
The mask shape changes across frames as the camera orbits — per-frame masks
are essential for temporal compositing.
