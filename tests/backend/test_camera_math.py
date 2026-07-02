"""Unit tests for camera_math — pure Python, no Blender dependency."""

from __future__ import annotations

import math
import unittest

from blender.scripts.camera_math import (
    catmull_rom,
    catmull_rom_vec,
    interpolate_keyframes,
    slerp,
    target_from_quat,
    three_to_blender_pose,
)


class CatmullRomTests(unittest.TestCase):
    """catmull_rom scalar interpolation."""

    def test_identity_four_equal(self) -> None:
        """Four equal control points → constant output at any t."""
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            self.assertAlmostEqual(catmull_rom(5.0, 5.0, 5.0, 5.0, t), 5.0)

    def test_linear_segment(self) -> None:
        """Linear ramp: 0, 1, 2, 3 → passes through middle at t=0.5."""
        # At t=0, catmull_rom(0,1,2,3, 0) = 1.0 (segment starts at p1)
        self.assertAlmostEqual(catmull_rom(0.0, 1.0, 2.0, 3.0, 0.0), 1.0)
        # At t=1, catmull_rom(0,1,2,3, 1) = 2.0 (segment ends at p2)
        self.assertAlmostEqual(catmull_rom(0.0, 1.0, 2.0, 3.0, 1.0), 2.0)
        # At t=0.5, midpoint ≈ 1.5 (linear interpolation through middle)
        self.assertAlmostEqual(catmull_rom(0.0, 1.0, 2.0, 3.0, 0.5), 1.5)

    def test_curved_segment(self) -> None:
        """Non-collinear control points produce curved output."""
        # p0=0, p1=1, p2=3, p3=10 → t=0.5 should not be simple midpoint
        val = catmull_rom(0.0, 1.0, 3.0, 10.0, 0.5)
        # Should differ from linear midpoint 2.0
        self.assertNotAlmostEqual(val, 2.0, places=3)

    def test_t_range(self) -> None:
        """t outside [0,1] extrapolates (expected Catmull-Rom behaviour)."""
        val0 = catmull_rom(0.0, 1.0, 2.0, 3.0, 0.0)
        val1 = catmull_rom(0.0, 1.0, 2.0, 3.0, 1.0)
        self.assertAlmostEqual(val0, 1.0)
        self.assertAlmostEqual(val1, 2.0)


class CatmullRomVecTests(unittest.TestCase):
    """catmull_rom_vec per-component vector interpolation."""

    def test_identity(self) -> None:
        v = [1.0, 2.0, 3.0]
        result = catmull_rom_vec(v, v, v, v, 0.5)
        self.assertEqual(len(result), 3)
        for i, expected in enumerate(v):
            self.assertAlmostEqual(result[i], expected)

    def test_linear_ramp(self) -> None:
        result = catmull_rom_vec([0, 0, 0], [1, 2, 3], [2, 4, 6], [3, 6, 9], 0.0)
        self.assertAlmostEqual(result[0], 1.0)
        self.assertAlmostEqual(result[1], 2.0)
        self.assertAlmostEqual(result[2], 3.0)


