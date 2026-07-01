"""Render Blender frames from the viewport-recorded keyframes."""
import json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
out_dir = REPO / "storage" / "visual_gate" / "loop08_parity"
out_dir.mkdir(parents=True, exist_ok=True)

import urllib.request
resp = urllib.request.urlopen("http://127.0.0.1:8000/api/keyframes")
kf_data = json.loads(resp.read())
# Also save for reference
(out_dir / "recorded_keyframes.json").write_text(json.dumps(kf_data, indent=2))
shots = kf_data["keyframes"]  # [{index, cut, keyframes: [...]}]

project = {
    "version": "0.1", "project_id": "parity-recorded",
    "template": "product_orbit",
    "output": {"duration": 8, "fps": 24, "aspect_ratio": "16:9", "resolution": "1080p"},
    "assets": [{"id": "main_subject", "type": "glb", "path": "E:/asset/AK/AK47_Gold_Arabesque_FN.glb"}],
    "camera": {
        "motion": "orbit", "speed": 1.0,
        "start_distance": 18.0, "end_distance": 22.0, "height": 0.55, "focal_length": 1.0,
        "shots": shots,
    },
    "scene": {"background": "dark_stage", "lighting": "rim_back", "particles": None, "fog": False},
    "text": {"title": "", "subtitle": "", "font_style": "bold_game"},
}

project_file = out_dir / "project_recorded.json"
project_file.write_text(json.dumps(project, indent=2))

frames_dir = out_dir / "frames_recorded"
frames_dir.mkdir(parents=True, exist_ok=True)
for f in frames_dir.glob("*.png"):
    f.unlink()

blender = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
cmd = [blender, "--background", "--python", str(REPO / "blender" / "scripts" / "render_project.py"),
       "--", "--project", str(project_file), "--frames-dir", str(frames_dir),
       "--width", "1920", "--height", "1080",
       "--asset-path", "E:/asset/AK/AK47_Gold_Arabesque_FN.glb"]
print("Rendering...")
result = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=900)
if result.returncode != 0:
    print(f"FAILED: {result.returncode}")
    for l in result.stdout.split("\n")[-20:]:
        print(l)
    sys.exit(1)

frames = sorted(frames_dir.glob("*.png"))
print(f"OK: {len(frames)} frames")

ffmpeg = r"E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
mp4 = out_dir / "parity_recorded.mp4"
subprocess.run([
    ffmpeg, "-y", "-framerate", "24",
    "-i", str(frames_dir / "%04d.png"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "23",
    str(mp4),
], check=True, capture_output=True)
print(f"MP4: {mp4}")
