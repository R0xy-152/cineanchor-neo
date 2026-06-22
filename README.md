# CineAnchor Neo

Generate 8-15 second game promotion videos from PNG images or GLB models.

**Stage:** Spike Technical Validation

## What is CineAnchor?

CineAnchor helps mobile game and indie game operators create promotional short videos without 3D art skills. Upload a character image or GLB model, choose a template, type your title, and get a 1080p MP4 ready for TikTok / Xiaohongshu / Steam.

## Tech Stack (Planned)

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 + React 18 + Tailwind CSS |
| 3D Preview | React Three Fiber |
| Backend | Python FastAPI |
| 3D Render | Blender 4.x Headless |
| AI Enhance | ComfyUI + SDXL |
| Video | FFmpeg |

## Current Status

- [ ] Route 0: 3D Render Loop
- [ ] Route 1: PNG 2.5D Video
- [ ] Route 2: JSON-Driven Template Rendering
- [ ] Route 3: ComfyUI AI Enhancement
- [ ] Route 4: Web To Local Render Chain

See `spike_results.md` for detailed validation results.

## Development

Read `AGENTS.md` before contributing. This project is AI-agent-first: all tasks are designed to be executed by AI agents following the rules in AGENTS.md.

## License

[to be determined]
