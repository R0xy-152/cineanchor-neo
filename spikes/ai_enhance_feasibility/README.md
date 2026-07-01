# AI Enhance Feasibility Gate

This spike tests whether true ComfyUI img2img enhancement can visibly improve
no-text Blender output while keeping text as deterministic FFmpeg overlay.

It is isolated from the Web/FastAPI render path. Generated frames, videos, and
ComfyUI images are written under `spikes/ai_enhance_feasibility/output/`, which
is ignored by Git.

## Experiments

1. Render `character_intro` without Blender title/subtitle, then overlay text
   after the AI stage with FFmpeg.
2. Extract no-text keyframes and run ComfyUI img2img at denoise values `0.25`,
   `0.35`, and `0.50`.
3. Process a 2-second / 48-frame no-text `character_intro` sample with the best
   denoise value and recompose a before/after MP4.
4. Optionally repeat keyframe enhancement for `product_orbit`.

## Manual Run

```powershell
$env:COMFYUI_API_URL="http://127.0.0.1:8188"

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\spikes\ai_enhance_feasibility\run_feasibility.ps1 `
  -IncludeProduct
```

The wrapper assumes the existing local tool paths:

- Blender: `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`
- FFmpeg: `.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe`
- ffprobe: `.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe`

Override the paths with `-BlenderPath`, `-FfmpegPath`, and `-FfprobePath`.
