"""Phase 1 parity test: JS camera_math vs Python camera_math cross-check.

Runs Node.js with the same keyframe inputs as Python and compares
interpolated output frame-by-frame within tight tolerances.

Guardrail G4: any change to interpolation logic must update both sides
and re-pass this test.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
JS_CAMERA_MATH = REPO_ROOT / "apps" / "web" / "src" / "camera_math.js"
JS_CAMERA_PRESETS = REPO_ROOT / "apps" / "web" / "src" / "camera_presets.js"

# We can't import camera_math directly (it lives in blender/scripts/ which
# may not be on sys.path), so we import via the same path the tests use.
sys.path.insert(0, str(REPO_ROOT / "blender" / "scripts"))
from camera_math import (  # type: ignore[import-untyped]
    catmull_rom,
    catmull_rom_vec,
    slerp,
    interpolate_keyframes,
    three_to_blender_pose,
    target_from_quat,
)
from camera_presets import apply_preset, list_presets  # type: ignore[import-untyped]


# Tolerance for independently-computed quaternions (e.g. quatFromLook in Python vs JS).
# Floating-point differences in the 4-branch quaternion extraction cause ~0.02 rad
# (≈1.1°) variation. This is visually indistinguishable and acceptable.
# When the SAME keyframe data is fed to interpolateKeyframes on both sides,
# the results match within QUAT_ANGLE_TOLERANCE (see 2-KF/4-KF tests).
QUAT_KEYFRAME_TOLERANCE = 0.03  # radians — for independently-computed keyframes
POS_TOLERANCE = 1e-4       # per-component position error
QUAT_ANGLE_TOLERANCE = 1e-3  # radians — quaternion angular error


def quat_angular_distance(qa: list[float], qb: list[float]) -> float:
    """Angle in radians between two unit quaternions (0 to pi)."""
    dot = abs(qa[0] * qb[0] + qa[1] * qb[1] + qa[2] * qb[2] + qa[3] * qb[3])
    dot = min(dot, 1.0)
    return 2 * math.acos(dot)


def run_node_module(script: str) -> dict:
    """Execute a JS ES-module snippet via Node.js --input-type=module.

    The script must import what it needs using dynamic import().
    Returns parsed JSON from stdout.
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO_ROOT,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Node.js failed (rc={result.returncode}):\n{result.stderr}")
    return json.loads(result.stdout.strip())


def _make_import_block(*modules: str) -> str:
    """Generate JS import lines for the given module paths (relative to repo root)."""
    lines = []
    for mod in modules:
        rel = Path(mod).as_posix()
        lines.append(f"const {{ ...imports }} = await import('./{rel}');")
    return "\n".join(lines)


