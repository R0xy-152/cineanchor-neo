"""
Recomposition check and measurement script (runs in Blender, numpy only).

Recomposes: L_background → L_subject → L_text
Compares against original composite frame.

Usage:
  "{blender_exe}" --background --python composite_layers.py --
    --layers-dir <dir> --output-dir <dir> [--frames 1,32,64,96]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import bpy
import numpy as np


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Recomposition checker")
    parser.add_argument("--layers-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--frames", type=str, default="1,32,64,96")
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Image I/O (via Blender)
# ---------------------------------------------------------------------------

def load_png(filepath: Path) -> tuple[np.ndarray, int, int]:
    img = bpy.data.images.load(str(filepath))
    w, h = img.size
    pixels = (np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4) * 255.0).astype(np.float32)
    bpy.data.images.remove(img)
    return pixels, w, h


def save_png_blender(pixels: np.ndarray, filepath: Path) -> None:
    h, w = pixels.shape[:2]
    img = bpy.data.images.new("temp", width=w, height=h, alpha=True)
    img.pixels[:] = (pixels.astype(np.float32) / 255.0).flatten()
    img.filepath_raw = str(filepath)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


# ---------------------------------------------------------------------------
# Compositing
# ---------------------------------------------------------------------------

def composite_layers(bg: np.ndarray, subj: np.ndarray, txt: np.ndarray) -> np.ndarray:
    """
    Composite: background → subject → text.

    Blender Eevee with film_transparent=True produces PREMULTIPLIED alpha
    (also called associated alpha). For premultiplied alpha, the over
    operator is:

        C_result = C_fg + C_bg * (1 - A_fg)
        A_result = A_fg + A_bg * (1 - A_fg)

    NOT the straight-alpha formula: C_fg * A_fg + C_bg * (1 - A_fg).
    """
    result = bg.copy()

    # Premultiplied-over for subject
    sa = subj[:, :, 3:4] / 255.0
    result[:, :, :3] = subj[:, :, :3] + result[:, :, :3] * (1.0 - sa)
    result[:, :, 3] = np.maximum(subj[:, :, 3], result[:, :, 3])

    # Premultiplied-over for text
    ta = txt[:, :, 3:4] / 255.0
    result[:, :, :3] = txt[:, :, :3] + result[:, :, :3] * (1.0 - ta)
    result[:, :, 3] = np.maximum(txt[:, :, 3], result[:, :, 3])

    return result


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = np.mean((a - b) ** 2)
    if mse < 1e-10:
        return 100.0
    return float(20.0 * math.log10(255.0 / math.sqrt(mse)))


def compute_diff_metrics(original: np.ndarray, reconstructed: np.ndarray) -> dict:
    diff = np.abs(original - reconstructed)
    pixel_max = np.max(diff, axis=2)
    thresholds = {}
    for t in [0, 1, 2, 3, 5]:
        thresholds[f"pct_le_{t}_255"] = round(float(np.mean(pixel_max <= t) * 100), 4)
    return {
        "max_diff": float(np.max(diff)),
        "mean_diff": float(np.mean(diff)),
        "thresholds": thresholds,
    }


# ---------------------------------------------------------------------------
# Pure-numpy morphology (no scipy needed)
# ---------------------------------------------------------------------------

def _morph_dilate(mask: np.ndarray, size: int) -> np.ndarray:
    """Binary dilation: OR over shifted copies (small kernel, OK for probe)."""
    result = mask.astype(np.float32).copy()
    for dy in range(-size, size + 1):
        for dx in range(-size, size + 1):
            shifted = np.roll(np.roll(mask.astype(np.float32), dy, axis=0), dx, axis=1)
            result = np.maximum(result, shifted)
    return result > 0


def _morph_erode(mask: np.ndarray, size: int) -> np.ndarray:
    """Binary erosion: AND over shifted copies (small kernel, OK for probe)."""
    result = mask.astype(np.float32).copy()
    for dy in range(-size, size + 1):
        for dx in range(-size, size + 1):
            shifted = np.roll(np.roll(mask.astype(np.float32), dy, axis=0), dx, axis=1)
            result = np.minimum(result, shifted)
    return result > 0


# ---------------------------------------------------------------------------
# Region analysis
# ---------------------------------------------------------------------------

def _get_masks(subject: np.ndarray, dilation_px: int) -> dict:
    """Generate core, edge, outside masks based on subject alpha."""
    subject_mask = (subject[:, :, 3] > 10)
    dilated = _morph_dilate(subject_mask, dilation_px)
    eroded = _morph_erode(subject_mask, dilation_px)

    core = eroded
    edge = dilated & (~eroded)
    outside = ~dilated

    return {"core": core, "edge": edge, "outside": outside, "dilated": dilated}


def compute_region_diff(original: np.ndarray, reconstructed: np.ndarray,
                        subject: np.ndarray, dilation_px: int = 2) -> dict:
    masks = _get_masks(subject, dilation_px)
    diff = np.abs(original - reconstructed)
    pixel_max = np.max(diff, axis=2)

    result = {"dilation_px": dilation_px}
    for name in ["core", "edge", "outside"]:
        m = masks[name]
        n = int(np.sum(m))
        if n > 0:
            result[name] = {
                "mean_diff": float(np.mean(pixel_max[m])),
                "max_diff": float(np.max(pixel_max[m])),
                "pixels": n,
            }
        else:
            result[name] = {"mean_diff": 0.0, "max_diff": 0.0, "pixels": 0}
    return result


def check_subject_safety(original: np.ndarray, modified: np.ndarray,
                         subject: np.ndarray, dilation_px: int = 2) -> dict:
    masks = _get_masks(subject, dilation_px)
    diff = np.abs(original - modified)
    pixel_max = np.max(diff, axis=2)

    result = {"dilation_px": dilation_px}
    for name, mask_key in [("core", "core"), ("dilated", "dilated")]:
        m = masks[mask_key]
        n = int(np.sum(m))
        if n > 0:
            md = float(np.max(pixel_max[m]))
            result[name] = {"safe": md == 0.0, "max_diff": md, "pixels": n}
        else:
            result[name] = {"safe": True, "max_diff": 0.0, "pixels": 0}
    return result


def check_text_safety(original: np.ndarray, modified: np.ndarray,
                      text: np.ndarray) -> dict:
    text_mask = text[:, :, 3] > 5
    n = int(np.sum(text_mask))
    if n == 0:
        return {"safe": True, "text_pixels": 0, "max_diff_in_text": 0.0}
    diff = np.abs(original - modified)
    pixel_max = np.max(diff, axis=2)
    td = pixel_max[text_mask]
    return {
        "safe": float(np.max(td)) == 0.0,
        "text_pixels": n,
        "max_diff_in_text": float(np.max(td)),
        "mean_diff_in_text": float(np.mean(td)),
    }


def analyze_alpha(subject: np.ndarray) -> dict:
    alpha = subject[:, :, 3].astype(np.float32) / 255.0
    rgb = subject[:, :, :3].astype(np.float32)
    mask = (alpha > 0.01) & (alpha < 0.99)
    n = int(np.sum(mask))
    if n < 10:
        return {"type": "hard_edges", "partial_alpha_pixels": n}
    max_rgb = np.max(rgb[mask], axis=1)
    limit = alpha[mask] * 255.0 + 10
    pct = float(np.mean(max_rgb > limit) * 100)
    return {
        "type": "straight_alpha" if pct > 30 else "likely_premultiplied",
        "partial_alpha_pixels": n,
        "pct_exceeding_premult_limit": round(pct, 2),
    }


# ---------------------------------------------------------------------------
# Background enhancement probe (deterministic)
# ---------------------------------------------------------------------------

def modify_background(bg: np.ndarray, method: str = "hue_shift") -> np.ndarray:
    """Apply deterministic modification to background only."""
    result = bg.copy()
    if method == "hue_shift":
        # Rotate hue by 60 degrees (simple RGB shuffle: R→G, G→B, B→R)
        rgb = result[:, :, :3].copy()
        result[:, :, 0] = rgb[:, :, 1]  # R ← G
        result[:, :, 1] = rgb[:, :, 2]  # G ← B
        result[:, :, 2] = rgb[:, :, 0]  # B ← R
    elif method == "saturation_boost":
        gray = np.mean(result[:, :, :3], axis=2, keepdims=True)
        result[:, :, :3] = gray + (result[:, :, :3] - gray) * 1.5
        result[:, :, :3] = np.clip(result[:, :, :3], 0, 255)
    elif method == "blur":
        # Simple box blur
        from math import floor
        size = 5
        for c in range(3):
            ch = result[:, :, c]
            result[:, :, c] = _box_blur(ch, size)
    elif method == "brightness_boost":
        result[:, :, :3] = np.clip(result[:, :, :3] * 1.3, 0, 255)
    return result


def _box_blur(channel: np.ndarray, size: int) -> np.ndarray:
    """Simple separable box blur."""
    result = channel.copy()
    for _ in range(2):  # Two passes
        padded = np.pad(result, size, mode='edge')
        # Horizontal
        kernel = np.ones(2 * size + 1) / (2 * size + 1)
        h, w = result.shape
        for i in range(h):
            result[i] = np.convolve(padded[i + size], kernel, mode='same')[size:-size]
        # Vertical
        padded2 = np.pad(result, size, mode='edge')
        for j in range(w):
            result[:, j] = np.convolve(padded2[:, j + size], kernel, mode='same')[size:-size]
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    layers_dir = Path(args.layers_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame_numbers = [int(f.strip()) for f in args.frames.split(",") if f.strip()]

    print("=" * 60)
    print("LAYER RECOMPOSITION CHECK")
    print(f"Layers dir: {layers_dir}")
    print(f"Frames: {frame_numbers}")
    print("=" * 60)

    all_results = {"frames": {}}
    frame_psnr, frame_pct_le_1 = [], []

    for frame_num in frame_numbers:
        print(f"\n--- Frame {frame_num} ---")
        paths = {
            name: layers_dir / name / f"{frame_num:04d}.png"
            for name in ["composite", "background", "subject", "text"]
        }
        for name, p in paths.items():
            if not p.exists():
                print(f"  MISSING: {name} at {p}")

        composite, w, h = load_png(paths["composite"])
        background = load_png(paths["background"])[0]
        subject = load_png(paths["subject"])[0]
        text = load_png(paths["text"])[0]

        # 1. Lossless recomposition
        recomposed = composite_layers(background, subject, text)
        psnr = compute_psnr(composite, recomposed)
        diff = compute_diff_metrics(composite, recomposed)
        region = compute_region_diff(composite, recomposed, subject)
        alpha = analyze_alpha(subject)

        frame_psnr.append(psnr)
        frame_pct_le_1.append(diff["thresholds"]["pct_le_1_255"])

        print(f"  PSNR: {psnr:.2f} dB")
        print(f"  Pixels diff=0: {diff['thresholds']['pct_le_0_255']:.2f}%")
        print(f"  Pixels diff<=1/255: {diff['thresholds']['pct_le_1_255']:.2f}%")
        print(f"  Max diff: {diff['max_diff']:.2f}")
        print(f"  Core mean/max: {region['core']['mean_diff']:.4f}/{region['core']['max_diff']:.2f}")
        print(f"  Edge mean/max: {region['edge']['mean_diff']:.4f}/{region['edge']['max_diff']:.2f}")
        print(f"  Alpha: {alpha['type']} (partial pixels: {alpha.get('partial_alpha_pixels', 0)})")

        # Save recomposed and diff map
        save_png_blender(recomposed, output_dir / f"recomposed_{frame_num:04d}.png")
        diff_map = np.clip(np.abs(composite - recomposed) * 10, 0, 255)
        diff_map[:, :, 3] = 255
        save_png_blender(diff_map, output_dir / f"diff_{frame_num:04d}.png")

        # 2. Background enhancement probe
        for method in ["hue_shift", "saturation_boost"]:
            bg_mod = modify_background(background, method)
            enhanced = composite_layers(bg_mod, subject, text)
            text_safety = check_text_safety(recomposed, enhanced, text)
            subj_safety = check_subject_safety(recomposed, enhanced, subject)

            print(f"\n  Background mod '{method}':")
            print(f"    A3 Text safety: {'PASS' if text_safety['safe'] else 'FAIL'} "
                  f"(max_diff={text_safety['max_diff_in_text']:.1f})")
            print(f"    A4 Subject core safety: {'PASS' if subj_safety['core']['safe'] else 'FAIL'} "
                  f"(max_diff={subj_safety['core']['max_diff']:.1f})")
            print(f"    A4 Subject dilated safety: {'PASS' if subj_safety['dilated']['safe'] else 'FAIL'} "
                  f"(max_diff={subj_safety['dilated']['max_diff']:.1f})")

            # Save enhanced
            save_png_blender(enhanced, output_dir / f"enhanced_{method}_{frame_num:04d}.png")

            enhanced_diff = np.clip(np.abs(composite - enhanced) * 5, 0, 255)
            enhanced_diff[:, :, 3] = 255
            save_png_blender(enhanced_diff,
                             output_dir / f"enhanced_diff_{method}_{frame_num:04d}.png")

            if method not in all_results.setdefault("enhancement", {}):
                all_results["enhancement"][method] = {}
            all_results["enhancement"][method][str(frame_num)] = {
                "text_safety": text_safety,
                "subject_safety": subj_safety,
            }

        all_results["frames"][str(frame_num)] = {
            "psnr": psnr, "diff": diff, "region": region, "alpha": alpha,
        }

    # Summary
    summary = {
        "psnr_mean": float(np.mean(frame_psnr)),
        "psnr_min": float(np.min(frame_psnr)),
        "pct_le_1_mean": float(np.mean(frame_pct_le_1)),
        "pct_le_1_min": float(np.min(frame_pct_le_1)),
    }
    all_results["summary"] = summary

    print(f"\n{'='*60}")
    print("RECOMPOSITION SUMMARY")
    print(f"{'='*60}")
    print(f"PSNR: mean={summary['psnr_mean']:.2f} dB, min={summary['psnr_min']:.2f} dB")
    print(f"Diff <= 1/255: mean={summary['pct_le_1_mean']:.2f}%, min={summary['pct_le_1_min']:.2f}%")

    a2_pct = summary["pct_le_1_min"] >= 99.5
    a2_psnr = summary["psnr_min"] >= 45.0
    print(f"A2 >= 99.5% diff <= 1/255: {'PASS' if a2_pct else 'FAIL'}")
    print(f"A2 PSNR >= 45 dB: {'PASS' if a2_psnr else 'FAIL'}")

    report_path = output_dir / "recomposition_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
