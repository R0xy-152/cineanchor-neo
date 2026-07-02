from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
OUTPUT_ROOT = SCRIPT_DIR / "output"
DEFAULT_FFMPEG = REPO_ROOT / ".tools" / "ffmpeg" / "ffmpeg-8.1.1-essentials_build" / "bin" / "ffmpeg.exe"
DEFAULT_FFPROBE = REPO_ROOT / ".tools" / "ffmpeg" / "ffmpeg-8.1.1-essentials_build" / "bin" / "ffprobe.exe"

TEXT = {
    "character_intro": ("New Hero Arrival", "Limited Event"),
    "product_orbit": ("Product Orbit", "GLB Showcase"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Video operations for the AI enhancement feasibility spike")
    parser.add_argument("--ffmpeg", default=os.environ.get("FFMPEG_PATH") or str(DEFAULT_FFMPEG))
    parser.add_argument("--ffprobe", default=os.environ.get("FFPROBE_PATH") or str(DEFAULT_FFPROBE))

    sub = parser.add_subparsers(dest="command", required=True)

    compose = sub.add_parser("compose-raw")
    compose.add_argument("--case", required=True)

    overlay = sub.add_parser("overlay-text")
    overlay.add_argument("--case", required=True)
    overlay.add_argument("--input", required=True)
    overlay.add_argument("--output", required=True)

    keyframes = sub.add_parser("extract-keyframes")
    keyframes.add_argument("--case", required=True)
    keyframes.add_argument("--count", type=int, default=4)

    continuous = sub.add_parser("extract-continuous")
    continuous.add_argument("--case", default="character_intro")
    continuous.add_argument("--seconds", type=float, default=2.0)

    comparisons = sub.add_parser("make-keyframe-comparisons")
    comparisons.add_argument("--case", required=True)
    comparisons.add_argument("--denoise", action="append", required=True)

    compose_ai = sub.add_parser("compose-ai-2s")
    compose_ai.add_argument("--case", default="character_intro")
    compose_ai.add_argument("--denoise", required=True)

    before_after = sub.add_parser("make-before-after-2s")
    before_after.add_argument("--case", default="character_intro")
    before_after.add_argument("--denoise", required=True)

    probe = sub.add_parser("ffprobe")
    probe.add_argument("--output", default=str(OUTPUT_ROOT / "ffprobe_report.json"))
    probe.add_argument("videos", nargs="+")

    return parser.parse_args()


def output_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = SCRIPT_DIR / path
    resolved = path.resolve()
    root = OUTPUT_ROOT.resolve()
    if root not in (resolved, *resolved.parents):
        raise ValueError(f"Path must stay under {root}: {resolved}")
    return resolved


def case_root(case: str) -> Path:
    return output_path(f"output/{case}")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def clean_dir(path: Path) -> None:
    resolved = output_path(str(path))
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def manifest(case: str) -> dict[str, Any]:
    return read_json(case_root(case) / "render_manifest.json")


def denoise_label(value: str | float) -> str:
    return f"denoise_{float(value):.2f}".replace(".", "_")


def compose_from_frames(ffmpeg: str, frames_dir: Path, fps: int, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames_dir / "%04d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-crf",
            "18",
            str(output),
        ]
    )


def compose_raw(args: argparse.Namespace) -> None:
    data = manifest(args.case)
    frames_dir = Path(data["frames_dir"])
    output = case_root(args.case) / "raw_no_text.mp4"
    compose_from_frames(args.ffmpeg, frames_dir, int(data["fps"]), output)
    print(f"AI_GATE_RAW_NO_TEXT={output}")


def font_path() -> Path:
    for candidate in (
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ):
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No Arial font found under C:/Windows/Fonts")


def escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace(":", "\\:")
        .replace("%", "\\%")
    )