class SlerpTests(unittest.TestCase):
    """SLERP quaternion interpolation."""

    def test_identity(self) -> None:
        q = [0.0, 0.0, 0.0, 1.0]
        for t in (0.0, 0.5, 1.0):
            result = slerp(q, q, t)
            for i in range(4):
                self.assertAlmostEqual(result[i], q[i], places=5)

    def test_midpoint_unit(self) -> None:
        """SLERP result must always be unit quaternion."""
        q0 = [0.0, 0.0, 0.0, 1.0]  # identity
        q1 = [0.0, 0.0, math.sin(math.pi / 4), math.cos(math.pi / 4)]  # 90° Z-rot
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            result = slerp(q0, q1, t)
            length = math.sqrt(sum(v * v for v in result))
            self.assertAlmostEqual(length, 1.0, places=5)

    def test_short_path_flip(self) -> None:
        """When dot < 0, slerp takes the short path via -q1."""
        q0 = [0.0, 0.0, 0.0, 1.0]
        q1_neg = [0.0, 0.0, 0.0, -1.0]  # same rotation as identity
        # slerp(identity, -identity, 0.5) should stay near identity
        result = slerp(q0, q1_neg, 0.5)
        length = math.sqrt(sum(v * v for v in result))
        self.assertAlmostEqual(length, 1.0, places=5)
        # Should be close to identity (short path)
        self.assertAlmostEqual(result[3], 1.0, places=2)

    def test_near_parallel_fallback(self) -> None:
        """Near-parallel quaternions fall back to LERP + renormalise."""
        q0 = [0.0, 0.0, 0.0, 1.0]
        # Very small rotation (dot > 0.9995)
        eps = 1e-5
        q1 = [eps, 0.0, 0.0, math.sqrt(1 - eps * eps)]
        result = slerp(q0, q1, 0.5)
        length = math.sqrt(sum(v * v for v in result))
        self.assertAlmostEqual(length, 1.0, places=5)

    def test_orthogonal_t0_t1(self) -> None:
        """t=0 returns q0, t=1 returns q1."""
        q0 = [1.0, 0.0, 0.0, 0.0]
        q1 = [0.0, 1.0, 0.0, 0.0]
        r0 = slerp(q0, q1, 0.0)
        r1 = slerp(q0, q1, 1.0)
        for i in range(4):
            self.assertAlmostEqual(r0[i], q0[i], places=5)
            self.assertAlmostEqual(r1[i], q1[i], places=5)


