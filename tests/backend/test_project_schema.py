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
            "height": 0.25,
            "focal_length": 1.0,
        },
        "scene": {
            "background": "dark_stage",
            "lighting": "rim_back",
            "particles": {
                "enabled": True,
                "density": 1.0,
                "speed": 1.0,
                "opacity": 0.6,
                "color": "#FF8C2E",
            },
            "fog": False,
            "background_enhance": {
                "rim_light": True,
                "rim_light_color": "#55EEFF",
                "rim_light_energy": 100,
                "cloth_texture": True,
                "cloth_mix": 0.07,
            },
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
    project["camera"]["start_distance"] = 18.0
    project["camera"]["end_distance"] = 22.0
    project["camera"]["height"] = 0.55
    project["scene"]["particles"] = None
    project["scene"]["background_enhance"] = {
        "rim_light": False,
        "rim_light_color": "#55EEFF",
        "rim_light_energy": 100,
        "cloth_texture": False,
        "cloth_mix": 0.07,
    }
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

    def test_particles_spec_validates_correctly(self) -> None:
        from server.schemas.project import ParticlesSpec

        spec = ParticlesSpec(
            enabled=True, density=1.0, speed=1.5, opacity=0.8, color="#FF8C2E"
        )
        self.assertTrue(spec.enabled)
        self.assertEqual(spec.density, 1.0)
        self.assertEqual(spec.speed, 1.5)
        self.assertEqual(spec.opacity, 0.8)
        self.assertEqual(spec.color, "#FF8C2E")

    def test_particles_spec_rejects_bad_hex_color(self) -> None:
        from server.schemas.project import ParticlesSpec

        with self.assertRaises(ValidationError):
            ParticlesSpec(color="invalid")

    def test_particles_spec_rejects_out_of_range_density(self) -> None:
        from server.schemas.project import ParticlesSpec

        with self.assertRaises(ValidationError):
            ParticlesSpec(density=3.0)

    def test_particles_spec_rejects_out_of_range_speed(self) -> None:
        from server.schemas.project import ParticlesSpec

        with self.assertRaises(ValidationError):
            ParticlesSpec(speed=5.0)

    def test_particles_defaults_are_usable(self) -> None:
        from server.schemas.project import ParticlesSpec

        spec = ParticlesSpec()
        self.assertTrue(spec.enabled)
        self.assertEqual(spec.density, 1.0)
        self.assertEqual(spec.speed, 1.0)
        self.assertEqual(spec.opacity, 0.6)
        self.assertEqual(spec.color, "#FF8C2E")

    def test_background_enhance_spec_defaults(self) -> None:
        from server.schemas.project import BackgroundEnhanceSpec

        spec = BackgroundEnhanceSpec()
        self.assertTrue(spec.rim_light)
        self.assertEqual(spec.rim_light_color, "#55EEFF")
        self.assertEqual(spec.rim_light_energy, 100)
        self.assertTrue(spec.cloth_texture)
        self.assertEqual(spec.cloth_mix, 0.07)

    def test_background_enhance_spec_rejects_bad_energy(self) -> None:
        from server.schemas.project import BackgroundEnhanceSpec

        with self.assertRaises(ValidationError):
            BackgroundEnhanceSpec(rim_light_energy=500)

    def test_scene_spec_particles_none_means_disabled(self) -> None:
        from server.schemas.project import SceneSpec

        scene = SceneSpec(
            background="dark_stage",
            lighting="rim_back",
            particles=None,
            fog=False,
        )
        self.assertIsNone(scene.particles)
        self.assertTrue(scene.background_enhance.rim_light)

    def test_scene_spec_background_enhance_defaults_applied(self) -> None:
        project = ProjectJSON.model_validate(character_project())
        bg = project.scene.background_enhance
        self.assertTrue(bg.rim_light)
        self.assertEqual(bg.rim_light_energy, 100)

    # ── ModelTransformSpec ──────────────────────────────────────────

    def test_model_transform_defaults_to_none(self) -> None:
        from server.schemas.project import ModelTransformSpec

        spec = ModelTransformSpec()
        self.assertIsNone(spec.location)
        self.assertIsNone(spec.rotation)
        self.assertIsNone(spec.scale)

    def test_model_transform_accepts_full_override(self) -> None:
        from server.schemas.project import ModelTransformSpec

        spec = ModelTransformSpec(
            location=(1.0, 2.0, 3.0),
            rotation=(0, 45, 0),
            scale=1.5,
        )
        self.assertEqual(spec.location, (1.0, 2.0, 3.0))
        self.assertEqual(spec.rotation, (0, 45, 0))
        self.assertEqual(spec.scale, 1.5)

    def test_model_transform_rejects_negative_scale(self) -> None:
        from server.schemas.project import ModelTransformSpec

        with self.assertRaises(ValidationError):
            ModelTransformSpec(scale=-1.0)

    def test_model_transform_rejects_zero_scale(self) -> None:
        from server.schemas.project import ModelTransformSpec

        with self.assertRaises(ValidationError):
            ModelTransformSpec(scale=0)

    # ── LightDefSpec ────────────────────────────────────────────────

    def test_light_def_defaults(self) -> None:
        from server.schemas.project import LightDefSpec

        spec = LightDefSpec()
        self.assertTrue(spec.enabled)
        self.assertIsNone(spec.location)
        self.assertIsNone(spec.energy)
        self.assertIsNone(spec.color)
        self.assertIsNone(spec.size)

    def test_light_def_accepts_full_override(self) -> None:
        from server.schemas.project import LightDefSpec

        spec = LightDefSpec(
            enabled=True,
            location=(0, -3.0, 2.5),
            energy=200,
            color="#FF0000",
            size=5.0,
        )
        self.assertEqual(spec.energy, 200)
        self.assertEqual(spec.color, "#FF0000")

    def test_light_def_rejects_bad_hex(self) -> None:
        from server.schemas.project import LightDefSpec

        with self.assertRaises(ValidationError):
            LightDefSpec(color="not-a-color")

    def test_light_def_rejects_negative_energy(self) -> None:
        from server.schemas.project import LightDefSpec

        with self.assertRaises(ValidationError):
            LightDefSpec(energy=-10)

    # ── LightingOverridesSpec ───────────────────────────────────────

    def test_lighting_overrides_all_none_by_default(self) -> None:
        from server.schemas.project import LightingOverridesSpec

        spec = LightingOverridesSpec()
        self.assertIsNone(spec.key)
        self.assertIsNone(spec.rim_left)
        self.assertIsNone(spec.rim_right)
        self.assertIsNone(spec.back)
        self.assertIsNone(spec.silhouette_rim)

    def test_lighting_overrides_partial_override(self) -> None:
        from server.schemas.project import LightingOverridesSpec, LightDefSpec

        spec = LightingOverridesSpec(
            key=LightDefSpec(energy=300),
            rim_left=LightDefSpec(color="#FF8800"),
        )
        self.assertEqual(spec.key.energy, 300)
        self.assertEqual(spec.rim_left.color, "#FF8800")
        self.assertIsNone(spec.rim_right)
        self.assertIsNone(spec.back)
        self.assertIsNone(spec.silhouette_rim)

    # ── SceneSpec extended fields ───────────────────────────────────

    def test_scene_spec_model_transform_accepted(self) -> None:
        from server.schemas.project import SceneSpec

        scene = SceneSpec(
            background="dark_stage",
            lighting="rim_back",
            fog=False,
            model_transform={"location": (0, 0, 0.5)},
            lighting_overrides={
                "key": {"energy": 300},
                "rim_left": {"color": "#FF8800"},
            },
        )
        self.assertIsNotNone(scene.model_transform)
        self.assertEqual(scene.model_transform.location, (0, 0, 0.5))
        self.assertIsNotNone(scene.lighting_overrides)
        self.assertEqual(scene.lighting_overrides.key.energy, 300)

    def test_full_project_with_overrides_validates(self) -> None:
        payload = character_project()
        payload["scene"]["model_transform"] = {
            "location": [0, 0, 0.5],
            "rotation": [0, 45, 0],
            "scale": 1.2,
        }
        payload["scene"]["lighting_overrides"] = {
            "key": {"energy": 300, "color": "#FFD700"},
            "rim_left": {"enabled": False},
        }
        project = ProjectJSON.model_validate(payload)
        self.assertIsNotNone(project.scene.model_transform)
        self.assertEqual(project.scene.model_transform.scale, 1.2)
        self.assertIsNotNone(project.scene.lighting_overrides)
        self.assertEqual(project.scene.lighting_overrides.key.energy, 300)

    # ── ADJ-6: text-free support ────────────────────────────────────

    def test_text_spec_empty_title_valid(self) -> None:
        from server.schemas.project import TextSpec

        spec = TextSpec(title="", subtitle="", font_style="bold_game")
        self.assertEqual(spec.title, "")
        self.assertEqual(spec.subtitle, "")

    def test_text_free_project_validates(self) -> None:
        """ADJ-6: empty title + text_overlay=false should validate."""
        payload = character_project()
        payload["text"]["title"] = ""
        payload["text"]["subtitle"] = ""
        payload["scene"]["background_enhance"]["text_overlay"] = False
        project = ProjectJSON.model_validate(payload)
        self.assertEqual(project.text.title, "")
        self.assertFalse(project.scene.background_enhance.text_overlay)

    # ── Loop 08: interactive camera ──────────────────────────────────

    def test_camera_keyframes_accepted(self) -> None:
        """Camera spec accepts keyframes for interactive recording."""
        payload = character_project()
        payload["camera"]["keyframes"] = [
            {"t": 0.0, "pos": [0, -5, 1.5], "quat": [0, 0, 0, 1], "fov": 55},
            {"t": 2.0, "pos": [0, -3, 1.5], "quat": [0, 0, 0.3827, 0.9239], "fov": 55},
        ]
        project = ProjectJSON.model_validate(payload)
        self.assertEqual(len(project.camera.keyframes), 2)
        self.assertEqual(project.camera.keyframes[0]["t"], 0.0)

    def test_camera_shots_accepted(self) -> None:
        """Camera spec accepts shots for multi-shot interactive recording."""
        payload = character_project()
        payload["camera"]["shots"] = [
            {"index": 0, "cut": True, "keyframes": [
                {"t": 0.0, "pos": [0, -5, 1.5], "quat": [0, 0, 0, 1], "fov": 55},
                {"t": 2.0, "pos": [0, -3, 1.5], "quat": [0, 0, 0.3827, 0.9239], "fov": 55, "cut": True},
            ]},
        ]
        project = ProjectJSON.model_validate(payload)
        self.assertEqual(len(project.camera.shots), 1)
        self.assertEqual(len(project.camera.shots[0]["keyframes"]), 2)

    def test_camera_keyframes_with_cut_accepted(self) -> None:
        """Keyframes with cut=true pass schema validation."""
        payload = character_project()
        payload["camera"]["keyframes"] = [
            {"t": 0.0, "pos": [0, -5, 1.5], "quat": [0, 0, 0, 1], "fov": 55},
            {"t": 2.0, "pos": [2, -3, 1.5], "quat": [0, 0, 0.3827, 0.9239], "fov": 55, "cut": True},
            {"t": 4.0, "pos": [2, -1, 1.5], "quat": [0, 0, 0, 1], "fov": 55},
        ]
        project = ProjectJSON.model_validate(payload)
        self.assertTrue(project.camera.keyframes[1].get("cut"))


if __name__ == "__main__":
    unittest.main()
