from __future__ import annotations

import unittest

from server.schemas.project import ProjectJSON
from server.services.task_queue import InMemoryTaskStore, TaskStatus
from tests.backend.test_project_schema import character_project


class TaskQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryTaskStore()
        self.project = ProjectJSON.model_validate(character_project())

    def test_create_returns_task_with_pending_status(self) -> None:
        task = self.store.create(self.project)
        self.assertTrue(task.task_id)
        self.assertEqual(len(task.task_id), 32)
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(task.message, "Queued")

    def test_get_returns_created_task(self) -> None:
        task = self.store.create(self.project)
        found = self.store.get(task.task_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.task_id, task.task_id)
        self.assertEqual(found.project_id, self.project.project_id)

    def test_get_nonexistent_returns_none(self) -> None:
        self.assertIsNone(self.store.get("nonexistent-id"))

    def test_update_changes_fields(self) -> None:
        task = self.store.create(self.project)
        updated = self.store.update(
            task.task_id,
            status=TaskStatus.RENDERING,
            message="Blender is running.",
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, TaskStatus.RENDERING)
        self.assertEqual(updated.message, "Blender is running.")
        self.assertGreaterEqual(updated.updated_at, task.updated_at)

    def test_update_nonexistent_returns_none(self) -> None:
        self.assertIsNone(
            self.store.update("nonexistent", status=TaskStatus.DONE)
        )

    def test_snapshot_contains_expected_keys(self) -> None:
        task = self.store.create(self.project)
        snap = task.snapshot()
        for key in (
            "task_id",
            "project_id",
            "status",
            "error_code",
            "message",
            "output_path",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, snap)


if __name__ == "__main__":
    unittest.main()