class InterpolateKeyframesTests(unittest.TestCase):
    """interpolate_keyframes — keyframe list → per-frame data."""

    def test_two_keyframes_frame_count(self) -> None:
        kfs = [
            {"t": 0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 55},
            {"t": 2, "pos": [10, 0, 0], "quat": [0, 0, 0, 1], "fov": 55},
        ]
        fps = 24
        frames = interpolate_keyframes(kfs, fps)
        # 2 seconds * 24 fps + 1 = 49 frames (inclusive of both ends)
        self.assertEqual(len(frames), 2 * fps + 1)
        self.assertAlmostEqual(frames[0]["t"], 0.0)
        self.assertAlmostEqual(frames[-1]["t"], 2.0)

    def test_four_keyframes_pass_through(self) -> None:
        """Interpolated frames should pass through each keyframe moment."""
        kfs = [
            {"t": 0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 50},
            {"t": 1, "pos": [5, 0, 0], "quat": [0, 0, 0, 1], "fov": 55},
            {"t": 2, "pos": [5, 5, 0], "quat": [0, 0, 0, 1], "fov": 60},
            {"t": 3, "pos": [0, 5, 5], "quat": [0, 0, 0, 1], "fov": 50},
        ]
        fps = 10
        frames = interpolate_keyframes(kfs, fps)

        for kf in kfs:
            frame_at_t = next(f for f in frames if abs(f["t"] - kf["t"]) < 0.001)
            for i in range(3):
                self.assertAlmostEqual(frame_at_t["pos"][i], kf["pos"][i], places=2)

    def test_fov_interpolation(self) -> None:
        kfs = [
            {"t": 0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 40},
            {"t": 1, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 60},
        ]
        fps = 10
        frames = interpolate_keyframes(kfs, fps)
        self.assertAlmostEqual(frames[0]["fov"], 40.0)
        self.assertAlmostEqual(frames[-1]["fov"], 60.0)
        # Mid-frame should be ≈ 50
        mid = frames[len(frames) // 2]
        self.assertAlmostEqual(mid["fov"], 50.0, delta=2.0)

    def test_target_interpolation(self) -> None:
        kfs = [
            {"t": 0, "pos": [0, -5, 1], "quat": [0, 0, 0, 1], "fov": 55,
             "target": [0, 0, 0]},
            {"t": 1, "pos": [5, -5, 1], "quat": [0, 0, 0, 1], "fov": 55,
             "target": [5, 0, 0]},
        ]
        fps = 10
        frames = interpolate_keyframes(kfs, fps)
        self.assertIn("target", frames[0])
        self.assertAlmostEqual(frames[0]["target"][0], 0.0)
        self.assertAlmostEqual(frames[-1]["target"][0], 5.0)

    def test_target_not_present_on_partial_kfs(self) -> None:
        """If some KFs lack target, no target is emitted."""
        kfs = [
            {"t": 0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 55,
             "target": [0, 0, 0]},
            {"t": 1, "pos": [1, 0, 0], "quat": [0, 0, 0, 1], "fov": 55},
        ]
        fps = 10
        frames = interpolate_keyframes(kfs, fps)
        self.assertNotIn("target", frames[0])

    def test_zero_duration_segment(self) -> None:
        """Duplicate-timestamp keyframes → local_t ends up 0, no division by zero."""
        kfs = [
            {"t": 0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 55},
            {"t": 0, "pos": [1, 0, 0], "quat": [0, 0, 0, 1], "fov": 55},
        ]
        frames = interpolate_keyframes(kfs, 24)
        # Should still produce frames without error
        self.assertGreater(len(frames), 0)

    def test_single_keyframe(self) -> None:
        kfs = [{"t": 0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 55}]
        result = interpolate_keyframes(kfs, 24)
        # Returns unchanged (fewer than 2 KFs)
        self.assertEqual(result, kfs)

    def test_quaternion_is_unit(self) -> None:
        kfs = [
            {"t": 0, "pos": [0, 0, 0], "quat": [0.0, 0.0, 0.0, 1.0], "fov": 55},
            {"t": 2, "pos": [0, 0, 0],
             "quat": [0.0, 0.0, math.sin(math.pi / 4), math.cos(math.pi / 4)],
             "fov": 55},
        ]
        frames = interpolate_keyframes(kfs, 10)
        for f in frames:
            length = math.sqrt(sum(v * v for v in f["quat"]))
            self.assertAlmostEqual(length, 1.0, places=5)


class ThreeToBlenderPoseTests(unittest.TestCase):
    """Coordinate conversion Three.js (Y-up) → Blender (Z-up)."""

    def test_origin(self) -> None:
        pos, target = three_to_blender_pose([0, 0, 0], [0, 0, 0])
        self.assertEqual(pos, (0, 0, 0))
        self.assertEqual(target, (0, 0, 0))

    def test_known_conversion(self) -> None:
        """Three.js (1, 2, 3) → Blender (1, -3, 2)."""
        pos, target = three_to_blender_pose([1, 2, 3], [4, 5, 6])
        self.assertAlmostEqual(pos[0], 1.0)
        self.assertAlmostEqual(pos[1], -3.0)
        self.assertAlmostEqual(pos[2], 2.0)
        self.assertAlmostEqual(target[0], 4.0)
        self.assertAlmostEqual(target[1], -6.0)
        self.assertAlmostEqual(target[2], 5.0)

    def test_up_axis_conversion(self) -> None:
        """Three.js Y-up vector → Blender Z-up."""
        # (0, 1, 0) in Three.js = up → (0, 0, 1) in Blender
        pos, _ = three_to_blender_pose([0, 1, 0], [0, 0, 0])
        self.assertAlmostEqual(pos[2], 1.0)
        self.assertAlmostEqual(pos[1], 0.0)


class TargetFromQuatTests(unittest.TestCase):
    """Estimate look-at target from camera quaternion."""

    def test_identity_quaternion(self) -> None:
        """Identity quaternion → target along -Z from position."""
        result = target_from_quat([0, 0, 0], [0, 0, 0, 1], target_dist=5.0)
        # Should be (0, 0, -5) = 5 units along Three.js -Z
        self.assertAlmostEqual(result[0], 0.0)
        self.assertAlmostEqual(result[1], 0.0)
        self.assertAlmostEqual(result[2], -5.0)

    def test_non_origin_position(self) -> None:
        result = target_from_quat([1, 2, 3], [0, 0, 0, 1], target_dist=10.0)
        self.assertAlmostEqual(result[0], 1.0)
        self.assertAlmostEqual(result[1], 2.0)
        self.assertAlmostEqual(result[2], -7.0)  # 3 - 10

    def test_zero_length_forward(self) -> None:
        """Degenerate quaternion → falls back to default forward."""
        # Zero quaternion should trigger flen < 0.001
        result = target_from_quat([0, 0, 0], [0, 0, 0, 0], target_dist=3.0)
        self.assertAlmostEqual(result[0], 0.0)
        self.assertAlmostEqual(result[1], 0.0)
        self.assertAlmostEqual(result[2], -3.0)

    def test_result_is_list(self) -> None:
        result = target_from_quat([0, 0, 0], [0, 0, 0, 1])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
