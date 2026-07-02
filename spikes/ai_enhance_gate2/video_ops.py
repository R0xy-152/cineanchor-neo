from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
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
    parser = argparse.ArgumentParser(description="FFmpeg helpers for Gate 2 structure-control spike")
    parser.add_argument("--ffmpeg", default=os.environ.get("FFMPEG_PATH") or str(DEFAULT_FFMPEG))
    parser.add_argument("--ffprobe", default=os.environ.get("FFPROBE_PATH") or str(DEFAULT_FFPROBE))

    sub = parser.add_subparsers(dest="command", required=True)

    compose_raw = sub.add_parser("compose-raw")
    compose_raw.add_argument("--case", default="character_intro")

    keyframes = sub.add_parser("extract-keyframes")
    keyframes.add_argument("--case", default="character_intro")
    keyframes.add_argument("--count", type=int, default=4)

    continuous = sub.add_parser("extract-continuous")
    continuous.add_argument("--case", default="character_intro")
    continuous.add_argument("--seconds", type=float, default=2.0)

    canny = sub.add_parser("make-canny")
    canny.add_argument("--input-dir", required=True)
    canny.add_argument("--output-dir", required=True)
    canny.add_argument("--low", type=float, default=0.08)
    canny.add_argument("--high", type=float, default=0.22)

    composite = sub.add_parser("composite-protected")
    composite.add_argument("--raw-dir", required=True)
    composite.add_argument("--ai-dir", required=True)
    composite.add_argument("--mask-dir", required=True)
    composite.add_argument("--output-dir", required=True)

    grid = sub.add_parser("make-keyframe-grid")
    grid.add_argument("--case", default="character_intro")
    grid.add_argument("--method", default="canny")
    grid.add_argument("--denoise", action="append", required=True)

    compose = sub.add_parser("compose-frames")
    compose.add_argument("--frames-dir", required=True)
    compose.add_argument("--fps", type=int, required=True)
    compose.add_argument("--output", required=True)

    overlay = sub.add_parser("overlay-text")
    overlay.add_argument("--case", required=True)
    overlay.add_argument("--input", required=True)
    overlay.add_argument("--output", required=True)

    before_after = sub.add_parser("make-before-after-2s")
    before_after.add_argument("--case", default="character_intro")
    before_after.add_argument("--method", default="canny")
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
    return read_json(case_root(case) / "structural_manifest.json")


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
    frames_dir = Path(data["rgb_frames_dir"])
    output = case_root(args.case) / "raw_no_text.mp4"
    compose_from_frames(args.ffmpeg, frames_dir, int(data["fps"]), output)
    print(f"AI_GATE2_RAW_NO_TEXT={output}")


