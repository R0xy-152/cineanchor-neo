# Normal Map — Character

## Status

**BLOCKED** — Blender 5.1.2 does not support OPEN_EXR_MULTILAYER output format.
Normal pass cannot be rendered from the current Blender build.

## Workarounds (untested)

1. **Upgrade Blender** — Blender 5.2+ may restore OPEN_EXR_MULTILAYER support.
   Enable Normal pass in View Layer Properties → Passes → Data → Normal.

2. **Normal estimation model** — Use a monocular normal estimation model
   on raw RGB frames (e.g. metric3D, Omnidata, or DSINE).

3. **ComfyUI Normal ControlNet preprocessor** — The ComfyUI ControlNet auxiliary
   preprocessors node pack includes a normal map estimator from RGB input.

## Expected Format

- PNG, same resolution as input (720×1280 for character)
- RGB-encoded normals (standard ControlNet normal format)
- R = X axis, G = Y axis, B = Z axis (range 0-255 → -1 to +1)

## For New Method Agents

If your method requires normal control, prefer ComfyUI's built-in normal
preprocessor unless Blender has been upgraded to support OPEN_EXR_MULTILAYER.
