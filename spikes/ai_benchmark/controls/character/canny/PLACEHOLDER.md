# Canny Edge Map — Character

## Status

Available from Gate 2: `spikes/ai_enhance_gate2/output/character_intro/keyframes/canny/`

## Generation Method

FFmpeg `edgedetect` filter applied to raw no-text keyframes:

```powershell
ffmpeg -i frame.png -vf "edgedetect=low=0.1:high=0.3,negate" -y output_canny.png
```

The Gate 2 `video_ops.py` script automates this for all frames. See
`spikes/ai_enhance_gate2/video_ops.py` for the `generate_canny()` function.

## Expected Format

- PNG, same resolution as input (720×1280 for character)
- White edges on black background (or inverted as needed by ControlNet)
- Single-channel grayscale is acceptable

## For New Method Agents

If you need Canny maps at different thresholds or for different frames, re-run
the generation from the benchmark keyframes:

```python
# Reference: spikes/ai_enhance_gate2/video_ops.py
import subprocess
ffmpeg = os.environ.get("FFMPEG_PATH", "ffmpeg")
subprocess.run([
    ffmpeg, "-i", keyframe_path,
    "-vf", "edgedetect=low=0.1:high=0.3,negate",
    "-y", output_path,
], check=True)
```
