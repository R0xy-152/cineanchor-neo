from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from server.config import REPO_ROOT, settings
from server.schemas.project import ProjectJSON
from server.services.blender_service import BlenderService
from server.services.errors import CineAnchorError, ErrorCode, error_payload
from server.services.ffmpeg_service import FFmpegService
from server.services.task_queue import TaskStatus, task_store

OVERLAYS_DIR = REPO_ROOT / "assets" / "overlays"

logger = logging.getLogger(__name__)
router = APIRouter()


def _validation_detail(exc: ValidationError) -> list[dict[str, Any]]:
    return exc.errors(include_url=False, include_context=False, include_input=False)


@router.post("/api/render")
def create_render(payload: Any = Body(...)) -> Any:
    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=400,
            content=error_payload(
                ErrorCode.INVALID_PROJECT_JSON,
                "Project JSON is invalid",
                "Request body must be a JSON object.",
            ),
        )

    try:
        project = ProjectJSON.model_validate(payload)
    except ValidationError as exc:
        return JSONResponse(
            status_code=400,
            content=error_payload(
                ErrorCode.INVALID_PROJECT_JSON,
                "Project JSON is invalid",
                _validation_detail(exc),
            ),
        )

    task = task_store.create(project)

    threading.Thread(
        target=_execute_render,
        args=(task.task_id,),
        daemon=True,
    ).start()

    return {"task_id": task.task_id, "status": TaskStatus.PENDING.value}


@router.get("/api/render/{task_id}/status")
def get_render_status(task_id: str) -> Any:
    task = task_store.get(task_id)
    if task is None:
        return JSONResponse(
            status_code=404,
            content=error_payload(
                ErrorCode.TASK_NOT_FOUND,
                f"Task not found: {task_id}",
            ),
        )
    return task.snapshot()


@router.get("/api/render/{task_id}/download")
def download_render(task_id: str) -> Any:
    task = task_store.get(task_id)
    if task is None:
        return JSONResponse(
            status_code=404,
            content=error_payload(
                ErrorCode.TASK_NOT_FOUND,
                f"Task not found: {task_id}",
            ),
        )

    if task.status != TaskStatus.DONE:
        return JSONResponse(
            status_code=409,
            content=error_payload(
                ErrorCode.OUTPUT_NOT_READY,
                f"Task {task_id} is {task.status.value}, not DONE.",
            ),
        )

    # Prefer enhanced MP4, fall back to standard MP4
    download_path: Path | None = None
    for candidate in (
        task.enhanced_output_path,
        task.output_path,
        task.standard_output_path,
    ):
        if candidate:
            p = Path(candidate)
            if p.exists():
                download_path = p
                break

    if download_path is None:
        return JSONResponse(
            status_code=404,
            content=error_payload(
                ErrorCode.OUTPUT_NOT_FOUND,
                f"Output file not found for task {task_id}.",
            ),
        )

    return FileResponse(
        path=download_path,
        media_type="video/mp4",
        filename=f"cineanchor-{task_id[:8]}.mp4",
    )


# ── loop 08: receive keyframes from viewport ──────────────────────────

_viewport_keyframes: list[dict[str, Any]] = []

@router.post("/api/keyframes")
def save_keyframes(payload: Any = Body(...)) -> Any:
    """Receive recorded camera keyframes from the interactive viewport."""
    global _viewport_keyframes
    _viewport_keyframes = payload if isinstance(payload, list) else []
    kf_count = sum(len(s.get("keyframes", [])) for s in _viewport_keyframes)
    return {"status": "ok", "shots": len(_viewport_keyframes), "keyframes": kf_count}

@router.get("/api/keyframes")
def get_keyframes() -> Any:
    """Get the most recently saved viewport keyframes."""
    return {"keyframes": _viewport_keyframes}

# ── internal render worker ────────────────────────────────────────────


def _execute_render(task_id: str) -> None:
    task = task_store.get(task_id)
    if task is None:
        return

    project = ProjectJSON.model_validate(task.project)
    frames_dir = settings.RENDERS_DIR / task_id / "frames"
    standard_path = settings.EXPORTS_DIR / task_id / "final.mp4"

    try:
        # ── Blender phase ───────────────────────────────────────────
        task_store.update(
            task_id,
            status=TaskStatus.RENDERING,
            message="Blender render is running.",
        )
        BlenderService.render_project(project, task_id)

        # ── FFmpeg phase ────────────────────────────────────────────
        task_store.update(
            task_id,
            status=TaskStatus.COMPOSITING,
            message="FFmpeg composition is running.",
        )

        if project.scene.particles and project.scene.particles.enabled:
            # Enhanced composition with vignette + particle/bokeh overlays
            particles = project.scene.particles
            FFmpegService.compose_mp4_with_effects(
                frames_dir=frames_dir,
                output_path=standard_path,
                fps=project.output.fps,
                task_id=task_id,
                ember_overlay_path=OVERLAYS_DIR / "embers_default.mp4",
                bokeh_overlay_path=OVERLAYS_DIR / "bokeh_default.mp4",
                particles_enabled=True,
                particles_speed=particles.speed,
                particles_opacity=particles.opacity,
                particles_color=particles.color,
                vignette_enabled=True,
            )
        else:
            # Standard composition (no effects)
            FFmpegService.compose_mp4(
                frames_dir=frames_dir,
                output_path=standard_path,
                fps=project.output.fps,
                task_id=task_id,
            )

        # ── optional AI enhancement ─────────────────────────────────
        enhanced_path: Path | None = None
        warning_code: str | None = None
        warning_message: str | None = None

        if project.ai_enhance.enabled:
            task_store.update(
                task_id,
                status=TaskStatus.ENHANCING,
                message="AI enhancement is running.",
            )
            enhanced_path = settings.EXPORTS_DIR / task_id / "enhanced.mp4"

            try:
                FFmpegService.enhance_mp4(
                    input_path=standard_path,
                    output_path=enhanced_path,
                    preset="conservative_premium",
                    task_id=task_id,
                )
                logger.info(
                    "task %s: enhancement complete, enhanced MP4 ready.",
                    task_id,
                )
            except CineAnchorError as exc:
                logger.warning(
                    "task %s: enhancement failed [%s] %s — "
                    "falling back to standard MP4.",
                    task_id,
                    exc.code.value,
                    exc.message,
                )
                warning_code = exc.code.value
                warning_message = exc.message
                enhanced_path = None

        # ── done ────────────────────────────────────────────────────
        task_store.update(
            task_id,
            status=TaskStatus.DONE,
            message="Render completed.",
            output_path=str(enhanced_path or standard_path),
            standard_output_path=str(standard_path),
            enhanced_output_path=str(enhanced_path) if enhanced_path else None,
            warning_code=warning_code,
            warning_message=warning_message,
        )

    except CineAnchorError as exc:
        logger.error(
            "Render failed for task %s: [%s] %s",
            task_id,
            exc.code.value,
            exc.message,
        )
        task_store.update(
            task_id,
            status=TaskStatus.FAILED,
            error_code=exc.code.value,
            message=exc.message,
        )
    except Exception as exc:
        logger.exception(
            "Unexpected render error for task %s",
            task_id,
        )
        task_store.update(
            task_id,
            status=TaskStatus.FAILED,
            error_code="UNEXPECTED_ERROR",
            message=str(exc),
        )
