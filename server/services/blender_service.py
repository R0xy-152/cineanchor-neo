from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from server.config import settings, REPO_ROOT
from server.schemas.project import ProjectJSON, Template
from server.services.birthday_renderer import BirthdayFrameRenderer
from server.services.errors import CineAnchorError, ErrorCode

logger = logging.getLogger(__name__)

RENDER_SCRIPT = REPO_ROOT / "blender" / "scripts" / "render_project.py"


class BlenderService:
    """Execute Blender headless for a validated ProjectJSON."""

    @staticmethod
    def render_project(
        project: ProjectJSON,
        task_id: str,
        *,
        timeout: int = 900,
    ) -> None:
        # ── resolve asset path ──────────────────────────────────────
        asset_paths: dict[str, Path] = {}
        for asset in project.assets:
            asset_path = Path(asset.path)
            if not asset_path.is_absolute():
                asset_path = settings.STORAGE_DIR / asset_path
            asset_path = asset_path.resolve()
            if not asset_path.exists():
                raise CineAnchorError(
                    ErrorCode.ASSET_NOT_FOUND,
                    f"Asset not found: {asset_path}",
                )
            asset_paths[asset.id] = asset_path

        # ── write project file ──────────────────────────────────────
        project_dir = settings.PROJECTS_DIR / task_id
        project_dir.mkdir(parents=True, exist_ok=True)
        project_file = project_dir / "project.json"
        project_file.write_text(
            json.dumps(project.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        # ── prepare output ──────────────────────────────────────────
        width, height = project.output.dimensions
        frames_dir = settings.RENDERS_DIR / task_id / "frames"

        if project.template == Template.CHARACTER_BIRTHDAY:
            BirthdayFrameRenderer.render(project, frames_dir, asset_paths)
            logger.info(
                "Birthday frame render complete for task %s, frames in %s",
                task_id,
                frames_dir,
            )
            return

        asset_path = asset_paths["main_subject"]

        # ── build command ───────────────────────────────────────────
        command = [
            settings.BLENDER_PATH,
            "--background",
            "--python",
            str(RENDER_SCRIPT),
            "--",
            "--project",
            str(project_file),
            "--frames-dir",
            str(frames_dir),
            "--width",
            str(width),
            "--height",
            str(height),
            "--asset-path",
            str(asset_path),
        ]

        # ── run ─────────────────────────────────────────────────────
        log_path = settings.LOGS_DIR / task_id / "blender.log"
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
                ErrorCode.BLENDER_RENDER_FAILED,
                f"Blender executable not found: {settings.BLENDER_PATH}",
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise CineAnchorError(
                ErrorCode.RENDER_TIMEOUT,
                f"Blender render timed out after {timeout}s",
            ) from exc

        if result.returncode != 0:
            tail = _tail(log_path)
            raise CineAnchorError(
                ErrorCode.BLENDER_RENDER_FAILED,
                f"Blender exited with code {result.returncode}. "
                f"Log tail: {tail}",
            )

        logger.info(
            "Blender render complete for task %s, frames in %s",
            task_id,
            frames_dir,
        )


def _tail(path: Path, max_chars: int = 2200) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:].strip()
