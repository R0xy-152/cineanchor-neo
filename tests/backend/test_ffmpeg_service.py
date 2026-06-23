from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from server.config import settings, REPO_ROOT
from server.services.errors import CineAnchorError, ErrorCode
from server.services.ffmpeg_service import FFmpegService


class FFmpegServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.task_id = "test-ffmpeg-12345678"
        self.frames_dir = settings.RENDERS_DIR / self.task_id / "frames"
        self.output_path = settings.EXPORTS_DIR / self.task_id / "final.mp4"
        self.fps = 24

    @patch("server.services.ffmpeg_service.subprocess.run")
    def test_constructs_correct_command(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 0
        # Make the output file appear to exist after the run
        with patch.object(Path, "exists", return_value=True):
            FFmpegService.compose_mp4(
                self.frames_dir, self.output_path, self.fps, self.task_id
            )

        mock_run.assert_called_once()
        command = mock_run.call_args[0][0] if mock_run.call_args[0] else mock_run.call_args[1]["args"]
        self.assertIn("-y", command)
        self.assertIn("-framerate", command)
        self.assertIn(str(self.fps), command)
        self.assertIn("-i", command)
        self.assertIn("libx264", command)
        self.assertIn("yuv420p", command)
        self.assertIn("+faststart", command)
        self.assertIn("18", command)

    @patch("server.services.ffmpeg_service.subprocess.run")
    def test_raises_on_nonzero_exit(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 1
        with self.assertRaises(CineAnchorError) as ctx:
            FFmpegService.compose_mp4(
                self.frames_dir, self.output_path, self.fps, self.task_id
            )
        self.assertEqual(ctx.exception.code, ErrorCode.FFMPEG_COMPOSE_FAILED)

    @patch("server.services.ffmpeg_service.subprocess.run")
    def test_raises_on_missing_ffmpeg(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError("ffmpeg not found")
        with self.assertRaises(CineAnchorError) as ctx:
            FFmpegService.compose_mp4(
                self.frames_dir, self.output_path, self.fps, self.task_id
            )
        self.assertEqual(ctx.exception.code, ErrorCode.FFMPEG_COMPOSE_FAILED)

    @patch("server.services.ffmpeg_service.subprocess.run")
    def test_raises_when_output_not_created(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 0
        with self.assertRaises(CineAnchorError) as ctx:
            FFmpegService.compose_mp4(
                self.frames_dir, self.output_path, self.fps, self.task_id
            )
        self.assertEqual(ctx.exception.code, ErrorCode.FFMPEG_COMPOSE_FAILED)
        self.assertIn("not created", ctx.exception.message)

    @patch("server.services.ffmpeg_service.subprocess.run")
    def test_creates_output_directory(self, mock_run: MagicMock) -> None:
        mock_run.return_value.returncode = 0
        with patch.object(Path, "exists", return_value=True):
            FFmpegService.compose_mp4(
                self.frames_dir, self.output_path, self.fps, self.task_id
            )
        self.assertTrue(self.output_path.parent.exists())


if __name__ == "__main__":
    unittest.main()
