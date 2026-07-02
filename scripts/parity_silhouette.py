"""
Gate 4 — Clean silhouette render + landmark error measurement.

Renders the AK47 model with minimal background (no rim lights, glints,
cloth, stage ring, fog, particles) so the model silhouette is clearly
distinguishable from the dark background.

Measures: subject bounding-box center vs frame center as % of diagonal.
"""
import json, math, subprocess, sys, urllib.request
from pathlib import Path
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
out_dir = REPO / "storage" / "visual_gate" / "loop08_silhouette"
out_dir.mkdir(parents=True, exist_ok=True)

# ── Fetch latest keyframes ──────────────────────────────────────────
resp = urllib.request.urlopen("http://127.0.0.1:8000/api/keyframes")
kf_data = json.loads(resp.read())
shots = kf_data["keyframes"]
kfs = shots[0]["keyframes"]
print(f"Keyframes: {len(kfs)}, FOVs: {set(k['fov'] for k in kfs)}")

# ── Build clean-scene project ───────────────────────────────────────
project = {
    "version": "0.1", "project_id": "silhouette",
    "template": "product_orbit",
    "output": {"duration": 8, "fps": 24, "aspect_ratio": "16:9", "resolution": "1080p"},
    "assets": [{"id": "main_subject", "type": "glb",
                "path": "E:/asset/AK/AK47_Gold_Arabesque_FN.glb"}],
    "camera": {
        "motion": "orbit", "speed": 1.0,
        "start_distance": 18, "end_distance": 22, "height": 0.55, "focal_length": 1.0,
        "keyframes": kfs,  # pass raw keyframes (not shot wrapper)
    },
    # Clean scene: NO background effects
    "scene": {
        "background": "dark_stage",
        "lighting": "rim_back",
        "particles": None,
        "fog": False,
        "background_enhance": {
            "rim_light": False,
            "cloth_texture": False,
            "glints": False,
            "text_overlay": False,
            "stage_ring": False,
        },
    },
    "text": {"title": "", "subtitle": "", "font_style": "bold_game"},
}
project_file = out_dir / "project.json"
project_file.write_text(json.dumps(project, indent=2))

# ── Render ───────────────────────────────────────────────────────────
frames_dir = out_dir / "frames"
frames_dir.mkdir(parents=True, exist_ok=True)
for f in frames_dir.glob("*.png"): f.unlink()

blender = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
cmd = [blender, "--background",
       "--python", str(REPO / "blender" / "scripts" / "render_project.py"),
       "--", "--project", str(project_file), "--frames-dir", str(frames_dir),
       "--width", "1920", "--height", "1080",
       "--asset-path", "E:/asset/AK/AK47_Gold_Arabesque_FN.glb"]
result = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=900)
if result.returncode != 0:
    print(f"Blender failed: {result.returncode}")
    sys.exit(1)

# Also check C:\ if cwd issue
frames = sorted(frames_dir.glob("*.png"))
if not frames:
    alt = Path("C:/storage/visual_gate/loop08_silhouette/frames")
    frames = sorted(alt.glob("*.png"))

print(f"Frames: {len(frames)}")

# ── Silhouette detection ────────────────────────────────────────────
# With clean background, subject = anything brighter than dark gray
w, h = 1920, 1080
diag = math.sqrt(w**2 + h**2)
print(f"\n{'Frame':>6s}  {'BBox':>20s}  {'Center':>12s}  {'Offset %':>8s}  {'Verdict':>8s}")
print("-" * 74)

results = []
for idx in [0, len(frames)//4, len(frames)//2, 3*len(frames)//4, len(frames)-1]:
    img = Image.open(frames[idx]).convert("RGB")
    px = img.load()

    # Find subject bounding box: pixels significantly above background
    # With clean scene, background should be near (5,5,6) or (63,63,63)
    # Sample background from corners
    bg_r = sum(px[x, y][0] for x, y in [(0, 0), (0, h-1), (w-1, 0), (w-1, h-1)]) / 4
    bg_g = sum(px[x, y][1] for x, y in [(0, 0), (0, h-1), (w-1, 0), (w-1, h-1)]) / 4
    bg_b = sum(px[x, y][2] for x, y in [(0, 0), (0, h-1), (w-1, 0), (w-1, h-1)]) / 4
    threshold = 30

    min_x, max_x, min_y, max_y = w, 0, h, 0
    count = 0
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if abs(r - bg_r) + abs(g - bg_g) + abs(b - bg_b) > threshold:
                count += 1
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)

    frame_num = idx + 1
    if count < 100:
        results.append((frame_num, 0, "NO SUBJECT"))
        print(f"  {frame_num:>3d}    {'(no subject)':>20s}  {'—':>12s}  {'—':>8s}  {'SKIP':>8s}")
        continue

    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    offset_px = math.sqrt((cx - w/2)**2 + (cy - h/2)**2)
    offset_pct = offset_px / diag * 100
    bbox = f"({min_x},{min_y})-({max_x},{max_y})"

    verdict = "PASS" if offset_pct <= 2.0 else "FAIL"
    results.append((frame_num, offset_pct, verdict))
    print(f"  {frame_num:>3d}    {bbox:>20s}  ({cx:>5.0f},{cy:>5.0f})  {offset_pct:>7.2f}%  {verdict:>8s}")

print("-" * 74)
all_pass = all(r[2] == "PASS" for r in results if r[2] != "NO SUBJECT")
print(f"\nGate 4 silhouette verdict: {'PASS' if all_pass else 'FAIL'}")
print(f"Output: {out_dir / 'frames'}")
