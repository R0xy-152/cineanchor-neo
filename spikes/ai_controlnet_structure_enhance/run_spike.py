"""
AI ControlNet Structure Enhancement Spike Runner.

Runs Experiments 2-6: ControlNet (Canny/Depth/Normal/Lineart) keyframe tests,
product shape-preservation test, 2-second temporal test, and plain img2img baseline.

Usage:
  # Experiment 2-3: Keyframe sweep (character)
  python run_spike.py --experiment character --methods canny,depth,normal,lineart,plain --denoise 0.25,0.35,0.45

  # Experiment 4: Product shape test with best method
  python run_spike.py --experiment product --methods depth --denoise 0.25,0.35,0.45

  # Experiment 5: 2-second temporal test with best settings
  python run_spike.py --experiment continuous --methods depth --denoise 0.35
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

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_ROOT = SCRIPT_DIR / "workflows"
PREPROC_WF = WORKFLOW_ROOT / "sdxl_preprocessor_controlnet_api.json"
PLAIN_WF = WORKFLOW_ROOT / "sdxl_img2img_api.json"
OUTPUT_ROOT = SCRIPT_DIR / "output"

GATE2_OUTPUT = Path("E:/cineanchor/spikes/ai_enhance_gate2/output")
CHAR_KF_RAW = GATE2_OUTPUT / "character_intro/keyframes/raw"
CHAR_KF_MASK = GATE2_OUTPUT / "character_intro/keyframes/mask"
CHAR_CT_RAW = GATE2_OUTPUT / "character_intro/continuous/raw"
CHAR_CT_MASK = GATE2_OUTPUT / "character_intro/continuous/mask"
PROD_KF_RAW = GATE2_OUTPUT / "product_orbit/keyframes/raw"
PROD_KF_MASK = GATE2_OUTPUT / "product_orbit/keyframes/mask"

# ---------------------------------------------------------------------------
# Method registry
# ---------------------------------------------------------------------------
METHODS = {
    "canny": {"preprocessor": "CannyEdgePreprocessor",
              "control_type": "canny/lineart/anime_lineart/mlsd",
              "strength": 0.75, "resolution": 1024},
    "depth": {"preprocessor": "DepthAnythingV2Preprocessor",
              "control_type": "depth",
              "strength": 0.75, "resolution": 1024},
    "normal": {"preprocessor": "BAE-NormalMapPreprocessor",
               "control_type": "normal",
               "strength": 0.75, "resolution": 1024},
    "lineart": {"preprocessor": "LineartStandardPreprocessor",
                "control_type": "canny/lineart/anime_lineart/mlsd",
                "strength": 0.75, "resolution": 1024},
    "plain": {"preprocessor": None, "control_type": None, "strength": None, "resolution": None},
}

POSITIVE = (
    "polished mobile game promotional keyframe, cinematic lighting, richer color, "
    "clean highlights, premium game ad still, crisp but stable edges, preserve "
    "exact subject silhouette, preserve exact pose, preserve exact composition, no text"
)
NEGATIVE = (
    "text, watermark, logo, deformed subject, changed face, changed costume, "
    "changed product geometry, extra limbs, extra objects, melted edges, blur, "
    "flicker, oversaturated, noisy artifacts, layout change"
)


# ---------------------------------------------------------------------------
class ComfyError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
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
        tail = e.read().decode(errors="replace")
        raise ComfyError(f"HTTP {e.code} {path}: {tail}") from e
    except URLError as e:
        raise ComfyError(f"Unreachable {base_url}: {e.reason}") from e


def _upload(base_url: str, path: Path, name: str = "", timeout=60) -> dict:
    b = f"----cineanchor-{uuid.uuid4().hex}"
    raw = path.read_bytes()
    parts = [
        f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; "
        f"filename=\"{name or path.name}\"\r\nContent-Type: image/png\r\n\r\n".encode(),
        raw,
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
        raise ComfyError(f"Upload HTTP {e.code}: {e.read().decode(errors='replace')}") from e
    except URLError as e:
        raise ComfyError(f"Upload failed: {e.reason}") from e


def _download(base_url: str, ref: dict, dest: Path, timeout=120) -> None:
    q = urlencode({"filename": ref["filename"],
                   "subfolder": ref.get("subfolder", ""),
                   "type": ref.get("type", "output")})
    req = Request(f"{base_url}/view?{q}", method="GET")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urlopen(req, timeout=timeout) as r:
            dest.write_bytes(r.read())
    except HTTPError as e:
        raise ComfyError(f"Download HTTP {e.code}: {e.read().decode(errors='replace')}") from e
    except URLError as e:
        raise ComfyError(f"Download failed: {e.reason}") from e


def _queue(base_url: str, wf: dict, client_id: str, timeout=60) -> str:
    r = _api(base_url, "/prompt", method="POST",
             payload={"prompt": wf, "client_id": client_id}, timeout=timeout)
    pid = r.get("prompt_id")
    if not pid:
        raise ComfyError(f"No prompt_id: {r}")
    return str(pid)


def _gpu() -> dict:
    smi = shutil.which("nvidia-smi")
    if not smi:
        return {"available": False}
    try:
        res = subprocess.run(
            [smi, "--query-gpu=name,memory.total,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10)
    except Exception as e:
        return {"available": False, "reason": str(e)}
    if res.returncode != 0:
        return {"available": False, "reason": res.stderr.strip()}
    gpus = []
    for line in res.stdout.splitlines():
        p = [x.strip() for x in line.split(",")]
        if len(p) >= 3:
            try:
                gpus.append({"name": p[0], "total_mb": int(p[1]), "used_mb": int(p[2])})
            except ValueError:
                pass
    return {"available": True, "gpus": gpus}


def _wait(base_url: str, prompt_id: str, timeout_s: float, poll_s: float):
    deadline = time.monotonic() + timeout_s
    peak_mb = None
    last = {}
    while time.monotonic() < deadline:
        snap = _gpu()
        if snap.get("available"):
            for g in snap.get("gpus", []):
                u = g.get("used_mb")
                if isinstance(u, int):
                    peak_mb = u if peak_mb is None else max(peak_mb, u)
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
                return imgs, entry, peak_mb
        time.sleep(poll_s)
    raise ComfyError(f"Timeout waiting for {prompt_id}; last: {list(last.keys())}")


# ---------------------------------------------------------------------------
def _sub(template: Any, reps: dict) -> Any:
    """Replace __PLACEHOLDER__ strings in a template."""
    if isinstance(template, dict):
        return {k: _sub(v, reps) for k, v in template.items()}
    if isinstance(template, list):
        return [_sub(v, reps) for v in template]
    if isinstance(template, str) and template in reps:
        return reps[template]
    return template


def _dlabel(v: float) -> str:
    return f"denoise_{v:.2f}".replace(".", "_")


# ---------------------------------------------------------------------------
def run_one_frame(base_url: str, client_id: str, raw: Path,
                  cfg_method: dict, output_dir: Path, idx: int,
                  checkpoint: str, control_model: str,
                  denoise: float, steps: int, cfg: float,
                  seed: int, template: dict) -> dict:
    """Process a single frame; return timing/vram data."""

    prefix = (f"cineanchor_cs_{cfg_method.get('label','method')}_"
              f"{_dlabel(denoise)}_f{idx:03d}_{uuid.uuid4().hex[:8]}")
    dest = output_dir / raw.name

    t0 = time.perf_counter()

    # Upload
    up = _upload(base_url, raw, name=f"cs_{uuid.uuid4().hex[:6]}_{raw.name}")
    up_name = up.get("name")
    if not up_name:
        raise ComfyError(f"Upload failed: {up}")

    # Build workflow
    wf = _sub(template, {
        "__INPUT_IMAGE__": up_name,
        "__PREPROCESSOR__": cfg_method["preprocessor"] or "",
        "__PREPROC_RESOLUTION__": cfg_method.get("resolution", 1024),
        "__OUTPUT_PREFIX__": prefix,
        "__CHECKPOINT_NAME__": checkpoint,
        "__CONTROL_NET_NAME__": control_model,
        "__CONTROL_TYPE__": cfg_method.get("control_type", "auto"),
        "__CONTROL_STRENGTH__": cfg_method.get("strength", 0.0),
        "__CONTROL_START__": 0.0,
        "__CONTROL_END__": 0.85,
        "__SEED__": seed,
        "__STEPS__": steps,
        "__CFG__": cfg,
        "__DENOISE__": denoise,
        "__POSITIVE_PROMPT__": POSITIVE,
        "__NEGATIVE_PROMPT__": NEGATIVE,
    })

    pid = _queue(base_url, wf, client_id)
    imgs, entry, peak = _wait(base_url, pid, timeout_s=1200, poll_s=1)
    _download(base_url, imgs[0], dest)
    elapsed = time.perf_counter() - t0

    return {
        "raw": str(raw), "enhanced": str(dest),
        "method": cfg_method.get("label", "?"),
        "denoise": denoise, "seed": seed,
        "prompt_id": pid, "seconds": round(elapsed, 3),
        "peak_gpu_mb": peak,
        "comfy_output": imgs[0],
    }


# ---------------------------------------------------------------------------
def run_sweep(args, checkpoint: str, control_model: str) -> int:
    """Run a full experiment sweep."""

    methods = [m.strip() for m in args.methods.split(",")]
    denoises = [float(d.strip()) for d in args.denoise.split(",")]
    exp = args.experiment

    # Select input frames
    raw_map = {
        "character": CHAR_KF_RAW,
        "product": PROD_KF_RAW,
        "continuous": CHAR_CT_RAW,
    }
    raw_dir = Path(args.input_dir) if args.input_dir else raw_map[exp]
    frames = sorted(raw_dir.glob("*.png"))
    if not frames:
        print(f"ERROR: No PNGs in {raw_dir}")
        return 1
    print(f"Input: {len(frames)} frames from {raw_dir}")

    # Load correct workflow template
    has_preproc = any(METHODS[m]["preprocessor"] is not None for m in methods)
    has_plain = "plain" in methods

    preproc_tmpl = json.loads(PREPROC_WF.read_text("utf-8")) if has_preproc else None
    plain_tmpl = json.loads(PLAIN_WF.read_text("utf-8")) if has_plain else None

    client_id = f"cineanchor-cs-{uuid.uuid4().hex}"
    report = {"experiment": exp, "methods": methods, "denoise_values": denoises,
              "checkpoint": checkpoint, "control_model": control_model,
              "settings": {"steps": args.steps, "cfg": args.cfg,
                           "seed_mode": args.seed_mode, "base_seed": args.base_seed},
              "gpu_before": _gpu(), "started_at": time.time(), "results": {}}

    for method_name in methods:
        mcfg = dict(METHODS[method_name])
        mcfg["label"] = method_name
        use_template = plain_tmpl if method_name == "plain" else preproc_tmpl

        for denoise in denoises:
            key = f"{method_name}_{_dlabel(denoise)}"
            out_dir = OUTPUT_ROOT / exp / "keyframes" / key
            out_dir.mkdir(parents=True, exist_ok=True)
            entries = []
            total_s = 0.0
            print(f"\n-- {key} -> {out_dir}")

            for i, f in enumerate(frames, start=1):
                seed = args.base_seed if args.seed_mode == "fixed" else args.base_seed + i
                fr = run_one_frame(
                    base_url=args.comfy_url.rstrip("/"), client_id=client_id,
                    raw=f, cfg_method=mcfg, output_dir=out_dir, idx=i,
                    checkpoint=checkpoint, control_model=control_model,
                    denoise=denoise, steps=args.steps, cfg=args.cfg,
                    seed=seed, template=use_template,
                )
                entries.append(fr)
                total_s += fr["seconds"]
                print(f"  [{i}/{len(frames)}] {fr['seconds']:.1f}s  "
                      f"peak_vram={fr.get('peak_gpu_mb','?')}MB")

            report["results"][key] = {"frames": entries, "total_s": total_s}

    report["gpu_after"] = _gpu()
    report["finished_at"] = time.time()

    # Save report
    rp = Path(args.report) if args.report else (
        OUTPUT_ROOT / exp / f"report_{'_'.join(methods)}_{uuid.uuid4().hex[:8]}.json")
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, indent=2, ensure_ascii=False), "utf-8")
    print(f"\nReport: {rp}")

    # Summary
    print("\n" + "=" * 60 + "\nSUMMARY\n" + "=" * 60)
    for key, val in report["results"].items():
        fs = val["frames"]
        if fs:
            avg_t = sum(x["seconds"] for x in fs) / len(fs)
            peak = max((x.get("peak_gpu_mb") or 0 for x in fs), default=0)
            print(f"  {key}: {len(fs)}f  avg={avg_t:.1f}s/f  total={val['total_s']:.0f}s  peak_vram={peak}MB")
    return 0


# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="ControlNet Structure Enhancement Spike")
    p.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    p.add_argument("--experiment", required=True,
                   choices=["character", "product", "continuous"])
    p.add_argument("--methods", required=True,
                   help="canny,depth,normal,lineart,plain")
    p.add_argument("--denoise", required=True, help="0.25,0.35,0.45")
    p.add_argument("--checkpoint", default="")
    p.add_argument("--control-model", default="")
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--cfg", type=float, default=1.6)
    p.add_argument("--seed-mode", choices=["fixed", "frame"], default="frame")
    p.add_argument("--base-seed", type=int, default=20260624)
    p.add_argument("--input-dir", default="")
    p.add_argument("--report", default="")
    p.add_argument("--timeout-seconds", type=float, default=1200)
    args = p.parse_args()

    # Validate
    for m in args.methods.split(","):
        m = m.strip()
        if m not in METHODS:
            print(f"Unknown method: {m}. Choices: {list(METHODS)}")
            return 1

    base_url = args.comfy_url.rstrip("/")

    # Verify ComfyUI
    try:
        info = _api(base_url, "/object_info", timeout=60)
        ver = _api(base_url, "/system_stats", timeout=10)
        print(f"ComfyUI {ver.get('system',{}).get('comfyui_version','?')} OK")
    except ComfyError as e:
        print(f"ComfyUI not reachable: {e}")
        return 1

    # Select checkpoint
    ckpts = []
    try:
        ckpts = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    except Exception:
        pass
    ckpt = args.checkpoint
    if not ckpt:
        for hint in ("realvisxl", "lightning", "sd_xl_base"):
            for c in ckpts:
                if hint in c.lower():
                    ckpt = c
                    break
            if ckpt:
                break
        if not ckpt and ckpts:
            ckpt = ckpts[0]
    print(f"Checkpoint: {ckpt}")

    # Select ControlNet
    cn = ""
    has_ctrl = any(METHODS[m.strip()]["control_type"] is not None
                   for m in args.methods.split(","))
    if has_ctrl:
        cns = []
        try:
            cns = info["ControlNetLoader"]["input"]["required"]["control_net_name"][0]
        except Exception:
            pass
        cn = args.control_model or (cns[0] if cns else "")
        print(f"ControlNet: {cn}")

    return run_sweep(args, ckpt, cn)


if __name__ == "__main__":
    raise SystemExit(main())
