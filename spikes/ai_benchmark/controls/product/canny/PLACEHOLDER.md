# Canny Edge Map — Product

## Status

**Not yet generated** — Gate 2 only generated Canny maps for character_intro.

## Generation Method

Same FFmpeg `edgedetect` approach as character. From raw product keyframes:

```powershell
ffmpeg -i frame.png -vf "edgedetect=low=0.1:high=0.3,negate" -y output_canny.png
```

Reference implementation: `spikes/ai_enhance_gate2/video_ops.py` (`generate_canny()`).

## Expected Format

- PNG, same resolution as input (1280×720 for product)
- White edges on black background (or inverted as needed by ControlNet)
- Single-channel grayscale is acceptable

## Source Keyframes

Keyframes are at: `spikes/ai_enhance_gate2/output/product_orbit/keyframes/`

If not available, regenerate from benchmark inputs using the render commands
in the main benchmark README.
