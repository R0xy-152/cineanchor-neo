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

    # ── compositing helpers ─────────────────────────────────────────

    @staticmethod
    def hex_to_rgb_floats(hex_str: str) -> tuple[float, float, float]:
        """Convert a hex color string to 0.0–1.0 float triple."""
        hex_str = hex_str.lstrip("#")
        return (
            int(hex_str[0:2], 16) / 255.0,
            int(hex_str[2:4], 16) / 255.0,
            int(hex_str[4:6], 16) / 255.0,
        )

    @staticmethod
    def derive_ember_color(asset_path: Path, asset_type: str) -> str:
        """Sample median hue from a PNG's alpha-bounded region.

        Returns a hex color string. Defaults to warm orange for GLB
        or when sampling cannot determine a dominant hue.
        """
        if asset_type != "image":
            return "#FF8C2E"

        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            return "#FF8C2E"

        try:
            img = Image.open(asset_path).convert("RGBA")
            pixels = np.array(img)
            alpha = pixels[:, :, 3]
            mask = alpha > 30
            if not mask.any():
                return "#FF8C2E"

            rgb = pixels[:, :, :3][mask]
            r_med = int(np.median(rgb[:, 0]))
            g_med = int(np.median(rgb[:, 1]))
            b_med = int(np.median(rgb[:, 2]))

            # If subject is near-monochrome, use default ember color
            max_diff = max(
                abs(r_med - g_med), abs(g_med - b_med), abs(b_med - r_med)
            )
            if max_diff < 30:
                return "#FF8C2E"

            return f"#{r_med:02X}{g_med:02X}{b_med:02X}"
        except Exception:
            return "#FF8C2E"

    @staticmethod
    def compose_mp4_with_effects(
        frames_dir: Path,
        output_path: Path,
        fps: int,
        task_id: str,
        *,
        ember_overlay_path: Path | None = None,
        bokeh_overlay_path: Path | None = None,
        particles_enabled: bool = True,
        particles_speed: float = 1.0,
        particles_opacity: float = 0.6,
        particles_color: str = "#FF8C2E",
        bokeh_opacity: float = 0.3,
        vignette_enabled: bool = True,
        timeout: int = 300,
    ) -> None:
        """Compose PNG frames with vignette + particle/bokeh overlays.

        Builds a single ``-filter_complex`` applying in order:
        1. vignette on main render
        2. ember particle overlay (screen blend)
        3. bokeh overlay (screen blend)

        All effects are deterministic — no AI involved.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        color_r, color_g, color_b = FFmpegService.hex_to_rgb_floats(
            particles_color
        )

        # Build filter_complex step by step.
        # Overlays are 2 s × 24 fps = 48 frame loops.
        OVERLAY_SIZE = 48

        filter_parts: list[str] = []
        # gbrp = planar RGB float — always full/PC range, no PC/TV mismatch.
        filter_parts.append("[0:v]format=gbrp[main]")

        # ── step 1: vignette ─────────────────────────────────────
        current = "main"
        if vignette_enabled:
            filter_parts.append(
                f"[{current}]vignette=angle=PI/4:x0=w/2:y0=h*0.42:eval=frame,"
                f"format=gbrp[after_vin]"
            )
            current = "after_vin"

        # ── step 2: ember particle overlay ───────────────────────
        has_ember = particles_enabled and ember_overlay_path and ember_overlay_path.exists()
        has_bokeh = bokeh_overlay_path and bokeh_overlay_path.exists()

        if has_ember:
            speed_pts = max(0.1, particles_speed)
            filter_parts.append(
                f"[1:v]setpts=PTS/{speed_pts:.4f},"
                f"loop=-1:size={OVERLAY_SIZE},"
                f"format=gbrp"
                f"[ember]"
            )
            filter_parts.append(
                f"[{current}][ember]blend=all_mode=screen:shortest=1[after_ember]"
            )
            current = "after_ember"

        # ── step 3: bokeh overlay ────────────────────────────────
        if has_bokeh:
            filter_parts.append(
                f"[2:v]setpts=PTS/1.0,"
                f"loop=-1:size={OVERLAY_SIZE},"
                f"format=gbrp"
                f"[bokeh]"
            )
            filter_parts.append(
                f"[{current}][bokeh]blend=all_mode=screen:shortest=1[out]"
            )
        else:
            filter_parts.append(f"[{current}]copy[out]")

        filter_complex = ";".join(filter_parts)

        # ── build command ────────────────────────────────────────
        command = [
            settings.FFMPEG_PATH,
            "-y",
            "-framerate", str(fps),
            "-i", str(frames_dir / "%04d.png"),
        ]

        # Add optional overlay inputs; indices must match filter_complex
        if has_ember:
            command.extend(["-i", str(ember_overlay_path)])
        if has_bokeh:
            command.extend(["-i", str(bokeh_overlay_path)])

        command.extend([
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-crf", "18",
            str(output_path),
        ])

        # ── run ──────────────────────────────────────────────────
        log_path = settings.LOGS_DIR / task_id / "ffmpeg_composite.log"
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
                f"FFmpeg composition with effects timed out after {timeout}s",
            ) from exc

        if result.returncode != 0:
            tail = _tail(log_path)
            raise CineAnchorError(
                ErrorCode.FFMPEG_COMPOSE_FAILED,
                f"FFmpeg (effects) exited with code {result.returncode}. "
                f"Log tail: {tail}",
            )

        if not output_path.exists():
            raise CineAnchorError(
                ErrorCode.FFMPEG_COMPOSE_FAILED,
                f"FFmpeg effects composition completed but output was "
                f"not created: {output_path}",
            )

        logger.info(
            "FFmpeg effects composition complete for task %s → %s",
            task_id,
            output_path,
        )


def _tail(path: Path, max_chars: int = 2200) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:].strip()
