"""
Lineart ControlNet Color Fix Spike — prompt engineering + color correction.
Narrow 4-hour R&D: fix saturation loss and weak visual lift from previous spike.

Usage:
  # Experiment 1: Prompt variants on character keyframes
  python run_color_fix.py --mode keyframes --variant A,B,C --denoise 0.30,0.35 \
    --input-dir spikes/ai_enhance_gate2/output/character_intro/keyframes/raw

  # Experiment 2: Continuous 2s with best variant
  python run_color_fix.py --mode continuous --variant B --denoise 0.35 \
    --input-dir spikes/ai_enhance_gate2/output/character_intro/continuous/raw

  # Experiment 3: Product sanity check
  python run_color_fix.py --mode product --variant B --denoise 0.35 \
    --input-dir spikes/ai_enhance_gate2/output/product_orbit/keyframes/raw
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = SCRIPT_DIR / "output"
WORKFLOW_JSON = SCRIPT_DIR / "workflows" / "sdxl_lineart_preproc_api.json"
PREV_WORKFLOW = Path("E:/cineanchor/spikes/ai_controlnet_structure_enhance/workflows/sdxl_preprocessor_controlnet_api.json")

GATE2 = Path("E:/cineanchor/spikes/ai_enhance_gate2/output")
CHAR_KF_RAW = GATE2 / "character_intro/keyframes/raw"
CHAR_CT_RAW = GATE2 / "character_intro/continuous/raw"
PROD_KF_RAW = GATE2 / "product_orbit/keyframes/raw"

FFMPEG = "E:/cineanchor/.tools/ffmpeg/ffmpeg-8.1.1-essentials_build/bin/ffmpeg.exe"

# ---------------------------------------------------------------------------
# Prompt variants
# ---------------------------------------------------------------------------
PROMPTS = {
    "A": {
        "label": "Game promo vivid",
        "positive": (
            "colorful mobile game promotion still, vivid saturated colors, "
            "bright stylized lighting, crisp character render, premium mobile game promo, "
            "preserve original character design, preserve silhouette, preserve color palette, "
            "game art style, vibrant game keyframe, rich bright colors, clean cel-shaded lighting, "
            "no cinematic dark mood, no filmic desaturation, no realistic skin texture, "
            "no gritty rendering, no moody shadows, no low saturation, no dramatic shadows, no text"
        ),
        "negative": (
            "text, watermark, logo, deformed subject, changed face, changed outfit, "
            "cinematic lighting, filmic look, desaturated, dark shadows, moody, "
            "gritty, realistic skin, photo-realistic, 3D render artifacts, "
            "extra limbs, extra objects, melted edges, blur, flicker, "
            "oversaturated to burned, noisy artifacts, layout change"
        ),
    },
    "B": {
        "label": "Original-color preservation",
        "positive": (
            "polished game promotional keyframe, preserve original colors exactly, "
            "preserve original hue and saturation, clean promotional lighting, "
            "polished render, higher clarity and sharpness, stronger contrast without darkening, "
            "enhanced material definition, crisp edges, bright game-ad presentation, "
            "original character design intact, no color shift, no text"
        ),
        "negative": (
            "text, watermark, logo, desaturated, washed out, darkened image, "
            "muted colors, color shift, identity change, changed outfit, changed silhouette, "
            "extra details not in original, deformation, skin texture change, "
            "cinematic desaturation, filmic color grading, moody lighting, "
            "flicker, noisy artifacts, layout change"
        ),
    },
    "C": {
        "label": "Minimal style lift",
        "positive": (
            "subtle quality enhancement only, cleaner lighting, sharper material definition, "
            "refined edges, no redesign, no color shift, no subject change, "
            "original colors and saturation preserved, light clarity boost, "
            "game character render polish, no text"
        ),
        "negative": (
            "text, watermark, logo, any color shift, any saturation change, "
            "any style change, any redesign, changed outfit, changed face, "
            "extra detail, deformation, darkening, brightening, "
            "cinematic look, filmic look, mood change, flicker, artifacts"
        ),
    },
}

# ---------------------------------------------------------------------------
class ComfyError(RuntimeError):
    pass


def _api(base_url: str, path: str, *, method="GET", payload=None, timeout=30) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = Request(f"{base_url}{path}", data=data, method=method, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as r:
            body = r.read().decode()
            return json.loads(body) if body else {}
    except HTTPError as e:
        raise ComfyError(f"HTTP {e.code} {path}") from e
    except URLError as e:
        raise ComfyError(f"Unreachable: {e.reason}") from e


def _upload(base_url: str, path: Path, name: str = "", timeout=60) -> dict:
    b = f"----cineanchor-{uuid.uuid4().hex}"
    raw_bytes = path.read_bytes()
    parts = [
        f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; "
        f"filename=\"{name or path.name}\"\r\nContent-Type: image/png\r\n\r\n".encode(),
        raw_bytes,
        f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"type\"\r\n\r\ninput\r\n"
        f"--{b}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n"
        f"--{b}--\r\n".encode(),
    ]
    body = b"".join(parts)
    req = Request(
        f"{base_url}/upload/image", data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={b}",
                 "Content-Length": str(len(body)), "Accept": "application/json"},
    )
    try:
        with urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except HTTPError as e:
        raise ComfyError(f"Upload failed HTTP {e.code}") from e
    except URLError as e:
        raise ComfyError(f"Upload failed: {e.reason}") from e


def _download(base_url: str, ref: dict, dest: Path, timeout=120) -> None:
    q = urlencode({"filename": ref["filename"],
                   "subfolder": ref.get("subfolder", ""),
                   "type": ref.get("type", "output")})
    req = Request(f"{base_url}/view?{q}", method="GET")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(req, timeout=timeout) as r:
        dest.write_bytes(r.read())


def _queue(base_url: str, wf: dict, client_id: str, timeout=60) -> str:
    r = _api(base_url, "/prompt", method="POST",
             payload={"prompt": wf, "client_id": client_id}, timeout=timeout)
    pid = r.get("prompt_id")
    if not pid:
        raise ComfyError(f"No prompt_id: {r}")
    return str(pid)


_gpu = lambda: {"available": False}  # simplified for speed


def _wait(base_url: str, prompt_id: str, timeout_s=1200, poll_s=1):
    deadline = time.monotonic() + timeout_s
    peak, last = None, {}
    while time.monotonic() < deadline:
        hist = _api(base_url, f"/history/{prompt_id}", timeout=30)
        last = hist
        entry = hist.get(prompt_id)
        if entry:
            st = entry.get("status", {})
            if st.get("status_str") == "error":
                raise ComfyError(f"Prompt failed: {st}")
            imgs = []
            for out in entry.get("outputs", {}).values():
                imgs.extend(out.get("images", []))
            if imgs:
                return imgs, entry, peak
        time.sleep(poll_s)
    raise ComfyError(f"Timeout waiting for {prompt_id}")


def _sub(template: Any, reps: dict) -> Any:
    if isinstance(template, dict):
        return {k: _sub(v, reps) for k, v in template.items()}
    if isinstance(template, list):
        return [_sub(v, reps) for v in template]
    if isinstance(template, str) and template in reps:
        return reps[template]
    return template


def _dlabel(v: float) -> str:
    return f"denoise_{v:.2f}".replace(".", "_")


def run_frames(base_url: str, frames: list[Path], variant_key: str, denoise: float,
               output_dir: Path, checkpoint: str, control_model: str,
               steps: int, cfg: float, base_seed: int, seed_mode: str,
               wf_template: dict) -> dict:
    """Run Lineart ControlNet on a set of frames with a specific prompt variant."""
    client_id = f"cineanchor-lcf-{uuid.uuid4().hex}"
    prompt_cfg = PROMPTS[variant_key]
    entries = []

    for i, f in enumerate(frames, start=1):
        prefix = (f"cineanchor_lcf_{variant_key}_{_dlabel(denoise)}_"
                  f"f{i:03d}_{uuid.uuid4().hex[:6]}")
        dest = output_dir / f.name
        seed = base_seed if seed_mode == "fixed" else base_seed + i

        t0 = time.perf_counter()
        up = _upload(base_url, f, name=f"lcf_{uuid.uuid4().hex[:6]}_{f.name}")
        up_name = up.get("name")
        if not up_name:
            raise ComfyError(f"Upload failed: {up}")

        wf = _sub(wf_template, {
            "__INPUT_IMAGE__": up_name,
            "__PREPROCESSOR__": "LineartStandardPreprocessor",
            "__PREPROC_RESOLUTION__": 1024,
            "__OUTPUT_PREFIX__": prefix,
            "__CHECKPOINT_NAME__": checkpoint,
            "__CONTROL_NET_NAME__": control_model,
            "__CONTROL_TYPE__": "canny/lineart/anime_lineart/mlsd",
            "__CONTROL_STRENGTH__": 0.75,
            "__CONTROL_START__": 0.0,
            "__CONTROL_END__": 0.85,
            "__SEED__": seed,
            "__STEPS__": steps,
            "__CFG__": cfg,
            "__DENOISE__": denoise,
            "__POSITIVE_PROMPT__": prompt_cfg["positive"],
            "__NEGATIVE_PROMPT__": prompt_cfg["negative"],
        })

        pid = _queue(base_url, wf, client_id)
        imgs, entry, peak = _wait(base_url, pid)
        _download(base_url, imgs[0], dest)
        elapsed = time.perf_counter() - t0

        entries.append({
            "raw": str(f), "enhanced": str(dest),
            "variant": variant_key, "denoise": denoise, "seed": seed,
            "prompt_id": pid, "seconds": round(elapsed, 3),
        })
        print(f"  [{i}/{len(frames)}] {elapsed:.1f}s  {dest}")

    return {"frames": entries, "total_s": sum(e["seconds"] for e in entries)}


def apply_color_correction(raw_dir: Path, enhanced_dir: Path, output_dir: Path,
                           saturation: float = 1.3, contrast: float = 1.05,
                           brightness: float = 0.0, gamma: float = 1.0) -> list[Path]:
    """Apply FFmpeg color correction to enhanced frames."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for raw_f in sorted(raw_dir.glob("*.png")):
        enh_f = enhanced_dir / raw_f.name
        out_f = output_dir / raw_f.name
        if not enh_f.exists():
            continue
        # eq filter: brightness, contrast, saturation, gamma
        vf = (f"eq=brightness={brightness}:contrast={contrast}:"
              f"saturation={saturation}:gamma={gamma}")
        cmd = [FFMPEG, "-y", "-i", str(enh_f), "-vf", vf,
               "-frames:v", "1", str(out_f)]
        subprocess.run(cmd, capture_output=True, check=True)
        results.append(out_f)
    print(f"  Color corrected {len(results)} frames -> {output_dir}")
    return results


