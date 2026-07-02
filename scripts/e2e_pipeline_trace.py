"""
End-to-end pipeline trace: inject synthetic test keyframe → API → Blender render → measure.

This bypasses the browser entirely. Uses a known Three.js camera pose to
verify every stage: recording format, API storage, _adapt_user_keyframes conversion,
FOV→lens, interpolation, and final render.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# ═══════════════════════════════════════════════════════════════════════
# 1. Generate a synthetic recording that mimics what the viewport POSTs
# ═══════════════════════════════════════════════════════════════════════

# Simulate a simple 2-second recording: camera orbits slightly around origin
# Three.js coords (Y-up): camera starts at (7, 0.5, 0), orbits to (5, 0.5, 5)
# This creates a clear visible difference if conversion is wrong

def quat_from_look_three(pos, target):
    """Three.js camera.lookAt with up=(0,1,0)."""
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    dz = target[2] - pos[2]
    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    if dist < 1e-6:
        return [0, 0, 0, 1]
    fwd = (dx/dist, dy/dist, dz/dist)
    up = (0, 1, 0)
    ux, uy, uz = up

    rx = fwd[1]*uz - fwd[2]*uy
    ry = fwd[2]*ux - fwd[0]*uz
    rz = fwd[0]*uy - fwd[1]*ux
    rlen = math.sqrt(rx*rx + ry*ry + rz*rz)
    if rlen < 1e-6:
        rx, ry, rz = 1.0, 0.0, 0.0
    else:
        rx, ry, rz = rx/rlen, ry/rlen, rz/rlen

    ux2 = ry*fwd[2] - rz*fwd[1]
    uy2 = rz*fwd[0] - rx*fwd[2]
    uz2 = rx*fwd[1] - ry*fwd[0]

    nfx, nfy, nfz = -fwd[0], -fwd[1], -fwd[2]
    trace = rx + uy2 + nfz
    EPS = 1e-10

    if trace > 0:
        s = max(math.sqrt(trace + 1) * 2, EPS)
        qw = 0.25 * s
        qx = (uz2 - nfy) / s
        qy = (nfx - rz) / s
        qz = (ry - ux2) / s
    elif rx > uy2 and rx > nfz:
        s = max(math.sqrt(1 + rx - uy2 - nfz) * 2, EPS)
        qw = (uz2 - nfy) / s
        qx = 0.25 * s
        qy = (ux2 + ry) / s
        qz = (nfx + rz) / s
    elif uy2 > nfz:
        s = max(math.sqrt(1 + uy2 - rx - nfz) * 2, EPS)
        qw = (nfx - rz) / s
        qx = (ux2 + ry) / s
        qy = 0.25 * s
        qz = (nfy + uz2) / s
    else:
        s = max(math.sqrt(1 + nfz - rx - uy2) * 2, EPS)
        qw = (ry - ux2) / s
        qx = (nfx + rz) / s
        qy = (nfy + uz2) / s
        qz = 0.25 * s

    qnorm = math.sqrt(qx*qx + qy*qy + qz*qz + qw*qw)
    return [qx/qnorm, qy/qnorm, qz/qnorm, qw/qnorm]


# Generate 3 keyframes over 2 seconds
target = [0, 0, 0]
poses = [
    (0.0, [7.0, 0.5, 0.0]),    # t=0s: right side
    (1.0, [4.0, 0.5, 4.0]),    # t=1s: moving to front-right
    (2.0, [0.0, 0.5, 7.0]),    # t=2s: front
]

keyframes = []
for t, pos in poses:
    q = quat_from_look_three(pos, target)
    keyframes.append({
        "t": t,
        "pos": [round(v, 3) for v in pos],
        "quat": [round(v, 4) for v in q],
        "fov": 55.0,
    })

# Wrap in shot format (matching fitter.js output)
shots_payload = [{
    "index": 0,
    "cut": False,
    "keyframes": keyframes,
}]

print("=" * 72)
print("END-TO-END PIPELINE TRACE")
print("=" * 72)
print("\n[1] Synthetic recording (3 keyframes over 2s):")
for kf in keyframes:
    print("    t=%.1f  pos=%s  quat=%s  fov=%.1f" % (
        kf["t"], kf["pos"], [round(q, 4) for q in kf["quat"]], kf["fov"]))

# ═══════════════════════════════════════════════════════════════════════
# 2. POST to API (simulating what viewport does on stop)
# ═══════════════════════════════════════════════════════════════════════

server_url = "http://127.0.0.1:8000"
try:
    req = urllib.request.Request(
        server_url + "/api/keyframes",
        data=json.dumps(shots_payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    print("\n[2] POST /api/keyframes: %s" % json.loads(resp.read()))
except Exception as e:
    print("\n[2] POST /api/keyframes FAILED: %s" % e)
    print("    Is the server running? Start with: python -m uvicorn server.main:app")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════
# 3. Fetch back and verify
# ═══════════════════════════════════════════════════════════════════════

resp2 = urllib.request.urlopen(server_url + "/api/keyframes", timeout=5)
stored = json.loads(resp2.read())
print("[3] GET /api/keyframes: %d shots retrieved" % len(stored.get("keyframes", [])))

# ═══════════════════════════════════════════════════════════════════════
# 4. Convert through _adapt_user_keyframes (Python-side trace)
# ═══════════════════════════════════════════════════════════════════════

sys.path.insert(0, str(REPO / "blender" / "scripts"))
from camera_presets import _quat_from_look as _qfl
from camera_math import target_from_quat as _tfq, interpolate_keyframes

# Simulate what Blender does (extract scene_center first)
# Run Blender info script to get actual scene_center
info_result = subprocess.run(
    [r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe", "--background",
     "--python", str(REPO / "scripts" / "_blender_model_info.py")],
    cwd=REPO, capture_output=True, text=True, timeout=60,
)
scene_center = [0.0, 0.0, 0.18]  # default from earlier run
for line in info_result.stdout.splitlines():
    if line.startswith("AFTER_CENTER="):
        parts = line.split("(")[1].split(")")[0].split(",")
        scene_center = [float(p) for p in parts]
        break
print("\n[4] Scene center from Blender: %s" % scene_center)

# Run _adapt_user_keyframes
print("\n[5] _adapt_user_keyframes conversion trace:")
print("    %-8s %-30s %-30s %-30s" % ("t", "Three.js pos", "Blender pos", "Blender quat"))
print("    " + "-" * 100)

cx, cy, cz = scene_center
for kf in keyframes:
    tx, ty, tz = kf["pos"]
    blender_pos = [tx + cx, -tz + cy, ty + cz]

    q_three = kf["quat"]
    three_target = _tfq([tx, ty, tz], q_three, 5.0)
    blender_target = [
        three_target[0] + cx,
        -three_target[2] + cy,
        three_target[1] + cz,
    ]
    quat = _qfl(blender_pos, blender_target, up=(0, 0, 1))

    print("    %-8.1f %-30s %-30s %-30s" % (
        kf["t"],
        "[%.3f,%.3f,%.3f]" % (tx, ty, tz),
        "[%.4f,%.4f,%.4f]" % tuple(blender_pos),
        "[%.4f,%.4f,%.4f,%.4f]" % tuple(quat),
    ))

# ═══════════════════════════════════════════════════════════════════════
# 5. Render via parity_silhouette-style project
# ═══════════════════════════════════════════════════════════════════════

out_dir = REPO / "storage" / "visual_gate" / "e2e_trace"
out_dir.mkdir(parents=True, exist_ok=True)

project = {
    "version": "0.1",
    "project_id": "e2e_trace",
    "template": "product_orbit",
    "output": {"duration": 2, "fps": 24, "aspect_ratio": "16:9", "resolution": "1080p"},
    "assets": [{"id": "main_subject", "type": "glb",
                "path": "E:/asset/AK/AK47_Gold_Arabesque_FN.glb"}],
    "camera": {
        "motion": "orbit",
        "keyframes": keyframes,  # flat keyframes → add_keyframed_camera_from_data
    },
    "scene": {
        "background": "dark_stage",
        "lighting": "rim_back",
        "background_enhance": {
            "rim_light": False, "cloth_texture": False,
            "glints": False, "text_overlay": False, "stage_ring": False,
        },
    },
    "text": {"title": "E2E TRACE", "subtitle": "", "font_style": "bold_game"},
}

project_file = out_dir / "project.json"
project_file.write_text(json.dumps(project, indent=2))

frames_dir = out_dir / "frames"
frames_dir.mkdir(parents=True, exist_ok=True)
for f in frames_dir.glob("*.png"): f.unlink()

print("\n[6] Rendering with Blender...")
result = subprocess.run(
    [r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe", "--background",
     "--python", str(REPO / "blender" / "scripts" / "render_project.py"),
     "--", "--project", str(project_file),
     "--frames-dir", str(frames_dir),
     "--width", "1920", "--height", "1080",
     "--asset-path", "E:/asset/AK/AK47_Gold_Arabesque_FN.glb"],
    cwd=REPO, capture_output=True, text=True, timeout=300,
)

if result.returncode != 0:
    print("    FAILED: %s" % result.stderr[-500:])
    sys.exit(1)

frames = sorted(frames_dir.glob("*.png"))
print("    OK - %d frames rendered" % len(frames))

# ═══════════════════════════════════════════════════════════════════════
# 6. Measure first, middle, and last frame
# ═══════════════════════════════════════════════════════════════════════

print("\n[7] Frame analysis:")
from PIL import Image

w, h = 1920, 1080
diag = math.sqrt(w**2 + h**2)

for idx in [0, len(frames)//2, len(frames)-1]:
    img = Image.open(frames[idx]).convert("RGB")
    px = img.load()

    # Sample background from corners
    corners = [(0, 0), (0, h-1), (w-1, 0), (w-1, h-1)]
    bg_r = sum(px[x, y][0] for x, y in corners) / 4
    bg_g = sum(px[x, y][1] for x, y in corners) / 4
    bg_b = sum(px[x, y][2] for x, y in corners) / 4

    # Find bright pixels (subject/floor vs dark background)
    threshold = 30
    min_x, max_x, min_y, max_y = w, 0, h, 0
    count = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            if abs(r-bg_r) + abs(g-bg_g) + abs(b-bg_b) > threshold:
                count += 1
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)

    if count > 50:
        cx_px = (min_x + max_x) / 2
        cy_px = (min_y + max_y) / 2
        offset_px = math.sqrt((cx_px - w/2)**2 + (cy_px - h/2)**2)
        offset_pct = offset_px / diag * 100
        status = "OK" if offset_pct <= 2.0 else "OFFSET"
        print("    Frame %3d: center=(%.0f,%.0f) offset=%.2f%% %s %s" % (
            idx + 1, cx_px, cy_px, offset_pct, status,
            "[bbox: %d,%d-%d,%d]" % (min_x, max_x, min_y, max_y)))
    else:
        print("    Frame %3d: NO SUBJECT DETECTED (only %d bright pixels)" % (idx + 1, count))
        # Sample some pixels to debug
        for sx, sy in [(960, 540), (500, 500), (1400, 500), (960, 200)]:
            sp = px[sx, sy]
            print("        pixel(%d,%d) = RGB(%d,%d,%d)" % (sx, sy, sp[0], sp[1], sp[2]))

print("\nDone. Output: %s" % out_dir)
print("Compare frame 0001.png with viewport at t=0: camera at (7, 0.5, 0) looking at origin")
