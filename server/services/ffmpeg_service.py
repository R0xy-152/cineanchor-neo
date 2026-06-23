from __future__ import annotations

from pathlib import Path


class FFmpegService:
    """Placeholder for V0.1 MP4 composition."""

    def compose_mp4(self, frames_dir: Path, output_path: Path, fps: int) -> None:
        raise NotImplementedError(
            "Phase A only defines the backend foundation. FFmpeg composition is "
            "kept out of POST /api/render until the render service is refactored."
        )
