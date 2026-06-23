from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from server.schemas.project import ProjectJSON


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RENDERING = "RENDERING"
    COMPOSITING = "COMPOSITING"
    ENHANCING = "ENHANCING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class RenderTask:
    task_id: str
    project_id: str
    status: TaskStatus = TaskStatus.PENDING
    project: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    message: str = "Queued"
    output_path: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def snapshot(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "error_code": self.error_code,
            "message": self.message,
            "output_path": self.output_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class InMemoryTaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, RenderTask] = {}
        self._lock = threading.Lock()

    def create(self, project: ProjectJSON) -> RenderTask:
        task = RenderTask(
            task_id=uuid.uuid4().hex,
            project_id=project.project_id,
            project=project.model_dump(mode="json"),
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> RenderTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def update(self, task_id: str, **changes: Any) -> RenderTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            for key, value in changes.items():
                setattr(task, key, value)
            task.updated_at = time.time()
            return task


task_store = InMemoryTaskStore()
