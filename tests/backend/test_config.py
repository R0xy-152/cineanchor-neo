from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from server.config import REPO_ROOT, load_settings


class ConfigTests(unittest.TestCase):
    def test_settings_read_environment_variables(self) -> None:
        with patch.dict(
            os.environ,
            {
                "BLENDER_PATH": "custom-blender",
                "FFMPEG_PATH": "custom-ffmpeg",
                "STORAGE_DIR": "runtime-storage",
                "CINEANCHOR_HOST": "0.0.0.0",
                "CINEANCHOR_PORT": "8123",
            },
        ):
            settings = load_settings()

        self.assertEqual(settings.BLENDER_PATH, "custom-blender")
        self.assertEqual(settings.FFMPEG_PATH, "custom-ffmpeg")
        self.assertEqual(settings.STORAGE_DIR, (REPO_ROOT / "runtime-storage").resolve())
        self.assertEqual(settings.ASSETS_DIR, Path(settings.STORAGE_DIR) / "assets")
        self.assertEqual(settings.RENDERS_DIR, Path(settings.STORAGE_DIR) / "renders")
        self.assertEqual(settings.EXPORTS_DIR, Path(settings.STORAGE_DIR) / "exports")
        self.assertEqual(settings.PROJECTS_DIR, Path(settings.STORAGE_DIR) / "projects")
        self.assertEqual(settings.LOGS_DIR, Path(settings.STORAGE_DIR) / "logs")
        self.assertEqual(settings.CINEANCHOR_HOST, "0.0.0.0")
        self.assertEqual(settings.CINEANCHOR_PORT, 8123)


if __name__ == "__main__":
    unittest.main()
