from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from server.config import settings
from server.schemas.project import ProjectJSON
from server.services.blender_service import BlenderService
from server.services.errors import CineAnchorError, ErrorCode, error_payload
from server.services.ffmpeg_service import FFmpegService
from server.services.task_queue import TaskStatus, task_store

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

    output_path = Path(task.output_path) if task.output_path else None
    if not output_path or not output_path.exists():
        return JSONResponse(
            status_code=404,
            content=error_payload(
                ErrorCode.OUTPUT_NOT_FOUND,
                f"Output file not found for task {task_id}.",
            ),
        )

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=f"cineanchor-{task_id[:8]}.mp4",
    )


# ── internal render worker ────────────────────────────────────────────


def _execute_render(task_id: str) -> None:
    task = task_store.get(task_id)
    if task is None:
        return

    project = ProjectJSON.model_validate(task.project)
    frames_dir = settings.RENDERS_DIR / task_id / "frames"
    output_path = settings.EXPORTS_DIR / task_id / "final.mp4"

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
        FFmpegService.compose_mp4(
            frames_dir=frames_dir,
            output_path=output_path,
            fps=project.output.fps,
            task_id=task_id,
        )

        # ── ai_enhance check ────────────────────────────────────────
        if project.ai_enhance.enabled:
            logger.warning(
                "task %s: ai_enhance.enabled=true is not supported in V0.1. "
                "Standard MP4 output will be returned without AI enhancement.",
                task_id,
            )

        # ── done ────────────────────────────────────────────────────
        task_store.update(
            task_id,
            status=TaskStatus.DONE,
            message="Render completed.",
            output_path=str(output_path),
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
