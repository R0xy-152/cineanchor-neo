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

    @staticmethod
    def enhance_mp4(
        input_path: Path,
        output_path: Path,
        preset: str,
        task_id: str,
        *,
        timeout: int = 120,
    ) -> None:
        """Apply conservative FFmpeg enhancement filters.

        Presets:
          conservative_premium — eq + unsharp (validated in Route 3 spike)
        """
        if preset != "conservative_premium":
            raise CineAnchorError(
                ErrorCode.AI_ENHANCE_SKIPPED,
                f"Unknown enhancement preset: {preset}",
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Conservative filter chain validated in Route 3 spike.
        # Values derived from ComfyUI color-reference analysis.
        video_filter = (
            "eq=brightness=0.003:contrast=0.99:saturation=1.01:gamma=0.999,"
            "unsharp=5:5:0.32:3:3:0.12"
        )

        command = [
            settings.FFMPEG_PATH,
            "-y",
            "-i",
            str(input_path),
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-crf",
            "18",
            "-c:a",
            "copy",
            str(output_path),
        ]

        log_path = settings.LOGS_DIR / task_id / "ffmpeg_enhance.log"
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
                ErrorCode.AI_ENHANCE_SKIPPED,
                f"FFmpeg not found during enhancement: {settings.FFMPEG_PATH}",
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise CineAnchorError(
                ErrorCode.AI_ENHANCE_SKIPPED,
                f"FFmpeg enhancement timed out after {timeout}s",
            ) from exc

        if result.returncode != 0:
            tail = _tail(log_path)
            raise CineAnchorError(
                ErrorCode.AI_ENHANCE_SKIPPED,
                f"FFmpeg enhancement exited with code {result.returncode}. "
                f"Log tail: {tail}",
            )

        if not output_path.exists():
            raise CineAnchorError(
                ErrorCode.AI_ENHANCE_SKIPPED,
                f"FFmpeg enhancement completed but output was not created: "
                f"{output_path}",
            )

        logger.info(
            "Enhancement complete for task %s (%s) → %s",
            task_id,
            preset,
            output_path,
        )


def _tail(path: Path, max_chars: int = 2200) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:].strip()
