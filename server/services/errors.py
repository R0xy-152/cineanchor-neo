from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    ASSET_NOT_FOUND = "ASSET_NOT_FOUND"
    INVALID_PROJECT_JSON = "INVALID_PROJECT_JSON"
    ASSET_IMPORT_FAILED = "ASSET_IMPORT_FAILED"
    UNSUPPORTED_TEMPLATE = "UNSUPPORTED_TEMPLATE"
    BLENDER_RENDER_FAILED = "BLENDER_RENDER_FAILED"
    FFMPEG_COMPOSE_FAILED = "FFMPEG_COMPOSE_FAILED"
    COMFY_ENHANCE_FAILED = "COMFY_ENHANCE_FAILED"
    RENDER_TIMEOUT = "RENDER_TIMEOUT"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    OUTPUT_NOT_READY = "OUTPUT_NOT_READY"
    OUTPUT_NOT_FOUND = "OUTPUT_NOT_FOUND"
    AI_ENHANCE_SKIPPED = "AI_ENHANCE_SKIPPED"


DEFAULT_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.ASSET_NOT_FOUND: "Asset was not found",
    ErrorCode.INVALID_PROJECT_JSON: "Project JSON is invalid",
    ErrorCode.ASSET_IMPORT_FAILED: "Asset import failed",
    ErrorCode.UNSUPPORTED_TEMPLATE: "Template is not supported",
    ErrorCode.BLENDER_RENDER_FAILED: "Blender render failed",
    ErrorCode.FFMPEG_COMPOSE_FAILED: "FFmpeg composition failed",
    ErrorCode.COMFY_ENHANCE_FAILED: "ComfyUI enhancement failed",
    ErrorCode.RENDER_TIMEOUT: "Render timed out",
    ErrorCode.TASK_NOT_FOUND: "Task was not found",
    ErrorCode.OUTPUT_NOT_READY: "Output is not ready",
    ErrorCode.OUTPUT_NOT_FOUND: "Output file was not found",
    ErrorCode.AI_ENHANCE_SKIPPED: "AI enhancement was skipped, standard output returned",
}


@dataclass
class CineAnchorError(Exception):
    code: ErrorCode
    message: str
    detail: Any | None = None

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_payload(self) -> dict[str, Any]:
        return error_payload(self.code, self.message, self.detail)


def error_payload(
    code: ErrorCode,
    message: str | None = None,
    detail: Any | None = None,
) -> dict[str, Any]:
    return {
        "error_code": code.value,
        "message": message or DEFAULT_MESSAGES[code],
        "detail": detail,
    }


# Future ComfyUI integration must treat COMFY_ENHANCE_FAILED as a warning and
# fallback condition. It must not fail the standard Blender + FFmpeg render path.
COMFY_ENHANCE_FAILED_IS_FALLBACK = True
