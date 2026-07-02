# Depth Map — Product

## Status

**BLOCKED** — Same Blender 5.1.2 OPEN_EXR_MULTILAYER limitation as character.

## Workarounds

Same as character: upgrade Blender, use monocular depth estimation model,
or use ComfyUI built-in depth preprocessor.

## Expected Format

- PNG or EXR, same resolution as input (1280×720 for product)
- Grayscale: lighter = closer to camera, darker = farther

## Notes for Product Orbit

Product orbit has a known camera path (front-arc rotation around the model).
The depth map will vary significantly frame-to-frame as the camera orbits.
A single representative depth map may not suffice — consider generating
per-frame depth maps if using depth for temporal processing.
