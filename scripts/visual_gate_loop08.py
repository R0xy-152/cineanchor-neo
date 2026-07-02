"""
Loop 08 Visual Gate — parity verification script.

Usage:
    $env:BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
    $env:FFMPEG_PATH="E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
    .venv\Scripts\python.exe scripts\visual_gate_loop08.py

This runs a Blender render with interactive camera keyframes and outputs
comparison frames for human review.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from server.schemas.project import ProjectJSON

sys.path.insert(0, str(REPO_ROOT / "blender" / "scripts"))
from camera_presets import _quat_from_look


def _make_kf(t, pos_three, fov, look_target=(0, 0, 0), cut=False):
    """Build a keyframe dict with proper look-at quaternion (Three.js coords)."""
    quat = _quat_from_look(pos_three, look_target)
    kf = {
        "t": t,
        "pos": [round(v, 4) for v in pos_three],
        "quat": [round(v, 6) for v in quat],
        "fov": fov,
    }
    if cut:
        kf["cut"] = True
    return kf


def main() -> None:
    # Build project with interactive keyframes (2 shots, hard cut).
    # All quaternions computed via _quat_from_look targeting [0, 0, 0].
    SCENE_CENTER = (0, 0, 0)
    # Orbit-style keyframes for product showcase (GLB model)
    kfs = [
        _make_kf(0.0,  [ 0.0, -5.0, 2.0],  45, SCENE_CENTER),
        _make_kf(3.0,  [ 4.0, -3.0, 2.0],  40, SCENE_CENTER, cut=True),
        _make_kf(6.0,  [ 4.0,  3.0, 2.0],  35, SCENE_CENTER),
    ]

    project = ProjectJSON.model_validate({
        "version": "0.1",
        "project_id": "loop08-visual-gate",
        "template": "product_orbit",
        "output": {"duration": 8, "fps": 24, "aspect_ratio": "16:9", "resolution": "1080p"},
        "assets": [{"id": "main_subject", "type": "glb", "path": str(Path("E:/asset/AK/AK47_Gold_Arabesque_FN.glb"))}],
        "camera": {
            "motion": "orbit",
            "speed": 1.0,
            "start_distance": 18.0,
            "end_distance": 22.0,
            "height": 0.55,
            "focal_length": 1.0,
            "keyframes": kfs,
        },
        "scene": {
            "background": "dark_stage",
            "lighting": "rim_back",
            "particles": None,
            "fog": False,
        },
        "text": {"title": "Parity Gate", "subtitle": "Loop 08", "font_style": "bold_game"},
    })

    out_dir = REPO_ROOT / "storage" / "visual_gate" / "loop08_parity"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write project file
    project_file = out_dir / "project.json"
    project_file.write_text(
        json.dumps(project.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    print(f"[visual-gate] project written to {project_file}")

    # Run Blender render
    blender = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
    if not blender.exists():
        print("[visual-gate] ERROR: Blender not found — skipping render")
        sys.exit(1)

    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(blender),
        "--background",
        "--python", str(REPO_ROOT / "blender" / "scripts" / "render_project.py"),
        "--",
        "--project", str(project_file),
        "--frames-dir", str(frames_dir),
        "--width", "1920",
        "--height", "1080",
        "--asset-path", str(Path("E:/asset/AK/AK47_Gold_Arabesque_FN.glb")),
    ]

    print(f"[visual-gate] running Blender...")
    log_file = out_dir / "blender.log"
    with log_file.open("w", encoding="utf-8", errors="replace") as lf:
        lf.write(f"$ {subprocess.list2cmdline(cmd)}\n\n")
        lf.flush()
        result = subprocess.run(cmd, cwd=REPO_ROOT, stdout=lf,
                                stderr=subprocess.STDOUT, text=True, timeout=900)

    if result.returncode != 0:
        print(f"[visual-gate] FAILED: Blender exited {result.returncode}")
        sys.exit(1)

    frame_count = len(list(frames_dir.glob("*.png")))
    print(f"[visual-gate] OK: {frame_count} frames rendered to {frames_dir}")

    # Run FFmpeg
    ffmpeg = Path(r"E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe")
    mp4_path = out_dir / "output.mp4"
    ffmpeg_cmd = [
        str(ffmpeg), "-y",
        "-framerate", "24",
        "-i", str(frames_dir / "%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "23",
        str(mp4_path),
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"[visual-gate] MP4 written to {mp4_path}")

    # Print frame files for inspection
    frame_files = sorted(frames_dir.glob("*.png"))
    key_indices = [0, len(frame_files)//3, len(frame_files)//2, 2*len(frame_files)//3, len(frame_files)-1]
    print("\n[visual-gate] Key frames for human inspection:")
    for idx in key_indices:
        if idx < len(frame_files):
            print(f"  Frame {idx}: {frame_files[idx]}")

    print("\n[visual-gate] PASS — visual inspection required by 启鸣")
    print(f"[visual-gate] Output: {mp4_path}")


if __name__ == "__main__":
    main()
