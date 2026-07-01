from __future__ import annotations

import argparse
import importlib.util
import json
import os
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
    parser = argparse.ArgumentParser(description="Render Gate 2 no-text frames and structural maps")
    parser.add_argument("--case", choices=sorted(CASES), default="character_intro")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--skip-data-passes", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else None)


def load_route2_renderer() -> Any:
    spec = importlib.util.spec_from_file_location("cineanchor_route2_renderer_gate2", ROUTE2_RENDERER)
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


def build_project(case_name: str, frames_dir: Path, raw_video: Path) -> dict[str, Any]:
    case = CASES[case_name]
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


def frame_count(path: Path, pattern: str = "*.png") -> int:
    return len(sorted(path.glob(pattern)))


def configure_and_build(route2: Any, project: dict[str, Any], frames_dir: Path) -> dict[str, Any]:
    route2.reset_scene()
    route2.configure_render(project, frames_dir)
    return route2.build_scene(project)


def render_animation(route2: Any, project: dict[str, Any], frames_dir: Path) -> tuple[dict[str, Any], float]:
    subject = configure_and_build(route2, project, frames_dir)
    start = time.perf_counter()
    route2.bpy.ops.render.render(animation=True)
    elapsed = time.perf_counter() - start
    return subject, elapsed


def children_recursive(obj: Any) -> set[Any]:
    result = {obj}
    for child in getattr(obj, "children_recursive", []):
        result.add(child)
    return result


def make_white_alpha_material(bpy: Any, source_obj: Any) -> Any:
    source_image = None
    if getattr(source_obj, "data", None) is not None:
        for material in source_obj.data.materials:
            if material is None or not getattr(material, "use_nodes", False):
                continue
            for node in material.node_tree.nodes:
                if getattr(node, "bl_idname", "") == "ShaderNodeTexImage" and getattr(node, "image", None) is not None:
                    source_image = node.image
                    break
            if source_image is not None:
                break

    material = bpy.data.materials.new("Gate2SubjectMaskMaterial")
    material.use_nodes = True
    material.blend_method = "BLEND"
    material.show_transparent_back = True
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
        bsdf.inputs["Alpha"].default_value = 1
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (1, 1, 1, 1)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 1
    if source_image is not None and bsdf is not None:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = source_image
        tex.extension = "CLIP"
        material.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    return material


def apply_subject_mask_scene(route2: Any, subject: dict[str, Any]) -> None:
    bpy = route2.bpy
    scene = bpy.context.scene
    subject_root = subject["object"]
    subject_objects = children_recursive(subject_root)
    mask_material = make_white_alpha_material(bpy, subject_root)

    for obj in bpy.data.objects:
        if obj not in subject_objects:
            obj.hide_render = True
            continue
        if obj.type == "MESH":
            obj.hide_render = False
            obj.data.materials.clear()
            obj.data.materials.append(mask_material)

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.color = (0, 0, 0)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGB"


def render_subject_mask(route2: Any, project: dict[str, Any], frames_dir: Path) -> tuple[dict[str, Any], float]:
    subject = configure_and_build(route2, project, frames_dir)
    apply_subject_mask_scene(route2, subject)
    start = time.perf_counter()
    route2.bpy.ops.render.render(animation=True)
    elapsed = time.perf_counter() - start
    return subject, elapsed


def get_socket(node: Any, names: tuple[str, ...]) -> Any | None:
    for name in names:
        if name in node.outputs:
            return node.outputs[name]
    return None


def render_data_passes(route2: Any, project: dict[str, Any], case_root: Path, output_root: Path) -> dict[str, Any]:
    bpy = route2.bpy
    exr_dir = case_root / "data_pass_exr"
    clear_dir(exr_dir, output_root)

    subject = configure_and_build(route2, project, exr_dir)
    scene = bpy.context.scene
    view_layer = scene.view_layers[0]
    available: dict[str, Any] = {
        "z_requested": hasattr(view_layer, "use_pass_z"),
        "normal_requested": hasattr(view_layer, "use_pass_normal"),
        "exr_dir": str(exr_dir),
        "format": "OPEN_EXR_MULTILAYER",
    }
    if hasattr(view_layer, "use_pass_z"):
        view_layer.use_pass_z = True
    if hasattr(view_layer, "use_pass_normal"):
        view_layer.use_pass_normal = True
    if hasattr(view_layer, "update_render_passes"):
        view_layer.update_render_passes()

    scene.render.filepath = str(exr_dir) + os.sep
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_mode = "RGBA"
    start = time.perf_counter()
    bpy.ops.render.render(animation=True)
    elapsed = time.perf_counter() - start

    available.update(
        {
            "subject_asset_path": subject.get("asset_path"),
            "alpha_bbox": subject.get("alpha_bbox"),
            "render_seconds": round(elapsed, 3),
            "exr_frame_count": frame_count(exr_dir, "*.exr"),
            "contains_depth_z_pass": bool(getattr(view_layer, "use_pass_z", False)),
            "contains_normal_pass": bool(getattr(view_layer, "use_pass_normal", False)),
        }
    )
    return available


