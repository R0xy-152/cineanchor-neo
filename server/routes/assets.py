from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from server.config import settings
from server.services.errors import ErrorCode, error_payload

router = APIRouter()

_ALLOWED_EXTENSIONS: dict[str, str] = {
    ".png": "image",
    ".glb": "glb",
}


def _identify_asset_type(filename: str) -> str | None:
    suffix = Path(filename).suffix.lower()
    return _ALLOWED_EXTENSIONS.get(suffix)


@router.post("/api/assets/upload")
def upload_asset(file: UploadFile = File(...)) -> Any:
    if not file.filename:
        return JSONResponse(
            status_code=400,
            content=error_payload(
                ErrorCode.UNSUPPORTED_ASSET_FORMAT,
                detail="No filename provided.",
            ),
        )

    asset_type = _identify_asset_type(file.filename)
    if asset_type is None:
        return JSONResponse(
            status_code=400,
            content=error_payload(
                ErrorCode.UNSUPPORTED_ASSET_FORMAT,
                detail=(
                    f"File extension is not supported: {file.filename}. "
                    "Supported formats: PNG, GLB."
                ),
            ),
        )

    asset_id = uuid.uuid4().hex
    asset_dir = settings.ASSETS_DIR / asset_id
    asset_dir.mkdir(parents=True, exist_ok=True)

    asset_path = asset_dir / file.filename
    try:
        content = file.file.read()
        asset_path.write_bytes(content)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_payload(
                ErrorCode.UNSUPPORTED_ASSET_FORMAT,
                detail=f"Failed to save uploaded file: {exc}",
            ),
        )

    relative_path = asset_path.relative_to(settings.STORAGE_DIR)

    return {
        "asset_id": asset_id,
        "path": str(relative_path),
        "type": asset_type,
        "filename": file.filename,
    }
