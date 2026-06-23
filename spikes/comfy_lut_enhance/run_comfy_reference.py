from __future__ import annotations

import argparse
import json
import os
import random
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
DEFAULT_WORKFLOW = SCRIPT_DIR / "workflows" / "conservative_sdxl_reference_api.json"
DEFAULT_POSITIVE = (
    "conservative cinematic game promo color grade reference, preserve exact subject, "
    "preserve exact text layout, subtle contrast, clean highlights, richer color, "
    "crisp but not redesigned"
)
DEFAULT_NEGATIVE = (
    "deformed subject, changed character, changed product geometry, changed logo, "
    "corrupted text, extra text, layout changes, heavy redraw, artifacts, oversaturated"
)
PREFERRED_CHECKPOINT_HINTS = ("realvisxl", "lightning", "sd_xl_base", "sdxl")


class ComfyError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    default_comfy_url = (
        os.environ.get("COMFYUI_API_URL")
        or os.environ.get("COMFYUI_URL")
        or "http://127.0.0.1:8188"
    )
    parser = argparse.ArgumentParser(description="Route 3B ComfyUI color reference spike")
    parser.add_argument("--comfy-url", default=default_comfy_url)
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW))
    parser.add_argument("--output-root", default=str(OUTPUT_ROOT))
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--cfg", type=float, default=1.4)
    parser.add_argument("--denoise", type=float, default=0.08)
    parser.add_argument("--timeout-seconds", type=float, default=900)
    parser.add_argument("--poll-seconds", type=float, default=1)
    parser.add_argument("--positive", default=DEFAULT_POSITIVE)
    parser.add_argument("--negative", default=DEFAULT_NEGATIVE)
    return parser.parse_args()


def normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


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


def upload_image(base_url: str, image_path: Path, *, timeout: float = 60) -> dict[str, Any]:
    boundary = f"----cineanchor-{uuid.uuid4().hex}"
    image_bytes = image_path.read_bytes()
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        parts.append(value.encode("utf-8") + b"\r\n")

    def add_file(name: str, filename: str, content: bytes) -> None:
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        disposition = f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
        parts.append(disposition.encode("utf-8"))
        parts.append(b"Content-Type: image/png\r\n\r\n")
        parts.append(content + b"\r\n")

    add_file("image", image_path.name, image_bytes)
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
    except Exception as exc:  # pragma: no cover - environment dependent
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
    used_values = [gpu.get("memory_used_mb") for gpu in snapshot.get("gpus", [])]
    used_values = [value for value in used_values if isinstance(value, int)]
    if not used_values:
        return current
    peak = max(used_values)
    return peak if current is None else max(current, peak)


def workflow_class_types(workflow: dict[str, Any]) -> set[str]:
    classes: set[str] = set()
    for node in workflow.values():
        if isinstance(node, dict) and "class_type" in node:
            classes.add(str(node["class_type"]))
    return classes


def checkpoint_choices(object_info: dict[str, Any]) -> list[str]:
    try:
        choices = object_info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
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
    output_prefix: str,
    checkpoint: str,
    seed: int,
    steps: int,
    cfg: float,
    denoise: float,
    positive: str,
    negative: str,
) -> dict[str, Any]:
    replacements = {
        "__INPUT_IMAGE__": uploaded_name,
        "__OUTPUT_PREFIX__": output_prefix,
        "__CHECKPOINT_NAME__": checkpoint,
        "__SEED__": seed,
        "__STEPS__": steps,
        "__CFG__": cfg,
        "__DENOISE__": denoise,
        "__POSITIVE_PROMPT__": positive,
        "__NEGATIVE_PROMPT__": negative,
    }
    return replace_placeholders(workflow_template, replacements)


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


def validate_workflow_nodes(workflow_template: dict[str, Any], object_info: dict[str, Any]) -> None:
    missing = sorted(workflow_class_types(workflow_template) - set(object_info.keys()))
    if missing:
        raise ComfyError(f"ComfyUI is missing workflow node classes: {', '.join(missing)}")


