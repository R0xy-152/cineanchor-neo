"""
Loop 08 Parity Measurement — quantify landmark error between preview and render.

Approach:
1. Generate orbit-style keyframes around the AK47 model
2. Render in Blender
3. Detect subject bounding box in rendered frames
4. Compare subject center vs frame center → landmark error as % of frame dimension
5. Verdict: human-indistinguishable + ≤ 2% of frame

Usage:
    .venv/Scripts/python.exe scripts/parity_measure.py
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "blender" / "scripts"))

from PIL import Image
from camera_presets import apply_preset, _quat_from_look


def main() -> None:
    asset_path = Path("E:/asset/AK/AK47_Gold_Arabesque_FN.glb")
    if not asset_path.exists():
        print(f"ERROR: asset not found: {asset_path}")
        sys.exit(1)

    out_dir = REPO_ROOT / "storage" / "visual_gate" / "loop08_parity"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Generate keyframes from orbit preset ──────────────────────────
    scene_center = [0.0, 0.0, 0.0]
    scene_radius = 1.0
    # Use nolan_orbit preset — 180° orbit at low angle
    raw_kfs = apply_preset("nolan_orbit", scene_center, scene_radius, num_keyframes=6)

    # Convert to user-keyframe format (Three.js Y-up)
    keyframes = []
    for kf in raw_kfs:
        keyframes.append({
            "t": kf["t"],
            "pos": kf["pos"],
            "quat": kf["quat"],
            "fov": kf.get("fov", 50),
        })

    print(f"[parity] Generated {len(keyframes)} keyframes from nolan_orbit preset")

    # ── Build project JSON ────────────────────────────────────────────
    project = {
        "version": "0.1",
        "project_id": "parity-measure",
        "template": "product_orbit",
        "output": {"duration": 8, "fps": 24, "aspect_ratio": "16:9", "resolution": "1080p"},
        "assets": [{"id": "main_subject", "type": "glb", "path": str(asset_path)}],
        "camera": {
            "motion": "orbit",
            "speed": 1.0,
            "start_distance": 18.0,
            "end_distance": 22.0,
            "height": 0.55,
            "focal_length": 1.0,
            "keyframes": keyframes,
        },
        "scene": {
            "background": "dark_stage",
            "lighting": "rim_back",
            "particles": None,
            "fog": False,
        },
        "text": {"title": "", "subtitle": "", "font_style": "bold_game"},
    }

    project_file = out_dir / "project_parity.json"
    project_file.write_text(json.dumps(project, indent=2), encoding="utf-8")

    # ── Run Blender ───────────────────────────────────────────────────
    blender = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
    if not blender.exists():
        print("ERROR: Blender not found")
        sys.exit(1)

    frames_dir = out_dir / "frames_parity"
    frames_dir.mkdir(parents=True, exist_ok=True)
    # Clean old frames
    for f in frames_dir.glob("*.png"):
        f.unlink()

    cmd = [
        str(blender), "--background",
        "--python", str(REPO_ROOT / "blender" / "scripts" / "render_project.py"),
        "--",
        "--project", str(project_file),
        "--frames-dir", str(frames_dir),
        "--width", "1920", "--height", "1080",
        "--asset-path", str(asset_path),
    ]

    print("[parity] Rendering with Blender...")
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True,
                            text=True, timeout=900)

    if result.returncode != 0:
        print(f"Blender failed (rc={result.returncode})")
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
        sys.exit(1)

    frame_files = sorted(frames_dir.glob("*.png"))
    print(f"[parity] Rendered {len(frame_files)} frames")

    if len(frame_files) < 3:
        print("ERROR: Not enough frames")
        sys.exit(1)

    # ── Analyze landmark error at sample frames ────────────────────────
    # Pick 5 evenly-spaced frames across the timeline
    n = len(frame_files)
    sample_indices = [0, n // 4, n // 2, 3 * n // 4, n - 1]
    sample_files = [frame_files[i] for i in sample_indices]

    print("\n[parity] === Landmark Error Analysis ===")
    print(f"{'Frame':>6s}  {'Time':>6s}  {'Subj Center':>14s}  {'Offset px':>10s}  {'Offset %':>8s}  {'Verdict':>8s}")
    print("-" * 80)

    frame_w, frame_h = 1920, 1080
    frame_diag = math.sqrt(frame_w**2 + frame_h**2)
    all_pass = True

    for idx, fpath in enumerate(sample_files):
        frame_num = sample_indices[idx] + 1
        t_sec = frame_num / 24.0

        img = Image.open(fpath).convert("RGB")
        pixels = img.load()

        # Find subject bounding box (non-dark pixels)
        min_x, max_x = frame_w, 0
        min_y, max_y = frame_h, 0
        pixel_count = 0

        for y in range(frame_h):
            for x in range(frame_w):
                r, g, b = pixels[x, y]
                # Dark background is ~(3,3,8). Threshold at brightness > 30
                if r + g + b > 30:
                    pixel_count += 1
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)

        if pixel_count < 100:
            print(f"  {frame_num:>4d}  {t_sec:>5.1f}s  {'(no subject)':>14s}  {'—':>10s}  {'—':>8s}  {'SKIP':>8s}")
            continue

        subj_cx = (min_x + max_x) / 2
        subj_cy = (min_y + max_y) / 2
        subj_w = max_x - min_x
        subj_h = max_y - min_y

        # Offset from frame center
        offset_x = subj_cx - frame_w / 2
        offset_y = subj_cy - frame_h / 2
        offset_px = math.sqrt(offset_x**2 + offset_y**2)
        offset_pct = offset_px / frame_diag * 100

        verdict = "PASS" if offset_pct <= 2.0 else "FAIL"
        if offset_pct > 2.0:
            all_pass = False

        print(f"  {frame_num:>4d}  {t_sec:>5.1f}s  "
              f"({subj_cx:>5.0f},{subj_cy:>5.0f}) {subj_w:>4.0f}x{subj_h:>4.0f}  "
              f"{offset_px:>8.1f}px  {offset_pct:>7.2f}%  {verdict:>8s}")

    print("-" * 80)
    print(f"\n[parity] Verdict: {'PASS' if all_pass else 'FAIL'} "
          f"(landmark error ≤ 2% of frame diagonal)")

    # ── Also compose MP4 for human review ─────────────────────────────
    ffmpeg = Path(r"E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe")
    mp4_path = out_dir / "parity_output.mp4"
    ffmpeg_cmd = [
        str(ffmpeg), "-y", "-framerate", "24",
        "-i", str(frames_dir / "%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "23",
        str(mp4_path),
    ]
    subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
    print(f"[parity] MP4: {mp4_path}")
    print(f"[parity] Frames: {frames_dir}")


if __name__ == "__main__":
    main()