def render_case(case_name: str, output_root: Path, *, skip_data_passes: bool) -> dict[str, Any]:
    route2 = load_route2_renderer()
    case_root = output_root / case_name
    rgb_dir = case_root / "rgb"
    mask_dir = case_root / "mask"
    raw_video = case_root / "raw_no_text.mp4"
    clear_dir(rgb_dir, output_root)
    clear_dir(mask_dir, output_root)

    project = build_project(case_name, rgb_dir, raw_video)

    subject, rgb_seconds = render_animation(route2, project, rgb_dir)
    _, mask_seconds = render_subject_mask(route2, build_project(case_name, mask_dir, raw_video), mask_dir)

    data_passes: dict[str, Any]
    if skip_data_passes:
        data_passes = {"skipped": True}
    else:
        try:
            data_passes = render_data_passes(route2, build_project(case_name, rgb_dir, raw_video), case_root, output_root)
        except Exception as exc:
            data_passes = {"skipped": False, "error": str(exc)}

    expected_frames = int(round(float(project["duration"]) * int(project["fps"])))
    manifest = {
        "case": case_name,
        "template": project["template"],
        "asset_type": project["asset"]["type"],
        "asset_path": subject.get("asset_path"),
        "camera_motion": project["camera"]["motion"],
        "text_baked_in_blender": False,
        "width": project["output"]["width"],
        "height": project["output"]["height"],
        "duration_seconds": project["duration"],
        "fps": project["fps"],
        "expected_frames": expected_frames,
        "rgb_frames_dir": str(rgb_dir),
        "mask_frames_dir": str(mask_dir),
        "raw_video_path": str(raw_video),
        "rgb_frame_count": frame_count(rgb_dir),
        "mask_frame_count": frame_count(mask_dir),
        "rgb_render_seconds": round(rgb_seconds, 3),
        "mask_render_seconds": round(mask_seconds, 3),
        "render_engine": route2.bpy.context.scene.render.engine,
        "alpha_bbox": subject.get("alpha_bbox"),
        "structural_maps": {
            "rgb_raw": "available",
            "subject_mask": "available",
            "depth_or_z_pass": "available" if data_passes.get("contains_depth_z_pass") and data_passes.get("exr_frame_count", 0) else "not_available",
            "normal_pass": "available" if data_passes.get("contains_normal_pass") and data_passes.get("exr_frame_count", 0) else "not_available",
        },
        "data_passes": data_passes,
    }
    write_json(case_root / "structural_manifest.json", manifest)

    print(f"AI_GATE2_RENDER_CASE={case_name}")
    print(f"AI_GATE2_RGB_FRAMES={rgb_dir}")
    print(f"AI_GATE2_MASK_FRAMES={mask_dir}")
    print(f"AI_GATE2_RGB_SECONDS={rgb_seconds:.3f}")
    print(f"AI_GATE2_MASK_SECONDS={mask_seconds:.3f}")
    print(f"AI_GATE2_RGB_FRAME_COUNT={manifest['rgb_frame_count']}")
    print(f"AI_GATE2_MASK_FRAME_COUNT={manifest['mask_frame_count']}")
    print(f"AI_GATE2_STRUCTURAL_MANIFEST={case_root / 'structural_manifest.json'}")
    return manifest


def main() -> None:
    args = parse_args()
    output_root = resolve_output_root(args.output_root)
    render_case(args.case, output_root, skip_data_passes=args.skip_data_passes)


if __name__ == "__main__":
    main()
