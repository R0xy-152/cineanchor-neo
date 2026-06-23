from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import patch

from server.main import app
from server.services import comfy_service
from tests.backend.test_project_schema import character_project


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

    start = next(message for message in messages if message["type"] == "http.response.start")
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

    def test_post_render_returns_task_id_for_valid_character_intro(self) -> None:
        def fail_if_called(*args, **kwargs) -> None:
            raise AssertionError("ComfyUI must not be called by POST /api/render")

        with patch.object(comfy_service.ComfyService, "enhance", fail_if_called):
            status, body = asgi_request("POST", "/api/render", character_project())

        self.assertEqual(status, 200)
        self.assertTrue(body["task_id"])
        self.assertEqual(body["status"], "PENDING")

    def test_post_render_rejects_invalid_template(self) -> None:
        payload = character_project()
        payload["template"] = "missing_template"

        status, body = asgi_request("POST", "/api/render", payload)

        self.assertEqual(status, 400)
        self.assertEqual(body["error_code"], "INVALID_PROJECT_JSON")
        self.assertEqual(body["message"], "Project JSON is invalid")


if __name__ == "__main__":
    unittest.main()
