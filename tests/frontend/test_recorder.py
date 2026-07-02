"""
TDD tests for recorder.js — recording state machine + sample capture.

These tests drive the viewport.js split (Task 1).
All tests should FAIL initially (recorder.js doesn't exist yet).
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORDER_JS = REPO_ROOT / "apps" / "web" / "src" / "recorder.js"
INPUT_CONTROLLER_JS = REPO_ROOT / "apps" / "web" / "src" / "input_controller.js"
VIEWPORT_JS = REPO_ROOT / "apps" / "web" / "src" / "viewport.js"


def run_node_module(script: str) -> dict:
    """Execute JS ES-module snippet via Node.js."""
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
                capture_output=True, text=True, encoding="utf-8",
                cwd=REPO_ROOT, timeout=30,
            )
        finally:
            Path(tmp.name).unlink(missing_ok=True)
    else:
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True, text=True, encoding="utf-8",
            cwd=REPO_ROOT, timeout=30,
        )
    if result.returncode != 0:
        raise RuntimeError(
            f"Node.js failed (rc={result.returncode}):\n{result.stderr}"
        )
    return json.loads(result.stdout.strip())


class RecorderModuleStructureTests(unittest.TestCase):
    """recorder.js module exists and exports expected API."""

    def test_module_exports(self):
        """recorder.js exports createRecorder factory function."""
        rec_rel = RECORDER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const mod = await import('./{rec_rel}');
        console.log(JSON.stringify(Object.keys(mod)));
        """
        exports = run_node_module(script)
        self.assertIn("createRecorder", exports)


class RecorderStateMachineTests(unittest.TestCase):
    """State transitions: IDLE → RECORDING → PAUSED → RECORDING → IDLE."""

    def _make_accessor(self):
        """Create a minimal camera accessor for testing (no Three.js needed)."""
        state = {"pos": [0, -5, 1.5], "quat": [0, 0, 0, 1], "fov": 55}
        return {
            "pos": state["pos"],
            "quat": state["quat"],
            "fov": state["fov"],
            "_state": state,
        }

    def test_initial_state_is_idle(self):
        """Recorder starts in IDLE state."""
        rec_rel = RECORDER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ createRecorder }} = await import('./{rec_rel}');
        const r = createRecorder({{ getPosition: () => [0,0,0], getQuat: () => [0,0,0,1], getFov: () => 55 }});
        console.log(JSON.stringify({{ state: r.getState() }}));
        """
        result = run_node_module(script)
        self.assertEqual(result["state"], "IDLE")

    def test_idle_to_recording(self):
        """start() transitions IDLE → RECORDING."""
        rec_rel = RECORDER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ createRecorder }} = await import('./{rec_rel}');
        const r = createRecorder({{ getPosition: () => [0,0,0], getQuat: () => [0,0,0,1], getFov: () => 55 }});
        r.start();
        console.log(JSON.stringify({{ state: r.getState() }}));
        """
        result = run_node_module(script)
        self.assertEqual(result["state"], "RECORDING")

    def test_recording_to_paused(self):
        """pause() transitions RECORDING → PAUSED."""
        rec_rel = RECORDER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ createRecorder }} = await import('./{rec_rel}');
        const r = createRecorder({{ getPosition: () => [0,0,0], getQuat: () => [0,0,0,1], getFov: () => 55 }});
        r.start();
        r.pause();
        console.log(JSON.stringify({{ state: r.getState() }}));
        """
        result = run_node_module(script)
        self.assertEqual(result["state"], "PAUSED")

    def test_paused_to_recording_resume(self):
        """resume() transitions PAUSED → RECORDING."""
        rec_rel = RECORDER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ createRecorder }} = await import('./{rec_rel}');
        const r = createRecorder({{ getPosition: () => [0,0,0], getQuat: () => [0,0,0,1], getFov: () => 55 }});
        r.start();
        r.pause();
        r.resume();
        console.log(JSON.stringify({{ state: r.getState() }}));
        """
        result = run_node_module(script)
        self.assertEqual(result["state"], "RECORDING")

    def test_recording_to_stop(self):
        """stop() transitions RECORDING → IDLE."""
        rec_rel = RECORDER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ createRecorder }} = await import('./{rec_rel}');
        const r = createRecorder({{ getPosition: () => [0,0,0], getQuat: () => [0,0,0,1], getFov: () => 55 }});
        r.start();
        r.stop();
        console.log(JSON.stringify({{ state: r.getState() }}));
        """
        result = run_node_module(script)
        self.assertEqual(result["state"], "IDLE")

    def test_cannot_pause_from_idle(self):
        """pause() when IDLE is a no-op (stays IDLE)."""
        rec_rel = RECORDER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ createRecorder }} = await import('./{rec_rel}');
        const r = createRecorder({{ getPosition: () => [0,0,0], getQuat: () => [0,0,0,1], getFov: () => 55 }});
        r.pause();
        console.log(JSON.stringify({{ state: r.getState() }}));
        """
        result = run_node_module(script)
        self.assertEqual(result["state"], "IDLE")


