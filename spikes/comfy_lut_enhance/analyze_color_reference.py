from __future__ import annotations

import json
import math
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
OUTPUT_ROOT = SCRIPT_DIR / "output"


def resolve_tool(env_name: str, exe_name: str) -> str:
    env_value = os.environ.get(env_name)
    if env_value:
        return env_value
    candidate = REPO_ROOT / ".tools" / "ffmpeg" / "ffmpeg-8.1.1-essentials_build" / "bin" / exe_name
    if candidate.exists():
        return str(candidate)
    return exe_name


def read_png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"Not a supported PNG file: {path}")
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def image_rgb_bytes(path: Path, ffmpeg: str) -> tuple[int, int, bytes]:
    width, height = read_png_size(path)
    command = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        str(path),
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-",
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {path}: {result.stderr.decode('utf-8', errors='replace')}")
    expected = width * height * 3
    if len(result.stdout) != expected:
        raise RuntimeError(f"Unexpected raw byte count for {path}: expected {expected}, got {len(result.stdout)}")
    return width, height, result.stdout


def image_stats(path: Path, ffmpeg: str) -> dict[str, float | int]:
    width, height, data = image_rgb_bytes(path, ffmpeg)
    count = width * height
    if count <= 0:
        raise ValueError(f"Invalid image dimensions for {path}: {width}x{height}")

    sum_y = 0.0
    sum_y2 = 0.0
    sum_sat = 0.0
    for index in range(0, len(data), 3):
        r = data[index] / 255.0
        g = data[index + 1] / 255.0
        b = data[index + 2] / 255.0
        y = 0.2126 * r + 0.7152 * g + 0.0722 * b
        sum_y += y
        sum_y2 += y * y
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        sat = 0.0 if max_c <= 0.0001 else (max_c - min_c) / max_c
        sum_sat += sat

    mean_y = sum_y / count
    variance = max(0.0, (sum_y2 / count) - (mean_y * mean_y))
    return {
        "width": width,
        "height": height,
        "brightness_mean": mean_y,
        "luma_stddev": math.sqrt(variance),
        "saturation_mean": sum_sat / count,
    }


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def analyze_case(case: str, output_root: Path, ffmpeg: str) -> dict[str, Any]:
    raw_dir = output_root / case / "keyframes_raw"
    reference_dir = output_root / case / "keyframes_reference"
    raw_frames = sorted(raw_dir.glob("*.png"))
    if len(raw_frames) != 4:
        raise RuntimeError(f"Expected 4 raw frames for {case}, found {len(raw_frames)}")

    samples: list[dict[str, Any]] = []
    brightness_deltas: list[float] = []
    contrast_ratios: list[float] = []
    saturation_ratios: list[float] = []

    for raw_path in raw_frames:
        reference_path = reference_dir / raw_path.name
        if not reference_path.exists():
            raise RuntimeError(f"Missing reference frame for {raw_path}: {reference_path}")
        raw_stats = image_stats(raw_path, ffmpeg)
        reference_stats = image_stats(reference_path, ffmpeg)
        if raw_stats["width"] != reference_stats["width"] or raw_stats["height"] != reference_stats["height"]:
            raise RuntimeError(f"Size mismatch for {raw_path.name}: raw={raw_stats}, reference={reference_stats}")

        raw_contrast = float(raw_stats["luma_stddev"])
        raw_saturation = float(raw_stats["saturation_mean"])
        brightness_delta = float(reference_stats["brightness_mean"]) - float(raw_stats["brightness_mean"])
        contrast_ratio = 1.0 if raw_contrast < 0.001 else float(reference_stats["luma_stddev"]) / raw_contrast
        saturation_ratio = 1.0 if raw_saturation < 0.001 else float(reference_stats["saturation_mean"]) / raw_saturation

        brightness_deltas.append(brightness_delta)
        contrast_ratios.append(contrast_ratio)
        saturation_ratios.append(saturation_ratio)
        samples.append(
            {
                "frame": raw_path.name,
                "raw": raw_stats,
                "reference": reference_stats,
                "brightness_delta": brightness_delta,
                "contrast_ratio": contrast_ratio,
                "saturation_ratio": saturation_ratio,
            }
        )

    avg_brightness = sum(brightness_deltas) / len(brightness_deltas)
    avg_contrast = sum(contrast_ratios) / len(contrast_ratios)
    avg_saturation = sum(saturation_ratios) / len(saturation_ratios)

    # The gamma estimate is intentionally conservative. It is derived from the
    # direction of the brightness shift, while brightness/contrast carry most of
    # the measurable change.
    gamma = 1.0 - clamp(avg_brightness * 0.5, -0.04, 0.04)

    params = {
        "brightness": round(clamp(avg_brightness, -0.06, 0.06), 4),
        "contrast": round(clamp(avg_contrast, 0.95, 1.16), 4),
        "saturation": round(clamp(avg_saturation, 0.95, 1.2), 4),
        "gamma": round(clamp(gamma, 0.96, 1.04), 4),
        "unsharp_luma_amount": 0.32,
    }
    return {
        "params": params,
        "samples": samples,
        "limits": {
            "brightness": [-0.06, 0.06],
            "contrast": [0.95, 1.16],
            "saturation": [0.95, 1.2],
            "gamma": [0.96, 1.04],
        },
        "analysis_note": "Parameters are bounded to avoid structural changes and text instability.",
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def run() -> int:
    output_root = OUTPUT_ROOT.resolve()
    ffmpeg = resolve_tool("FFMPEG_PATH", "ffmpeg.exe")
    result: dict[str, Any] = {
        "status": "PASS",
        "ffmpeg": ffmpeg,
        "cases": {},
    }
    try:
        for case in ("character_intro", "product_orbit"):
            result["cases"][case] = analyze_case(case, output_root, ffmpeg)
        color_params = {
            case: case_result["params"]
            for case, case_result in result["cases"].items()
        }
        result["color_params"] = color_params
        output_path = output_root / "color_params.json"
        write_json(output_path, result)
        print(f"ROUTE3B_COLOR_PARAMS={output_path}")
        print(json.dumps(color_params, indent=2, ensure_ascii=True))
        return 0
    except Exception as exc:
        result["status"] = "FAILED"
        result["error"] = str(exc)
        output_path = output_root / "color_params.json"
        write_json(output_path, result)
        print(f"ROUTE3B_COLOR_ANALYSIS_ERROR={exc}", file=sys.stderr)
        print(f"ROUTE3B_COLOR_PARAMS={output_path}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
