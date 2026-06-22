from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "apps" / "web"
RENDER_JSON_DIR = Path(
    os.environ.get("CINEANCHOR_RENDER_JSON_DIR", REPO_ROOT / "spikes" / "render_json")
).resolve()
RENDER_SCRIPT = Path(
    os.environ.get("CINEANCHOR_RENDER_SCRIPT", RENDER_JSON_DIR / "render_project.py")
).resolve()
MAKE_VIDEO_SCRIPT = Path(
    os.environ.get("CINEANCHOR_MAKE_VIDEO_SCRIPT", RENDER_JSON_DIR / "make_video.ps1")
).resolve()
BLENDER_PATH = os.environ.get("BLENDER_PATH", "blender")
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")
POWERSHELL_PATH = os.environ.get("POWERSHELL_PATH", "powershell")
RENDER_TIMEOUT_SECONDS = int(os.environ.get("CINEANCHOR_RENDER_TIMEOUT_SECONDS", "900"))
FFMPEG_TIMEOUT_SECONDS = int(os.environ.get("CINEANCHOR_FFMPEG_TIMEOUT_SECONDS", "180"))

TASK_ROOT = RENDER_JSON_DIR / "output" / "web"

TEMPLATE_PRESETS: dict[str, dict[str, Any]] = {
    "character_intro": {
        "asset": {"type": "image", "path": "input/hero.png"},
        "camera": {"motion": "dolly_in"},
        "duration": 4,
        "fps": 24,
        "output": {"width": 720, "height": 1280},
        "text": {
            "title": "New Hero Arrival",
            "subtitle": "Limited Event",
        },
    },
    "product_orbit": {
        "asset": {"type": "glb", "path": "input/model.glb"},
        "camera": {"motion": "orbit"},
        "duration": 4,
        "fps": 12,
        "output": {"width": 1280, "height": 720},
        "text": {
            "title": "Product Orbit",
            "subtitle": "GLB Showcase",
        },
    },
}


class RenderRequest(BaseModel):
    template: str = Field(default="character_intro")
    title: str | None = Field(default=None, max_length=80)
    subtitle: str | None = Field(default=None, max_length=120)


@dataclass
class RenderTask:
    task_id: str
    template: str
    title: str
    subtitle: str
    project_path: Path
    output_path: Path
    log_dir: Path
    status: str = "PENDING"
    error_code: str | None = None
    message: str = "Queued"
    blender_seconds: float | None = None
    ffmpeg_seconds: float | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class RenderFailure(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


tasks: dict[str, RenderTask] = {}
task_lock = threading.Lock()

app = FastAPI(title="CineAnchor Local Render Spike")


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/web/")


@app.post("/api/render")
def create_render(request: RenderRequest) -> dict[str, Any]:
    template = request.template.strip()
    if template not in TEMPLATE_PRESETS:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "UNSUPPORTED_TEMPLATE",
                "message": f"Unsupported template: {template}",
            },
        )

    preset = TEMPLATE_PRESETS[template]
    default_text = preset["text"]
    title = clean_text(request.title, default_text["title"], 80)
    subtitle = clean_text(request.subtitle, default_text["subtitle"], 120)
    task_id = uuid.uuid4().hex
    task_dir = TASK_ROOT / task_id
    frames_dir = f"output/web/{task_id}/frames"
    video_path = f"output/web/{task_id}/final.mp4"
    project_path = task_dir / "project.json"
    output_path = task_dir / "final.mp4"

    task_dir.mkdir(parents=True, exist_ok=True)
    project = {
        "template": template,
        "asset": preset["asset"],
        "camera": preset["camera"],
        "duration": preset["duration"],
        "fps": preset["fps"],
        "output": {
            "width": preset["output"]["width"],
            "height": preset["output"]["height"],
            "frames_dir": frames_dir,
            "video_path": video_path,
        },
        "text": {
            "title": title,
            "subtitle": subtitle,
        },
    }
    project_path.write_text(json.dumps(project, indent=2), encoding="utf-8")

    task = RenderTask(
        task_id=task_id,
        template=template,
        title=title,
        subtitle=subtitle,
        project_path=project_path,
        output_path=output_path,
        log_dir=task_dir,
    )
    with task_lock:
        tasks[task_id] = task

    worker = threading.Thread(target=run_render_task, args=(task_id,), daemon=True)
    worker.start()

    return task_snapshot(task)


@app.get("/api/render/{task_id}")
def get_render(task_id: str) -> dict[str, Any]:
    return task_snapshot(get_task(task_id))


