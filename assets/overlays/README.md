# Overlay Assets

Deterministic overlay assets for post-render compositing.

**These are NOT AI-generated.** All assets are produced by deterministic Blender particle systems
or procedural shaders, rendered once and checked in as pre-built media.

## Contents

| File | Description | Source |
|------|-------------|--------|
| `embers_default.mp4` | Warm orange ember particles rising, 2s loop, 1080p, 24fps | `blender/scripts/generate_overlays.py` |
| `bokeh_default.mp4` | Soft white bokeh circles drifting, 2s loop, 1080p, 24fps | `blender/scripts/generate_overlays.py` |

## Regeneration

To regenerate all overlays:

```powershell
$env:BLENDER_PATH = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $env:BLENDER_PATH --background --python blender/scripts/generate_overlays.py
```

Output lands in this directory.

## Usage in Pipeline

Overlays are composited via FFmpeg `blend=all_mode=screen` in the post-render step.
All tuning parameters (speed, opacity, color) are applied at compositing time without
re-rendering the 3D scene.
