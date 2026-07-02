# Subject Mask — Character

## Status

**Available** from Gate 2: `spikes/ai_enhance_gate2/output/character_intro/mask/`
(96 frames, 720×1280, rendered by Blender material override)

Also available as continuous frames:
`spikes/ai_enhance_gate2/output/character_intro/continuous/mask/0001.png` … `0048.png`

## Generation Method

Gate 2's `render_structural.py` renders masks by overriding all materials to emit
white for the subject and setting the background to black. The subject (character
plane with alpha-textured PNG) renders as white silhouette; everything else is black.

```python
# Key lines from render_structural.py:
# - Override all materials to white emissive
# - Set world/background to black
# - Render pass outputs pure subject silhouette
```

The script is at `spikes/ai_enhance_gate2/render_structural.py`.

## Expected Format

- PNG, same resolution as input (720×1280 for character)
- White (255,255,255) = subject pixels
- Black (0,0,0) = background / non-subject pixels
- No alpha channel needed (binary mask)

## For New Method Agents

Masks are used for:
- **Subject protection compositing**: paste original subject back over AI-enhanced background
- **ControlNet inpaint**: restrict AI enhancement to background only
- **Alpha compositing**: blend AI and original with per-pixel weights

To regenerate masks for different frames or settings:

```powershell
.\.venv\Scripts\python.exe spikes\ai_enhance_gate2\render_structural.py `
  --template character_intro `
  --asset-path samples/assets/hero.png `
  --output <output_dir> `
  --duration 2 --fps 24 --no-text
```

This outputs both `rgb/` and `mask/` frame directories.
