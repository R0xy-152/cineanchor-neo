from __future__ import annotations

import argparse
import json
import os
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
WORKFLOW_ROOT = SCRIPT_DIR / "workflows"
PLAIN_WORKFLOW = WORKFLOW_ROOT / "sdxl_img2img_api.json"
CONTROL_WORKFLOW = WORKFLOW_ROOT / "sdxl_controlnet_img2img_api.json"

DEFAULT_POSITIVE = (
    "polished mobile game promotional keyframe, cinematic lighting, richer color, "
    "clean highlights, premium game ad still, crisp but stable edges, preserve "
    "exact subject silhouette, preserve exact pose, preserve exact composition, no text"
)
DEFAULT_NEGATIVE = (
    "text, watermark, logo, deformed subject, changed face, changed costume, "
    "changed product geometry, extra limbs, extra objects, melted edges, blur, "
    "flicker, oversaturated, noisy artifacts, layout change"
)
PREFERRED_CHECKPOINT_HINTS = ("realvisxl", "lightning", "sd_xl_base", "sdxl")
CONTROL_MODEL_HINTS = {
    "canny": ("canny",),
    "depth": ("depth", "zoe", "midas"),
    "normal": ("normal", "bae"),
    "lineart": ("lineart", "line"),
}
CONTROL_TYPES = {
    "canny": "canny/lineart/anime_lineart/mlsd",
    "depth": "depth",
    "normal": "normal",
    "lineart": "canny/lineart/anime_lineart/mlsd",
}


class ComfyError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    default_comfy_url = os.environ.get("COMFYUI_API_URL") or os.environ.get("COMFYUI_URL") or "http://127.0.0.1:8188"
    parser = argparse.ArgumentParser(description="Gate 2 ComfyUI plain/control denoise sweep")
    parser.add_argument("--comfy-url", default=default_comfy_url)
    parser.add_argument("--mode", choices=("plain", "control"), required=True)
    parser.add_argument("--workflow", default="")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--control-dir", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--control-method", choices=sorted(CONTROL_MODEL_HINTS), default="canny")
    parser.add_argument("--control-model", default="")
    parser.add_argument("--control-strength", type=float, default=0.75)
    parser.add_argument("--control-start", type=float, default=0.0)
    parser.add_argument("--control-end", type=float, default=0.85)
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--cfg", type=float, default=1.6)
    parser.add_argument("--denoise", action="append", type=float, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=1200)
    parser.add_argument("--poll-seconds", type=float, default=1)
    parser.add_argument("--seed-mode", choices=("fixed", "frame"), default="frame")
    parser.add_argument("--base-seed", type=int, default=20260624)
    parser.add_argument("--positive", default=DEFAULT_POSITIVE)
    parser.add_argument("--negative", default=DEFAULT_NEGATIVE)
    parser.add_argument("--allow-skip", action="store_true")
    return parser.parse_args()


def normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def resolve_output_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = SCRIPT_DIR / path
    resolved = path.resolve()
    root = OUTPUT_ROOT.resolve()
    if root not in (resolved, *resolved.parents):
        raise ValueError(f"Path must stay under {root}: {resolved}")
    return resolved


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(5):
        try:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=True)
                handle.write("\n")
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.25)


