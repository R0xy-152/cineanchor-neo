from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from server.config import settings, REPO_ROOT
from server.services.errors import CineAnchorError, ErrorCode

logger = logging.getLogger(__name__)


class FFmpegService:
    """Compose PNG frame sequences into H.264 MP4 via FFmpeg."""

    @staticmethod
    def compose_mp4(
        frames_dir: Path,
        output_path: Path,
        fps: int,
        task_id: str,
        *,
        timeout: int = 180,
    ) -> None:
        # ── ensure output directory ─────────────────────────────────
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # ── build command ───────────────────────────────────────────
        command = [
            settings.FFMPEG_PATH,
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames_dir / "%04d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-crf",
            "18",
            str(output_path),
        ]

        # ── run ─────────────────────────────────────────────────────
        log_path = settings.LOGS_DIR / task_id / "ffmpeg.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with log_path.open("w", encoding="utf-8", errors="replace") as log_file:
                log_file.write(f"$ {subprocess.list2cmdline(command)}\n\n")
                log_file.flush()
                result = subprocess.run(
                    command,
                    cwd=REPO_ROOT,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
        except FileNotFoundError as exc:
            raise CineAnchorError(
                ErrorCode.FFMPEG_COMPOSE_FAILED,
                f"FFmpeg executable not found: {settings.FFMPEG_PATH}",
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise CineAnchorError(
                ErrorCode.FFMPEG_COMPOSE_FAILED,
                f"FFmpeg composition timed out after {timeout}s",
            ) from exc

        if result.returncode != 0:
            tail = _tail(log_path)
            raise CineAnchorError(
                ErrorCode.FFMPEG_COMPOSE_FAILED,
                f"FFmpeg exited with code {result.returncode}. "
                f"Log tail: {tail}",
            )

        if not output_path.exists():
            raise CineAnchorError(
                ErrorCode.FFMPEG_COMPOSE_FAILED,
                f"FFmpeg completed but output MP4 was not created: {output_path}",
            )

        logger.info(
            "FFmpeg composition complete for task %s → %s",
            task_id,
            output_path,
        )


def _tail(path: Path, max_chars: int = 2200) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:].strip()
