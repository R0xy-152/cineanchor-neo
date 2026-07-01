# Normal Map — Product

## Status

**BLOCKED** — Same Blender 5.1.2 OPEN_EXR_MULTILAYER limitation as character.

## Workarounds

Same as character: upgrade Blender, use monocular normal estimation, or
use ComfyUI built-in normal preprocessor.

## Notes for Product Orbit

For 3D product models (GLB), normal maps are especially relevant because
surface orientation changes continuously as the camera orbits. A normal
ControlNet could help preserve 3D surface detail during enhancement.