def drawtext_filter(case: str) -> str:
    title, subtitle = TEXT[case]
    font = str(font_path()).replace("\\", "/").replace(":", "\\:")
    if case == "product_orbit":
        title_size = 44
        subtitle_size = 28
        title_y = "h*0.72"
        subtitle_y = "h*0.80"
        box_y = "ih*0.68"
        box_h = "ih*0.22"
    else:
        title_size = 58
        subtitle_size = 36
        title_y = "h*0.735"
        subtitle_y = "h*0.805"
        box_y = "ih*0.70"
        box_h = "ih*0.18"
    return ",".join(
        [
            f"drawbox=x=0:y={box_y}:w=iw:h={box_h}:color=black@0.28:t=fill",
            (
                f"drawtext=fontfile='{font}':text='{escape_drawtext(title)}':"
                f"fontsize={title_size}:fontcolor=0xF2F6FF:"
                "shadowcolor=black@0.75:shadowx=3:shadowy=3:"
                f"x=(w-text_w)/2:y={title_y}"
            ),
            (
                f"drawtext=fontfile='{font}':text='{escape_drawtext(subtitle)}':"
                f"fontsize={subtitle_size}:fontcolor=0x8FEFFF:"
                "shadowcolor=black@0.75:shadowx=2:shadowy=2:"
                f"x=(w-text_w)/2:y={subtitle_y}"
            ),
        ]
    )


def overlay_text(args: argparse.Namespace) -> None:
    input_path = output_path(args.input)
    output = output_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            args.ffmpeg,
            "-y",
            "-i",
            str(input_path),
            "-vf",
            drawtext_filter(args.case),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-crf",
            "18",
            "-an",
            str(output),
        ]
    )
    print(f"AI_GATE_TEXT_OVERLAY={output}")