class RecorderSampleTests(unittest.TestCase):
    """Sample recording and shot segmentation."""

    def test_tick_records_sample_when_recording(self):
        """tick() adds a sample when state is RECORDING."""
        rec_rel = RECORDER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ createRecorder }} = await import('./{rec_rel}');
        const pos = {{ x: 0, y: -5, z: 1.5 }};
        const r = createRecorder({{
            getPosition: () => [pos.x, pos.y, pos.z],
            getQuat: () => [0, 0, 0, 1],
            getFov: () => 55,
        }});
        r.start();
        r.tick(0.1);
        r.tick(0.1);
        r.tick(0.1);
        r.stop();
        const shots = r.getShots();
        const hasSamples = shots.length > 0 && shots[0].samples.length > 0;
        console.log(JSON.stringify({{ shots: shots.length, samplesInFirst: shots[0]?.samples?.length || 0, hasSamples }}));
        """
        result = run_node_module(script)
        self.assertTrue(result["hasSamples"],
                        f"Expected samples in first shot, got {result}")

    def test_pause_creates_shot_boundary(self):
        """Pause saves current samples as a shot, resume starts a new shot."""
        rec_rel = RECORDER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ createRecorder }} = await import('./{rec_rel}');
        const pos = {{ x: 0, y: -5, z: 1.5 }};
        const r = createRecorder({{
            getPosition: () => [pos.x, pos.y, pos.z],
            getQuat: () => [0, 0, 0, 1],
            getFov: () => 55,
        }});
        r.start();
        r.tick(0.1);
        r.pause();  // should create shot 0
        r.resume();
        r.tick(0.1);
        r.stop();   // should create shot 1
        const shots = r.getShots();
        console.log(JSON.stringify({{ shotCount: shots.length }}));
        """
        result = run_node_module(script)
        self.assertGreaterEqual(result["shotCount"], 2,
                                f"Pause/resume should create 2+ shots, got {result['shotCount']}")

    def test_on_stop_callback(self):
        """onStop callback receives all shots on stop()."""
        rec_rel = RECORDER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const {{ createRecorder }} = await import('./{rec_rel}');
        const r = createRecorder({{
            getPosition: () => [1, 2, 3],
            getQuat: () => [0, 0, 0, 1],
            getFov: () => 55,
        }});
        let captured = null;
        r.onStop((shots) => {{ captured = shots; }});
        r.start();
        r.tick(0.1);
        r.stop();
        console.log(JSON.stringify({{ hasCapture: captured !== null, shotCount: captured?.length || 0 }}));
        """
        result = run_node_module(script)
        self.assertTrue(result["hasCapture"], "onStop callback should be called")
        self.assertGreater(result["shotCount"], 0, "Should have at least 1 shot")


class ViewportModuleStructureTests(unittest.TestCase):
    """viewport.js integrity checks (no Node.js import — needs Three.js + DOM)."""

    def test_viewport_file_exists_and_references_submodules(self):
        """viewport.js exists and references fitter/recorder/input_controller modules."""
        self.assertTrue(VIEWPORT_JS.exists(),
                        f"viewport.js not found at {VIEWPORT_JS}")
        content = VIEWPORT_JS.read_text(encoding="utf-8")
        self.assertIn("fitter.js", content,
                      "viewport.js should import from fitter.js")
        self.assertIn("recorder.js", content,
                      "viewport.js should import from recorder.js")
        self.assertIn("input_controller.js", content,
                      "viewport.js should import from input_controller.js")


class InputControllerModuleStructureTests(unittest.TestCase):
    """input_controller.js module exists and exports expected API."""

    def test_module_exports(self):
        """input_controller.js exports initInput, updateFlight, etc."""
        ic_rel = INPUT_CONTROLLER_JS.relative_to(REPO_ROOT).as_posix()
        script = f"""
        const mod = await import('./{ic_rel}');
        console.log(JSON.stringify(Object.keys(mod)));
        """
        exports = run_node_module(script)
        for name in ["initInput", "updateFlight", "tickHUD", "getIsFlying",
                      "getCurrentSpeed", "disposeInput", "isSpeedKeyHeld"]:
            self.assertIn(name, exports,
                          f"input_controller.js must export {name}")


if __name__ == "__main__":
    unittest.main()
