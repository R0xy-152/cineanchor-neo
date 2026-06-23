# Route 3 Conservative AI Enhancement

This spike validates the conservative Route 3 AI enhancement path:

1. Extract 4 keyframes per input MP4.
2. Send only those keyframes to ComfyUI for color/style reference.
3. Analyze raw vs reference frames to estimate stable video-wide color parameters.
4. Apply FFmpeg filters to the original MP4.
5. Generate comparison images.

The final video frames are not replaced with ComfyUI output.

## Run

```powershell
$env:COMFYUI_API_URL="http://127.0.0.1:8188"
$env:FFMPEG_PATH=(Resolve-Path .\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe).Path
$env:FFPROBE_PATH=(Resolve-Path .\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe).Path

powershell -NoProfile -ExecutionPolicy Bypass -File .\spikes\comfy_lut_enhance\extract_keyframes.ps1
.\.venv\Scripts\python.exe .\spikes\comfy_lut_enhance\run_comfy_reference.py --timeout-seconds 1200
.\.venv\Scripts\python.exe .\spikes\comfy_lut_enhance\analyze_color_reference.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\spikes\comfy_lut_enhance\apply_ffmpeg_enhance.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\spikes\comfy_lut_enhance\make_comparisons.ps1
```

Product-level decision: conservative ComfyUI reference plus FFmpeg enhancement is PARTIAL. It is stable, but the visual improvement is light, so it should remain an optional V0.1 preset.

Generated output stays under `spikes/comfy_lut_enhance/output/` and is ignored by Git.
