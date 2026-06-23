from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from server.schemas.project import ProjectJSON
from server.services.errors import ErrorCode, error_payload
from server.services.task_queue import TaskStatus, task_store


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
def download_render(task_id: str) -> JSONResponse:
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
    return JSONResponse(
        status_code=501,
        content=error_payload(
            ErrorCode.OUTPUT_NOT_READY,
            "Download is reserved for the render execution phase.",
        ),
    )
