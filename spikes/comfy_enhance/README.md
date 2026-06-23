# Route 3 ComfyUI Keyframe Enhancement Spike

This spike keeps ComfyUI outside the Web/FastAPI render chain. It extracts 4 keyframes from existing Route 4 MP4 outputs, sends only those still images to a conservative ComfyUI img2img workflow, and generates side-by-side comparison PNGs for manual review.

## Inputs

- Existing Route 4 MP4 outputs under `spikes/render_json/output/web/*/final.mp4`, discovered by their `project.json` template.
- Fallback MP4s under `spikes/render_json/output/character_intro/final.mp4` and `spikes/render_json/output/product_orbit/final.mp4`.

## Outputs

Generated files are written under `spikes/comfy_enhance/output/` and are ignored by Git.

```text
output/
  character_intro/
    keyframes_raw/
    keyframes_enhanced/
    comparisons/
  product_orbit/
    keyframes_raw/
    keyframes_enhanced/
    comparisons/
```

## Run

Set tool paths without hardcoding them in scripts:

```powershell
$env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
$env:FFPROBE_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe"
$env:COMFYUI_API_URL="http://127.0.0.1:8188"
```

Extract 4 keyframes per input video:

```powershell
.\spikes\comfy_enhance\extract_keyframes.ps1
```

Run ComfyUI enhancement:

```powershell
.\.venv\Scripts\python.exe .\spikes\comfy_enhance\run_comfy_enhance.py
```

Generate side-by-side comparisons:

```powershell
.\spikes\comfy_enhance\make_comparisons.ps1
```

Or run the full isolated spike:

```powershell
.\spikes\comfy_enhance\run_spike.ps1
```

## Workflow

Default API URL resolution:

- `COMFYUI_API_URL`
- `COMFYUI_URL`
- `http://127.0.0.1:8188`

Default workflow:

- `spikes/comfy_enhance/workflows/conservative_sdxl_img2img_api.json`

The workflow uses SDXL img2img with low denoise. It is intentionally conservative to reduce subject deformation and text corruption risk. Use `--checkpoint` to choose a specific checkpoint if ComfyUI exposes more than one.
