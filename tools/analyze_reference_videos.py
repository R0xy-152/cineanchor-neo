#!/usr/bin/env python3
"""Batch-inspect reference videos with FFprobe, FFmpeg and Pillow.

The tool intentionally avoids semantic/AI recognition. It extracts measurable
properties and visual evidence that a human can use to separate source footage,
operator packaging and platform-recording contamination.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import math
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit("Pillow is required: python -m pip install Pillow") from exc


SCENE_RE = re.compile(r"pts_time:([0-9.]+)")


@dataclass
class VideoAnalysis:
    file: str
    duration_seconds: float
    width: int
    height: int
    fps: float
    aspect_ratio: str
    video_codec: str
    audio: dict[str, Any] | None
    crop: str | None
    scene_change_seconds: list[float]
    dominant_colors: list[dict[str, Any]]
    timeline_draft: list[dict[str, Any]]
    contact_sheet: str


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def parse_rate(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return 0.0


def reduce_ratio(width: int, height: int) -> str:
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def probe_video(path: Path, ffprobe: str) -> dict[str, Any]:
    result = run([
        ffprobe,
        "-v", "error",
        "-show_streams",
        "-show_format",
        "-of", "json",
        str(path),
    ])
    payload = json.loads(result.stdout)
    video = next((s for s in payload.get("streams", []) if s.get("codec_type") == "video"), None)
    if video is None:
        raise ValueError(f"No video stream found: {path}")
    audio_stream = next((s for s in payload.get("streams", []) if s.get("codec_type") == "audio"), None)
    duration = float(payload.get("format", {}).get("duration") or video.get("duration") or 0)
    audio = None
    if audio_stream:
        audio = {
            "codec": audio_stream.get("codec_name"),
            "sample_rate": int(audio_stream.get("sample_rate") or 0),
            "channels": audio_stream.get("channels"),
            "channel_layout": audio_stream.get("channel_layout"),
            "bit_rate": int(audio_stream.get("bit_rate") or 0),
        }
    return {
        "duration": duration,
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        "video_codec": video.get("codec_name", "unknown"),
        "audio": audio,
    }


def load_crop_config(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in payload.items()):
        raise ValueError("crop config must be a JSON object mapping path/basename to W:H:X:Y")
    return payload


def crop_for(path: Path, global_crop: str | None, crop_config: dict[str, str]) -> str | None:
    return crop_config.get(str(path)) or crop_config.get(path.name) or global_crop


def video_filter(crop: str | None, tail: str) -> str:
    parts = []
    if crop:
        parts.append(f"crop={crop}")
    parts.append(tail)
    return ",".join(parts)


def detect_scenes(path: Path, ffmpeg: str, crop: str | None, threshold: float) -> list[float]:
    select = f"select='gt(scene,{threshold:.3f})',showinfo"
    result = run([
        ffmpeg, "-hide_banner", "-i", str(path),
        "-vf", video_filter(crop, select),
        "-an", "-f", "null", "-",
    ], check=False)
    points = [float(match.group(1)) for match in SCENE_RE.finditer(result.stderr)]
    return sorted({round(value, 3) for value in points if value > 0.05})


def extract_one_fps(path: Path, ffmpeg: str, crop: str | None, target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = target_dir / "%04d.jpg"
    result = run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(path),
        "-vf", video_filter(crop, "fps=1,scale=360:-2"),
        "-q:v", "3", str(output_pattern),
    ], check=False)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg frame extraction failed for {path}: {result.stderr[-1000:]}")
    return sorted(target_dir.glob("*.jpg"))


def default_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def build_contact_sheet(frames: list[Path], output_path: Path, columns: int = 5) -> None:
    if not frames:
        raise ValueError("Cannot build a contact sheet without frames")
    images = [Image.open(frame).convert("RGB") for frame in frames]
    cell_w = max(image.width for image in images)
    cell_h = max(image.height for image in images) + 30
    rows = math.ceil(len(images) / columns)
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), "#111827")
    draw = ImageDraw.Draw(sheet)
    font = default_font(18)
    for index, image in enumerate(images):
        x = (index % columns) * cell_w
        y = (index // columns) * cell_h
        sheet.paste(image, (x + (cell_w - image.width) // 2, y))
        draw.text((x + 8, y + image.height + 4), f"{index:02d}s", fill="white", font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=88)
    for image in images:
        image.close()


def dominant_colors(frames: list[Path], limit: int = 8) -> list[dict[str, Any]]:
    canvas = Image.new("RGB", (96, 96 * max(1, len(frames))))
    for index, frame in enumerate(frames):
        with Image.open(frame) as image:
            sample = image.convert("RGB").resize((96, 96), Image.Resampling.BILINEAR)
            canvas.paste(sample, (0, index * 96))
    quantized = canvas.quantize(colors=limit, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette() or []
    counts = quantized.getcolors() or []
    total = sum(count for count, _ in counts) or 1
    output = []
    for count, palette_index in sorted(counts, reverse=True):
        offset = palette_index * 3
        rgb = tuple(palette[offset:offset + 3])
        if len(rgb) != 3:
            continue
        hue, saturation, value = colorsys.rgb_to_hsv(*(component / 255 for component in rgb))
        output.append({
            "hex": "#{:02X}{:02X}{:02X}".format(*rgb),
            "share": round(count / total, 4),
            "hsv": [round(hue * 360, 1), round(saturation, 3), round(value, 3)],
        })
    return output


def draft_timeline(duration: float, scenes: list[float]) -> list[dict[str, Any]]:
    """Create a deliberately simple draft; human review remains authoritative."""
    anchors = [0.0] + scenes + [duration]
    anchors = sorted({round(max(0.0, min(duration, point)), 3) for point in anchors})
    segments = []
    for start, end in zip(anchors, anchors[1:]):
        if end - start < 0.12:
            continue
        segments.append({
            "start": start,
            "end": end,
            "duration": round(end - start, 3),
            "label": "scene-change segment (manual classification required)",
        })
    return segments


def audio_summary(audio: dict[str, Any] | None) -> str:
    if audio is None:
        return "none"
    return f"{audio['codec']}, {audio['sample_rate']} Hz, {audio['channels']} ch"


def write_report(analyses: list[VideoAnalysis], output_dir: Path) -> Path:
    report_path = output_dir / "reference_video_analysis.md"
    lines = [
        "# Reference Video Analysis",
        "",
        "> Generated by `tools/analyze_reference_videos.py`. Scene labels are intentionally left for human review; no AI recognition is used.",
        "",
        "## Batch summary",
        "",
        "| File | Duration | Resolution | FPS | Ratio | Audio | Scene cuts | Crop |",
        "|---|---:|---:|---:|---:|---|---:|---|",
    ]
    for item in analyses:
        lines.append(
            f"| `{Path(item.file).name}` | {item.duration_seconds:.2f}s | {item.width}×{item.height} | "
            f"{item.fps:.3f} | {item.aspect_ratio} | {audio_summary(item.audio)} | "
            f"{len(item.scene_change_seconds)} | `{item.crop or 'none'}` |"
        )
    lines.extend(["", "## Per-video evidence", ""])
    for item in analyses:
        colors = ", ".join(f"`{entry['hex']}` {entry['share']:.1%}" for entry in item.dominant_colors)
        cuts = ", ".join(f"{value:.2f}s" for value in item.scene_change_seconds) or "none detected"
        lines.extend([
            f"### {Path(item.file).name}",
            "",
            f"- Source: `{item.file}`",
            f"- Video: {item.video_codec}, {item.width}×{item.height}, {item.fps:.3f} fps, {item.duration_seconds:.2f}s",
            f"- Audio: {audio_summary(item.audio)}",
            f"- Scene-change candidates: {cuts}",
            f"- Dominant colors: {colors}",
            f"- Contact sheet: [open]({item.contact_sheet})",
            "- Manual classification: generated evidence only; see the human-reviewed synthesis in the checked-in report.",
            "",
        ])
    lines.extend([
        "## Interpretation guardrails",
        "",
        "- Apply crop configuration before reading scene cuts, colors or contact sheets when the source is a platform screen recording.",
        "- Treat status bars, Reels/TikTok controls, like/comment/share buttons, handles, notifications and letterboxing outside the crop as contamination.",
        "- Scene detection is a visual-difference heuristic. White flashes, particles and UI popups can create false positives.",
        "- Contact sheets are evidence for manual analysis; they are not semantic classifications.",
        "",
    ])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def analyze(args: argparse.Namespace) -> int:
    output_dir = args.output_dir.resolve()
    sheets_dir = output_dir / "contact_sheets"
    raw_dir = output_dir / "data"
    temp_root = output_dir / ".frames"
    crop_config = load_crop_config(args.crop_config)
    analyses: list[VideoAnalysis] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    for source in args.videos:
        path = source.resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        crop = crop_for(path, args.crop, crop_config)
        metadata = probe_video(path, args.ffprobe)
        frames_dir = temp_root / path.stem
        frames = extract_one_fps(path, args.ffmpeg, crop, frames_dir)
        scenes = detect_scenes(path, args.ffmpeg, crop, args.scene_threshold)
        sheet_path = sheets_dir / f"{path.stem}.jpg"
        build_contact_sheet(frames, sheet_path, columns=args.columns)
        item = VideoAnalysis(
            file=str(path),
            duration_seconds=round(metadata["duration"], 3),
            width=metadata["width"],
            height=metadata["height"],
            fps=round(metadata["fps"], 4),
            aspect_ratio=reduce_ratio(metadata["width"], metadata["height"]),
            video_codec=metadata["video_codec"],
            audio=metadata["audio"],
            crop=crop,
            scene_change_seconds=scenes,
            dominant_colors=dominant_colors(frames),
            timeline_draft=draft_timeline(metadata["duration"], scenes),
            contact_sheet=f"contact_sheets/{sheet_path.name}",
        )
        analyses.append(item)
        (raw_dir / f"{path.stem}.json").write_text(
            json.dumps(asdict(item), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"analyzed {path.name}: {item.duration_seconds:.2f}s, {len(scenes)} scene candidates")

    report = write_report(analyses, output_dir)
    shutil.rmtree(temp_root, ignore_errors=True)
    print(f"report: {report}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("videos", nargs="+", type=Path, help="one or more MP4 paths")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/reference_analysis"))
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--scene-threshold", type=float, default=0.30)
    parser.add_argument("--columns", type=int, default=5)
    parser.add_argument("--crop", help="FFmpeg crop W:H:X:Y applied to every input")
    parser.add_argument("--crop-config", type=Path, help="JSON mapping basename/path to W:H:X:Y")
    return parser


if __name__ == "__main__":
    try:
        sys.exit(analyze(build_parser().parse_args()))
    except (FileNotFoundError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
