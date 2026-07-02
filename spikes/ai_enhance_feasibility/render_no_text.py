from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
ROUTE2_RENDERER = REPO_ROOT / "spikes" / "render_json" / "render_project.py"
DEFAULT_OUTPUT_ROOT = SCRIPT_DIR / "output"

CASES: dict[str, dict[str, Any]] = {
    "character_intro": {
        "template": "character_intro",
        "asset": {"type": "image", "path": "input/hero.png"},
        "camera": {"motion": "dolly_in"},
        "duration": 4,
        "fps": 24,
        "width": 720,
        "height": 1280,
        "samples": 48,
    },
    "product_orbit": {
        "template": "product_orbit",
        "asset": {"type": "glb", "path": "input/model.glb"},
        "camera": {"motion": "orbit"},
        "duration": 4,
        "fps": 12,
        "width": 1280,
        "height": 720,
        "samples": 48,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render no-text feasibility frames with the Route 2 spike renderer")
    parser.add_argument("--case", choices=sorted(CASES), default="character_intro")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else None)


def load_route2_renderer() -> Any:
    spec = importlib.util.spec_from_file_location("cineanchor_route2_renderer", ROUTE2_RENDERER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load renderer module from {ROUTE2_RENDERER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def resolve_output_root(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = SCRIPT_DIR / path
    resolved = path.resolve()
    allowed = DEFAULT_OUTPUT_ROOT.resolve()
    if allowed not in (resolved, *resolved.parents):
        raise ValueError(f"Output root must stay under {allowed}: {resolved}")
    return resolved


def clear_dir(path: Path, output_root: Path) -> None:
    resolved = path.resolve()
    root = output_root.resolve()
    if root not in (resolved, *resolved.parents):
        raise ValueError(f"Refusing to clear path outside output root: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def build_project(case_name: str, case_root: Path) -> dict[str, Any]:
    case = CASES[case_name]
    frames_dir = case_root / "frames"
    raw_video = case_root / "raw_no_text.mp4"
    return {
        "template": case["template"],
        "asset": case["asset"],
        "camera": case["camera"],
        "duration": case["duration"],
        "fps": case["fps"],
        "samples": case["samples"],
        "output": {
            "width": case["width"],
            "height": case["height"],
            "frames_dir": str(frames_dir),
            "video_path": str(raw_video),
        },
        "text": {
            "title": "",
            "subtitle": "",
        },
    }


def render_case(case_name: str, output_root: Path) -> dict[str, Any]:
    route2 = load_route2_renderer()
    case_root = output_root / case_name
    frames_dir = case_root / "frames"
    clear_dir(frames_dir, output_root)

    project = build_project(case_name, case_root)
    route2.reset_scene()
    route2.configure_render(project, frames_dir)
    subject = route2.build_scene(project)

    start = time.perf_counter()
    route2.bpy.ops.render.render(animation=True)
    elapsed = time.perf_counter() - start

    expected_frames = int(round(float(project["duration"]) * int(project["fps"])))
    frame_count = len(sorted(frames_dir.glob("*.png")))
    manifest = {
        "case": case_name,
        "template": project["template"],
        "asset_type": project["asset"]["type"],
        "asset_path": subject.get("asset_path"),
        "camera_motion": project["camera"]["motion"],
        "text_baked_in_blender": False,
        "title": "",
        "subtitle": "",
        "width": project["output"]["width"],
        "height": project["output"]["height"],
        "duration_seconds": project["duration"],
        "fps": project["fps"],
        "expected_frames": expected_frames,
        "actual_frames": frame_count,
        "frames_dir": str(frames_dir),
        "raw_video_path": project["output"]["video_path"],
        "render_seconds": round(elapsed, 3),
        "render_engine": route2.bpy.context.scene.render.engine,
        "alpha_bbox": subject.get("alpha_bbox"),
    }
    write_json(case_root / "render_manifest.json", manifest)

    print(f"AI_GATE_RENDER_CASE={case_name}")
    print(f"AI_GATE_RENDER_FRAMES={frames_dir}")
    print(f"AI_GATE_RENDER_SECONDS={elapsed:.3f}")
    print(f"AI_GATE_RENDER_FRAME_COUNT={frame_count}")
    print(f"AI_GATE_RENDER_MANIFEST={case_root / 'render_manifest.json'}")
    return manifest


def main() -> None:
    args = parse_args()
    output_root = resolve_output_root(args.output_root)
    render_case(args.case, output_root)


if __name__ == "__main__":
    main()