def copy_frame(source: Path, target: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def extract_keyframes(args: argparse.Namespace) -> None:
    data = manifest(args.case)
    root = case_root(args.case)
    key_root = root / "keyframes"
    raw_out = key_root / "raw"
    mask_out = key_root / "mask"
    clean_dir(raw_out)
    clean_dir(mask_out)

    total = int(data["rgb_frame_count"])
    rgb_dir = Path(data["rgb_frames_dir"])
    mask_dir = Path(data["mask_frames_dir"])
    entries = []
    for index in range(args.count):
        frame_number = max(1, min(total, int(round(((index + 0.5) / args.count) * total))))
        name = f"frame_{index + 1:02d}.png"
        raw_target = raw_out / name
        mask_target = mask_out / name
        copy_frame(rgb_dir / f"{frame_number:04d}.png", raw_target)
        copy_frame(mask_dir / f"{frame_number:04d}.png", mask_target)
        entries.append(
            {
                "case": args.case,
                "keyframe_index": index + 1,
                "source_frame_number": frame_number,
                "raw_frame": str(raw_target),
                "mask_frame": str(mask_target),
            }
        )
        print(f"AI_GATE2_KEYFRAME={raw_target}")
    write_json(key_root / "keyframes_manifest.json", entries)
    print(f"AI_GATE2_KEYFRAME_MANIFEST={key_root / 'keyframes_manifest.json'}")


def extract_continuous(args: argparse.Namespace) -> None:
    data = manifest(args.case)
    fps = int(data["fps"])
    count = int(math.floor(args.seconds * fps))
    root = case_root(args.case)
    cont_root = root / "continuous"
    raw_out = cont_root / "raw"
    mask_out = cont_root / "mask"
    clean_dir(raw_out)
    clean_dir(mask_out)
    rgb_dir = Path(data["rgb_frames_dir"])
    mask_dir = Path(data["mask_frames_dir"])
    for index in range(1, count + 1):
        copy_frame(rgb_dir / f"{index:04d}.png", raw_out / f"{index:04d}.png")
        copy_frame(mask_dir / f"{index:04d}.png", mask_out / f"{index:04d}.png")
    raw_2s = root / "raw_no_text_2s.mp4"
    compose_from_frames(args.ffmpeg, raw_out, fps, raw_2s)
    write_json(
        cont_root / "continuous_manifest.json",
        {
            "case": args.case,
            "seconds": args.seconds,
            "fps": fps,
            "frame_count": count,
            "raw_frames_dir": str(raw_out),
            "mask_frames_dir": str(mask_out),
            "raw_2s_video": str(raw_2s),
        },
    )
    print(f"AI_GATE2_CONTINUOUS_RAW_DIR={raw_out}")
    print(f"AI_GATE2_CONTINUOUS_MASK_DIR={mask_out}")
    print(f"AI_GATE2_CONTINUOUS_RAW_MP4={raw_2s}")
    print(f"AI_GATE2_CONTINUOUS_FRAME_COUNT={count}")


def make_canny(args: argparse.Namespace) -> None:
    input_dir = output_path(args.input_dir)
    output_dir = output_path(args.output_dir)
    clean_dir(output_dir)
    for raw in sorted(input_dir.glob("*.png")):
        output = output_dir / raw.name
        run(
            [
                args.ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(raw),
                "-vf",
                f"format=gray,edgedetect=low={args.low}:high={args.high}",
                "-frames:v",
                "1",
                str(output),
            ]
        )
        print(f"AI_GATE2_CANNY={output}")


def composite_protected(args: argparse.Namespace) -> None:
    raw_dir = output_path(args.raw_dir)
    ai_dir = output_path(args.ai_dir)
    mask_dir = output_path(args.mask_dir)
    output_dir = output_path(args.output_dir)
    clean_dir(output_dir)
    for raw in sorted(raw_dir.glob("*.png")):
        ai = ai_dir / raw.name
        mask = mask_dir / raw.name
        output = output_dir / raw.name
        if not ai.exists():
            raise FileNotFoundError(ai)
        if not mask.exists():
            raise FileNotFoundError(mask)
        run(
            [
                args.ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(ai),
                "-i",
                str(raw),
                "-i",
                str(mask),
                "-filter_complex",
                "[2:v]format=gray,lut=y='if(gt(val,128),255,0)'[mask];[1:v][mask]alphamerge[subject];[0:v][subject]overlay=format=auto[out]",
                "-map",
                "[out]",
                "-frames:v",
                "1",
                str(output),
            ]
        )
        print(f"AI_GATE2_PROTECTED_FRAME={output}")


def make_keyframe_grid(args: argparse.Namespace) -> None:
    root = case_root(args.case)
    raw_dir = root / "keyframes" / "raw"
    comparison_root = root / "keyframes" / "comparisons"
    clean_dir(comparison_root)
    for denoise in args.denoise:
        label = denoise_label(denoise)
        plain_dir = root / "keyframes" / "plain_img2img" / label
        control_dir = root / "keyframes" / f"control_{args.method}" / label
        protected_dir = root / "keyframes" / f"protected_{args.method}" / label
        out_dir = comparison_root / f"{args.method}_{label}"
        out_dir.mkdir(parents=True, exist_ok=True)
        for raw in sorted(raw_dir.glob("*.png")):
            inputs = [raw]
            labels = ["raw"]
            for candidate, name in ((plain_dir / raw.name, "plain"), (control_dir / raw.name, "control"), (protected_dir / raw.name, "protected")):
                if candidate.exists():
                    inputs.append(candidate)
                    labels.append(name)
            if len(inputs) < 2:
                continue
            command = [args.ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
            for image in inputs:
                command.extend(["-i", str(image)])
            stack_inputs = "".join(f"[{index}:v]" for index in range(len(inputs)))
            output = out_dir / f"{raw.stem}_{'_'.join(labels)}.png"
            command.extend(["-filter_complex", f"{stack_inputs}hstack=inputs={len(inputs)}[out]", "-map", "[out]", "-frames:v", "1", str(output)])
            run(command)
            print(f"AI_GATE2_KEYFRAME_GRID={output}")


def compose_frames(args: argparse.Namespace) -> None:
    frames_dir = output_path(args.frames_dir)
    output = output_path(args.output)
    compose_from_frames(args.ffmpeg, frames_dir, args.fps, output)
    print(f"AI_GATE2_COMPOSED_VIDEO={output}")


def font_path() -> Path:
    for candidate in (
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ):
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No Arial font found under C:/Windows/Fonts")


def escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "\\%")


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
    print(f"AI_GATE2_TEXT_OVERLAY={output}")


def make_before_after_2s(args: argparse.Namespace) -> None:
    root = case_root(args.case)
    label = denoise_label(args.denoise)
    raw_video = root / "raw_no_text_2s.mp4"
    full_video = root / f"control_{args.method}_2s_{label}.mp4"
    protected_video = root / f"protected_{args.method}_2s_{label}.mp4"
    raw_text = root / "raw_2s_with_text.mp4"
    full_text = root / f"control_{args.method}_2s_{label}_with_text.mp4"
    protected_text = root / f"protected_{args.method}_2s_{label}_with_text.mp4"
    before_after = root / "before_after_2s.mp4"

    for input_video, output_video in (
        (raw_video, raw_text),
        (full_video, full_text),
        (protected_video, protected_text),
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
            str(raw_text),
            "-i",
            str(full_text),
            "-i",
            str(protected_text),
            "-filter_complex",
            "[0:v][1:v][2:v]hstack=inputs=3[out]",
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
    print(f"AI_GATE2_RAW_2S_WITH_TEXT={raw_text}")
    print(f"AI_GATE2_CONTROL_2S_WITH_TEXT={full_text}")
    print(f"AI_GATE2_PROTECTED_2S_WITH_TEXT={protected_text}")
    print(f"AI_GATE2_BEFORE_AFTER_2S={before_after}")


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


def ffprobe_report(args: argparse.Namespace) -> None:
    output = output_path(args.output)
    report = []
    for video_text in args.videos:
        video = output_path(video_text)
        report.append({"video": str(video), "ffprobe": video_info(args.ffprobe, video)})
    write_json(output, report)
    print(f"AI_GATE2_FFPROBE_REPORT={output}")


def main() -> int:
    args = parse_args()
    handlers = {
        "compose-raw": compose_raw,
        "extract-keyframes": extract_keyframes,
        "extract-continuous": extract_continuous,
        "make-canny": make_canny,
        "composite-protected": composite_protected,
        "make-keyframe-grid": make_keyframe_grid,
        "compose-frames": compose_frames,
        "overlay-text": overlay_text,
        "make-before-after-2s": make_before_after_2s,
        "ffprobe": ffprobe_report,
    }
    handlers[args.command](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
