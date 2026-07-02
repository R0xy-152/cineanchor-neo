"""
Alternative recomposition strategy: mask-based background replacement.

Uses subject/text alpha from separate renders as masks to protect pixels
in the original composite frame when modifying the background.

This avoids the lossy compositing problem (Eevee non-linear transforms
prevent lossless layer-by-layer recomposition).

Usage:
  "{blender_exe}" --background --python measure_recompose.py --
    --layers-dir <dir> --output-dir <dir> [--frames 1,32,64,96]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Mask-based recomposition")
    parser.add_argument("--layers-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--frames", type=str, default="1,32,64,96")
    return parser.parse_args(argv)


def load_png(filepath: Path) -> tuple:
    img = bpy.data.images.load(str(filepath))
    w, h = img.size
    pixels = (np.array(img.pixels[:]).reshape(h, w, 4) * 255.0).astype(np.float32)
    bpy.data.images.remove(img)
    return pixels, w, h


def save_png_blender(pixels: np.ndarray, filepath: Path) -> None:
    h, w = pixels.shape[:2]
    img = bpy.data.images.new("temp", width=w, height=h, alpha=True)
    img.pixels[:] = (np.clip(pixels, 0, 255).astype(np.float32) / 255.0).flatten()
    img.filepath_raw = str(filepath)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def create_masks(subject: np.ndarray, text: np.ndarray) -> dict:
    """
    Create binary masks from subject and text alpha channels.

    Returns:
        subject_mask: True where subject is visible (alpha > threshold)
        text_mask: True where text is visible (alpha > threshold)
        protected_mask: True where EITHER subject or text is visible
        safe_background_mask: True where background can be safely modified
    """
    subj_mask = subject[:, :, 3] > 10
    text_mask = text[:, :, 3] > 10
    protected = subj_mask | text_mask
    safe_bg = ~protected

    # Also compute dilated protection zone for edge safety
    # Subject core (eroded)
    subj_core = _morph_erode(subj_mask, 2)
    subj_edge = subj_mask & (~subj_core)

    text_core = _morph_erode(text_mask, 2)
    text_edge = text_mask & (~text_core)

    return {
        "subject_mask": subj_mask,
        "text_mask": text_mask,
        "protected_mask": protected,
        "safe_background": safe_bg,
        "subject_core": subj_core,
        "subject_edge": subj_edge,
        "text_core": text_core,
        "text_edge": text_edge,
        "subject_pixels": int(np.sum(subj_mask)),
        "text_pixels": int(np.sum(text_mask)),
    }


def _morph_erode(mask: np.ndarray, size: int) -> np.ndarray:
    """Binary erosion via AND over shifted copies."""
    result = mask.astype(np.float32).copy()
    for dy in range(-size, size + 1):
        for dx in range(-size, size + 1):
            shifted = np.roll(np.roll(mask.astype(np.float32), dy, axis=0), dx, axis=1)
            result = np.minimum(result, shifted)
    return result > 0


def _morph_dilate(mask: np.ndarray, size: int) -> np.ndarray:
    """Binary dilation via OR over shifted copies."""
    result = mask.astype(np.float32).copy()
    for dy in range(-size, size + 1):
        for dx in range(-size, size + 1):
            shifted = np.roll(np.roll(mask.astype(np.float32), dy, axis=0), dx, axis=1)
            result = np.maximum(result, shifted)
    return result > 0


def modify_background(composite: np.ndarray, mask: np.ndarray, method: str) -> np.ndarray:
    """Apply deterministic modification only to background region."""
    result = composite.copy()

    if method == "hue_shift":
        # RGB channel rotation
        rgb = result[:, :, :3].copy()
        result[:, :, 0] = np.where(mask, result[:, :, 0], rgb[:, :, 1])
        result[:, :, 1] = np.where(mask, result[:, :, 1], rgb[:, :, 2])
        result[:, :, 2] = np.where(mask, result[:, :, 2], rgb[:, :, 0])

    elif method == "saturation_boost":
        gray = np.mean(result[:, :, :3], axis=2, keepdims=True)
        boosted = gray + (result[:, :, :3] - gray) * 1.5
        boosted = np.clip(boosted, 0, 255)
        for c in range(3):
            result[:, :, c] = np.where(mask, result[:, :, c], boosted[:, :, c])

    elif method == "brightness":
        bg_only = result[:, :, :3].copy()
        bg_only = np.clip(bg_only * 1.3, 0, 255)
        for c in range(3):
            result[:, :, c] = np.where(mask, result[:, :, c], bg_only[:, :, c])

    elif method == "blur_bg":
        from math import floor
        ks = 3
        for c in range(3):
            ch = result[:, :, c].copy()
            blurred = _box_blur(ch, ks)
            result[:, :, c] = np.where(mask, ch, blurred)

    return result


def _box_blur(channel: np.ndarray, size: int) -> np.ndarray:
    """Separable box blur."""
    result = channel.copy()
    h, w = channel.shape
    for _ in range(2):
        kernel = np.ones(2 * size + 1) / (2 * size + 1)
        # Horizontal
        for i in range(h):
            row = np.pad(result[i], size, mode='edge')
            result[i] = np.convolve(row, kernel, mode='same')[size:-size]
        # Vertical
        for j in range(w):
            col = np.pad(result[:, j], size, mode='edge')
            result[:, j] = np.convolve(col, kernel, mode='same')[size:-size]
    return result


def compute_metrics(original: np.ndarray, modified: np.ndarray,
                    masks: dict, label: str) -> dict:
    """Compute safety metrics for a modified composite."""
    diff = np.abs(original - modified)
    pixel_max_diff = np.max(diff, axis=2)

    results = {"method": label}

    # A3: Text safety
    tm = masks["text_mask"]
    if np.any(tm):
        td = pixel_max_diff[tm]
        results["text"] = {
            "safe": float(np.max(td)) == 0.0,
            "max_diff": float(np.max(td)),
            "mean_diff": float(np.mean(td)),
            "pixels": int(np.sum(tm)),
        }
    else:
        results["text"] = {"safe": True, "max_diff": 0.0, "pixels": 0}

    # A4: Subject safety
    for region_name, region_mask_key in [
        ("subject_core", "subject_core"),
        ("subject_edge", "subject_edge"),
        ("subject_full", "subject_mask"),
    ]:
        m = masks[region_mask_key]
        if np.any(m):
            md = float(np.max(pixel_max_diff[m]))
            results[region_name] = {
                "safe": md == 0.0,
                "max_diff": md,
                "mean_diff": float(np.mean(pixel_max_diff[m])),
                "pixels": int(np.sum(m)),
            }
        else:
            results[region_name] = {"safe": True, "max_diff": 0.0, "pixels": 0}

    # Background change verification
    bg_mask = masks["safe_background"]
    if np.any(bg_mask):
        bg_diff = pixel_max_diff[bg_mask]
        results["background"] = {
            "changed": float(np.max(bg_diff)) > 0.0,
            "max_diff": float(np.max(bg_diff)),
            "mean_diff": float(np.mean(bg_diff)),
            "pixels": int(np.sum(bg_mask)),
        }

    return results


def compute_mask_iou(subject: np.ndarray, ground_truth_alpha: np.ndarray | None = None) -> dict:
    """
    Compute IoU between generated subject mask and ground truth.
    For PNG subjects, use the original PNG alpha as ground truth.
    For GLB subjects, no ground truth available.
    """
    subj_mask = subject[:, :, 3] > 10

    if ground_truth_alpha is None:
        return {"iou": None, "note": "No ground truth alpha available"}

    gt_mask = ground_truth_alpha[:, :, 3] > 10
    intersection = np.sum(subj_mask & gt_mask)
    union = np.sum(subj_mask | gt_mask)

    iou = float(intersection / union) if union > 0 else 0.0
    return {
        "iou": round(iou, 6),
        "intersection": int(intersection),
        "union": int(union),
    }


def main() -> None:
    args = parse_args()
    layers_dir = Path(args.layers_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame_numbers = [int(f.strip()) for f in args.frames.split(",") if f.strip()]

    print("=" * 60)
    print("MASK-BASED BACKGROUND ENHANCEMENT PROBE")
    print(f"Layers dir: {layers_dir}")
    print("=" * 60)

    all_results = {"frames": {}}

    methods = ["hue_shift", "saturation_boost", "brightness"]
    summary_text_safe = []
    summary_subj_core_safe = []
    summary_subj_full_safe = []

    for frame_num in frame_numbers:
        print(f"\n--- Frame {frame_num} ---")
        paths = {
            "composite": layers_dir / "composite" / f"{frame_num:04d}.png",
            "subject": layers_dir / "subject" / f"{frame_num:04d}.png",
            "text": layers_dir / "text" / f"{frame_num:04d}.png",
        }
        for name, p in paths.items():
            if not p.exists():
                print(f"  MISSING: {name} at {p}")
                return

        composite, w, h = load_png(paths["composite"])
        subject, _, _ = load_png(paths["subject"])
        text, _, _ = load_png(paths["text"])

        # Create masks from alpha channels
        masks = create_masks(subject, text)
        print(f"  Subject mask: {masks['subject_pixels']} px "
              f"(core: {int(np.sum(masks['subject_core']))}, edge: {int(np.sum(masks['subject_edge']))})")
        print(f"  Text mask: {masks['text_pixels']} px")
        print(f"  Protected region: {int(np.sum(masks['protected_mask']))} px "
              f"({float(np.mean(masks['protected_mask'])*100):.1f}% of frame)")

        frame_results = {"masks": {k: int(np.sum(v)) if isinstance(v, np.ndarray) else v
                                  for k, v in masks.items()
                                  if k in ["subject_pixels", "text_pixels"]}}

        # Save mask visualization
        mask_viz = np.zeros_like(composite)
        mask_viz[masks["subject_core"], 0] = 255  # Red: subject core
        mask_viz[masks["subject_edge"], 1] = 255  # Green: subject edge
        mask_viz[masks["text_mask"], 2] = 255  # Blue: text
        mask_viz[:, :, 3] = 255
        save_png_blender(mask_viz, output_dir / f"masks_{frame_num:04d}.png")

        # Apply each modification method
        for method in methods:
            modified = modify_background(composite, masks["protected_mask"], method)
            metrics = compute_metrics(composite, modified, masks, method)

            print(f"\n  Method '{method}':")
            print(f"    Text safe: {'PASS' if metrics['text']['safe'] else 'FAIL'} "
                  f"(max={metrics['text']['max_diff']:.1f}, n={metrics['text']['pixels']})")
            print(f"    Subject core safe: {'PASS' if metrics['subject_core']['safe'] else 'FAIL'} "
                  f"(max={metrics['subject_core']['max_diff']:.1f})")
            print(f"    Subject full safe: {'PASS' if metrics['subject_full']['safe'] else 'FAIL'} "
                  f"(max={metrics['subject_full']['max_diff']:.1f})")
            print(f"    Subject edge safe: {'PASS' if metrics['subject_edge']['safe'] else 'FAIL'} "
                  f"(max={metrics['subject_edge']['max_diff']:.1f})")
            print(f"    Background changed: {metrics['background']['changed']} "
                  f"(mean={metrics['background']['mean_diff']:.1f})")

            frame_results[method] = metrics

            # Track summary
            if method == methods[0]:  # Only track first method for summary
                summary_text_safe.append(metrics['text']['safe'])
                summary_subj_core_safe.append(metrics['subject_core']['safe'])
                summary_subj_full_safe.append(metrics['subject_full']['safe'])

            # Save modified frame
            save_png_blender(modified, output_dir / f"modified_{method}_{frame_num:04d}.png")

        all_results["frames"][str(frame_num)] = frame_results

    # Summary
    summary = {
        "text_safe_all_frames": all(summary_text_safe),
        "subject_core_safe_all_frames": all(summary_subj_core_safe),
        "subject_full_safe_all_frames": all(summary_subj_full_safe),
    }
    all_results["summary"] = summary

    print(f"\n{'='*60}")
    print("ENHANCEMENT PROBE SUMMARY")
    print(f"{'='*60}")
    print(f"A3 Text safety: {'PASS' if summary['text_safe_all_frames'] else 'FAIL'}")
    print(f"A4 Subject core safety: {'PASS' if summary['subject_core_safe_all_frames'] else 'FAIL'}")
    print(f"A4 Subject full safety: {'PASS' if summary['subject_full_safe_all_frames'] else 'FAIL'}")

    report_path = output_dir / "enhancement_probe_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