def find_raw_frames(output_root: Path) -> list[tuple[str, Path]]:
    frames: list[tuple[str, Path]] = []
    for case in ("character_intro", "product_orbit"):
        raw_dir = output_root / case / "keyframes_raw"
        case_frames = sorted(raw_dir.glob("*.png"))
        if len(case_frames) != 4:
            raise ComfyError(f"Expected exactly 4 raw keyframes for {case}, found {len(case_frames)}")
        for frame_path in case_frames:
            frames.append((case, frame_path))
    return frames


def run() -> int:
    args = parse_args()
    base_url = normalize_base_url(args.comfy_url)
    workflow_path = Path(args.workflow)
    if not workflow_path.is_absolute():
        workflow_path = SCRIPT_DIR / workflow_path
    workflow_path = workflow_path.resolve()
    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = SCRIPT_DIR / output_root
    output_root = output_root.resolve()
    report_path = output_root / "comfy_reference_report.json"

    report: dict[str, Any] = {
        "status": "FAILED",
        "comfy_url": base_url,
        "workflow_path": str(workflow_path),
        "started_at_epoch": time.time(),
        "settings": {
            "steps": args.steps,
            "cfg": args.cfg,
            "denoise": args.denoise,
            "checkpoint_requested": args.checkpoint or None,
            "purpose": "color/style reference only; final video frames are not replaced",
        },
        "gpu_before": gpu_snapshot(),
        "frames": [],
    }

    try:
        workflow_template = read_json(workflow_path)
        system_stats = api_json(base_url, "/system_stats", timeout=10)
        object_info = api_json(base_url, "/object_info", timeout=30)
        validate_workflow_nodes(workflow_template, object_info)

        choices = checkpoint_choices(object_info)
        checkpoint = choose_checkpoint(choices, args.checkpoint)
        report["comfy_reachable"] = True
        report["system_stats"] = system_stats
        report["checkpoint_name"] = checkpoint
        report["checkpoint_choices_sample"] = choices[:8]

        raw_frames = find_raw_frames(output_root)
        client_id = f"cineanchor-route3b-{uuid.uuid4().hex}"
        random.seed(3074)
        for index, (case, raw_frame) in enumerate(raw_frames, start=1):
            reference_dir = output_root / case / "keyframes_reference"
            reference_path = reference_dir / raw_frame.name
            output_prefix = f"cineanchor_route3b_{case}_{raw_frame.stem}_{uuid.uuid4().hex[:8]}"
            seed = random.randrange(1, 2**31)

            frame_report: dict[str, Any] = {
                "case": case,
                "raw_frame": str(raw_frame),
                "reference_frame": str(reference_path),
                "seed": seed,
                "gpu_before": gpu_snapshot(),
            }
            start = time.perf_counter()
            uploaded = upload_image(base_url, raw_frame)
            uploaded_name = uploaded.get("name")
            if not uploaded_name:
                raise ComfyError(f"Upload response did not include name: {uploaded}")

            workflow = prepare_workflow(
                workflow_template,
                uploaded_name=str(uploaded_name),
                output_prefix=output_prefix,
                checkpoint=checkpoint,
                seed=seed,
                steps=args.steps,
                cfg=args.cfg,
                denoise=args.denoise,
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
            download_image(base_url, images[0], reference_path)
            elapsed = time.perf_counter() - start

            frame_report.update(
                {
                    "uploaded_name": uploaded_name,
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
            print(f"ROUTE3B_COMFY_REFERENCE={reference_path}")
            print(f"ROUTE3B_COMFY_SECONDS={elapsed:.3f}")

        report["status"] = "PASS"
        report["gpu_after"] = gpu_snapshot()
        report["finished_at_epoch"] = time.time()
        write_json(report_path, report)
        print(f"ROUTE3B_COMFY_REPORT={report_path}")
        return 0
    except Exception as exc:
        report["error"] = str(exc)
        report["comfy_reachable"] = False
        report["gpu_after"] = gpu_snapshot()
        report["finished_at_epoch"] = time.time()
        write_json(report_path, report)
        print(f"ROUTE3B_COMFY_ERROR={exc}", file=sys.stderr)
        print(f"ROUTE3B_COMFY_REPORT={report_path}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
