from __future__ import annotations

import unittest
from pydantic import ValidationError

from server.schemas.project import ProjectJSON, resolve_dimensions


def character_project() -> dict:
    return {
        "version": "0.1",
        "project_id": "test-character",
        "template": "character_intro",
        "output": {
            "duration": 8,
            "fps": 24,
            "aspect_ratio": "9:16",
            "resolution": "1080p",
        },
        "assets": [
            {
                "id": "main_subject",
                "type": "image",
                "path": "storage/assets/hero.png",
            }
        ],
        "camera": {
            "motion": "dolly_in",
            "speed": 1.0,
            "start_distance": 7.2,
            "end_distance": 5.8,
            "height": 1.4,
            "focal_length": 70.0,
        },
        "scene": {
            "background": "dark_stage",
            "lighting": "rim_back",
            "particles": True,
            "fog": False,
        },
        "text": {
            "title": "New Hero Arrival",
            "subtitle": "Limited Event",
            "font_style": "bold_game",
        },
    }


def product_project() -> dict:
    project = character_project()
    project["project_id"] = "test-product"
    project["template"] = "product_orbit"
    project["output"]["aspect_ratio"] = "16:9"
    project["assets"][0] = {
        "id": "main_subject",
        "type": "glb",
        "path": "storage/assets/model.glb",
    }
    project["camera"]["motion"] = "orbit"
    project["scene"]["particles"] = False
    project["text"]["title"] = "Product Orbit"
    project["text"]["subtitle"] = "GLB Showcase"
    return project


class ProjectSchemaTests(unittest.TestCase):
    def test_valid_character_intro_schema_passes(self) -> None:
        project = ProjectJSON.model_validate(character_project())
        self.assertEqual(project.template.value, "character_intro")
        self.assertEqual(project.assets[0].type.value, "image")
        self.assertEqual(project.output.frame_count, 192)

    def test_valid_product_orbit_schema_passes(self) -> None:
        project = ProjectJSON.model_validate(product_project())
        self.assertEqual(project.template.value, "product_orbit")
        self.assertEqual(project.assets[0].type.value, "glb")
        self.assertEqual(project.output.dimensions, (1920, 1080))

    def test_invalid_template_fails(self) -> None:
        payload = character_project()
        payload["template"] = "missing_template"
        with self.assertRaises(ValidationError):
            ProjectJSON.model_validate(payload)

    def test_invalid_asset_template_combination_fails(self) -> None:
        payload = product_project()
        payload["assets"][0]["type"] = "image"
        with self.assertRaises(ValidationError):
            ProjectJSON.model_validate(payload)

    def test_ai_enhance_defaults_to_disabled(self) -> None:
        project = ProjectJSON.model_validate(character_project())
        self.assertFalse(project.ai_enhance.enabled)
        self.assertEqual(project.ai_enhance.mode.value, "conservative")

    def test_resolution_mapping_for_9_16_and_16_9(self) -> None:
        self.assertEqual(resolve_dimensions("9:16", "1080p"), (1080, 1920))
        self.assertEqual(resolve_dimensions("16:9", "1080p"), (1920, 1080))


if __name__ == "__main__":
    unittest.main()
