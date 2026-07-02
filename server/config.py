from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _env_text(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value else default


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return int(value)


def _resolve_repo_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


@dataclass(frozen=True)
class Settings:
    BLENDER_PATH: str
    FFMPEG_PATH: str
    STORAGE_DIR: Path
    ASSETS_DIR: Path
    RENDERS_DIR: Path
    EXPORTS_DIR: Path
    PROJECTS_DIR: Path
    LOGS_DIR: Path
    CINEANCHOR_HOST: str
    CINEANCHOR_PORT: int

    @property
    def OVERLAYS_DIR(self) -> Path:
        """Repo-root overlay assets (checked in, not runtime)."""
        return REPO_ROOT / "assets" / "overlays"


def load_settings() -> Settings:
    storage_dir = _resolve_repo_path(_env_text("STORAGE_DIR", "storage"))
    return Settings(
        BLENDER_PATH=_env_text("BLENDER_PATH", "blender"),
        FFMPEG_PATH=_env_text("FFMPEG_PATH", "ffmpeg"),
        STORAGE_DIR=storage_dir,
        ASSETS_DIR=storage_dir / "assets",
        RENDERS_DIR=storage_dir / "renders",
        EXPORTS_DIR=storage_dir / "exports",
        PROJECTS_DIR=storage_dir / "projects",
        LOGS_DIR=storage_dir / "logs",
        CINEANCHOR_HOST=_env_text("CINEANCHOR_HOST", "127.0.0.1"),
        CINEANCHOR_PORT=_env_int("CINEANCHOR_PORT", 8000),
    )


settings = load_settings()
