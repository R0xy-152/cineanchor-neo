from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import PropertyMock, patch

from PIL import Image, ImageDraw

from server.schemas.project import OutputSpec, ProjectJSON
from server.services.birthday_renderer import BirthdayFrameRenderer
from tests.backend.test_project_schema import birthday_project


class BirthdayRendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.character = self.root / "character.png"
        image = Image.new("RGBA", (500, 900), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((90, 30, 410, 350), fill=(255, 215, 225, 255))
        draw.rounded_rectangle((120, 310, 380, 880), radius=80, fill=(89, 103, 176, 255))
        image.save(self.character)

        payload = birthday_project()
        payload["assets"][0]["path"] = str(self.character)
        self.project = ProjectJSON.model_validate(payload)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_component_timeline_has_all_required_stages(self) -> None:
        renderer = BirthdayFrameRenderer(self.project, {"main_character": self.character})
        samples = [0.5, 2.5, 4.0, 7.0, 10.0, 14.0]
        names = [renderer.component_at(second)[0] for second in samples]
        self.assertEqual(names, [
            "opening_date_card", "name_card", "birthday_title_closeup",
            "character_poster", "character_interaction", "brand_end_card",
        ])

    def test_frame_renders_without_logo_support_images_bgm_or_ai(self) -> None:
        renderer = BirthdayFrameRenderer(self.project, {"main_character": self.character})
        frame = renderer.render_frame(10 * self.project.output.fps)
        self.assertEqual(frame.size, (1080, 1920))
        self.assertEqual(frame.mode, "RGBA")

    def test_dialogue_wraps_to_at_most_two_lines(self) -> None:
        renderer = BirthdayFrameRenderer(self.project, {"main_character": self.character})
        draw = ImageDraw.Draw(Image.new("RGBA", (1080, 1920)))
        font = renderer._font(48, bold=True)
        wrapped = renderer._wrap_text(
            draw,
            "Thank you for celebrating this important birthday together with me today.",
            font,
            600,
            max_lines=2,
        )
        self.assertLessEqual(len(wrapped.splitlines()), 2)

    def test_short_render_writes_frames_and_manifest(self) -> None:
        frames_dir = self.root / "frames"
        with patch.object(OutputSpec, "frame_count", new_callable=PropertyMock, return_value=6):
            BirthdayFrameRenderer.render(
                self.project,
                frames_dir,
                {"main_character": self.character},
            )
        self.assertEqual(len(list(frames_dir.glob("*.png"))), 6)
        manifest_path = frames_dir.parent / "render_manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["resolution"], [1080, 1920])
        self.assertFalse(manifest["ai_required"])
        self.assertIn("brand_end_card", [item["name"] for item in manifest["components"]])


if __name__ == "__main__":
    unittest.main()
