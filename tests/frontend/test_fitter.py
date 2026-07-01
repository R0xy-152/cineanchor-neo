"""
TDD tests for fitter.js — keyframe fitting (RDP + angle filter).

These tests drive Task 2 implementation.
Run with: python -m unittest tests.frontend.test_fitter

ALL tests should FAIL initially (fitter.js doesn't export fitSamples yet).
"""

from __future__ import annotations

import json
import math
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FITTER_JS = REPO_ROOT / "apps" / "web" / "src" / "fitter.js"
CAMERA_MATH_JS = REPO_ROOT / "apps" / "web" / "src" / "camera_math.js"

# Force import of blender scripts
import sys
sys.path.insert(0, str(REPO_ROOT / "blender" / "scripts"))


def run_node_module(script: str) -> dict:
    """Execute JS ES-module snippet via Node.js --input-type=module.

    For long scripts, writes to a temp file to avoid Windows command-line
    length limits (WinError 206).
    """
    if len(script) > 4000:
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".mjs", delete=False,
            encoding="utf-8", dir=REPO_ROOT,
        )
        try:
            tmp.write(script)
            tmp.close()
            result = subprocess.run(
                ["node", tmp.name],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=REPO_ROOT,
                timeout=30,
            )
        finally:
            Path(tmp.name).unlink(missing_ok=True)
    else:
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=REPO_ROOT,
            timeout=30,
        )
    if result.returncode != 0:
        raise RuntimeError(
            f"Node.js failed (rc={result.returncode}):\n{result.stderr}"
        )
    return json.loads(result.stdout.strip())


def _make_straight_line_samples(n: int, duration: float = 4.0) -> list[dict]:
    """Generate n samples moving in a straight line along -Y axis."""
    samples = []
    for i in range(n):
        t = i / (n - 1) * duration if n > 1 else 0
        frac = i / (n - 1) if n > 1 else 0
        pos = [0, -5.0 + frac * 4.0, 1.5]
        quat = [0, 0, 0, 1]  # identity
        samples.append({
            "t": round(t, 4),
            "pos": pos,
            "quat": quat,
            "fov": 55.0,
        })
    return samples


def _make_curve_samples(n: int, duration: float = 4.0) -> list[dict]:
    """Generate n samples along a sinusoidal curve."""
    samples = []
    for i in range(n):
        t = i / (n - 1) * duration if n > 1 else 0
        frac = i / (n - 1) if n > 1 else 0
        pos = [
            math.sin(frac * math.pi * 2) * 2.0,
            -5.0 + frac * 3.0,
            1.5 + math.cos(frac * math.pi) * 0.5,
        ]
        # Quaternion rotating around Z
        angle = frac * math.pi
        qx = 0
        qy = 0
        qz = math.sin(angle / 2)
        qw = math.cos(angle / 2)
        samples.append({
            "t": round(t, 4),
            "pos": pos,
            "quat": [qx, qy, qz, qw],
            "fov": 55.0,
        })
    return samples