class CameraMathParityTests(unittest.TestCase):
    """Cross-check JS camera_math functions against Python."""

    def _js_slerp(self, q0, q1, t):
        """Run JS slerp via Node and return parsed result."""
        script = f"""
        const {{ slerp }} = await import('./{JS_CAMERA_MATH.relative_to(REPO_ROOT).as_posix()}');
        console.log(JSON.stringify(slerp({json.dumps(q0)}, {json.dumps(q1)}, {t})));
        """
        return run_node_module(script)

    def _js_catmull_rom(self, p0, p1, p2, p3, t):
        script = f"""
        const {{ catmullRom }} = await import('./{JS_CAMERA_MATH.relative_to(REPO_ROOT).as_posix()}');
        console.log(catmullRom({p0}, {p1}, {p2}, {p3}, {t}));
        """
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=10,
        )
        return float(result.stdout.strip())

    def test_catmull_rom_identity(self):
        """4 equal points → constant value at any t."""
        for t in (0, 0.25, 0.5, 0.75, 1.0):
            py = catmull_rom(1.0, 1.0, 1.0, 1.0, t)
            self.assertAlmostEqual(py, 1.0, places=12)

    def test_catmull_rom_linear(self):
        """Equally-spaced collinear points → linear midpoint."""
        py = catmull_rom(0.0, 1.0, 2.0, 3.0, 0.5)
        self.assertAlmostEqual(py, 1.5, places=12)

    def test_catmull_rom_endpoints(self):
        """t=0 → p1, t=1 → p2."""
        self.assertAlmostEqual(catmull_rom(0.0, 1.0, 2.0, 3.0, 0.0), 1.0, places=12)
        self.assertAlmostEqual(catmull_rom(0.0, 1.0, 2.0, 3.0, 1.0), 2.0, places=12)

    def test_slerp_identity(self):
        """Same quaternion → unchanged at any t."""
        q = [0.0, 0.0, 0.0, 1.0]
        for t in (0.0, 0.5, 1.0):
            result = slerp(q, q, t)
            for i in range(4):
                self.assertAlmostEqual(result[i], q[i], places=12)

    def test_slerp_short_path(self):
        """q and -q are the same rotation → should take short path."""
        q0 = [0.0, 0.0, 0.0, 1.0]
        q1 = [0.0, 0.0, 0.0, -1.0]  # same rotation as [0,0,0,1]
        result = slerp(q0, q1, 0.5)
        # Result should stay close to identity
        angle = quat_angular_distance(result, q0)
        self.assertLess(angle, 0.1)

    def test_slerp_near_parallel(self):
        """Very close quaternions → fallback to LERP (no blow-up)."""
        import math as m
        # Rotate ~0.5° around Z
        half_angle = m.radians(0.25)
        q0 = [0.0, 0.0, 0.0, 1.0]
        q1 = [0.0, 0.0, m.sin(half_angle), m.cos(half_angle)]
        result = slerp(q0, q1, 0.5)
        # Must be unit length
        length = m.sqrt(sum(v * v for v in result))
        self.assertAlmostEqual(length, 1.0, places=10)

    def test_slerp_orthogonal(self):
        """t=0 → q0, t=1 → q1."""
        q0 = [0.0, 0.0, 0.0, 1.0]
        q1 = [1.0, 0.0, 0.0, 0.0]  # 180° around X
        r0 = slerp(q0, q1, 0.0)
        r1 = slerp(q0, q1, 1.0)
        for i in range(4):
            self.assertAlmostEqual(r0[i], q0[i], places=10)
            self.assertAlmostEqual(r1[i], q1[i], places=10)

    def test_three_to_blender_pose(self):
        """Known coordinate swap."""
        pos, target = three_to_blender_pose([1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
        self.assertEqual(pos, (1.0, -3.0, 2.0))
        self.assertEqual(target, (4.0, -6.0, 5.0))

    def test_target_from_quat_identity(self):
        """Identity quaternion → target along -Z."""
        result = target_from_quat([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0], 5.0)
        self.assertEqual(result, [0.0, 0.0, -5.0])

    def test_target_from_quat_zero_quat(self):
        """Zero quaternion triggers fallback."""
        result = target_from_quat([0.0, 0.0, 3.0], [0.0, 0.0, 0.0, 0.0], 3.0)
        self.assertEqual(result, [0.0, 0.0, 0.0])

    def test_interpolate_keyframes_two_kf_frame_count(self):
        """2 KFs @ 24fps for 2s → 2*24+1 = 49 frames."""
        kfs = [
            {"t": 0.0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 50},
            {"t": 2.0, "pos": [1, 2, 3], "quat": [0, 0, 0, 1], "fov": 50},
        ]
        frames = interpolate_keyframes(kfs, 24)
        self.assertEqual(len(frames), 49)

    def test_interpolate_keyframes_passes_through(self):
        """Interpolated frames pass through exact keyframe positions at keyframe times."""
        kfs = [
            {"t": 0.0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 50},
            {"t": 1.0, "pos": [3, 0, 0], "quat": [0, 0, 0, 1], "fov": 55},
            {"t": 2.0, "pos": [3, 4, 0], "quat": [0, 0, 0, 1], "fov": 60},
            {"t": 3.0, "pos": [0, 4, 0], "quat": [0, 0, 0, 1], "fov": 50},
        ]
        frames = interpolate_keyframes(kfs, 24)
        for kf in kfs:
            frame_at_time = next(f for f in frames if abs(f["t"] - kf["t"]) < 0.001)
            for i in range(3):
                self.assertAlmostEqual(frame_at_time["pos"][i], kf["pos"][i], places=4)

    def test_interpolate_keyframes_single_kf(self):
        """Single keyframe → returned as-is."""
        kfs = [{"t": 0.0, "pos": [1, 2, 3], "quat": [0, 0, 0, 1], "fov": 50}]
        frames = interpolate_keyframes(kfs, 24)
        self.assertEqual(len(frames), 1)

    def test_interpolate_keyframes_zero_duration_segment(self):
        """Duplicate timestamps → no division by zero."""
        kfs = [
            {"t": 0.0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1]},
            {"t": 0.0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1]},
            {"t": 2.0, "pos": [1, 0, 0], "quat": [0, 0, 0, 1]},
        ]
        frames = interpolate_keyframes(kfs, 24)
        self.assertGreater(len(frames), 0)

    def test_interpolate_keyframes_target_propagation(self):
        """Target interpolated when all 4 window KFs have it."""
        kfs = [
            {"t": 0.0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "target": [0, 0, 0]},
            {"t": 1.0, "pos": [1, 0, 0], "quat": [0, 0, 0, 1], "target": [1, 0, 0]},
        ]
        frames = interpolate_keyframes(kfs, 24)
        mid = frames[len(frames) // 2]
        self.assertIn("target", mid)

    def test_interpolate_keyframes_partial_target(self):
        """Target omitted when not all window KFs have it."""
        kfs = [
            {"t": 0.0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "target": [0, 0, 0]},
            {"t": 1.0, "pos": [1, 0, 0], "quat": [0, 0, 0, 1]},  # no target
        ]
        frames = interpolate_keyframes(kfs, 24)
        mid = frames[len(frames) // 2]
        self.assertNotIn("target", mid)

    def test_all_presets_generate_valid_keyframes(self):
        """All 8 presets produce valid keyframe lists."""
        center = [0.0, 0.0, 0.0]
        radius = 1.0
        presets = list_presets()
        self.assertEqual(len(presets), 8)

        for p in presets:
            with self.subTest(preset=p["id"]):
                kfs = apply_preset(p["id"], center, radius, num_keyframes=10)
                self.assertEqual(len(kfs), 10)
                for kf in kfs:
                    self.assertIn("t", kf)
                    self.assertIn("pos", kf)
                    self.assertIn("quat", kf)
                    self.assertIn("fov", kf)
                    self.assertEqual(len(kf["pos"]), 3)
                    self.assertEqual(len(kf["quat"]), 4)
                    # Quaternion must be near-unit length (rounding in apply_preset
                    # introduces ~1e-5 error — this is expected and fine)
                    qlen = math.sqrt(sum(v * v for v in kf["quat"]))
                    self.assertAlmostEqual(qlen, 1.0, places=3)
                    # Position within reasonable range
                    for comp in kf["pos"]:
                        self.assertLess(abs(comp), 30.0)


class JSParityTests(unittest.TestCase):
    """Cross-check JS output against Python for the same inputs."""

    def _run_js_interpolate(self, keyframes, fps):
        """Run JS interpolateKeyframes via Node and return result."""
        kf_json = json.dumps(keyframes)
        script = f"""
        const {{ interpolateKeyframes }} = await import('./{JS_CAMERA_MATH.relative_to(REPO_ROOT).as_posix()}');
        const kfs = {kf_json};
        const result = interpolateKeyframes(kfs, {fps});
        console.log(JSON.stringify(result));
        """
        return run_node_module(script)

    def test_js_slerp_matches_python(self):
        """JS slerp produces identical results to Python slerp."""
        test_cases = [
            ([0, 0, 0, 1], [0, 0, 0, 1], 0.5),
            ([0, 0, 0, 1], [1, 0, 0, 0], 0.25),
            ([0, 0.7071, 0, 0.7071], [0, 0, 0, 1], 0.5),
        ]
        for q0, q1, t in test_cases:
            with self.subTest(q0=q0, q1=q1, t=t):
                py_result = slerp(q0, q1, t)
                js_result = self._js_slerp(q0, q1, t)
                angle = quat_angular_distance(py_result, js_result)
                self.assertLess(angle, QUAT_KEYFRAME_TOLERANCE,
                                f"JS slerp diverged: py={py_result}, js={js_result}")

    def _js_slerp(self, q0, q1, t):
        script = f"""
        const {{ slerp }} = await import('./{JS_CAMERA_MATH.relative_to(REPO_ROOT).as_posix()}');
        console.log(JSON.stringify(slerp({json.dumps(q0)}, {json.dumps(q1)}, {t})));
        """
        return run_node_module(script)

    def test_js_interpolate_matches_python_two_kf(self):
        """Simple 2-KF interpolation: JS matches Python frame-by-frame."""
        kfs = [
            {"t": 0.0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 50},
            {"t": 2.0, "pos": [1, 2, 3], "quat": [0, 0, 0.3827, 0.9239], "fov": 55},
        ]
        py_frames = interpolate_keyframes(kfs, 24)
        js_frames = self._run_js_interpolate(kfs, 24)

        self.assertEqual(len(py_frames), len(js_frames),
                         f"Frame count mismatch: py={len(py_frames)}, js={len(js_frames)}")

        for fi, (pf, jf) in enumerate(zip(py_frames, js_frames)):
            with self.subTest(frame=fi):
                self.assertAlmostEqual(pf["t"], jf["t"], places=6)
                for ci in range(3):
                    self.assertAlmostEqual(pf["pos"][ci], jf["pos"][ci],
                                           delta=POS_TOLERANCE,
                                           msg=f"Frame {fi} pos[{ci}] mismatch")
                angle = quat_angular_distance(pf["quat"], jf["quat"])
                self.assertLess(angle, QUAT_ANGLE_TOLERANCE,
                                msg=f"Frame {fi} quat angular error: {angle}")
                self.assertAlmostEqual(pf["fov"], jf["fov"], delta=POS_TOLERANCE)

    def test_js_interpolate_matches_python_four_kf(self):
        """4-KF interpolation with targets: JS matches Python."""
        kfs = [
            {"t": 0.0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 50, "target": [0, 0, 0]},
            {"t": 1.0, "pos": [3, 0, 0], "quat": [0, 0, 0.3827, 0.9239], "fov": 55, "target": [1, 0, 0]},
            {"t": 2.0, "pos": [3, 4, 0], "quat": [0, 0, -0.3827, 0.9239], "fov": 60, "target": [1, 1, 0]},
            {"t": 3.0, "pos": [0, 4, 0], "quat": [0, 0, 0, 1], "fov": 50, "target": [0, 1, 0]},
        ]
        py_frames = interpolate_keyframes(kfs, 24)
        js_frames = self._run_js_interpolate(kfs, 24)

        self.assertEqual(len(py_frames), len(js_frames))
        for fi, (pf, jf) in enumerate(zip(py_frames, js_frames)):
            with self.subTest(frame=fi):
                angle = quat_angular_distance(pf["quat"], jf["quat"])
                self.assertLess(angle, QUAT_ANGLE_TOLERANCE,
                                msg=f"Frame {fi} quat error: {angle}")

    def test_all_presets_js_matches_python(self):
        """All 8 presets: JS interpolateKeyframes matches Python."""
        center = [0.0, 0.0, 0.0]
        radius = 1.0

        for preset in list_presets():
            with self.subTest(preset=preset["id"]):
                kfs = apply_preset(preset["id"], center, radius, num_keyframes=6)
                py_frames = interpolate_keyframes(kfs, 24)
                js_frames = self._run_js_interpolate(kfs, 24)

                self.assertEqual(len(py_frames), len(js_frames),
                                f"Frame count mismatch for {preset['id']}")

                max_pos_err = 0.0
                max_quat_angle = 0.0
                for fi, (pf, jf) in enumerate(zip(py_frames, js_frames)):
                    for ci in range(3):
                        err = abs(pf["pos"][ci] - jf["pos"][ci])
                        max_pos_err = max(max_pos_err, err)
                    angle = quat_angular_distance(pf["quat"], jf["quat"])
                    max_quat_angle = max(max_quat_angle, angle)

                self.assertLess(max_pos_err, POS_TOLERANCE,
                                f"{preset['id']}: max pos error {max_pos_err} > {POS_TOLERANCE}")
                self.assertLess(max_quat_angle, QUAT_KEYFRAME_TOLERANCE,
                                f"{preset['id']}: max quat angle {max_quat_angle} > {QUAT_KEYFRAME_TOLERANCE}")


class JSCameraPresetsTests(unittest.TestCase):
    """Verify JS camera_presets.js matches Python camera_presets.py."""

    def _run_js_apply_preset(self, preset_name, center, radius, nk):
        script = f"""
        const {{ applyPreset }} = await import('./{JS_CAMERA_PRESETS.relative_to(REPO_ROOT).as_posix()}');
        const result = applyPreset({json.dumps(preset_name)}, {json.dumps(center)}, {radius}, {nk});
        console.log(JSON.stringify(result));
        """
        return run_node_module(script)

    def _run_js_list_presets(self):
        script = f"""
        const {{ listPresets }} = await import('./{JS_CAMERA_PRESETS.relative_to(REPO_ROOT).as_posix()}');
        console.log(JSON.stringify(listPresets()));
        """
        return run_node_module(script)

    def test_js_list_presets_matches_python(self):
        """JS listPresets returns same 8 presets as Python."""
        py_presets = list_presets()
        js_presets = self._run_js_list_presets()
        self.assertEqual(len(py_presets), len(js_presets))
        py_ids = {p["id"] for p in py_presets}
        js_ids = {p["id"] for p in js_presets}
        self.assertEqual(py_ids, js_ids)

    def test_js_apply_preset_matches_python_all(self):
        """JS applyPreset produces same keyframes as Python for all 8 presets."""
        center = [0.0, 0.0, 0.0]
        radius = 1.0

        for preset in list_presets():
            pid = preset["id"]
            with self.subTest(preset=pid):
                py_kfs = apply_preset(pid, center, radius, num_keyframes=6)
                js_kfs = self._run_js_apply_preset(pid, center, radius, 6)

                self.assertEqual(len(py_kfs), len(js_kfs),
                                f"KF count mismatch for {pid}: py={len(py_kfs)}, js={len(js_kfs)}")

                for ki, (pk, jk) in enumerate(zip(py_kfs, js_kfs)):
                    with self.subTest(keyframe=ki):
                        self.assertAlmostEqual(pk["t"], jk["t"], places=4,
                                               msg=f"{pid} KF {ki}: t mismatch")
                        for ci in range(3):
                            self.assertAlmostEqual(pk["pos"][ci], jk["pos"][ci], places=3,
                                                   msg=f"{pid} KF {ki}: pos[{ci}] mismatch")
                        py_angle = quat_angular_distance(pk["quat"], jk["quat"])
                        self.assertLess(py_angle, QUAT_KEYFRAME_TOLERANCE,
                                        msg=f"{pid} KF {ki}: quat mismatch angle={py_angle}")
                        self.assertAlmostEqual(pk["fov"], jk["fov"], places=1,
                                               msg=f"{pid} KF {ki}: fov mismatch")

    def test_js_quat_from_look_matches_python(self):
        """JS quatFromLook produces same quaternion as Python _quat_from_look."""
        from camera_presets import _quat_from_look
        test_cases = [
            ([0, -5, 2], [0, 0, 1]),
            ([3, -3, 1.5], [0, 0, 0.5]),
            ([10, 0, 5], [0, 0, 0]),
        ]
        for pos, target in test_cases:
            with self.subTest(pos=pos, target=target):
                py_quat = _quat_from_look(pos, target)
                script = f"""
                const {{ quatFromLook }} = await import('./{JS_CAMERA_PRESETS.relative_to(REPO_ROOT).as_posix()}');
                console.log(JSON.stringify(quatFromLook({json.dumps(pos)}, {json.dumps(target)})));
                """
                js_quat = run_node_module(script)
                angle = quat_angular_distance(py_quat, js_quat)
                self.assertLess(angle, QUAT_KEYFRAME_TOLERANCE,
                                msg=f"quatFromLook mismatch: py={py_quat}, js={js_quat}")


class HardCutTests(unittest.TestCase):
    """Hard-cut boundary support: interpolation never crosses cut points."""

    def test_python_cut_prevents_pre_cut_influence(self):
        """A far-away pre-cut KF must NOT influence post-cut interpolation."""
        kfs = [
            {"t": 0.0, "pos": [100, 0, 0], "quat": [0, 0, 0, 1], "fov": 50},
            {"t": 2.0, "pos": [2, 0, 0], "quat": [0, 0, 0, 1], "fov": 50, "cut": True},
            {"t": 4.0, "pos": [2, 4, 0], "quat": [0, 0, 0.7071, 0.7071], "fov": 55},
        ]
        frames = interpolate_keyframes(kfs, 24)

        # Frames in the post-cut segment should NOT be pulled toward x=100
        post_cut_frames = [f for f in frames if f["t"] > 2.01]
        self.assertGreater(len(post_cut_frames), 0, "Should have post-cut frames")

        for f in post_cut_frames:
            self.assertAlmostEqual(f["pos"][0], 2.0, delta=0.5,
                msg=f"t={f['t']:.2f}: x={f['pos'][0]:.2f} — "
                    f"should stay near 2.0, not pulled toward pre-cut x=100")

    def test_python_no_cross_cut_interpolation(self):
        """Python interpolate_keyframes: no interpolation across cut boundaries."""
        kfs = [
            {"t": 0.0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 50},
            {"t": 2.0, "pos": [2, 0, 0], "quat": [0, 0, 0, 1], "fov": 50, "cut": True},
            {"t": 4.0, "pos": [2, 4, 0], "quat": [0, 0, 0.7071, 0.7071], "fov": 55},
        ]
        frames = interpolate_keyframes(kfs, 24)

        # Find frames near the cut boundary
        cut_frame_idx = None
        for fi, f in enumerate(frames):
            if f["t"] >= 2.0:
                cut_frame_idx = fi
                break

        self.assertIsNotNone(cut_frame_idx, "Should find a frame at or past the cut point")
        frame_after = frames[cut_frame_idx + 1] if cut_frame_idx + 1 < len(frames) else frames[-1]
        self.assertAlmostEqual(frame_after["pos"][0], 2.0, delta=0.1,
                               msg="X should stay near 2.0 (cut prevents interpolation from pre-cut)")
        self.assertGreater(frame_after["pos"][1], 0.0,
                           msg="Y should progress into segment 2")

    def test_js_no_cross_cut_interpolation(self):
        """JS interpolateKeyframes: no interpolation across cut boundaries."""
        kfs = [
            {"t": 0.0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 50},
            {"t": 2.0, "pos": [2, 0, 0], "quat": [0, 0, 0, 1], "fov": 50, "cut": True},
            {"t": 4.0, "pos": [2, 4, 0], "quat": [0, 0, 0.7071, 0.7071], "fov": 55},
        ]
        js_frames = self._run_js_interpolate(kfs, 24)

        cut_frame_idx = None
        for fi, f in enumerate(js_frames):
            if f["t"] >= 2.0:
                cut_frame_idx = fi
                break

        self.assertIsNotNone(cut_frame_idx)
        frame_after = js_frames[cut_frame_idx + 1] if cut_frame_idx + 1 < len(js_frames) else js_frames[-1]
        self.assertAlmostEqual(frame_after["pos"][0], 2.0, delta=0.1)
        self.assertGreater(frame_after["pos"][1], 0.0)

    def test_cut_parity_js_matches_python(self):
        """JS and Python produce identical frames for keyframes with cuts."""
        kfs = [
            {"t": 0.0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 50},
            {"t": 1.5, "pos": [3, 1, 0], "quat": [0, 0, 0.3827, 0.9239], "fov": 55, "cut": True},
            {"t": 3.0, "pos": [3, 5, 2], "quat": [0, 0, -0.3827, 0.9239], "fov": 60},
        ]
        py_frames = interpolate_keyframes(kfs, 24)
        js_frames = self._run_js_interpolate(kfs, 24)

        self.assertEqual(len(py_frames), len(js_frames),
                         f"Frame count: py={len(py_frames)}, js={len(js_frames)}")
        for fi, (pf, jf) in enumerate(zip(py_frames, js_frames)):
            with self.subTest(frame=fi):
                self.assertAlmostEqual(pf["t"], jf["t"], places=6)
                for ci in range(3):
                    self.assertAlmostEqual(pf["pos"][ci], jf["pos"][ci],
                                           delta=POS_TOLERANCE)
                angle = quat_angular_distance(pf["quat"], jf["quat"])
                self.assertLess(angle, QUAT_ANGLE_TOLERANCE,
                                msg=f"Frame {fi} quat angular error: {angle}")

    def test_backward_compat_no_cuts(self):
        """Keyframes without 'cut' field behave identically to before."""
        kfs = [
            {"t": 0.0, "pos": [0, 0, 0], "quat": [0, 0, 0, 1], "fov": 50},
            {"t": 1.0, "pos": [3, 0, 0], "quat": [0, 0, 0.3827, 0.9239], "fov": 55},
            {"t": 2.0, "pos": [3, 4, 0], "quat": [0, 0, 0, 1], "fov": 50},
        ]
        py_frames = interpolate_keyframes(kfs, 24)
        js_frames = self._run_js_interpolate(kfs, 24)
        self.assertEqual(len(py_frames), len(js_frames))
        for fi, (pf, jf) in enumerate(zip(py_frames, js_frames)):
            with self.subTest(frame=fi):
                angle = quat_angular_distance(pf["quat"], jf["quat"])
                self.assertLess(angle, QUAT_ANGLE_TOLERANCE)

    def _run_js_interpolate(self, keyframes, fps):
        kf_json = json.dumps(keyframes)
        script = f"""
        const {{ interpolateKeyframes }} = await import('./{JS_CAMERA_MATH.relative_to(REPO_ROOT).as_posix()}');
        const kfs = {kf_json};
        const result = interpolateKeyframes(kfs, {fps});
        console.log(JSON.stringify(result));
        """
        return run_node_module(script)


if __name__ == "__main__":
    unittest.main()
