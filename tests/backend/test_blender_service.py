from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from server.config import settings, REPO_ROOT
from server.schemas.project import ProjectJSON
from server.services.blender_service import BlenderService, RENDER_SCRIPT
from server.services.errors import CineAnchorError, ErrorCode
from tests.backend.test_project_schema import character_project, product_project


class BlenderServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.char_project = ProjectJSON.model_validate(character_project())
        self.prod_project = ProjectJSON.model_validate(product_project())
        self.task_id = "test-task-12345678"

    def test_raises_on_missing_asset(self) -> None:
        with self.assertRaises(CineAnchorError) as ctx:
            BlenderService.render_project(self.char_project, self.task_id)
        self.assertEqual(ctx.exception.code, ErrorCode.ASSET_NOT_FOUND)

    @patch("server.services.blender_service.subprocess.run")
    def test_constructs_correct_command_for_character_intro(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 0

        # Point to a real file so the asset check passes
        asset_path = REPO_ROOT / "spikes" / "render_json" / "input" / "hero.png"
        if not asset_path.exists():
            self.skipTest("sample asset not available")

        project = ProjectJSON.model_validate({
            **character_project(),
            "assets": [{"id": "main_subject", "type": "image", "path": str(asset_path)}],
        })

        BlenderService.render_project(project, self.task_id)

        # Verify subprocess was called
        mock_run.assert_called_once()
        command = mock_run.call_args[0][0] if mock_run.call_args[0] else mock_run.call_args[1]["args"]
        self.assertIn("--background", command)
        self.assertIn("--python", command)
        self.assertIn(str(RENDER_SCRIPT), command)
        self.assertIn("--width", command)
        self.assertIn("--height", command)
        self.assertIn("--asset-path", command)
        self.assertIn("--project", command)
        self.assertIn("--frames-dir", command)

    @patch("server.services.blender_service.subprocess.run")
    def test_raises_on_nonzero_exit(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 1

        asset_path = REPO_ROOT / "spikes" / "render_json" / "input" / "hero.png"
        if not asset_path.exists():
            self.skipTest("sample asset not available")

        project = ProjectJSON.model_validate({
            **character_project(),
            "assets": [{"id": "main_subject", "type": "image", "path": str(asset_path)}],
        })

        with self.assertRaises(CineAnchorError) as ctx:
            BlenderService.render_project(project, self.task_id)
        self.assertEqual(ctx.exception.code, ErrorCode.BLENDER_RENDER_FAILED)

    @patch("server.services.blender_service.subprocess.run")
    def test_raises_on_timeout(self, mock_run: MagicMock) -> None:
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("blender", 900)

        asset_path = REPO_ROOT / "spikes" / "render_json" / "input" / "hero.png"
        if not asset_path.exists():
            self.skipTest("sample asset not available")

        project = ProjectJSON.model_validate({
            **character_project(),
            "assets": [{"id": "main_subject", "type": "image", "path": str(asset_path)}],
        })

        with self.assertRaises(CineAnchorError) as ctx:
            BlenderService.render_project(project, self.task_id)
        self.assertEqual(ctx.exception.code, ErrorCode.RENDER_TIMEOUT)

    @patch("server.services.blender_service.subprocess.run")
    def test_raises_on_missing_blender_executable(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError("blender not found")

        asset_path = REPO_ROOT / "spikes" / "render_json" / "input" / "hero.png"
        if not asset_path.exists():
            self.skipTest("sample asset not available")

        project = ProjectJSON.model_validate({
            **character_project(),
            "assets": [{"id": "main_subject", "type": "image", "path": str(asset_path)}],
        })

        with self.assertRaises(CineAnchorError) as ctx:
            BlenderService.render_project(project, self.task_id)
        self.assertEqual(ctx.exception.code, ErrorCode.BLENDER_RENDER_FAILED)

    @patch("server.services.blender_service.subprocess.run")
    def test_writes_project_file_with_correct_content(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 0

        asset_path = REPO_ROOT / "spikes" / "render_json" / "input" / "hero.png"
        if not asset_path.exists():
            self.skipTest("sample asset not available")

        project = ProjectJSON.model_validate({
            **character_project(),
            "assets": [{"id": "main_subject", "type": "image", "path": str(asset_path)}],
        })

        BlenderService.render_project(project, self.task_id)

        project_file = settings.PROJECTS_DIR / self.task_id / "project.json"
        self.assertTrue(project_file.exists())
        data = json.loads(project_file.read_text(encoding="utf-8"))
        self.assertEqual(data["template"], "character_intro")
        self.assertEqual(data["assets"][0]["type"], "image")


if __name__ == "__main__":
    unittest.main()
