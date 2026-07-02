"""
Gate 6: Default-path regression — verify orbit/dolly/preset paths still work
after loop 08 changes (_quat_from_look trace fix, quaternion order fix).
"""
import json, math, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
out_dir = REPO / "storage" / "visual_gate" / "gate6_regression"
out_dir.mkdir(parents=True, exist_ok=True)
blender = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
render_script = str(REPO / "blender" / "scripts" / "render_project.py")
asset = "E:/asset/AK/AK47_Gold_Arabesque_FN.glb"

tests = [
    {
        "name": "orbit_default",
        "desc": "Default orbit path (2-KF Bezier, ORTHO)",
        "project": {
            "version": "0.1", "project_id": "gate6_orbit",
            "template": "product_orbit",
            "output": {"duration": 2, "fps": 24, "aspect_ratio": "16:9", "resolution": "1080p"},
            "assets": [{"id": "main_subject", "type": "glb", "path": asset}],
            "camera": {"motion": "orbit", "speed": 1.0, "start_distance": 18, "end_distance": 22, "height": 0.55, "focal_length": 1.0},
            "scene": {"background": "dark_stage", "lighting": "rim_back"},
            "text": {"title": "GATE6 ORBIT", "subtitle": "", "font_style": "bold_game"},
        },
    },
    {
        "name": "dolly_default",
        "desc": "Default dolly path (2-KF Bezier, ORTHO)",
        "project": {
            "version": "0.1", "project_id": "gate6_dolly",
            "template": "product_orbit",
            "output": {"duration": 2, "fps": 24, "aspect_ratio": "16:9", "resolution": "1080p"},
            "assets": [{"id": "main_subject", "type": "glb", "path": asset}],
            "camera": {"motion": "dolly_in", "speed": 1.0, "start_distance": 7.2, "end_distance": 5.8, "height": 0.25, "focal_length": 1.0},
            "scene": {"background": "dark_stage", "lighting": "rim_back"},
            "text": {"title": "GATE6 DOLLY", "subtitle": "", "font_style": "bold_game"},
        },
    },
    {
        "name": "preset_nolan_orbit",
        "desc": "Preset path (PERSP, multi-KF, uses _quat_from_look)",
        "project": {
            "version": "0.1", "project_id": "gate6_preset",
            "template": "product_orbit",
            "output": {"duration": 3, "fps": 24, "aspect_ratio": "16:9", "resolution": "1080p"},
            "assets": [{"id": "main_subject", "type": "glb", "path": asset}],
            "camera": {"motion": "orbit", "preset": "nolan_orbit", "focal_length": 1.0},
            "scene": {"background": "dark_stage", "lighting": "rim_back"},
            "text": {"title": "GATE6 PRESET", "subtitle": "", "font_style": "bold_game"},
        },
    },
]

results = []
for tc in tests:
    print(f"\n{'='*60}")
    print(f"Test: {tc['name']} — {tc['desc']}")

    test_dir = out_dir / tc["name"]
    test_dir.mkdir(parents=True, exist_ok=True)
    project_file = test_dir / "project.json"
    project_file.write_text(json.dumps(tc["project"], indent=2))

    frames_dir = test_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for f in frames_dir.glob("*.png"): f.unlink()

    cmd = [blender, "--background", "--python", render_script,
           "--", "--project", str(project_file),
           "--frames-dir", str(frames_dir),
           "--width", "1920", "--height", "1080",
           "--asset-path", asset]
    result = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=300)

    frames = sorted(frames_dir.glob("*.png"))
    expected_frames = tc["project"]["output"]["duration"] * tc["project"]["output"]["fps"]

    passed = True
    issues = []

    if result.returncode != 0:
        passed = False
        issues.append(f"Blender rc={result.returncode}")

    if len(frames) != expected_frames:
        passed = False
        issues.append(f"Expected {expected_frames} frames, got {len(frames)}")

    if frames:
        from PIL import Image
        # Check first, middle, last frames
        for idx in [0, len(frames)//2, len(frames)-1]:
            img = Image.open(frames[idx]).convert("RGB")
            w, h = img.size
            px = img.load()
            # Count varied pixels (model should be visible)
            center = px[w//2, h//2]
            varied = 0
            for y in range(0, h, 8):
                for x in range(0, w, 8):
                    r, g, b = px[x, y]
                    if abs(r-center[0]) + abs(g-center[1]) + abs(b-center[2]) > 20:
                        varied += 1
            total = (w//8)*(h//8)
            pct = varied/total*100
            if pct < 5:  # Less than 5% variation = likely no model visible
                passed = False
                issues.append(f"Frame {idx+1}: only {pct:.1f}% variation (model not visible?)")

    status = "PASS" if passed else "FAIL"
    print(f"  Result: {status}")
    print(f"  Frames: {len(frames)}/{expected_frames}")
    if issues:
        for issue in issues:
            print(f"  Issue: {issue}")
    results.append((tc["name"], status, issues))

print(f"\n{'='*60}")
print("GATE 6 SUMMARY")
print(f"{'='*60}")
all_pass = all(r[1] == "PASS" for r in results)
for name, status, issues in results:
    print(f"  {name}: {status}")
    if issues:
        for issue in issues:
            print(f"    - {issue}")
print(f"\nGate 6 verdict: {'PASS' if all_pass else 'FAIL'}")
