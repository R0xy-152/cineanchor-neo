# AI Enhance Gate 2: Structure Control

This isolated spike tests whether structure-controlled AI enhancement can give
CineAnchor a stronger visual lift than raw Blender while preserving subject
identity, product shape, text stability, and temporal stability.

The spike is intentionally not wired into the Web/FastAPI render path.
Generated frames, videos, ComfyUI outputs, and reports are written under
`spikes/ai_enhance_gate2/output/`, which is ignored by Git.

## Experiments

1. Render a no-text `character_intro` sample and export RGB frames, subject
   masks, and Blender data-pass evidence where available.
2. Extract no-text keyframes and compare plain SDXL img2img against a
   structure-control workflow at denoise values `0.25`, `0.35`, and `0.45`.
3. Composite original subject pixels back over the enhanced background using
   the rendered mask, then add deterministic text with FFmpeg.
4. Process a 2-second / 48-frame continuous sample with the best available
   method and generate `before_after_2s.mp4`.
5. Optionally repeat the keyframe structure test on `product_orbit`.

## Manual Run

```powershell
$env:COMFYUI_API_URL="http://127.0.0.1:8188"

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\spikes\ai_enhance_gate2\run_gate2.ps1
```

The wrapper assumes these local tool paths:

- Blender: `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`
- FFmpeg: `.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe`
- ffprobe: `.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe`

Override with `-BlenderPath`, `-FfmpegPath`, and `-FfprobePath` if needed.
