from __future__ import annotations

import unittest

from server.services.errors import ErrorCode


class ErrorCodeTests(unittest.TestCase):
    def test_required_error_codes_exist(self) -> None:
        required = {
            "ASSET_NOT_FOUND",
            "INVALID_PROJECT_JSON",
            "ASSET_IMPORT_FAILED",
            "UNSUPPORTED_TEMPLATE",
            "BLENDER_RENDER_FAILED",
            "FFMPEG_COMPOSE_FAILED",
            "COMFY_ENHANCE_FAILED",
            "RENDER_TIMEOUT",
            "TASK_NOT_FOUND",
            "OUTPUT_NOT_READY",
            "OUTPUT_NOT_FOUND",
            "AI_ENHANCE_SKIPPED",
            "UNSUPPORTED_ASSET_FORMAT",
        }
        self.assertTrue(required.issubset({code.value for code in ErrorCode}))


if __name__ == "__main__":
    unittest.main()
