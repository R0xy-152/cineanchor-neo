# CineAnchor AI Enhancement Benchmark

Shared benchmark package for R&D method search. All AI enhancement spike agents use
the same inputs, control signals, and evaluation scorecard so results are comparable.

## Quick Reference

| Item | Location |
|---|---|
| No-text benchmark videos/keyframes | `input/character/`, `input/product/` |
| Control signal placeholders | `controls/character/`, `controls/product/` |
| Method priority ranking | `evaluation/method_matrix.md` |
| Unified scorecard template | `evaluation/scorecard_template.md` |
| Follow-up task prompts | `tasks/` |

## Hard Rules

### Text Handling (IMMUTABLE)

**Text must NEVER be processed by AI.**

- Titles, subtitles, and any text overlay must be added AFTER the AI stage via
  deterministic FFmpeg `drawtext` or equivalent overlay.
- Any method that requires AI to process final text pixels is **invalid**.
- The benchmark input videos and keyframes intentionally have no text so every
  method starts from the same clean base.

### Stability Requirements

- Subject shape must not visibly deform.
- Product geometry must stay recognizable.
- No obvious temporal flicker over 2 seconds (48 frames at 24fps).

### Evaluation Rule

- If visual lift is strong but stability fails → FAIL (not PASS).
- If stable but visual lift is weak → FAIL (not enough ROI for integration).
- Stable + strong lift → PASS.

## Benchmark Inputs

### Source

All benchmark inputs are generated from the same Blender render paths used by the
V0.1 production pipeline. The render script at `spikes/render_json/render_project.py`
supports suppressing text by setting:

```json
"text": {"title": "", "subtitle": ""}
```

### Character Intro (no-text)

| Asset | Path (relative to spike output) | Source Spike |
|---|---|---|
| 2s video (48 frames, 720×1280, 24fps) | `spikes/ai_enhance_gate2/output/character_intro/raw_no_text_2s.mp4` | Gate 2 |
| 4 keyframes | `spikes/ai_enhance_gate2/output/character_intro/keyframes/frame_01.png` … `frame_04.png` | Gate 2 |
| Continuous frames (48) | `spikes/ai_enhance_gate2/output/character_intro/continuous_raw/0001.png` … `0048.png` | Gate 2 |

### Product Orbit (no-text)

| Asset | Path (relative to spike output) | Source Spike |
|---|---|---|
| Keyframes (4) | `spikes/ai_enhance_gate2/output/product_orbit/keyframes/frame_01.png` … `frame_04.png` | Gate 2 |
| Raw no-text MP4 | `spikes/ai_enhance_gate2/output/product_orbit/raw_no_text.mp4` (1280×720, 12fps, 4s) | Gate 2 |
| Raw RGB frames | `spikes/ai_enhance_gate2/output/product_orbit/rgb/0001.png` … `0048.png` | Gate 2 |

### Regenerating Benchmark Inputs

If the Gate 2 outputs are not available, regenerate from the render pipeline:

```powershell
$env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"

# Character intro no-text (2s, 720×1280, 24fps)
.\.venv\Scripts\python.exe spikes\ai_enhance_gate2\render_structural.py `
  --template character_intro `
  --asset-path samples/assets/hero.png `
  --output spikes/ai_benchmark/input/character/ `
  --duration 2 --fps 24 --resolution 720p --no-text

# Product orbit no-text keyframes
.\.venv\Scripts\python.exe spikes\ai_enhance_gate2\render_structural.py `
  --template product_orbit `
  --asset-path samples/assets/model.glb `
  --output spikes/ai_benchmark/input/product/ `
  --duration 2 --fps 24 --resolution 720p --no-text
```

Note: The Gate 2 `render_structural.py` outputs a `structural_manifest.json` that records
which passes were successfully rendered (rgb, mask, depth, normal).

## Control Signal Plan

### Available (from Gate 2)

| Signal | Character | Product | Method |
|---|---|---|---|
| Subject mask | ✓ (Blender-rendered) | ✓ (Blender-rendered) | Blender material override — white subject on black background |
| Canny edge map | ✓ (FFmpeg `edgedetect`) | Not yet generated | FFmpeg `edgedetect` filter |

Canny maps were generated via FFmpeg in Gate 2's `video_ops.py`. The script extracts
frames and applies:

```python
ffmpeg -i frame.png -vf "edgedetect=low=0.1:high=0.3,negate" output_canny.png
```

### Not Available

| Signal | Reason |
|---|---|
| Depth / Z-pass | Blender 5.1.2 lacks OPEN_EXR_MULTILAYER output format |
| Normal pass | Same as depth — OPEN_EXR_MULTILAYER not supported in this build |

### Placeholder Directories

Each `controls/*/{canny,depth,normal,mask}/` directory contains a `PLACEHOLDER.md`
with the expected format and generation command for that signal type.

When a method agent successfully generates a new control signal, it should document
the generation method and save a reference frame to the corresponding directory.

## Control Signal Directories

```
controls/
├── character/
│   ├── canny/     # Canny edge maps (FFmpeg edgedetect)
│   ├── depth/     # Depth maps (BLOCKED — Blender 5.1 limitation)
│   ├── normal/    # Normal maps (BLOCKED — Blender 5.1 limitation)
│   └── mask/      # Subject/alpha masks (Blender material override)
└── product/
    ├── canny/     # Canny edge maps
    ├── depth/     # Depth maps (BLOCKED)
    ├── normal/    # Normal maps (BLOCKED)
    └── mask/      # Subject masks (Blender material override)
```

## Workflow for Method Agents

1. Read `evaluation/method_matrix.md` for context on where this method fits.
2. Read the assigned task prompt in `tasks/`.
3. Use benchmark inputs from `input/` (or reference Gate 2 outputs directly).
4. Generate or reuse control signals from `controls/`.
5. Run the method experiment.
6. Fill out `evaluation/scorecard_template.md` with results.
7. Report decision: PASS / PARTIAL / FAIL.

## Git Policy

- Generated MP4, PNG frames, ComfyUI outputs, model files, `.venv`, `.tools`,
  `storage/` outputs, and cache files are **never committed**.
- Commit only: scripts, Markdown docs, templates, workflow JSON, and metadata.
- All media output is already covered by the repo `.gitignore`.