def main():
    p = argparse.ArgumentParser(description="Lineart Color Fix Spike")
    p.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    p.add_argument("--mode", required=True, choices=["keyframes", "continuous", "product"])
    p.add_argument("--variant", required=True, help="A,B,C or comma-separated")
    p.add_argument("--denoise", required=True, help="0.30,0.35")
    p.add_argument("--checkpoint", default="")
    p.add_argument("--control-model", default="")
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--cfg", type=float, default=1.6)
    p.add_argument("--seed-mode", choices=["fixed", "frame"], default="frame")
    p.add_argument("--base-seed", type=int, default=20260624)
    p.add_argument("--input-dir", default="")
    p.add_argument("--color-correct", action="store_true")
    p.add_argument("--saturation", type=float, default=1.3)
    p.add_argument("--contrast", type=float, default=1.05)
    p.add_argument("--brightness", type=float, default=0.0)
    p.add_argument("--gamma", type=float, default=1.0)
    args = p.parse_args()

    variants = [v.strip() for v in args.variant.split(",")]
    denoises = [float(d.strip()) for d in args.denoise.split(",")]

    for v in variants:
        if v not in PROMPTS:
            print(f"Unknown variant: {v}. Choices: {list(PROMPTS)}")
            return 1

    base_url = args.comfy_url.rstrip("/")

    # Verify ComfyUI
    try:
        info = _api(base_url, "/object_info", timeout=30)
        ver = _api(base_url, "/system_stats", timeout=10)
        print(f"ComfyUI {ver['system']['comfyui_version']} OK")
    except ComfyError as e:
        print(f"ComfyUI error: {e}")
        return 1

    # Resolve checkpoint
    ckpts = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    ckpt = args.checkpoint
    if not ckpt:
        for hint in ("realvisxl", "lightning", "sd_xl_base"):
            for c in ckpts:
                if hint in c.lower():
                    ckpt = c
                    break
            if ckpt:
                break
        ckpt = ckpt or ckpts[0]
    print(f"Checkpoint: {ckpt}")

    # Resolve ControlNet
    cns = info["ControlNetLoader"]["input"]["required"]["control_net_name"][0]
    cn = args.control_model or cns[0]
    print(f"ControlNet: {cn}")

    # Load workflow
    wf_src = PREV_WORKFLOW if PREV_WORKFLOW.exists() else WORKFLOW_JSON
    wf_template = json.loads(wf_src.read_text("utf-8"))
    print(f"Workflow: {wf_src}")

    # Input frames
    raw_map = {"keyframes": CHAR_KF_RAW, "continuous": CHAR_CT_RAW, "product": PROD_KF_RAW}
    raw_dir = Path(args.input_dir) if args.input_dir else raw_map[args.mode]
    frames = sorted(raw_dir.glob("*.png"))
    if not frames:
        print(f"ERROR: No PNGs in {raw_dir}")
        return 1
    print(f"Input: {len(frames)} frames from {raw_dir}")

    report = {"mode": args.mode, "variants": variants, "denoises": denoises,
              "checkpoint": ckpt, "control_model": cn,
              "settings": {"steps": args.steps, "cfg": args.cfg,
                           "seed_mode": args.seed_mode, "base_seed": args.base_seed},
              "started_at": time.time(), "results": {}}

    for variant in variants:
        for denoise in denoises:
            key = f"{variant}_{_dlabel(denoise)}"
            mode_dir = OUTPUT_ROOT / args.mode
            out_dir = mode_dir / "keyframes" / key
            out_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n{'='*60}\nVariant {variant} ({PROMPTS[variant]['label']})  "
                  f"denoise={denoise:.2f}\n{'='*60}")

            result = run_frames(base_url, frames, variant, denoise, out_dir,
                                ckpt, cn, args.steps, args.cfg,
                                args.base_seed, args.seed_mode, wf_template)
            report["results"][key] = result

            # Color correction if enabled
            if args.color_correct:
                cc_dir = mode_dir / "keyframes" / f"{key}_colorfix"
                apply_color_correction(raw_dir, out_dir, cc_dir,
                                       args.saturation, args.contrast,
                                       args.brightness, args.gamma)
                report["results"][f"{key}_colorfix"] = {"color_correction": {
                    "saturation": args.saturation, "contrast": args.contrast,
                    "brightness": args.brightness, "gamma": args.gamma,
                    "output_dir": str(cc_dir),
                }}

    report["finished_at"] = time.time()
    rp = OUTPUT_ROOT / args.mode / f"report_{'_'.join(variants)}_{uuid.uuid4().hex[:8]}.json"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, indent=2, ensure_ascii=False), "utf-8")
    print(f"\nReport: {rp}")

    print("\n" + "=" * 60 + "\nSUMMARY\n" + "=" * 60)
    for key, val in report["results"].items():
        if "frames" in val:
            fs = val["frames"]
            if fs:
                avg = sum(x["seconds"] for x in fs) / len(fs)
                print(f"  {key}: {len(fs)}f  avg={avg:.1f}s/f  total={val['total_s']:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