@app.get("/api/render/{task_id}/download")
def download_render(task_id: str) -> FileResponse:
    task = get_task(task_id)
    if task.status != "DONE":
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "TASK_NOT_DONE",
                "message": f"Task {task_id} is {task.status}, not DONE.",
            },
        )
    if not task.output_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "OUTPUT_NOT_FOUND",
                "message": f"Output file is missing for task {task_id}.",
            },
        )
    return FileResponse(
        path=task.output_path,
        media_type="video/mp4",
        filename=f"cineanchor-{task.template}-{task_id[:8]}.mp4",
    )


def clean_text(value: str | None, fallback: str, max_length: int) -> str:
    text = (value or fallback).strip()
    return (text or fallback)[:max_length]


def get_task(task_id: str) -> RenderTask:
    with task_lock:
        task = tasks.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "TASK_NOT_FOUND",
                "message": f"Task not found: {task_id}",
            },
        )
    return task


def task_snapshot(task: RenderTask) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "status": task.status,
        "template": task.template,
        "title": task.title,
        "subtitle": task.subtitle,
        "error_code": task.error_code,
        "message": task.message,
        "download_url": f"/api/render/{task.task_id}/download"
        if task.status == "DONE"
        else None,
        "project_path": str(task.project_path.relative_to(REPO_ROOT)),
        "output_path": str(task.output_path.relative_to(REPO_ROOT)),
        "blender_seconds": task.blender_seconds,
        "ffmpeg_seconds": task.ffmpeg_seconds,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def set_task(task_id: str, **changes: Any) -> RenderTask:
    with task_lock:
        task = tasks[task_id]
        for key, value in changes.items():
            setattr(task, key, value)
        task.updated_at = time.time()
        return task


def run_render_task(task_id: str) -> None:
    task = get_task(task_id)
    try:
        ensure_runtime_files()
        set_task(task_id, status="RENDERING", message="Blender render is running.")
        blender_command = [
            BLENDER_PATH,
            "--background",
            "--python",
            str(RENDER_SCRIPT),
            "--",
            "--project",
            str(task.project_path),
        ]
        task.blender_seconds = run_command(
            blender_command,
            task.log_dir / "blender.log",
            RENDER_TIMEOUT_SECONDS,
            "BLENDER_FAILED",
        )

        set_task(task_id, status="COMPOSITING", message="FFmpeg composition is running.")
        ffmpeg_command = [
            POWERSHELL_PATH,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(MAKE_VIDEO_SCRIPT),
            "-Project",
            str(task.project_path),
            "-FfmpegPath",
            FFMPEG_PATH,
        ]
        task.ffmpeg_seconds = run_command(
            ffmpeg_command,
            task.log_dir / "ffmpeg.log",
            FFMPEG_TIMEOUT_SECONDS,
            "FFMPEG_FAILED",
        )

        if not task.output_path.exists():
            raise RenderFailure("OUTPUT_NOT_FOUND", f"MP4 was not created: {task.output_path}")

        set_task(task_id, status="DONE", message="Render completed.")
    except RenderFailure as exc:
        set_task(
            task_id,
            status="FAILED",
            error_code=exc.error_code,
            message=exc.message,
        )
    except Exception as exc:  # Keep async spike failures inspectable through the status API.
        set_task(
            task_id,
            status="FAILED",
            error_code="UNEXPECTED_ERROR",
            message=str(exc),
        )


def ensure_runtime_files() -> None:
    for path, code in (
        (RENDER_JSON_DIR, "RENDER_JSON_DIR_MISSING"),
        (RENDER_SCRIPT, "RENDER_SCRIPT_MISSING"),
        (MAKE_VIDEO_SCRIPT, "MAKE_VIDEO_SCRIPT_MISSING"),
    ):
        if not path.exists():
            raise RenderFailure(code, f"Required path is missing: {path}")


def run_command(command: list[str], log_path: Path, timeout: int, error_code: str) -> float:
    started = time.perf_counter()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with log_path.open("w", encoding="utf-8", errors="replace") as log_file:
            log_file.write(f"$ {subprocess.list2cmdline(command)}\n\n")
            log_file.flush()
            completed = subprocess.run(
                command,
                cwd=REPO_ROOT,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                check=False,
            )
    except FileNotFoundError as exc:
        raise RenderFailure(error_code, f"Executable not found: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RenderFailure(error_code, f"Command timed out after {timeout}s: {command[0]}") from exc

    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        raise RenderFailure(
            error_code,
            f"Command failed with exit code {completed.returncode}. Log tail: {tail(log_path)}",
        )
    return round(elapsed, 2)


def tail(path: Path, max_chars: int = 2200) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:].strip()


app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")