def video_info(ffprobe: str, video: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,avg_frame_rate,nb_frames,duration",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def stream_duration(info: dict[str, Any]) -> float:
    stream = info["streams"][0]
    value = stream.get("duration") or info.get("format", {}).get("duration") or 0
    return float(value)


def extract_keyframes(args: argparse.Namespace) -> None:
    root = case_root(args.case)
    raw = root / "raw_no_text.mp4"
    out_dir = root / "keyframes_raw"
    clean_dir(out_dir)
    info = video_info(args.ffprobe, raw)
    duration = stream_duration(info)
    entries = []
    for index in range(args.count):
        timestamp = min(((index + 0.5) / args.count) * duration, max(duration - 0.05, 0))
        frame = out_dir / f"frame_{index + 1:02d}.png"
        run(
            [
                args.ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(raw),
                "-frames:v",
                "1",
                str(frame),
            ]
        )
        entries.append(
            {
                "case": args.case,
                "source_video": str(raw),
                "frame_index": index + 1,
                "source_time_seconds": round(timestamp, 3),
                "raw_frame": str(frame),
            }
        )
        print(f"AI_GATE_KEYFRAME={frame}")
    write_json(root / "keyframes_manifest.json", entries)
    print(f"AI_GATE_KEYFRAME_MANIFEST={root / 'keyframes_manifest.json'}")


def extract_continuous(args: argparse.Namespace) -> None:
    data = manifest(args.case)
    fps = int(data["fps"])
    count = int(math.floor(args.seconds * fps))
    source_dir = Path(data["frames_dir"])
    out_dir = case_root(args.case) / "continuous_raw"
    clean_dir(out_dir)
    for index in range(1, count + 1):
        source = source_dir / f"{index:04d}.png"
        target = out_dir / f"{index:04d}.png"
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copy2(source, target)
    raw_2s = case_root(args.case) / "raw_no_text_2s.mp4"
    compose_from_frames(args.ffmpeg, out_dir, fps, raw_2s)
    write_json(
        case_root(args.case) / "continuous_manifest.json",
        {
            "case": args.case,
            "seconds": args.seconds,
            "fps": fps,
            "frame_count": count,
            "frames_dir": str(out_dir),
            "raw_2s_video": str(raw_2s),
        },
    )
    print(f"AI_GATE_CONTINUOUS_RAW_DIR={out_dir}")
    print(f"AI_GATE_CONTINUOUS_RAW_MP4={raw_2s}")
    print(f"AI_GATE_CONTINUOUS_FRAME_COUNT={count}")


def make_keyframe_comparisons(args: argparse.Namespace) -> None:
    root = case_root(args.case)
    raw_dir = root / "keyframes_raw"
    comparison_root = root / "comparisons"
    clean_dir(comparison_root)
    for denoise in args.denoise:
        label = denoise_label(denoise)
        enhanced_dir = root / "keyframes_ai" / label
        denoise_dir = comparison_root / label
        denoise_dir.mkdir(parents=True, exist_ok=True)
        for raw in sorted(raw_dir.glob("*.png")):
            enhanced = enhanced_dir / raw.name
            if not enhanced.exists():
                raise FileNotFoundError(enhanced)
            output = denoise_dir / f"{raw.stem}_raw_vs_ai.png"
            run(
                [
                    args.ffmpeg,
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(raw),
                    "-i",
                    str(enhanced),
                    "-filter_complex",
                    "[0:v][1:v]hstack=inputs=2[out]",
                    "-map",
                    "[out]",
                    "-frames:v",
                    "1",
                    str(output),
                ]
            )
            print(f"AI_GATE_KEYFRAME_COMPARISON={output}")
    make_denoise_grids(args.ffmpeg, args.case, args.denoise)


def make_denoise_grids(ffmpeg: str, case: str, denoises: list[str]) -> None:
    root = case_root(case)
    raw_dir = root / "keyframes_raw"
    grid_dir = root / "comparisons" / "denoise_grid"
    grid_dir.mkdir(parents=True, exist_ok=True)
    for raw in sorted(raw_dir.glob("*.png")):
        inputs = [raw]
        for denoise in denoises:
            inputs.append(root / "keyframes_ai" / denoise_label(denoise) / raw.name)
        command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
        for image in inputs:
            if not image.exists():
                raise FileNotFoundError(image)
            command.extend(["-i", str(image)])
        labels = "".join(f"[{index}:v]" for index in range(len(inputs)))
        output = grid_dir / f"{raw.stem}_raw_d025_d035_d050.png"
        command.extend(["-filter_complex", f"{labels}hstack=inputs={len(inputs)}[out]", "-map", "[out]", "-frames:v", "1", str(output)])
        run(command)
        print(f"AI_GATE_DENOISE_GRID={output}")


def compose_ai_2s(args: argparse.Namespace) -> None:
    data = manifest(args.case)
    fps = int(data["fps"])
    label = denoise_label(args.denoise)
    frames_dir = case_root(args.case) / "continuous_ai" / label
    output = case_root(args.case) / "ai_enhanced_2s.mp4"
    compose_from_frames(args.ffmpeg, frames_dir, fps, output)
    print(f"AI_GATE_AI_ENHANCED_2S={output}")


def make_before_after_2s(args: argparse.Namespace) -> None:
    root = case_root(args.case)
    raw_with_text = root / "raw_2s_with_text.mp4"
    ai_with_text = root / "ai_enhanced_2s_with_text.mp4"
    before_after = root / "before_after_2s.mp4"

    for input_video, output_video in (
        (root / "raw_no_text_2s.mp4", raw_with_text),
        (root / "ai_enhanced_2s.mp4", ai_with_text),
    ):
        run(
            [
                args.ffmpeg,
                "-y",
                "-i",
                str(input_video),
                "-vf",
                drawtext_filter(args.case),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-crf",
                "18",
                "-an",
                str(output_video),
            ]
        )

    run(
        [
            args.ffmpeg,
            "-y",
            "-i",
            str(raw_with_text),
            "-i",
            str(ai_with_text),
            "-filter_complex",
            "[0:v][1:v]hstack=inputs=2[out]",
            "-map",
            "[out]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-crf",
            "18",
            "-an",
            str(before_after),
        ]
    )
    print(f"AI_GATE_RAW_2S_WITH_TEXT={raw_with_text}")
    print(f"AI_GATE_AI_2S_WITH_TEXT={ai_with_text}")
    print(f"AI_GATE_BEFORE_AFTER_2S={before_after}")


def ffprobe_report(args: argparse.Namespace) -> None:
    output = output_path(args.output)
    report = []
    for video_text in args.videos:
        video = output_path(video_text)
        report.append({"video": str(video), "ffprobe": video_info(args.ffprobe, video)})
    write_json(output, report)
    print(f"AI_GATE_FFPROBE_REPORT={output}")


def main() -> int:
    args = parse_args()
    handlers = {
        "compose-raw": compose_raw,
        "overlay-text": overlay_text,
        "extract-keyframes": extract_keyframes,
        "extract-continuous": extract_continuous,
        "make-keyframe-comparisons": make_keyframe_comparisons,
        "compose-ai-2s": compose_ai_2s,
        "make-before-after-2s": make_before_after_2s,
        "ffprobe": ffprobe_report,
    }
    handlers[args.command](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