def api_json(base_url: str, path: str, *, method: str = "GET", payload: Any | None = None, timeout: float = 30) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(f"{base_url}{path}", data=data, method=method, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ComfyError(f"ComfyUI HTTP {exc.code} for {path}: {body}") from exc
    except URLError as exc:
        raise ComfyError(f"ComfyUI is not reachable at {base_url}: {exc.reason}") from exc


def upload_image(base_url: str, image_path: Path, *, upload_name: str | None = None, timeout: float = 60) -> dict[str, Any]:
    boundary = f"----cineanchor-{uuid.uuid4().hex}"
    image_bytes = image_path.read_bytes()
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        parts.append(value.encode("utf-8") + b"\r\n")

    def add_file(name: str, filename: str, content: bytes) -> None:
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"))
        parts.append(b"Content-Type: image/png\r\n\r\n")
        parts.append(content + b"\r\n")

    add_file("image", upload_name or image_path.name, image_bytes)
    add_field("type", "input")
    add_field("overwrite", "true")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)

    request = Request(
        f"{base_url}/upload/image",
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ComfyError(f"ComfyUI upload failed HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise ComfyError(f"ComfyUI upload failed: {exc.reason}") from exc


def download_image(base_url: str, image_ref: dict[str, Any], output_path: Path, *, timeout: float = 120) -> None:
    query = urlencode(
        {
            "filename": image_ref["filename"],
            "subfolder": image_ref.get("subfolder", ""),
            "type": image_ref.get("type", "output"),
        }
    )
    request = Request(f"{base_url}/view?{query}", method="GET")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urlopen(request, timeout=timeout) as response:
            output_path.write_bytes(response.read())
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ComfyError(f"ComfyUI image download failed HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise ComfyError(f"ComfyUI image download failed: {exc.reason}") from exc


def parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def gpu_snapshot() -> dict[str, Any]:
    smi = shutil.which("nvidia-smi")
    if smi is None:
        return {"available": False, "reason": "nvidia-smi not found"}
    command = [
        smi,
        "--query-gpu=name,memory.total,memory.used",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
    if result.returncode != 0:
        return {"available": False, "reason": result.stderr.strip()}
    rows = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) >= 3:
            rows.append(
                {
                    "name": parts[0],
                    "memory_total_mb": parse_int(parts[1]),
                    "memory_used_mb": parse_int(parts[2]),
                }
            )
    return {"available": True, "gpus": rows, "raw": result.stdout.strip()}


def max_gpu_used(current: int | None, snapshot: dict[str, Any]) -> int | None:
    if not snapshot.get("available"):
        return current
    values = [gpu.get("memory_used_mb") for gpu in snapshot.get("gpus", [])]
    values = [value for value in values if isinstance(value, int)]
    if not values:
        return current
    value = max(values)
    return value if current is None else max(current, value)


def workflow_class_types(workflow: dict[str, Any]) -> set[str]:
    classes: set[str] = set()
    for node in workflow.values():
        if isinstance(node, dict) and "class_type" in node:
            classes.add(str(node["class_type"]))
    return classes


def node_choices(object_info: dict[str, Any], node: str, field: str) -> list[str]:
    try:
        choices = object_info[node]["input"]["required"][field][0]
    except (KeyError, IndexError, TypeError):
        return []
    return [str(choice) for choice in choices]


def choose_checkpoint(choices: list[str], requested: str) -> str:
    if requested:
        if requested not in choices:
            raise ComfyError(f"Requested checkpoint is not exposed by ComfyUI: {requested}")
        return requested
    for hint in PREFERRED_CHECKPOINT_HINTS:
        for choice in choices:
            if hint in choice.lower():
                return choice
    if choices:
        return choices[0]
    raise ComfyError("No checkpoint choices exposed by ComfyUI")


def choose_control_model(choices: list[str], method: str, requested: str) -> str:
    if requested:
        if requested not in choices:
            raise ComfyError(f"Requested ControlNet model is not exposed by ComfyUI: {requested}")
        return requested
    hints = CONTROL_MODEL_HINTS[method]
    for hint in hints:
        for choice in choices:
            if hint in choice.lower():
                return choice
    if len(choices) == 1:
        return choices[0]
    raise ComfyError(f"No ControlNet model matching method '{method}' is exposed by ComfyUI")


def replace_placeholders(value: Any, replacements: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: replace_placeholders(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_placeholders(item, replacements) for item in value]
    if isinstance(value, str) and value in replacements:
        return replacements[value]
    return value


def prepare_workflow(
    workflow_template: dict[str, Any],
    *,
    uploaded_name: str,
    control_name: str | None,
    output_prefix: str,
    checkpoint: str,
    control_model: str | None,
    control_type: str,
    control_strength: float,
    control_start: float,
    control_end: float,
    seed: int,
    steps: int,
    cfg: float,
    denoise: float,
    positive: str,
    negative: str,
) -> dict[str, Any]:
    return replace_placeholders(
        workflow_template,
        {
            "__INPUT_IMAGE__": uploaded_name,
            "__CONTROL_IMAGE__": control_name or "",
            "__OUTPUT_PREFIX__": output_prefix,
            "__CHECKPOINT_NAME__": checkpoint,
            "__CONTROL_NET_NAME__": control_model or "",
            "__CONTROL_TYPE__": control_type,
            "__CONTROL_STRENGTH__": control_strength,
            "__CONTROL_START__": control_start,
            "__CONTROL_END__": control_end,
            "__SEED__": seed,
            "__STEPS__": steps,
            "__CFG__": cfg,
            "__DENOISE__": denoise,
            "__POSITIVE_PROMPT__": positive,
            "__NEGATIVE_PROMPT__": negative,
        },
    )


def queue_prompt(base_url: str, workflow: dict[str, Any], client_id: str) -> str:
    response = api_json(base_url, "/prompt", method="POST", payload={"prompt": workflow, "client_id": client_id}, timeout=60)
    prompt_id = response.get("prompt_id")
    if not prompt_id:
        raise ComfyError(f"ComfyUI prompt response did not include prompt_id: {response}")
    return str(prompt_id)


def wait_for_images(
    base_url: str,
    prompt_id: str,
    *,
    timeout_seconds: float,
    poll_seconds: float,
) -> tuple[list[dict[str, Any]], dict[str, Any], int | None]:
    deadline = time.monotonic() + timeout_seconds
    peak_gpu_mb: int | None = None
    last_history: dict[str, Any] = {}
    while time.monotonic() < deadline:
        snapshot = gpu_snapshot()
        peak_gpu_mb = max_gpu_used(peak_gpu_mb, snapshot)
        history = api_json(base_url, f"/history/{prompt_id}", timeout=30)
        last_history = history
        entry = history.get(prompt_id)
        if entry:
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                raise ComfyError(f"ComfyUI prompt failed: {status}")
            images: list[dict[str, Any]] = []
            for output in entry.get("outputs", {}).values():
                images.extend(output.get("images", []))
            if images:
                return images, entry, peak_gpu_mb
        time.sleep(poll_seconds)
    raise ComfyError(f"Timed out waiting for ComfyUI prompt {prompt_id}; last history: {last_history}")


def validate_workflow_nodes(workflow_template: dict[str, Any], object_info: dict[str, Any]) -> list[str]:
    return sorted(workflow_class_types(workflow_template) - set(object_info.keys()))


def denoise_label(value: float) -> str:
    return f"denoise_{value:.2f}".replace(".", "_")


def frame_seed(seed_mode: str, base_seed: int, frame_index: int) -> int:
    if seed_mode == "fixed":
        return base_seed
    return base_seed + frame_index


def workflow_path_for(args: argparse.Namespace) -> Path:
    if args.workflow:
        path = Path(args.workflow)
    elif args.mode == "plain":
        path = PLAIN_WORKFLOW
    else:
        path = CONTROL_WORKFLOW
    if not path.is_absolute():
        path = SCRIPT_DIR / path
    return path.resolve()


def skip_or_raise(report_path: Path, report: dict[str, Any], args: argparse.Namespace, exc: Exception) -> int:
    report["status"] = "SKIPPED" if args.allow_skip else "FAILED"
    report["error"] = str(exc)
    report["gpu_after"] = gpu_snapshot()
    report["finished_at_epoch"] = time.time()
    write_json(report_path, report)
    print(f"AI_GATE2_COMFY_{report['status']}={exc}", file=sys.stderr)
    print(f"AI_GATE2_COMFY_REPORT={report_path}", file=sys.stderr)
    return 0 if args.allow_skip else 1


def run() -> int:
    args = parse_args()
    base_url = normalize_base_url(args.comfy_url)
    workflow_path = workflow_path_for(args)
    input_dir = resolve_output_path(args.input_dir)
    control_dir = resolve_output_path(args.control_dir) if args.control_dir else None
    output_root = resolve_output_path(args.output_dir)
    report_path = resolve_output_path(args.report)

    report: dict[str, Any] = {
        "status": "FAILED",
        "case": args.case,
        "experiment": args.experiment,
        "mode": args.mode,
        "control_method": args.control_method if args.mode == "control" else None,
        "comfy_url": base_url,
        "workflow_path": str(workflow_path),
        "input_dir": str(input_dir),
        "control_dir": str(control_dir) if control_dir else None,
        "output_dir": str(output_root),
        "started_at_epoch": time.time(),
        "settings": {
            "steps": args.steps,
            "cfg": args.cfg,
            "denoise_values": args.denoise,
            "checkpoint_requested": args.checkpoint or None,
            "control_model_requested": args.control_model or None,
            "control_strength": args.control_strength,
            "control_start": args.control_start,
            "control_end": args.control_end,
            "seed_mode": args.seed_mode,
            "base_seed": args.base_seed,
            "positive": args.positive,
            "negative": args.negative,
        },
        "gpu_before": gpu_snapshot(),
        "frames": [],
    }

    try:
        workflow_template = read_json(workflow_path)
        system_stats = api_json(base_url, "/system_stats", timeout=10)
        object_info = api_json(base_url, "/object_info", timeout=60)
        missing = validate_workflow_nodes(workflow_template, object_info)
        if missing:
            raise ComfyError(f"ComfyUI is missing workflow node classes: {', '.join(missing)}")

        checkpoint_choices = node_choices(object_info, "CheckpointLoaderSimple", "ckpt_name")
        checkpoint = choose_checkpoint(checkpoint_choices, args.checkpoint)
        control_model = None
        control_choices: list[str] = []
        if args.mode == "control":
            if control_dir is None:
                raise ComfyError("--control-dir is required for control mode")
            control_choices = node_choices(object_info, "ControlNetLoader", "control_net_name")
            control_model = choose_control_model(control_choices, args.control_method, args.control_model)

        report["comfy_reachable"] = True
        report["system_stats"] = system_stats
        report["checkpoint_name"] = checkpoint
        report["checkpoint_choices_sample"] = checkpoint_choices[:8]
        report["control_model_name"] = control_model
        report["control_choices_sample"] = control_choices[:12]

        raw_frames = sorted(input_dir.glob("*.png"))
        if not raw_frames:
            raise ComfyError(f"No PNG frames found under {input_dir}")
        client_id = f"cineanchor-ai-gate2-{uuid.uuid4().hex}"

        for denoise in args.denoise:
            denoise_dir = output_root / denoise_label(denoise)
            denoise_dir.mkdir(parents=True, exist_ok=True)
            for index, raw_frame in enumerate(raw_frames, start=1):
                enhanced_path = denoise_dir / raw_frame.name
                control_frame = control_dir / raw_frame.name if control_dir else None
                if args.mode == "control" and (control_frame is None or not control_frame.exists()):
                    raise FileNotFoundError(control_frame)
                seed = frame_seed(args.seed_mode, args.base_seed, index)
                output_prefix = (
                    f"cineanchor_ai_gate2_{args.case}_{args.experiment}_{args.mode}_"
                    f"{args.control_method}_{denoise_label(denoise)}_{raw_frame.stem}_{uuid.uuid4().hex[:8]}"
                )
                frame_report: dict[str, Any] = {
                    "case": args.case,
                    "experiment": args.experiment,
                    "mode": args.mode,
                    "control_method": args.control_method if args.mode == "control" else None,
                    "denoise": denoise,
                    "raw_frame": str(raw_frame),
                    "control_frame": str(control_frame) if control_frame else None,
                    "enhanced_frame": str(enhanced_path),
                    "seed": seed,
                    "gpu_before": gpu_snapshot(),
                }

                start = time.perf_counter()
                uploaded = upload_image(base_url, raw_frame, upload_name=f"gate2_raw_{uuid.uuid4().hex}_{raw_frame.name}")
                uploaded_name = uploaded.get("name")
                if not uploaded_name:
                    raise ComfyError(f"Upload response did not include name: {uploaded}")
                control_name = None
                if control_frame is not None:
                    uploaded_control = upload_image(base_url, control_frame, upload_name=f"gate2_control_{uuid.uuid4().hex}_{control_frame.name}")
                    control_name = uploaded_control.get("name")
                    if not control_name:
                        raise ComfyError(f"Control upload response did not include name: {uploaded_control}")

                workflow = prepare_workflow(
                    workflow_template,
                    uploaded_name=str(uploaded_name),
                    control_name=str(control_name) if control_name else None,
                    output_prefix=output_prefix,
                    checkpoint=checkpoint,
                    control_model=control_model,
                    control_type=CONTROL_TYPES.get(args.control_method, "auto"),
                    control_strength=args.control_strength,
                    control_start=args.control_start,
                    control_end=args.control_end,
                    seed=seed,
                    steps=args.steps,
                    cfg=args.cfg,
                    denoise=denoise,
                    positive=args.positive,
                    negative=args.negative,
                )
                prompt_id = queue_prompt(base_url, workflow, client_id)
                images, history_entry, peak_gpu_mb = wait_for_images(
                    base_url,
                    prompt_id,
                    timeout_seconds=args.timeout_seconds,
                    poll_seconds=args.poll_seconds,
                )
                download_image(base_url, images[0], enhanced_path)
                elapsed = time.perf_counter() - start
                frame_report.update(
                    {
                        "uploaded_name": uploaded_name,
                        "uploaded_control_name": control_name,
                        "prompt_id": prompt_id,
                        "seconds": round(elapsed, 3),
                        "gpu_peak_used_mb": peak_gpu_mb,
                        "gpu_after": gpu_snapshot(),
                        "comfy_output": images[0],
                        "status": history_entry.get("status", {}),
                    }
                )
                report["frames"].append(frame_report)
                write_json(report_path, report)
                print(f"AI_GATE2_COMFY_FRAME={enhanced_path}")
                print(f"AI_GATE2_COMFY_MODE={args.mode}")
                print(f"AI_GATE2_COMFY_DENOISE={denoise:.2f}")
                print(f"AI_GATE2_COMFY_SECONDS={elapsed:.3f}")

        report["status"] = "COMPLETED"
        report["gpu_after"] = gpu_snapshot()
        report["finished_at_epoch"] = time.time()
        write_json(report_path, report)
        print(f"AI_GATE2_COMFY_REPORT={report_path}")
        return 0
    except Exception as exc:
        return skip_or_raise(report_path, report, args, exc)


if __name__ == "__main__":
    raise SystemExit(run())
