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
from tests.backend.test_project_schema import birthday_project, character_project


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


def _wait_for_status(task_id: str, target: frozenset[str], timeout: float = 10) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        _, snap = asgi_request("GET", f"/api/render/{task_id}/status")
        if snap["status"] in target:
            return snap
        time.sleep(0.1)
    _, snap = asgi_request("GET", f"/api/render/{task_id}/status")
    return snap


class GoldenPathSmokeTests(unittest.TestCase):
    @patch.object(BlenderService, "render_project")
    @patch.object(FFmpegService, "compose_mp4")
    @patch.object(FFmpegService, "compose_mp4_with_effects")
    @patch.object(FFmpegService, "enhance_mp4")
    def test_character_birthday_uses_standard_non_ai_mp4_path(
        self,
        mock_enhance: object,
        mock_effects: object,
        mock_compose: object,
        mock_render: object,
    ) -> None:
        status, body = asgi_request("POST", "/api/render", birthday_project())
        self.assertEqual(status, 200)
        snap = _wait_for_status(body["task_id"], frozenset({"DONE", "FAILED"}))
        self.assertEqual(snap["status"], "DONE")
        self.assertTrue(snap["standard_output_path"].endswith("final.mp4"))
        mock_render.assert_called_once()
        mock_compose.assert_called_once()
        mock_effects.assert_not_called()
        mock_enhance.assert_not_called()

    # ── infrastructure ───────────────────────────────────────────────

    def test_server_app_imports_and_health_is_ok(self) -> None:
        status, body = asgi_request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_project_json_parses_valid_example(self) -> None:
        from server.schemas.project import ProjectJSON

        project = ProjectJSON.model_validate(character_project())
        self.assertEqual(project.project_id, "test-character")

    # ── standard path (ai_enhance.enabled=false) ─────────────────────

    @patch.object(BlenderService, "render_project")
    @patch.object(FFmpegService, "compose_mp4")
    @patch.object(comfy_service.ComfyService, "enhance")
    def test_standard_path_does_not_call_enhancement(
        self,
        mock_enhance: object,
        mock_ffmpeg: object,
        mock_blender: object,
    ) -> None:
        payload = character_project()
        payload["scene"]["particles"] = None  # standard path, no particles
        status, body = asgi_request("POST", "/api/render", payload)
        self.assertEqual(status, 200)
        self.assertTrue(body["task_id"])
        self.assertEqual(body["status"], "PENDING")

        task_id = body["task_id"]
        snap = _wait_for_status(task_id, frozenset({"DONE", "FAILED"}))

        self.assertEqual(snap["status"], "DONE")
        self.assertIsNone(snap["error_code"])
        self.assertIsNotNone(snap["standard_output_path"])
        self.assertIsNone(snap["enhanced_output_path"])
        self.assertIsNone(snap["warning_code"])

        # ComfyUI must never be called
        mock_enhance.assert_not_called()
        # enhance_mp4 must not be called
        self.assertFalse(
            hasattr(FFmpegService, "_enhance_called")
            or mock_ffmpeg._mock_name == "enhance_mp4"
        )

    @patch.object(BlenderService, "render_project")
    @patch.object(FFmpegService, "compose_mp4")
    @patch.object(comfy_service.ComfyService, "enhance")
    def test_post_render_returns_task_id_for_valid_character_intro(
        self,
        mock_enhance: object,
        mock_ffmpeg: object,
        mock_blender: object,
    ) -> None:
        payload = character_project()
        payload["scene"]["particles"] = None  # standard path, no particles
        status, body = asgi_request("POST", "/api/render", payload)
        self.assertEqual(status, 200)
        self.assertTrue(body["task_id"])
        self.assertEqual(body["status"], "PENDING")
        mock_enhance.assert_not_called()

    # ── enhancement success (ai_enhance.enabled=true) ────────────────

    @patch.object(BlenderService, "render_project")
    @patch.object(FFmpegService, "compose_mp4")
    @patch.object(FFmpegService, "enhance_mp4")
    @patch.object(comfy_service.ComfyService, "enhance")
    def test_enhancement_success_produces_enhanced_output(
        self,
        mock_enhance: object,
        mock_enhance_mp4: object,
        mock_ffmpeg: object,
        mock_blender: object,
    ) -> None:
        payload = character_project()
        payload["scene"]["particles"] = None  # standard path, no particles
        payload["ai_enhance"] = {"enabled": True, "mode": "conservative"}

        status, body = asgi_request("POST", "/api/render", payload)
        self.assertEqual(status, 200)
        task_id = body["task_id"]

        snap = _wait_for_status(task_id, frozenset({"DONE", "FAILED"}))

        self.assertEqual(snap["status"], "DONE")
        self.assertIsNone(snap["error_code"])
        self.assertIsNone(snap["warning_code"])
        self.assertIsNotNone(snap["standard_output_path"])
        self.assertIsNotNone(snap["enhanced_output_path"])
        self.assertIn("enhanced.mp4", snap["enhanced_output_path"])

        mock_enhance.assert_not_called()  # ComfyUI not called

    # ── enhancement failure fallback ─────────────────────────────────

    @patch.object(BlenderService, "render_project")
    @patch.object(FFmpegService, "compose_mp4")
    @patch.object(FFmpegService, "enhance_mp4")
    def test_enhancement_failure_falls_back_to_standard(
        self,
        mock_enhance_mp4: object,
        mock_ffmpeg: object,
        mock_blender: object,
    ) -> None:
        mock_enhance_mp4.side_effect = CineAnchorError(
            ErrorCode.AI_ENHANCE_SKIPPED, "Enhancement filter failed"
        )

        payload = character_project()
        payload["scene"]["particles"] = None  # standard path, no particles
        payload["ai_enhance"] = {"enabled": True, "mode": "conservative"}

        status, body = asgi_request("POST", "/api/render", payload)
        self.assertEqual(status, 200)
        task_id = body["task_id"]

        snap = _wait_for_status(task_id, frozenset({"DONE", "FAILED"}))

        self.assertEqual(snap["status"], "DONE")
        self.assertEqual(snap["warning_code"], "AI_ENHANCE_SKIPPED")
        self.assertIsNotNone(snap["warning_message"])
        self.assertIsNotNone(snap["standard_output_path"])
        self.assertIsNone(snap["enhanced_output_path"])
        # download should return standard MP4 (via output_path fallback)
        self.assertIn("final.mp4", snap["output_path"])

    # ── error paths ──────────────────────────────────────────────────

    @patch.object(BlenderService, "render_project")
    def test_post_render_fails_on_blender_error(self, mock_blender: object) -> None:
        mock_blender.side_effect = CineAnchorError(
            ErrorCode.BLENDER_RENDER_FAILED, "Blender crashed"
        )

        status, body = asgi_request("POST", "/api/render", character_project())
        self.assertEqual(status, 200)
        task_id = body["task_id"]

        snap = _wait_for_status(task_id, frozenset({"FAILED"}))

        self.assertEqual(snap["status"], "FAILED")
        self.assertEqual(snap["error_code"], "BLENDER_RENDER_FAILED")

    def test_post_render_rejects_invalid_template(self) -> None:
        payload = character_project()
        payload["template"] = "missing_template"

        status, body = asgi_request("POST", "/api/render", payload)
        self.assertEqual(status, 400)
        self.assertEqual(body["error_code"], "INVALID_PROJECT_JSON")

    # ── status and download edge cases ───────────────────────────────

    def test_status_returns_404_for_unknown_task(self) -> None:
        status, body = asgi_request("GET", "/api/render/nonexistent-id/status")
        self.assertEqual(status, 404)
        self.assertEqual(body["error_code"], "TASK_NOT_FOUND")

    def test_download_returns_404_for_unknown_task(self) -> None:
        status, body = asgi_request("GET", "/api/render/nonexistent-id/download")
        self.assertEqual(status, 404)
        self.assertEqual(body["error_code"], "TASK_NOT_FOUND")

    def test_download_returns_409_when_not_done(self) -> None:
        from server.services.task_queue import task_store
        from server.schemas.project import ProjectJSON

        project = ProjectJSON.model_validate(character_project())
        task = task_store.create(project)

        status, body = asgi_request(
            "GET", f"/api/render/{task.task_id}/download"
        )
        self.assertEqual(status, 409)
        self.assertEqual(body["error_code"], "OUTPUT_NOT_READY")

    def test_snapshot_includes_new_task_fields(self) -> None:
        from server.services.task_queue import task_store
        from server.schemas.project import ProjectJSON

        project = ProjectJSON.model_validate(character_project())
        task = task_store.create(project)
        snap = task.snapshot()

        for key in (
            "standard_output_path",
            "enhanced_output_path",
            "warning_code",
            "warning_message",
        ):
            self.assertIn(key, snap)


    # ── web serving ────────────────────────────────────────────────

    def test_web_index_is_served(self) -> None:
        """GET /web/ should return the static HTML page."""
        import asyncio

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/web/",
            "raw_path": b"/web/",
            "query_string": b"",
            "headers": [(b"host", b"testserver")],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        messages: list[dict] = []

        async def receive() -> dict:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict) -> None:
            messages.append(message)

        asyncio.run(app(scope, receive, send))
        start = next(m for m in messages if m["type"] == "http.response.start")
        self.assertEqual(start["status"], 200)


    # ── Loop 08: interactive camera render ──────────────────────────

    @patch.object(BlenderService, "render_project")
    @patch.object(FFmpegService, "compose_mp4")
    @patch.object(comfy_service.ComfyService, "enhance")
    def test_render_with_keyframes_completes(
        self,
        mock_enhance: object,
        mock_ffmpeg: object,
        mock_blender: object,
    ) -> None:
        """Interactive camera keyframes pass through render pipeline."""
        payload = character_project()
        payload["scene"]["particles"] = None
        payload["camera"]["keyframes"] = [
            {"t": 0.0, "pos": [0, -5, 1.5], "quat": [0, 0, 0, 1], "fov": 55},
            {"t": 2.0, "pos": [0, -3, 1.5], "quat": [0, 0, 0.3827, 0.9239], "fov": 55, "cut": True},
            {"t": 4.0, "pos": [0, -1, 1.5], "quat": [0, 0, 0, 1], "fov": 55},
        ]
        status, body = asgi_request("POST", "/api/render", payload)
        self.assertEqual(status, 200)
        self.assertTrue(body["task_id"])

        snap = _wait_for_status(body["task_id"], frozenset({"DONE", "FAILED"}))
        self.assertEqual(snap["status"], "DONE")
        self.assertIsNotNone(snap["standard_output_path"])

    @patch.object(BlenderService, "render_project")
    @patch.object(FFmpegService, "compose_mp4")
    @patch.object(comfy_service.ComfyService, "enhance")
    def test_render_with_shots_completes(
        self,
        mock_enhance: object,
        mock_ffmpeg: object,
        mock_blender: object,
    ) -> None:
        """Multi-shot interactive camera shots pass through render pipeline."""
        payload = character_project()
        payload["scene"]["particles"] = None
        payload["camera"]["shots"] = [
            {"index": 0, "cut": True, "keyframes": [
                {"t": 0.0, "pos": [0, -5, 1.5], "quat": [0, 0, 0, 1], "fov": 55},
                {"t": 2.0, "pos": [0, -3, 1.5], "quat": [0, 0, 0.3827, 0.9239], "fov": 55, "cut": True},
            ]},
            {"index": 1, "cut": False, "keyframes": [
                {"t": 2.0, "pos": [0, -3, 1.5], "quat": [0, 0, 0.3827, 0.9239], "fov": 55},
                {"t": 4.0, "pos": [3, -1, 1.5], "quat": [0, 0, 0, 1], "fov": 55},
            ]},
        ]
        status, body = asgi_request("POST", "/api/render", payload)
        self.assertEqual(status, 200)
        self.assertTrue(body["task_id"])

        snap = _wait_for_status(body["task_id"], frozenset({"DONE", "FAILED"}))
        self.assertEqual(snap["status"], "DONE")


if __name__ == "__main__":
    unittest.main()