class FitterModuleStructureTests(unittest.TestCase):
    """Verify fitter.js module exists and exports expected symbols."""

    def test_module_imports(self):
        """fitter.js exports fitSamples, convertToKeyframeFormat."""
        fitter_rel = FITTER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const fitter = await import('./{fitter_rel}');
        const exports = Object.keys(fitter);
        console.log(JSON.stringify(exports));
        """
        exports = run_node_module(script)
        self.assertIn("fitSamples", exports)
        self.assertIn("convertToKeyframeFormat", exports)


class FitterStraightLineTests(unittest.TestCase):
    """Straight-line motion: RDP should drastically reduce KF count."""

    def test_straight_line_minimal_keyframes(self):
        """100-sample straight line → ≤ 5 keyframes after RDP."""
        samples = _make_straight_line_samples(100)
        fitter_rel = FITTER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ fitSamples }} = await import('./{fitter_rel}');
        const shots = [{{ shotIndex: 0, samples: {json.dumps(samples)} }}];
        const result = fitSamples(shots, [], {{ posEpsilon: 0.1, angleEpsilon: 0.05 }});
        console.log(JSON.stringify(result));
        """
        result = run_node_module(script)
        self.assertEqual(len(result), 1, "Should have 1 shot")
        kf_count = len(result[0]["keyframes"])
        self.assertLessEqual(kf_count, 5,
                             f"Straight line should need ≤ 5 KFs, got {kf_count}")
        # Should always include first and last
        self.assertAlmostEqual(result[0]["keyframes"][0]["t"], 0.0, places=2)
        self.assertAlmostEqual(result[0]["keyframes"][-1]["t"], 4.0, places=1)

    def test_straight_line_preserves_endpoints(self):
        """First and last samples are always in the keyframe set."""
        samples = _make_straight_line_samples(50)
        fitter_rel = FITTER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ fitSamples }} = await import('./{fitter_rel}');
        const shots = [{{ shotIndex: 0, samples: {json.dumps(samples)} }}];
        const result = fitSamples(shots, [], {{ posEpsilon: 0.05, angleEpsilon: 0.02 }});
        console.log(JSON.stringify(result));
        """
        result = run_node_module(script)
        kfs = result[0]["keyframes"]
        # First KF should be near t=0
        self.assertAlmostEqual(kfs[0]["t"], 0.0, places=2)
        # Last KF should be near t=2.0 (50 samples at 4s duration)
        self.assertAlmostEqual(kfs[-1]["t"], samples[-1]["t"], places=1)


class FitterCurveTests(unittest.TestCase):
    """Curved motion: RDP keeps inflection points, reduces redundant samples."""

    def test_curve_reduces_keyframes(self):
        """100-sample curve → fewer KFs than input (but more than straight line)."""
        samples = _make_curve_samples(100)
        fitter_rel = FITTER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ fitSamples }} = await import('./{fitter_rel}');
        const shots = [{{ shotIndex: 0, samples: {json.dumps(samples)} }}];
        const result = fitSamples(shots, [], {{ posEpsilon: 0.1, angleEpsilon: 0.05 }});
        console.log(JSON.stringify(result));
        """
        result = run_node_module(script)
        kf_count = len(result[0]["keyframes"])
        self.assertLess(kf_count, 100, "Should reduce from 100 samples")
        self.assertGreater(kf_count, 2, "Curve should need more than just endpoints")

    def test_curve_reinterpolation_error_within_tolerance(self):
        """RDP-fitted KFs → Catmull-Rom reinterpolation → error < posEpsilon."""
        samples = _make_curve_samples(100)
        fitter_rel = FITTER_JS.relative_to(REPO_ROOT).as_posix()
        cm_rel = CAMERA_MATH_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ fitSamples }} = await import('./{fitter_rel}');
        const {{ catmullRomVec, slerp }} = await import('./{cm_rel}');

        const shots = [{{ shotIndex: 0, samples: {json.dumps(samples)} }}];
        const POS_EPS = 0.1;
        const result = fitSamples(shots, [], {{ posEpsilon: POS_EPS, angleEpsilon: 0.05 }});
        const kfs = result[0].keyframes;

        // Re-interpolate at original sample times and check error
        const errors = [];
        for (const s of {json.dumps(samples)}) {{
            // Find segment
            let idx = 0;
            for (let i = 0; i < kfs.length; i++) {{
                if (kfs[i].t <= s.t) idx = i;
            }}
            if (idx >= kfs.length - 1) continue;

            const k0 = kfs[Math.max(0, idx - 1)];
            const k1 = kfs[idx];
            const k2 = kfs[Math.min(kfs.length - 1, idx + 1)];
            const k3 = kfs[Math.min(kfs.length - 1, idx + 2)];

            const segDur = k2.t - k1.t;
            const localT = segDur < 0.001 ? 0 : (s.t - k1.t) / segDur;

            const interpPos = catmullRomVec(k0.pos, k1.pos, k2.pos, k3.pos, localT);
            const dx = interpPos[0] - s.pos[0];
            const dy = interpPos[1] - s.pos[1];
            const dz = interpPos[2] - s.pos[2];
            errors.push(Math.sqrt(dx*dx + dy*dy + dz*dz));
        }}

        const maxErr = Math.max(...errors);
        console.log(JSON.stringify({{ maxErr, kfCount: kfs.length, pass: maxErr <= POS_EPS * 3 }}));
        """
        result = run_node_module(script)
        # Allow 3x epsilon for Catmull-Rom overshoot at segment boundaries
        self.assertTrue(result["pass"],
                        f"Max reinterpolation error {result['maxErr']:.4f} > "
                        f"tolerance. KFs used: {result['kfCount']}")


class FitterHardCutTests(unittest.TestCase):
    """Multi-shot (hard cut) handling."""

    def test_two_shots_produces_cut_boundary(self):
        """Two shots → output has 2 shot groups, first shot's last KF has cut:true."""
        shot1 = _make_straight_line_samples(30, duration=2.0)
        shot2 = _make_curve_samples(30, duration=2.0)
        # Offset shot2 times
        for s in shot2:
            s["t"] += 2.0

        fitter_rel = FITTER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ fitSamples }} = await import('./{fitter_rel}');
        const shots = [
            {{ shotIndex: 0, samples: {json.dumps(shot1)} }},
            {{ shotIndex: 1, samples: {json.dumps(shot2)} }},
        ];
        const result = fitSamples(shots, [], {{ posEpsilon: 0.1, angleEpsilon: 0.05 }});
        console.log(JSON.stringify(result));
        """
        result = run_node_module(script)
        self.assertGreaterEqual(len(result), 2,
                                "Should have at least 2 keyframe groups")
        # First shot's last KF should have cut=true
        last_of_first = result[0]["keyframes"][-1]
        self.assertTrue(last_of_first.get("cut"),
                        "First shot's last KF must have cut:true")

    def test_no_cut_for_single_shot(self):
        """Single shot: no cut flag on keyframes."""
        samples = _make_straight_line_samples(30)
        fitter_rel = FITTER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ fitSamples }} = await import('./{fitter_rel}');
        const shots = [{{ shotIndex: 0, samples: {json.dumps(samples)} }}];
        const result = fitSamples(shots, [], {{ posEpsilon: 0.1, angleEpsilon: 0.05 }});
        console.log(JSON.stringify(result));
        """
        result = run_node_module(script)
        for kf in result[0]["keyframes"]:
            self.assertFalse(kf.get("cut", False),
                             f"Single shot KFs should not have cut:true (got {kf})")


class FitterConvertFormatTests(unittest.TestCase):
    """convertToKeyframeFormat serialization."""

    def test_rounds_correctly(self):
        """Values are rounded to reasonable precision."""
        fitter_rel = FITTER_JS.relative_to(REPO_ROOT).as_posix()
        samples = [{
            "t": 1.234567,
            "pos": [1.234567, -5.987654, 0.123456],
            "quat": [0.0, 0.0, 0.7071, 0.7071],
            "fov": 55.123,
        }]
        script = f"""
        const {{ convertToKeyframeFormat }} = await import('./{fitter_rel}');
        const result = convertToKeyframeFormat({json.dumps(samples)});
        console.log(JSON.stringify(result));
        """
        result = run_node_module(script)
        self.assertEqual(len(result), 1)
        kf = result[0]
        # t rounded to 0.01
        self.assertEqual(kf["t"], 1.23)
        # pos rounded to 0.001
        self.assertEqual(kf["pos"][0], 1.235)
        # quat rounded to 0.0001
        self.assertAlmostEqual(kf["quat"][2], 0.7071, places=4)
        # fov rounded to 0.1
        self.assertEqual(kf["fov"], 55.1)


if __name__ == "__main__":
    unittest.main()
