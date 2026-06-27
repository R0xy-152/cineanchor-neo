# Route 2 Spike Report: JSON-Driven Template Rendering

Status: PASS

## Goal

Verify whether one Project JSON can drive template, asset path, camera motion, duration, fps, output size, title, and subtitle for Blender Eevee rendering.

## Scope

- Script: `spikes/render_json/render_project.py`
- FFmpeg wrapper: `spikes/render_json/make_video.ps1`
- Projects:
  - `spikes/render_json/projects/character_intro.json`
  - `spikes/render_json/projects/product_orbit.json`

## Supported JSON Fields

- `template`
- `asset.type`
- `asset.path`
- `camera.motion`
- `duration`
- `fps`
- `output.width`
- `output.height`
- `output.frames_dir`
- `output.video_path`
- `text.title`
- `text.subtitle`

## Results

Route 2 passed for the current two-template Spike scope.

| Field | character_intro | product_orbit |
|---|---:|---:|
| Template | `character_intro` | `product_orbit` |
| Asset | `input/hero.png` | `input/model.glb` |
| Asset type | `image` | `glb` |
| Camera motion | `dolly_in` | `orbit` |
| Resolution | 720x1280 | 1280x720 |
| Duration | 4s | 4s |
| FPS | 24 | 12 |
| Expected frames | 96 | 48 |
| Render engine | Eevee (`BLENDER_EEVEE`) | Eevee (`BLENDER_EEVEE`) |
| Blender render duration | 45.58s | 19.18s |
| FFmpeg duration | 0.34s | 0.23s |
| ffprobe codec | h264 | h264 |
| ffprobe frame count | 96 | 48 |
| Output MP4 | `spikes/render_json/output/character_intro/final.mp4` | `spikes/render_json/output/product_orbit/final.mp4` |

PNG alpha validation:

- `hero_alpha_min=0`
- `hero_alpha_max=255`
- `frame0048_near_white_ratio=0.000000`

Visual checks:

- `character_intro` frame 0048: PNG subject stayed in frame, no white background box, title/subtitle rendered from JSON.
- `product_orbit` frames 0001, 0024, and 0048: GLB subject stayed in frame, camera motion changed angle over time, title/subtitle rendered from JSON.

## Commands Run

```powershell
& 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile spikes\render_json\render_project.py
Get-Content -Raw spikes\render_json\projects\character_intro.json | ConvertFrom-Json
Get-Content -Raw spikes\render_json\projects\product_orbit.json | ConvertFrom-Json
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --python E:\cineanchor\spikes\render_json\render_project.py -- --project projects\character_intro.json
powershell -NoProfile -ExecutionPolicy Bypass -File E:\cineanchor\spikes\render_json\make_video.ps1 -Project projects\character_intro.json -FfmpegPath E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --python E:\cineanchor\spikes\render_json\render_project.py -- --project projects\product_orbit.json
powershell -NoProfile -ExecutionPolicy Bypass -File E:\cineanchor\spikes\render_json\make_video.ps1 -Project projects\product_orbit.json -FfmpegPath E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe
& E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe -v error -count_frames -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,duration,nb_read_frames -of default=noprint_wrappers=1 E:\cineanchor\spikes\render_json\output\character_intro\final.mp4
& E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe -v error -count_frames -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,duration,nb_read_frames -of default=noprint_wrappers=1 E:\cineanchor\spikes\render_json\output\product_orbit\final.mp4
```

## Acceptance Result

- Changing `asset.path` changes the rendered subject without code changes: PASS.
- Changing `text.title` changes rendered title without code changes: PASS.
- Changing `output.width` / `output.height` changes aspect ratio: PASS.
- Changing `duration` / `fps` changes total frame count correctly: PASS.
- Changing `camera.motion` changes camera animation: PASS.
- Both templates render playable MP4 files: PASS.
- ffprobe confirms codec, resolution, duration, fps, and frame count: PASS.

## Known Risks

- This is still a Spike-only JSON shape. It should not be treated as the V1 production schema.
- `prop_showcase` is intentionally out of this task's current scope; this route validates `character_intro` and `product_orbit`.
- `product_orbit` uses a front-arc orbit, not a full 360-degree orbit, so titles remain readable and the fixed stage does not occlude the model. A full orbit needs camera-facing text overlay and a non-occluding stage design.
- Blender 5.1.2 prints non-blocking `Unable to delete file` messages after successful renders. The output frames and MP4 files were still created.
- Blender reports a `Material.use_nodes` deprecation warning for Blender 6.0. It is not a current blocker for Blender 5.1.2.
