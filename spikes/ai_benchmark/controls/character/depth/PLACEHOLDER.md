# Depth Map — Character

## Status

**BLOCKED** — Blender 5.1.2 does not support OPEN_EXR_MULTILAYER output format.
Depth pass cannot be rendered from the current Blender build.

## Workarounds (untested)

1. **Upgrade Blender** — Blender 5.2+ may restore OPEN_EXR_MULTILAYER support.
   If available, enable Z-pass in View Layer Properties → Passes → Data → Z,
   then output as OpenEXR Multilayer.

2. **Depth estimation model** — Use a monocular depth estimation model
   (e.g. Depth Anything v2, ZoeDepth) on raw RGB frames to generate depth maps
   without requiring Blender Z-pass.

3. **ComfyUI Depth ControlNet preprocessor** — ComfyUI's built-in depth
   preprocessor can generate depth maps from RGB input without needing an
   external depth pass.

## Expected Format

- PNG or EXR, same resolution as input (720×1280 for character)
- Grayscale: lighter = closer to camera, darker = farther
- 16-bit preferred for depth precision; 8-bit acceptable for ControlNet

## For New Method Agents

If your method requires depth control, prefer ComfyUI's built-in depth
preprocessor over attempting to extract depth from Blender 5.1.
