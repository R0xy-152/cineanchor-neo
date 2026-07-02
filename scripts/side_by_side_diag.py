"""
Side-by-side diagnostic: compare keyframed camera vs working orbit camera.
Renders the same frame with BOTH camera types to isolate the issue.
"""
import json, math, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
out_dir = REPO / "storage" / "visual_gate" / "side_by_side"
out_dir.mkdir(parents=True, exist_ok=True)
blender = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
render_script = str(REPO / "blender" / "scripts" / "render_project.py")
asset = "E:/asset/AK/AK47_Gold_Arabesque_FN.glb"

# ═══════════════════════════════════════════════════════════════════════
# Test 1: Default orbit camera (known to work) — CONTROL
# ═══════════════════════════════════════════════════════════════════════
print("=" * 60)
print("Test 1: ORBIT camera (CONTROL - known working)")
print("=" * 60)

orbit_project = {
    "version": "0.1", "project_id": "orbit_control",
    "template": "product_orbit",
    "output": {"duration": 1, "fps": 1, "aspect_ratio": "16:9", "resolution": "1080p"},
    "assets": [{"id": "main_subject", "type": "glb", "path": asset}],
    "camera": {
        "motion": "orbit",
        "speed": 1.0,
        "start_distance": 18, "end_distance": 22,
        "height": 0.55, "focal_length": 1.0,
        # NO keyframes → uses add_orbit_camera which is known to work
    },
    "scene": {
        "background": "dark_stage", "lighting": "rim_back",
        "lighting_overrides": {
            "rim_left": {"enabled": False},
            "rim_right": {"enabled": False},
            "back": {"enabled": False},
        },
        "background_enhance": {
            "rim_light": False, "cloth_texture": False,
            "glints": False, "text_overlay": False, "stage_ring": False,
        },
    },
    "text": {"title": "ORBIT CONTROL", "subtitle": "", "font_style": "bold_game"},
}

orbit_dir = out_dir / "orbit_control"
orbit_dir.mkdir(parents=True, exist_ok=True)
(orbit_dir / "project.json").write_text(json.dumps(orbit_project, indent=2))
orbit_frames = orbit_dir / "frames"
orbit_frames.mkdir(parents=True, exist_ok=True)
for f in orbit_frames.glob("*.png"): f.unlink()

cmd = [blender, "--background", "--python", render_script,
       "--", "--project", str(orbit_dir / "project.json"),
       "--frames-dir", str(orbit_frames),
       "--width", "1920", "--height", "1080", "--asset-path", asset]
result = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=300)
print("Result: rc=%d" % result.returncode)
if result.returncode == 0:
    frames = sorted(orbit_frames.glob("*.png"))
    print("Frames: %d" % len(frames))
    if frames:
        from PIL import Image
        img = Image.open(frames[0]).convert("RGB")
        w, h = img.size
        px = img.load()
        # Check center pixel vs corners
        center = px[w//2, h//2]
        corners = [px[0,0], px[0,h-1], px[w-1,0], px[w-1,h-1]]
        print("Center pixel: RGB(%d,%d,%d)" % center)
        print("Corner pixels: %s" % ["RGB(%d,%d,%d)" % c for c in corners])
        # Count varied pixels
        varied = 0
        for y in range(0, h, 4):
            for x in range(0, w, 4):
                r, g, b = px[x, y]
                if abs(r - center[0]) + abs(g - center[1]) + abs(b - center[2]) > 10:
                    varied += 1
        total = (w//4)*(h//4)
        print("Varied pixels: %d/%d (%.1f%%)" % (varied, total, varied/total*100))
else:
    print("STDERR:", result.stderr[-500:])

# ═══════════════════════════════════════════════════════════════════════
# Test 2: Keyframed camera at the SAME position as orbit camera
# Orbit camera at (0, ORBIT_Y=-7.0, z=0.55+target_z) = (0, -7.0, 0.73)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("Test 2: KEYFRAMED camera at same position as orbit")

sys.path.insert(0, str(REPO / "blender" / "scripts"))
from camera_presets import _quat_from_look as _qfl

# Orbit camera position in Blender coords
orbit_pos = [0.0, -7.0, 0.73]  # (0, ORBIT_Y, target.z + height)
orbit_target = [0.0, 0.0, 0.18]  # model center

kf_quat = _qfl(orbit_pos, orbit_target, up=(0, 0, 1))
print("Position: %s" % orbit_pos)
print("Target: %s" % orbit_target)
print("Quat: %s" % [round(v,4) for v in kf_quat])

kf_project = {
    "version": "0.1", "project_id": "kf_at_orbit",
    "template": "product_orbit",
    "output": {"duration": 1, "fps": 1, "aspect_ratio": "16:9", "resolution": "1080p"},
    "assets": [{"id": "main_subject", "type": "glb", "path": asset}],
    "camera": {
        "motion": "orbit",
        "keyframes": [{
            "t": 0.0,
            "pos": orbit_pos,
            "quat": kf_quat,
            "fov": 55,
        }],
    },
    "scene": orbit_project["scene"],  # same scene
    "text": {"title": "KF AT ORBIT", "subtitle": "", "font_style": "bold_game"},
}

kf_dir = out_dir / "kf_at_orbit"
kf_dir.mkdir(parents=True, exist_ok=True)
(kf_dir / "project.json").write_text(json.dumps(kf_project, indent=2))
kf_frames = kf_dir / "frames"
kf_frames.mkdir(parents=True, exist_ok=True)
for f in kf_frames.glob("*.png"): f.unlink()

cmd = [blender, "--background", "--python", render_script,
       "--", "--project", str(kf_dir / "project.json"),
       "--frames-dir", str(kf_frames),
       "--width", "1920", "--height", "1080", "--asset-path", asset]
result = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=300)
print("Result: rc=%d" % result.returncode)
if result.returncode == 0:
    frames = sorted(kf_frames.glob("*.png"))
    print("Frames: %d" % len(frames))
    if frames:
        img = Image.open(frames[0]).convert("RGB")
        w, h = img.size
        px = img.load()
        center = px[w//2, h//2]
        corners = [px[0,0], px[0,h-1], px[w-1,0], px[w-1,h-1]]
        print("Center pixel: RGB(%d,%d,%d)" % center)
        print("Corner pixels: %s" % ["RGB(%d,%d,%d)" % c for c in corners])
        varied = 0
        for y in range(0, h, 4):
            for x in range(0, w, 4):
                r, g, b = px[x, y]
                if abs(r - center[0]) + abs(g - center[1]) + abs(b - center[2]) > 10:
                    varied += 1
        total = (w//4)*(h//4)
        print("Varied pixels: %d/%d (%.1f%%)" % (varied, total, varied/total*100))
else:
    print("STDERR:", result.stderr[-500:])

# ═══════════════════════════════════════════════════════════════════════
# Test 3: Keyframed camera with direct Blender coords (bypass ALL conversion)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("Test 3: KEYFRAMED camera - EXACT orbit camera position/quat")

# Use the EXACT same orbit camera setup
# build_scene routes to add_orbit_camera when motion="orbit" and no keyframes
# add_orbit_camera creates camera at (0, ORBIT_Y, target.z + height) = (0, -7.0, 0.73)
# and uses look_at() which calls direction.to_track_quat('-Z', 'Y')

sys.path.insert(0, str(REPO / "blender" / "scripts"))
from camera_presets import _quat_from_look as _qfl
from render_defaults import ORBIT_Y, ORBIT_Z_OFFSET

# Manually compute the exact orbit camera pose
orbit_cam_pos = [0.0, ORBIT_Y, 0.18 + ORBIT_Z_OFFSET]  # target.z + height_offset
print("Orbit cam pos: %s" % orbit_cam_pos)

# look_at in Blender uses direction.to_track_quat('-Z', 'Y')
# This is equivalent to _quat_from_look with up=(0,0,1)
orbit_cam_quat = _qfl(orbit_cam_pos, [0.0, 0.0, 0.18], up=(0, 0, 1))
print("Orbit cam quat: %s" % [round(v,4) for v in orbit_cam_quat])

# Also render with a slightly different FOV
for fov_test in [55, 35, 70]:
    kf2_project = {
        "version": "0.1", "project_id": "kf_orbit_fov%d" % fov_test,
        "template": "product_orbit",
        "output": {"duration": 1, "fps": 1, "aspect_ratio": "16:9", "resolution": "1080p"},
        "assets": [{"id": "main_subject", "type": "glb", "path": asset}],
        "camera": {
            "motion": "orbit",
            "keyframes": [{
                "t": 0.0,
                "pos": orbit_cam_pos,
                "quat": orbit_cam_quat,
                "fov": fov_test,
            }],
        },
        "scene": orbit_project["scene"],
        "text": {"title": "FOV=%d" % fov_test, "subtitle": "", "font_style": "bold_game"},
    }

    kf2_dir = out_dir / ("kf_orbit_fov%d" % fov_test)
    kf2_dir.mkdir(parents=True, exist_ok=True)
    (kf2_dir / "project.json").write_text(json.dumps(kf2_project, indent=2))
    kf2_frames = kf2_dir / "frames"
    kf2_frames.mkdir(parents=True, exist_ok=True)
    for f in kf2_frames.glob("*.png"): f.unlink()

    cmd = [blender, "--background", "--python", render_script,
           "--", "--project", str(kf2_dir / "project.json"),
           "--frames-dir", str(kf2_frames),
           "--width", "1920", "--height", "1080", "--asset-path", asset]
    result = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=300)

    frames = sorted(kf2_frames.glob("*.png"))
    if frames:
        img = Image.open(frames[0]).convert("RGB")
        px = img.load()
        varied = 0
        center = px[w//2, h//2]
        for y in range(0, h, 4):
            for x in range(0, w, 4):
                r, g, b = px[x, y]
                if abs(r - center[0]) + abs(g - center[1]) + abs(b - center[2]) > 10:
                    varied += 1
        total = (w//4)*(h//4)
        print("FOV=%d: varied=%d/%d (%.1f%%) center=RGB(%d,%d,%d)" % (
            fov_test, varied, total, varied/total*100, *center))
    else:
        print("FOV=%d: NO FRAMES (rc=%d)" % (fov_test, result.returncode))

print("\nDone. Output: %s" % out_dir)
print("\nCompare:")
print("  orbit_control/frames/0001.png  — CONTROL (Orbit cam, ORTHO)")
print("  kf_at_orbit/frames/0001.png    — Keyframed at same position (PERSP)")
