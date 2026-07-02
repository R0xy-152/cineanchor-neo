"""
Precision parity diagnostic: single-frame pipeline trace.

Hard-codes a simple Three.js camera pose, traces through EVERY conversion
step, dumps all intermediate values, and renders ONE Blender frame.

This eliminates ALL pipeline variables: recording, interpolation, multi-shot,
fitter, API, etc.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "blender" / "scripts"))

from camera_math import target_from_quat as _tfq
from camera_presets import _quat_from_look as _qfl


# ===========================================================================
# Test pose: Three.js camera at (7, 0.5, 0), looking at origin.
# This is the viewport.js default starting position.
# ===========================================================================

THREE_POS = [7.0, 0.5, 0.0]
THREE_TARGET = [0.0, 0.0, 0.0]
FOV = 55.0

print("=" * 72)
print("PARITY DIAGNOSTIC - Single Frame Pipeline Trace")
print("=" * 72)

def quat_from_look_any_up(pos, target, up):
    """Re-implement inline to avoid any module issues."""
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    dz = target[2] - pos[2]
    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    if dist < 1e-6:
        return [0, 0, 0, 1]
    fwd = (dx/dist, dy/dist, dz/dist)
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


def extract_look_dir(q):
    """Extract camera -Z axis (look direction) from quaternion."""
    x, y, z, w = q
    fx = -2 * (x * z + w * y)
    fy = -2 * (y * z - w * x)
    fz = -1 + 2 * (x * x + y * y)
    return [fx, fy, fz]


# ---- Step 1: Three.js quaternion (matching camera.lookAt) ----
q_three_yup = quat_from_look_any_up(THREE_POS, THREE_TARGET, up=(0, 1, 0))
print("\n[1] Three.js quaternion (up=Y, matching camera.lookAt):")
print("    q = [%.6f, %.6f, %.6f, %.6f]" % tuple(q_three_yup))

look_three = extract_look_dir(q_three_yup)
expected_fwd = [-THREE_POS[0]/math.sqrt(THREE_POS[0]**2+THREE_POS[1]**2+THREE_POS[2]**2),
                -THREE_POS[1]/math.sqrt(THREE_POS[0]**2+THREE_POS[1]**2+THREE_POS[2]**2),
                -THREE_POS[2]/math.sqrt(THREE_POS[0]**2+THREE_POS[1]**2+THREE_POS[2]**2)]
print("    Look dir from quat = [%.6f, %.6f, %.6f]" % tuple(look_three))
print("    Expected look dir  = [%.6f, %.6f, %.6f]" % tuple(expected_fwd))
dot_fwd = look_three[0]*expected_fwd[0] + look_three[1]*expected_fwd[1] + look_three[2]*expected_fwd[2]
print("    Dot product = %.8f  %s" % (dot_fwd, "OK" if dot_fwd > 0.9999 else "MISMATCH!"))

# ---- Step 2: target_from_quat (what _adapt_user_keyframes uses) ----
three_target_5m = _tfq(THREE_POS, q_three_yup, 5.0)
print("\n[2] target_from_quat(pos, q, 5.0) in Three.js space:")
print("    target_5m = [%.6f, %.6f, %.6f]" % tuple(three_target_5m))
print("    Expected  = [%.3f, %.3f, %.3f]" % (
    THREE_POS[0] + 5*expected_fwd[0],
    THREE_POS[1] + 5*expected_fwd[1],
    THREE_POS[2] + 5*expected_fwd[2]))

# ---- Step 3: Position conversion ----
cx, cy, cz = 0.0, 0.0, 0.0  # will be updated after Blender model info
tx, ty, tz = THREE_POS
blender_pos = [tx + cx, -tz + cy, ty + cz]
print("\n[3] Position conversion (cx=cy=cz=0):")
print("    Three.js pos  = [%.1f, %.1f, %.1f]" % (tx, ty, tz))
print("    Blender pos   = [%.6f, %.6f, %.6f]" % tuple(blender_pos))

blender_target = [
    three_target_5m[0] + cx,
    -three_target_5m[2] + cy,
    three_target_5m[1] + cz,
]
print("    Three.js target_5m = [%.6f, %.6f, %.6f]" % tuple(three_target_5m))
print("    Blender target     = [%.6f, %.6f, %.6f]" % tuple(blender_target))

# ---- Step 4: _quat_from_look (current pipeline method) ----
quat_look_based = _qfl(blender_pos, blender_target, up=(0, 0, 1))
print("\n[4] _quat_from_look result (current pipeline method):")
print("    q = [%.6f, %.6f, %.6f, %.6f]" % tuple(quat_look_based))

look_b = extract_look_dir(quat_look_based)
b_expected_fwd = [blender_target[i] - blender_pos[i] for i in range(3)]
b_dist = math.sqrt(sum(v*v for v in b_expected_fwd))
b_expected_fwd = [v/b_dist for v in b_expected_fwd]
print("    Look dir from quat = [%.6f, %.6f, %.6f]" % tuple(look_b))
print("    Expected look dir  = [%.6f, %.6f, %.6f]" % tuple(b_expected_fwd))
dot_b = look_b[0]*b_expected_fwd[0] + look_b[1]*b_expected_fwd[1] + look_b[2]*b_expected_fwd[2]
print("    Dot product = %.8f  %s" % (dot_b, "OK" if dot_b > 0.9999 else "MISMATCH!"))

# ---- Step 5: Direct quaternion conversion (mathematical ground truth) ----
# Coordinate change Three.js->Blender: X->X, Y->Z, Z->-Y
# This is a +90 deg rotation around X axis
# q_convert = (sin(45), 0, 0, cos(45))
sqrt2_2 = math.sqrt(2) / 2
q_conv = [sqrt2_2, 0, 0, sqrt2_2]  # (x, y, z, w)

# Hamilton product: q_conv * q_three (apply q_three then q_conv)
aw, ax, ay, az = q_conv[3], q_conv[0], q_conv[1], q_conv[2]
bw, bx, by, bz = q_three_yup[3], q_three_yup[0], q_three_yup[1], q_three_yup[2]

qw2 = aw*bw - ax*bx - ay*by - az*bz
qx2 = aw*bx + ax*bw + ay*bz - az*by
qy2 = aw*by - ax*bz + ay*bw + az*bx
qz2 = aw*bz + ax*by - ay*bx + az*bw

quat_direct = [qx2, qy2, qz2, qw2]
qnorm2 = math.sqrt(sum(v*v for v in quat_direct))
quat_direct = [v/qnorm2 for v in quat_direct]

print("\n[5] Direct quaternion conversion (q_convert * q_three):")
print("    q_convert (+90 X)  = [%.6f, 0, 0, %.6f]" % (sqrt2_2, sqrt2_2))
print("    q_blender direct   = [%.6f, %.6f, %.6f, %.6f]" % tuple(quat_direct))

look_d = extract_look_dir(quat_direct)
print("    Look dir from q    = [%.6f, %.6f, %.6f]" % tuple(look_d))
dot_d = look_d[0]*b_expected_fwd[0] + look_d[1]*b_expected_fwd[1] + look_d[2]*b_expected_fwd[2]
print("    Dot product = %.8f  %s" % (dot_d, "OK" if dot_d > 0.9999 else "MISMATCH!"))

# ---- Step 6: Compare methods ----
dot_methods = abs(sum(quat_look_based[i] * quat_direct[i] for i in range(4)))
dot_methods = min(dot_methods, 1.0)
angle_deg = math.degrees(2 * math.acos(dot_methods))
print("\n[6] Quaternion comparison:")
print("    Angle between look-based and direct: %.4f deg" % angle_deg)
if angle_deg < 0.1:
    print("    OK - Methods agree (no conversion error)")
else:
    print("    MISMATCH - %.2f deg difference!" % angle_deg)

# ---- Summary ----
print("\n" + "=" * 72)
print("SUMMARY")
print("=" * 72)
print("Three.js pose: pos=%s, target=%s, fov=%s" % (THREE_POS, THREE_TARGET, FOV))
print("Three.js quat (Y-up): %s" % [round(v,6) for v in q_three_yup])
print("Blender pos: %s" % [round(v,6) for v in blender_pos])
print("Blender quat (look-based): %s" % [round(v,6) for v in quat_look_based])
print("Blender quat (direct):     %s" % [round(v,6) for v in quat_direct])

# ---- Render single frame with BOTH methods ----
out_dir = REPO / "storage" / "visual_gate" / "parity_diag"
out_dir.mkdir(parents=True, exist_ok=True)
blender_exe = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
render_script = str(REPO / "blender" / "scripts" / "render_project.py")
asset_path = "E:/asset/AK/AK47_Gold_Arabesque_FN.glb"

for method_name, test_quat in [
    ("look_based", quat_look_based),
    ("direct_conv", quat_direct),
]:
    project = {
        "version": "0.1",
        "project_id": "diag_%s" % method_name,
        "template": "product_orbit",
        "output": {"duration": 1, "fps": 1, "aspect_ratio": "16:9", "resolution": "1080p"},
        "assets": [{"id": "main_subject", "type": "glb", "path": asset_path}],
        "camera": {
            "motion": "orbit",
            "keyframes": [{
                "t": 0.0,
                "pos": list(blender_pos),
                "quat": list(test_quat),
                "fov": FOV,
            }],
        },
        "scene": {
            "background": "dark_stage",
            "lighting": "rim_back",
            "background_enhance": {
                "rim_light": False, "cloth_texture": False,
                "glints": False, "text_overlay": False, "stage_ring": False,
            },
        },
        "text": {"title": "DIAG: %s" % method_name, "subtitle": "", "font_style": "bold_game"},
    }

    method_dir = out_dir / method_name
    method_dir.mkdir(parents=True, exist_ok=True)
    project_file = method_dir / "project.json"
    project_file.write_text(json.dumps(project, indent=2))

    frames_dir = method_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for f in frames_dir.glob("*.png"): f.unlink()

    cmd = [
        blender_exe, "--background",
        "--python", render_script,
        "--", "--project", str(project_file),
        "--frames-dir", str(frames_dir),
        "--width", "1920", "--height", "1080",
        "--asset-path", asset_path,
    ]
    print("\nRendering %s..." % method_name)
    result = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print("  FAILED (rc=%d)" % result.returncode)
        print("  stdout: %s" % result.stdout[-500:])
        print("  stderr: %s" % result.stderr[-500:])
    else:
        frames = sorted(frames_dir.glob("*.png"))
        print("  OK - %d frame(s) rendered" % len(frames))
        for f in frames:
            print("    %s" % f)

# ---- Blender model info ----
print("\n" + "=" * 72)
print("MODEL CENTERING INFO")
print("=" * 72)

info_result = subprocess.run(
    [blender_exe, "--background",
     "--python", str(REPO / "scripts" / "_blender_model_info.py")],
    cwd=REPO, capture_output=True, text=True, timeout=60,
)
print(info_result.stdout)
if info_result.stderr:
    print("STDERR:", info_result.stderr[-500:])

print("\nDone. Output: %s" % out_dir)
