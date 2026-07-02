# CineAnchor Character Birthday V0.2 Change Report

## Scope isolation

- Original project read only: `E:\cineanchor`.
- Isolated implementation workspace: `C:\Users\Administrator\Documents\Codex\2026-07-02\wo\cineanchor_birthday_v02`.
- Reference videos read only: `E:\cineanchor\bluearchive`.
- No original project file was edited.

## Changed

### Files created

- `tools/analyze_reference_videos.py`
- `docs/reference_analysis/reference_video_analysis.md`
- `docs/reference_analysis/contact_sheets/*.jpg` (13)
- `docs/reference_analysis/data/*.json` (13)
- `docs/templates/character_birthday_template.md`
- `docs/change_report_character_birthday_v02.md`
- `server/services/birthday_renderer.py`
- `samples/projects/character_birthday.json`
- `scripts/render_birthday_sample.py`
- `tests/backend/test_birthday_renderer.py`
- `tests/frontend/test_birthday_ui.py`

### Files modified in the isolated copy

- `server/schemas/project.py`
- `server/services/blender_service.py`
- `server/routes/render.py`
- `server/requirements.txt`
- `apps/web/index.html`
- `apps/web/app.js`
- `apps/web/styles.css`
- `tests/backend/test_project_schema.py`
- `tests/smoke/test_golden_path.py`
- `docs/project_json_schema.md`
- `README.md`

## Behavior changed

- Added additive Project JSON version `0.2` and `character_birthday` while preserving legacy template constraints.
- Added named PNG slots: required `main_character`; optional `logo`, `support_image_1..3`.
- Added birthday text, style and six-component timeline models.
- Added deterministic Pillow layer rendering behind the existing `BlenderService.render_project` service boundary. Legacy templates still call Blender unchanged.
- Birthday output reuses the existing FFmpeg H.264 path, task states, storage, download route and errors.
- Added a Web template entry, main-character/Logo uploads, character/date/dialogue/color fields, and a 15-second 9:16 payload.
- Added font preset resolution, subtitle wrapping/outline, particles, blur zoom, white flash, cloud wipe and Logo end card.
- Added frame `render_manifest.json` containing component timings, resolution, asset presence and AI dependency state.

API changed: no new endpoint; `/api/render` accepts an additive schema variant.

Schema changed: yes, additive `0.2`; `0.1` payloads remain valid.

## Tests and verification

Run:

```powershell
$env:PYTHONPATH=(Get-Location).Path
E:\cineanchor\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Isolated workspace result: 203 tests passed, 5 skipped. Clean publish-checkout result from remote base `abfb032`: 164 tests passed, 5 skipped. The count difference is caused by additional local Loop 09 tests present under `E:\cineanchor` but absent from the remote base; those unrelated files are intentionally excluded from this branch. The skipped legacy Blender command tests require historical files under `spikes/render_json/input`, which were intentionally not copied into the isolated workspace. All schema, API smoke, renderer, FFmpeg unit, frontend, camera parity and new birthday tests passed.

Real export verification:

- File: `outputs/character_birthday_sample.mp4`
- Container: MP4 (`mov,mp4,m4a,3gp,3g2,mj2`)
- Video: H.264, `yuv420p`, 1080×1920, 24 fps
- Duration: 15.000 seconds
- Size at verification: about 1.36 MB

## Analyze reference videos

```powershell
$videos = (Get-ChildItem E:\cineanchor\bluearchive\*.mp4).FullName
E:\cineanchor\.venv\Scripts\python.exe tools\analyze_reference_videos.py @videos `
  --output-dir docs\reference_analysis `
  --ffmpeg E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe `
  --ffprobe E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe
```

Use `--crop W:H:X:Y` for one common crop, or `--crop-config crop.json` for per-file crops.

## Generate a sample video

Via Web: start FastAPI, choose **角色生日 / 生贺**, upload a character PNG and Logo, fill the fields, then generate.

Via CLI:

```powershell
$env:PYTHONPATH=(Get-Location).Path
python scripts\render_birthday_sample.py `
  --character C:\assets\character.png `
  --logo C:\assets\logo.png `
  --output C:\exports\birthday.mp4 `
  --ffmpeg C:\tools\ffmpeg.exe
```

## Not implemented

- BGM or gameplay-video upload, trim, mix and beat sync.
- Automatic background removal.
- Project history, persistent queue, batch CSV and template version storage.
- Support-image Web upload UI (API and renderer slots exist).
- Brand font upload/package; only system-font presets with fallback are implemented.
- AI background generation, character motion, ComfyUI and external video models.
- Free timeline, free multi-object layout or complex user camera controls for this template.

## Recommended next step

Implement brand packs and production controls before adding visual complexity: BGM/gameplay slots with licensing metadata, project persistence, batch generation, text/contrast/safe-area preflight, low-resolution preview and golden-render visual regression.
