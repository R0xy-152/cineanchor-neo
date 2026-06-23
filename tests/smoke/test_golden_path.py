from __future__ import annotations

import asyncio
import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from server.main import app
from server.services import comfy_service
from server.services.blender_service import BlenderService
from server.services.errors import CineAnchorError, ErrorCode
from server.services.ffmpeg_service import FFmpegService
from server.services.task_queue import TaskStatus, task_store
from tests.backend.test_project_schema import character_project


_MOCK_PNG = Path(__file__).resolve().parents[2] / "spikes" / "render_json" / "input" / "hero.png"


def asgi_request(method: str, path: str, json_body: dict | None = None) -> tuple[int, dict]:
    body_bytes = b"" if json_body is None else json.dumps(json_body).encode("utf-8")
    headers = [
        (b"host", b"testserver"),
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body_bytes)).encode("ascii")),
    ]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    messages: list[dict] = []
    sent_body = False

    async def receive() -> dict:
        nonlocal sent_body
        if not sent_body:
            sent_body = True
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    asyncio.run(app(scope, receive, send))

    start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start["status"], json.loads(body.decode("utf-8"))


class GoldenPathSmokeTests(unittest.TestCase):
    def test_server_app_imports_and_health_is_ok(self) -> None:
        status, body = asgi_request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_project_json_parses_valid_example(self) -> None:
        from server.schemas.project import ProjectJSON

        project = ProjectJSON.model_validate(character_project())
        self.assertEqual(project.project_id, "test-character")

    @patch.object(BlenderService, "render_project")
    @patch.object(FFmpegService, "compose_mp4")
    @patch.object(comfy_service.ComfyService, "enhance")
    def test_post_render_runs_pipeline_to_done(
        self,
        mock_enhance: object,
        mock_ffmpeg: object,
        mock_blender: object,
    ) -> None:
        status, body = asgi_request("POST", "/api/render", character_project())
        self.assertEqual(status, 200)
        self.assertTrue(body["task_id"])
        self.assertEqual(body["status"], "PENDING")

        task_id = body["task_id"]

        # Wait for background thread to complete (services are mocked)
        deadline = time.time() + 10
        while time.time() < deadline:
            _, snap = asgi_request("GET", f"/api/render/{task_id}/status")
            if snap["status"] in ("DONE", "FAILED"):
                break
            time.sleep(0.1)

        self.assertEqual(snap["status"], "DONE")
        self.assertEqual(snap["error_code"], None)
        self.assertEqual(snap["message"], "Render completed.")
        self.assertIsNotNone(snap["output_path"])

        # Verify ComfyUI was never called
        mock_enhance.assert_not_called()

    @patch.object(BlenderService, "render_project")
    def test_post_render_fails_on_blender_error(self, mock_blender: object) -> None:
        mock_blender.side_effect = CineAnchorError(
            ErrorCode.BLENDER_RENDER_FAILED, "Blender crashed"
        )

        status, body = asgi_request("POST", "/api/render", character_project())
        self.assertEqual(status, 200)
        task_id = body["task_id"]

        deadline = time.time() + 10
        while time.time() < deadline:
            _, snap = asgi_request("GET", f"/api/render/{task_id}/status")
            if snap["status"] == "FAILED":
                break
            time.sleep(0.1)

        self.assertEqual(snap["status"], "FAILED")
        self.assertEqual(snap["error_code"], "BLENDER_RENDER_FAILED")

    @patch.object(BlenderService, "render_project")
    @patch.object(FFmpegService, "compose_mp4")
    def test_ai_enhance_enabled_does_not_fail_render(
        self, mock_ffmpeg: object, mock_blender: object
    ) -> None:
        payload = character_project()
        payload["ai_enhance"] = {"enabled": True, "mode": "conservative"}

        status, body = asgi_request("POST", "/api/render", payload)
        self.assertEqual(status, 200)
        task_id = body["task_id"]

        deadline = time.time() + 10
        while time.time() < deadline:
            _, snap = asgi_request("GET", f"/api/render/{task_id}/status")
            if snap["status"] in ("DONE", "FAILED"):
                break
            time.sleep(0.1)

        self.assertEqual(snap["status"], "DONE")

    @patch.object(BlenderService, "render_project")
    @patch.object(FFmpegService, "compose_mp4")
    @patch.object(comfy_service.ComfyService, "enhance")
    def test_post_render_returns_task_id_for_valid_character_intro(
        self,
        mock_enhance: object,
        mock_ffmpeg: object,
        mock_blender: object,
    ) -> None:
        status, body = asgi_request("POST", "/api/render", character_project())
        self.assertEqual(status, 200)
        self.assertTrue(body["task_id"])
        self.assertEqual(body["status"], "PENDING")
        mock_enhance.assert_not_called()

    def test_post_render_rejects_invalid_template(self) -> None:
        payload = character_project()
        payload["template"] = "missing_template"

        status, body = asgi_request("POST", "/api/render", payload)

        self.assertEqual(status, 400)
        self.assertEqual(body["error_code"], "INVALID_PROJECT_JSON")
        self.assertEqual(body["message"], "Project JSON is invalid")

    def test_status_returns_404_for_unknown_task(self) -> None:
        status, body = asgi_request("GET", "/api/render/nonexistent-id/status")
        self.assertEqual(status, 404)
        self.assertEqual(body["error_code"], "TASK_NOT_FOUND")

    def test_download_returns_404_for_unknown_task(self) -> None:
        status, body = asgi_request("GET", "/api/render/nonexistent-id/download")
        self.assertEqual(status, 404)
        self.assertEqual(body["error_code"], "TASK_NOT_FOUND")

    def test_download_returns_409_when_not_done(self) -> None:
        # Create a task but don't run the pipeline
        from server.services.task_queue import task_store
        from server.schemas.project import ProjectJSON

        project = ProjectJSON.model_validate(character_project())
        task = task_store.create(project)

        status, body = asgi_request(
            "GET", f"/api/render/{task.task_id}/download"
        )
        self.assertEqual(status, 409)
        self.assertEqual(body["error_code"], "OUTPUT_NOT_READY")


if __name__ == "__main__":
    unittest.main()
