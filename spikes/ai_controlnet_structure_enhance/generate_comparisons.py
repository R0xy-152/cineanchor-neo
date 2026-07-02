"""
Generate side-by-side comparison grids and before/after videos from spike output.

Usage:
  python generate_comparisons.py --report output/character/char_keyframes_sweep_report.json
  python generate_comparisons.py --experiment character --methods canny,depth --denoise 0.35
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = SCRIPT_DIR / "output"
FFMPEG_EXE = os.environ.get("FFMPEG_PATH", "")
GATE2_CHAR_RAW = Path("E:/cineanchor/spikes/ai_enhance_gate2/output/character_intro/keyframes/raw")
GATE2_PROD_RAW = Path("E:/cineanchor/spikes/ai_enhance_gate2/output/product_orbit/keyframes/raw")


def find_ffmpeg() -> str:
    for candidate in [
        FFMPEG_EXE,
        r"E:\cineanchor\.tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe",
        "ffmpeg",
    ]:
        try:
            subprocess.run([candidate, "-version"], capture_output=True, timeout=5, check=True)
            return candidate
        except Exception:
            continue
    raise FileNotFoundError("FFmpeg not found")


def grid_4up(raw_frames: list[Path], enhanced_frames: list[Path], output_path: Path) -> None:
    """Generate 4-up comparison grid: top=raw, bottom=enhanced."""
    ffmpeg = find_ffmpeg()
    assert len(raw_frames) == len(enhanced_frames) >= 1

    for i, (raw, enhanced) in enumerate(zip(raw_frames, enhanced_frames), start=1):
        out = output_path / f"compare_{i:02d}.png"
        # hstack: raw on left, enhanced on right
        cmd = [
            ffmpeg, "-y", "-i", str(raw), "-i", str(enhanced),
            "-filter_complex", "hstack=inputs=2",
            "-frames:v", "1", str(out),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        print(f"  Comparison: {out}")


def label_frames(raw_frames: list[Path], enhanced_frames: list[Path],
                 output_path: Path, label: str) -> None:
    """Add labels to raw and enhanced frames."""
    ffmpeg = find_ffmpeg()
    out_raw = output_path / f"raw_labeled_{label}.png"
    out_enh = output_path / f"enhanced_labeled_{label}.png"

    for src, out, txt in [
        (raw_frames[0], out_raw, "Raw Blender"),
        (enhanced_frames[0], out_enh, f"AI Enhanced ({label})"),
    ]:
        cmd = [
            ffmpeg, "-y", "-i", str(src),
            "-vf", f"drawtext=text='{txt}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-th-20:box=1:boxcolor=black@0.5:boxborderw=10",
            "-frames:v", "1", str(out),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    print(f"  Labels: {out_raw}, {out_enh}")


def make_side_by_side_video(raw_dir: Path, enhanced_dir: Path, output_path: Path,
                             label_raw: str = "Raw", label_enh: str = "AI Enhanced") -> None:
    """Create side-by-side MP4 from frame directories."""
    ffmpeg = find_ffmpeg()

    if raw_dir.is_file() and enhanced_dir.is_file():
        # Single MP4 inputs
        cmd = [
            ffmpeg, "-y", "-i", str(raw_dir), "-i", str(enhanced_dir),
            "-filter_complex",
            "[0:v]drawtext=text='Raw Blender':fontsize=36:fontcolor=white:x=10:y=10:box=1:boxcolor=black@0.4:boxborderw=6[raw];"
            "[1:v]drawtext=text='AI Enhanced':fontsize=36:fontcolor=white:x=10:y=10:box=1:boxcolor=black@0.4:boxborderw=6[enh];"
            "[raw][enh]hstack=inputs=2",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            str(output_path),
        ]
    else:
        # Frame directories
        raw_pattern = str(raw_dir / "%04d.png") if raw_dir.is_dir() else str(raw_dir)
        enh_pattern = str(enhanced_dir / "%04d.png") if enhanced_dir.is_dir() else str(enhanced_dir)
        cmd = [
            ffmpeg, "-y",
            "-framerate", "24", "-i", str(raw_dir / "%04d.png"),
            "-framerate", "24", "-i", str(enhanced_dir / "%04d.png"),
            "-filter_complex",
            "[0:v]drawtext=text='Raw Blender':fontsize=36:fontcolor=white:x=10:y=10:box=1:boxcolor=black@0.4:boxborderw=6[raw];"
            "[1:v]drawtext=text='AI Enhanced':fontsize=36:fontcolor=white:x=10:y=10:box=1:boxcolor=black@0.4:boxborderw=6[enh];"
            "[raw][enh]hstack=inputs=2",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]
    subprocess.run(cmd, capture_output=True, check=True)
    print(f"Side-by-side video: {output_path}")


def generate_keyframe_comparisons(report_path: Path) -> None:
    """From a report JSON, generate comparison grids for all methods/denoises."""
    report = json.loads(report_path.read_text("utf-8"))
    comp_dir = report_path.parent / "comparisons"
    comp_dir.mkdir(parents=True, exist_ok=True)

    # Detect experiment type from report
    exp_type = report.get("experiment", "character")
    raw_dir = GATE2_PROD_RAW if exp_type == "product" else GATE2_CHAR_RAW
    raw_frames = sorted(raw_dir.glob("*.png"))
    if not raw_frames:
        print(f"WARNING: No raw keyframes found in {raw_dir}")

    for key, result in report.get("results", {}).items():
        frames_data = result.get("frames", [])
        if not frames_data:
            continue
        enhanced_frames = [Path(f["enhanced"]) for f in frames_data if Path(f["enhanced"]).exists()]
        if len(enhanced_frames) != len(raw_frames):
            print(f"  SKIP {key}: frame count mismatch ({len(enhanced_frames)} vs {len(raw_frames)})")
            continue

        method_dir = comp_dir / key
        method_dir.mkdir(parents=True, exist_ok=True)
        print(f"Generating comparisons for {key}...")
        grid_4up(raw_frames, enhanced_frames, method_dir)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", default="")
    p.add_argument("--experiment", default="")
    p.add_argument("--methods", default="")
    p.add_argument("--denoise", default="")
    args = p.parse_args()

    if args.report:
        generate_keyframe_comparisons(Path(args.report))
    elif args.experiment:
        methods = [m.strip() for m in (args.methods or "").split(",") if m.strip()]
        denoises = [d.strip() for d in (args.denoise or "").split(",") if d.strip()]
        exp_dir = OUTPUT_ROOT / args.experiment / "keyframes"
        for method in methods:
            for d in denoises:
                key = f"{method}_denoise_{d.replace('.', '_')}"
                mdir = exp_dir / key
                if mdir.exists():
                    raw_dir_2 = GATE2_PROD_RAW if args.experiment == "product" else GATE2_CHAR_RAW
                    raw_frames = sorted(raw_dir_2.glob("*.png"))
                    enhanced = sorted(mdir.glob("*.png"))
                    if enhanced and raw_frames:
                        comp_dir = OUTPUT_ROOT / args.experiment / "comparisons" / key
                        comp_dir.mkdir(parents=True, exist_ok=True)
                        grid_4up(raw_frames, enhanced, comp_dir)
    else:
        print("Usage: --report <path>  OR  --experiment <name> --methods a,b --denoise 0.35")


if __name__ == "__main__":
    main()
