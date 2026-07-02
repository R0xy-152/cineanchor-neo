"""Compute objective image quality metrics across all character keyframe experiments."""
from pathlib import Path
import json
from PIL import Image
import numpy as np

RAW_DIR = Path("spikes/ai_enhance_gate2/output/character_intro/keyframes/raw")
OUT_DIR = Path("spikes/ai_controlnet_structure_enhance/output/character/keyframes")

def load_rgb(path):
    return np.array(Image.open(path).convert("RGB"), dtype=np.float32)

def metrics(raw, enhanced):
    diff = np.abs(enhanced - raw)
    mae = diff.mean()
    rmse = np.sqrt(np.square(enhanced - raw).mean())
    # Luminance change
    ry = 0.299*raw[:,:,0] + 0.587*raw[:,:,1] + 0.114*raw[:,:,2]
    ey = 0.299*enhanced[:,:,0] + 0.587*enhanced[:,:,1] + 0.114*enhanced[:,:,2]
    lum = np.abs(ey - ry).mean()
    # Saturation
    def sat(img):
        r,g,b = img[:,:,0], img[:,:,1], img[:,:,2]
        return np.mean((np.maximum(np.maximum(r,g),b) - np.minimum(np.minimum(r,g),b)) / (np.maximum(np.maximum(r,g),b) + 1e-6))
    sr, se = sat(raw), sat(enhanced)
    # Edge energy (Sobel)
    def edge_energy(img):
        gx = np.abs(img[1:-1,2:,1] - img[1:-1,:-2,1]) + np.abs(img[2:,1:-1,1] - img[:-2,1:-1,1])
        return gx.mean()
    er, ee = edge_energy(raw), edge_energy(enhanced)
    return {"mae": mae, "rmse": rmse, "lum_change": lum, "sat_raw": sr, "sat_enh": se,
            "sat_delta": se-sr, "edge_raw": er, "edge_enh": ee, "edge_ratio": ee/(er+1e-6)}

raws = sorted(RAW_DIR.glob("*.png"))
print(f"Raw frames: {len(raws)}")

results = {}
for raw_f in raws:
    raw = load_rgb(raw_f)
    for method_dir in sorted(OUT_DIR.iterdir()):
        if not method_dir.is_dir():
            continue
        enh_f = method_dir / raw_f.name
        if not enh_f.exists():
            continue
        name = method_dir.name
        enhanced = load_rgb(enh_f)
        m = metrics(raw, enhanced)
        if name not in results:
            results[name] = {k: 0.0 for k in m}
            results[name]["count"] = 0
        for k in m:
            results[name][k] += m[k]
        results[name]["count"] += 1

# Average
for name in results:
    c = results[name]["count"]
    for k in list(results[name]):
        if k != "count":
            results[name][k] /= c

# Print table
header = f"{'Method':<30} {'MAE':>8} {'RMSE':>8} {'LumChg':>8} {'SatRaw':>8} {'SatEnh':>8} {'SatD':>8} {'EdgeRaw':>8} {'EdgeEnh':>8} {'EdgeR':>8}"
print("\n" + header)
print("-" * len(header))
for name in sorted(results):
    r = results[name]
    print(f"{name:<30} {r['mae']:8.2f} {r['rmse']:8.2f} {r['lum_change']:8.2f} {r['sat_raw']:8.4f} {r['sat_enh']:8.4f} {r['sat_delta']:8.4f} {r['edge_raw']:8.2f} {r['edge_enh']:8.2f} {r['edge_ratio']:8.4f}")
