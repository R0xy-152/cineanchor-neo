"""Parity measurement via difference imaging.
Renders with model, then without, subtracts to isolate subject."""
import json, subprocess, math
from pathlib import Path
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
out_dir = REPO / "storage" / "visual_gate" / "loop08_parity"
blender = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
ffmpeg = r"E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"

# Load keyframes from server API
import urllib.request, json as _json
resp = urllib.request.urlopen("http://127.0.0.1:8000/api/keyframes")
kf_data = _json.loads(resp.read())
shots = kf_data["keyframes"][0]["keyframes"]

# Build project with just 1 frame (middle of recording)
project = {
    "version": "0.1", "project_id": "parity-diff",
    "template": "product_orbit",
    "output": {"duration": 1, "fps": 1, "aspect_ratio": "16:9", "resolution": "1080p"},
    "assets": [{"id": "main_subject", "type": "glb", "path": "E:/asset/AK/AK47_Gold_Arabesque_FN.glb"}],
    "camera": {
        "motion": "orbit", "speed": 1.0,
        "start_distance": 18.0, "end_distance": 22.0, "height": 0.55, "focal_length": 1.0,
        "keyframes": shots,  # pass raw keyframes
    },
    "scene": {"background": "dark_stage", "lighting": "rim_back", "particles": None, "fog": False},
    "text": {"title": "", "subtitle": "", "font_style": "bold_game"},
}
project_file = out_dir / "project_diff.json"
project_file.write_text(_json.dumps(project, indent=2))

# Render with model
with_dir = out_dir / "frames_with"
with_dir.mkdir(parents=True, exist_ok=True)
for f in with_dir.glob("*.png"): f.unlink()
subprocess.run([blender, "--background", "--python",
    str(REPO / "blender" / "scripts" / "render_project.py"),
    "--", "--project", str(project_file), "--frames-dir", str(with_dir),
    "--width", "1920", "--height", "1080",
    "--asset-path", "E:/asset/AK/AK47_Gold_Arabesque_FN.glb"],
    cwd=REPO, capture_output=True, timeout=300, check=True)

with_frames = sorted(with_dir.glob("*.png"))
print(f"With model: {len(with_frames)} frame(s)")

# Render with a tiny proxy asset (almost invisible) to get scene-only
# Use a non-existent path so Blender creates a tiny placeholder cube
project2 = dict(project)
project2["assets"] = [{"id": "main_subject", "type": "glb", "path": "E:/asset/AK/_NONEXISTENT_.glb"}]
project2_file = out_dir / "project_diff_empty.json"
project2_file.write_text(_json.dumps(project2, indent=2))

without_dir = out_dir / "frames_without"
without_dir.mkdir(parents=True, exist_ok=True)
for f in without_dir.glob("*.png"): f.unlink()
result = subprocess.run([blender, "--background", "--python",
    str(REPO / "blender" / "scripts" / "render_project.py"),
    "--", "--project", str(project2_file), "--frames-dir", str(without_dir),
    "--width", "1920", "--height", "1080",
    "--asset-path", "E:/asset/AK/_NONEXISTENT_.glb"],
    cwd=REPO, capture_output=True, text=True, timeout=300)
# This may fail — Blender might create a demo cube. Check for frames anyway.
without_frames = sorted(without_dir.glob("*.png"))
print(f"Without model: {len(without_frames)} frame(s)")

if with_frames and without_frames:
    # Difference analysis
    img_with = Image.open(with_frames[0]).convert("RGB")
    img_without = Image.open(without_frames[0]).convert("RGB")
    w, h = img_with.size
    pw = img_with.load()
    pn = img_without.load()

    # Find pixels that differ significantly
    min_x, max_x, min_y, max_y = w, 0, h, 0
    diff_pixels = 0
    for y in range(h):
        for x in range(w):
            rw, gw, bw = pw[x, y]
            rn, gn, bn = pn[x, y]
            d = abs(rw-rn) + abs(gw-gn) + abs(bw-bn)
            if d > 10:  # significant difference = model
                diff_pixels += 1
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)

    if diff_pixels > 100:
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        offset = math.sqrt((cx - w/2)**2 + (cy - h/2)**2)
        diag = math.sqrt(w**2 + h**2)
        pct = offset / diag * 100
        bbox_w = max_x - min_x
        bbox_h = max_y - min_y
        print(f"\nSubject detected via difference: {diff_pixels} pixels")
        print(f"  BBox: ({min_x},{min_y})-({max_x},{max_y}) {bbox_w}x{bbox_h}")
        print(f"  Center: ({cx:.0f},{cy:.0f}), offset: {offset:.0f}px ({pct:.2f}%)")
        print(f"  Verdict: {'PASS' if pct <= 2.0 else 'FAIL'} (≤2% threshold)")
    else:
        print(f"\nNo significant differences found ({diff_pixels} pixels) — scene may be identical")
        print("This means the model didn't render, or both scenes rendered the same.")
else:
    print("Cannot compare — missing frames")
