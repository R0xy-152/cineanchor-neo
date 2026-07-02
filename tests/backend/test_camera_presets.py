"""Unit tests for camera_presets — pure Python, no Blender dependency."""

from __future__ import annotations

import math
import unittest

from blender.scripts.camera_presets import (
    PRESETS,
    _quat_from_look,
    apply_preset,
    list_presets,
)


class QuatFromLookTests(unittest.TestCase):
    """_quat_from_look — position + target → quaternion."""

    def test_looking_along_negative_y(self) -> None:
        """Camera at (0, -5, 1) looking at (0, 0, 1) → reasonable quat."""
        quat = _quat_from_look([0, -5, 1], [0, 0, 1])
        # Must be unit length
        length = math.sqrt(sum(v * v for v in quat))
        self.assertAlmostEqual(length, 1.0, places=5)
        # All components finite
        for v in quat:
            self.assertTrue(math.isfinite(v))

    def test_same_position_as_target(self) -> None:
        """Camera at same position as target → identity quaternion."""
        quat = _quat_from_look([0, 0, 0], [0, 0, 0])
        self.assertAlmostEqual(quat[0], 0.0)
        self.assertAlmostEqual(quat[1], 0.0)
        self.assertAlmostEqual(quat[2], 0.0)
        self.assertAlmostEqual(quat[3], 1.0)

    def test_custom_up_vector(self) -> None:
        """Custom up vector still produces unit quaternion."""
        quat = _quat_from_look([5, 0, 0], [0, 0, 0], up=(0, 1, 0))
        length = math.sqrt(sum(v * v for v in quat))
        self.assertAlmostEqual(length, 1.0, places=5)

    def test_result_is_unit_regression(self) -> None:
        """Spot-check: quaternion from a typical scene position is unit."""
        quat = _quat_from_look([3.0, -5.0, 1.5], [0.0, 0.0, 0.3])
        length = math.sqrt(sum(v * v for v in quat))
        self.assertAlmostEqual(length, 1.0, places=5)


class ApplyPresetTests(unittest.TestCase):
    """apply_preset — each preset generates valid keyframes."""

    SCENE_CENTER = [0.0, 0.0, 0.3]
    SCENE_RADIUS = 1.5

    def _assert_valid_keyframes(
        self, kfs: list[dict], min_count: int = 3
    ) -> None:
        """Common assertions for a valid keyframe list."""
        self.assertGreaterEqual(
            len(kfs), min_count,
            f"Expected ≥{min_count} keyframes, got {len(kfs)}"
        )
        required = {"t", "pos", "quat", "fov"}
        for kf in kfs:
            self.assertTrue(
                required.issubset(kf.keys()),
                f"Keyframe missing fields: {required - kf.keys()}"
            )
            self.assertEqual(len(kf["pos"]), 3)
            self.assertEqual(len(kf["quat"]), 4)
            self.assertIsInstance(kf["fov"], (int, float))
            # Quaternion must be unit
            length = math.sqrt(sum(v * v for v in kf["quat"]))
            self.assertAlmostEqual(length, 1.0, places=3)

    def _assert_positions_in_range(
        self, kfs: list[dict], max_dist: float = 30.0
    ) -> None:
        """Positions must be within reasonable distance of scene center."""
        cx, cy, cz = self.SCENE_CENTER
        for kf in kfs:
            px, py, pz = kf["pos"]
            dist = math.sqrt(
                (px - cx) ** 2 + (py - cy) ** 2 + (pz - cz) ** 2
            )
            self.assertLess(
                dist, max_dist,
                f"Position {kf['pos']} is {dist:.1f} from center (max {max_dist})"
            )

    def test_nolan_orbit(self) -> None:
        kfs = apply_preset("nolan_orbit", self.SCENE_CENTER, self.SCENE_RADIUS)
        self._assert_valid_keyframes(kfs)
        self._assert_positions_in_range(kfs)

    def test_anime_closeup(self) -> None:
        kfs = apply_preset("anime_closeup", self.SCENE_CENTER, self.SCENE_RADIUS)
        self._assert_valid_keyframes(kfs)
        self._assert_positions_in_range(kfs)
        # FOV should decrease (close-up effect)
        self.assertLess(kfs[-1]["fov"], kfs[0]["fov"])

    def test_dolly_reveal(self) -> None:
        kfs = apply_preset("dolly_reveal", self.SCENE_CENTER, self.SCENE_RADIUS)
        self._assert_valid_keyframes(kfs)
        self._assert_positions_in_range(kfs)

    def test_drone_ascend(self) -> None:
        kfs = apply_preset("drone_ascend", self.SCENE_CENTER, self.SCENE_RADIUS)
        self._assert_valid_keyframes(kfs)
        self._assert_positions_in_range(kfs)
        # Should ascend: last Z > first Z
        self.assertGreater(kfs[-1]["pos"][2], kfs[0]["pos"][2])

    def test_hero_tracking(self) -> None:
        kfs = apply_preset("hero_tracking", self.SCENE_CENTER, self.SCENE_RADIUS)
        self._assert_valid_keyframes(kfs)
        self._assert_positions_in_range(kfs)

    def test_suspense_pan(self) -> None:
        kfs = apply_preset("suspense_pan", self.SCENE_CENTER, self.SCENE_RADIUS)
        self._assert_valid_keyframes(kfs)
        self._assert_positions_in_range(kfs)

    def test_god_eye(self) -> None:
        kfs = apply_preset("god_eye", self.SCENE_CENTER, self.SCENE_RADIUS)
        self._assert_valid_keyframes(kfs)
        self._assert_positions_in_range(kfs)
        # Should be high above: last Z >> scene_center Z
        self.assertGreater(kfs[-1]["pos"][2], self.SCENE_CENTER[2] + 5.0)

    def test_whip_pan(self) -> None:
        kfs = apply_preset("whip_pan", self.SCENE_CENTER, self.SCENE_RADIUS)
        self._assert_valid_keyframes(kfs)
        self._assert_positions_in_range(kfs)

    def test_unknown_preset_raises_keyerror(self) -> None:
        with self.assertRaises(KeyError):
            apply_preset("nonexistent_preset", self.SCENE_CENTER, 1.0)

    def test_custom_num_keyframes(self) -> None:
        kfs = apply_preset(
            "nolan_orbit", self.SCENE_CENTER, self.SCENE_RADIUS,
            num_keyframes=10,
        )
        self.assertEqual(len(kfs), 10)

    def test_zero_radius(self) -> None:
        """Zero radius should not crash (produces distance=0 for some params)."""
        kfs = apply_preset("nolan_orbit", self.SCENE_CENTER, 0.0)
        self._assert_valid_keyframes(kfs)


class ListPresetsTests(unittest.TestCase):
    """list_presets — returns all 8 entries."""

    def test_returns_eight(self) -> None:
        result = list_presets()
        self.assertEqual(len(result), 8)
        preset_ids = {p["id"] for p in result}
        self.assertEqual(preset_ids, set(PRESETS.keys()))

    def test_each_has_required_fields(self) -> None:
        for entry in list_presets():
            self.assertIn("id", entry)
            self.assertIn("name", entry)
            self.assertIn("description", entry)

    def test_matches_presets_dict(self) -> None:
        for entry in list_presets():
            self.assertEqual(entry["name"], PRESETS[entry["id"]]["name"])
            self.assertEqual(
                entry["description"], PRESETS[entry["id"]]["description"]
            )
