from __future__ import annotations

import io
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from server.config import settings, REPO_ROOT
from server.routes.assets import _identify_asset_type


class AssetTypeTests(unittest.TestCase):
    def test_identify_png_as_image(self) -> None:
        self.assertEqual(_identify_asset_type("hero.png"), "image")
        self.assertEqual(_identify_asset_type("CHARACTER.PNG"), "image")

    def test_identify_glb_as_glb(self) -> None:
        self.assertEqual(_identify_asset_type("model.glb"), "glb")
        self.assertEqual(_identify_asset_type("PRODUCT.GLB"), "glb")

    def test_identify_unknown_returns_none(self) -> None:
        self.assertIsNone(_identify_asset_type("file.txt"))
        self.assertIsNone(_identify_asset_type("file.jpg"))
        self.assertIsNone(_identify_asset_type("file"))
        self.assertIsNone(_identify_asset_type(""))


class UploadAssetTests(unittest.TestCase):
    """Test the upload_asset route handler via direct function call with mocks.

    We test the handler logic directly rather than through ASGI multipart
    encoding, keeping test dependencies minimal.
    """

    def _make_mock_file(self, filename: str, content: bytes = b"test") -> MagicMock:
        mock = MagicMock()
        mock.filename = filename
        mock.file = io.BytesIO(content)
        return mock

    def test_upload_png_saves_file_and_returns_metadata(self) -> None:
        from server.routes.assets import upload_asset

        mock_file = self._make_mock_file("test-hero.png", b"\x89PNG\r\n\x1a\nfake")
        result = upload_asset(file=mock_file)

        self.assertEqual(result["type"], "image")
        self.assertEqual(result["filename"], "test-hero.png")
        self.assertTrue(result["asset_id"])
        self.assertIn("assets", result["path"])

        # Verify file was saved
        saved = settings.STORAGE_DIR / result["path"]
        self.assertTrue(saved.exists())
        self.assertEqual(saved.read_bytes(), b"\x89PNG\r\n\x1a\nfake")

    def test_upload_glb_saves_file_and_returns_metadata(self) -> None:
        from server.routes.assets import upload_asset

        mock_file = self._make_mock_file("model.glb", b"glb-binary-data")
        result = upload_asset(file=mock_file)

        self.assertEqual(result["type"], "glb")
        self.assertEqual(result["filename"], "model.glb")
        self.assertTrue(result["asset_id"])

        saved = settings.STORAGE_DIR / result["path"]
        self.assertTrue(saved.exists())

    def test_upload_rejects_unknown_extension(self) -> None:
        from server.routes.assets import upload_asset
        from fastapi.responses import JSONResponse

        mock_file = self._make_mock_file("readme.txt")
        response = upload_asset(file=mock_file)

        self.assertIsInstance(response, JSONResponse)
        self.assertEqual(response.status_code, 400)
        import json
        body = json.loads(response.body.decode("utf-8"))
        self.assertEqual(body["error_code"], "UNSUPPORTED_ASSET_FORMAT")

    def test_upload_rejects_empty_filename(self) -> None:
        from server.routes.assets import upload_asset
        from fastapi.responses import JSONResponse

        mock_file = self._make_mock_file("")
        response = upload_asset(file=mock_file)

        self.assertIsInstance(response, JSONResponse)
        self.assertEqual(response.status_code, 400)
        import json
        body = json.loads(response.body.decode("utf-8"))
        self.assertEqual(body["error_code"], "UNSUPPORTED_ASSET_FORMAT")


if __name__ == "__main__":
    unittest.main()
