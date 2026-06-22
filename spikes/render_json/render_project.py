from __future__ import annotations

import argparse
import json
import math
import os
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Route 2 JSON-driven render spike")
    parser.add_argument("--project", default="projects/character_intro.json")
    return parser.parse_args(argv)


def load_project(path_text: str) -> dict[str, Any]:
    project_path = resolve_under_spike(path_text, must_exist=True)
    with project_path.open("r", encoding="utf-8") as handle:
        project = json.load(handle)
    project["_project_path"] = str(project_path)
    validate_project(project)
    return project


def validate_project(project: dict[str, Any]) -> None:
    template = project.get("template")
    asset = project.get("asset", {})
    camera = project.get("camera", {})
    output = project.get("output", {})

    if template not in {"character_intro", "product_orbit"}:
        raise ValueError(f"Unsupported template: {template}")
    if asset.get("type") not in {"image", "glb"}:
        raise ValueError(f"Unsupported asset.type: {asset.get('type')}")
    if not asset.get("path"):
        raise ValueError("asset.path is required")
    if camera.get("motion") not in {"dolly_in", "orbit"}:
        raise ValueError(f"Unsupported camera.motion: {camera.get('motion')}")

    for key in ("width", "height", "frames_dir", "video_path"):
        if key not in output:
            raise ValueError(f"output.{key} is required")
    for key in ("duration", "fps"):
        if key not in project:
            raise ValueError(f"{key} is required")


def resolve_under_spike(path_text: str, *, must_exist: bool = False) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = SCRIPT_DIR / path
    resolved = path.resolve()
    if SCRIPT_DIR not in (resolved, *resolved.parents):
        raise ValueError(f"Path must stay under {SCRIPT_DIR}: {resolved}")
    if must_exist and not resolved.exists():
        raise FileNotFoundError(resolved)
    return resolved


def resolve_output_path(path_text: str) -> Path:
    resolved = resolve_under_spike(path_text)
    output_root = (SCRIPT_DIR / "output").resolve()
    if output_root not in (resolved, *resolved.parents):
        raise ValueError(f"Output path must stay under {output_root}: {resolved}")
    return resolved


def clear_frames_dir(path: Path) -> None:
    resolved = path.resolve()
    output_root = (SCRIPT_DIR / "output").resolve()
    if output_root not in (resolved, *resolved.parents):
        raise ValueError(f"Refusing to clear path outside output dir: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def configure_render(project: dict[str, Any], frames_dir: Path) -> None:
    scene = bpy.context.scene
    duration = float(project["duration"])
    fps = int(project["fps"])
    output = project["output"]

    scene.frame_start = 1
    scene.frame_end = int(round(duration * fps))
    scene.frame_set(1)
    scene.render.fps = fps
    scene.render.resolution_x = int(output["width"])
    scene.render.resolution_y = int(output["height"])
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(frames_dir) + os.sep

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"

    eevee = getattr(scene, "eevee", None)
    if eevee is not None:
        for attr, value in {
            "taa_render_samples": int(project.get("samples", 48)),
            "use_gtao": True,
            "gtao_distance": 4,
            "gtao_factor": 1.45,
            "use_bloom": True,
            "bloom_intensity": 0.045,
        }.items():
            if hasattr(eevee, attr):
                setattr(eevee, attr, value)

    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.color = (0.012, 0.014, 0.022)


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    emission: float = 0,
    roughness: float = 0.55,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Alpha"].default_value = color[3]
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = color
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission
    if color[3] < 1:
        material.blend_method = "BLEND"
    return material


def load_image_alpha_bbox(image_path: Path) -> tuple[bpy.types.Image, tuple[int, int, int, int]]:
    image = bpy.data.images.load(str(image_path), check_existing=True)
    image.colorspace_settings.name = "sRGB"
    width, height = image.size
    pixels = list(image.pixels)

    min_x = width
    min_y = height
    max_x = 0
    max_y = 0
    found = False

    for y in range(height):
        row = y * width * 4
        for x in range(width):
            alpha = pixels[row + x * 4 + 3]
            if alpha > 0.02:
                found = True
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if not found:
        raise ValueError(f"Input PNG has no visible alpha pixels: {image_path}")

    return image, (min_x, min_y, max_x, max_y)


def make_png_plane(image: bpy.types.Image, bbox: tuple[int, int, int, int]) -> dict[str, Any]:
    width_px, height_px = image.size
    min_x, min_y, max_x, max_y = bbox
    visible_w_norm = (max_x - min_x + 1) / width_px
    visible_h_norm = (max_y - min_y + 1) / height_px
    visible_center_x = ((min_x + max_x + 1) / 2) / width_px
    visible_center_y = ((min_y + max_y + 1) / 2) / height_px

    target_visible_width = 1.85
    plane_width = target_visible_width / visible_w_norm
    plane_height = plane_width * (height_px / width_px)

    x_offset = -((visible_center_x - 0.5) * plane_width)
    z_offset = -((0.5 - visible_center_y) * plane_height) + 0.28

    mesh = bpy.data.meshes.new("HeroImagePlaneMesh")
    vertices = [
        (-plane_width / 2 + x_offset, 0, -plane_height / 2 + z_offset),
        (plane_width / 2 + x_offset, 0, -plane_height / 2 + z_offset),
        (plane_width / 2 + x_offset, 0, plane_height / 2 + z_offset),
        (-plane_width / 2 + x_offset, 0, plane_height / 2 + z_offset),
    ]
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for loop, uv in zip(uv_layer.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        loop.uv = uv

    obj = bpy.data.objects.new("HeroPNGPlane", mesh)
    bpy.context.collection.objects.link(obj)

    material = bpy.data.materials.new("HeroPNGAlphaMaterial")
    material.use_nodes = True
    material.blend_method = "BLEND"
    material.show_transparent_back = True
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.extension = "CLIP"
    material.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    material.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    obj.data.materials.append(material)

    visible_width = plane_width * visible_w_norm
    visible_height = plane_height * visible_h_norm
    return {
        "object": obj,
        "target": Vector((0, 0, 0.12)),
        "visible_width": visible_width,
        "visible_height": visible_height,
        "alpha_bbox": bbox,
    }


def world_bbox(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    bpy.context.view_layer.update()
    min_corner = Vector((math.inf, math.inf, math.inf))
    max_corner = Vector((-math.inf, -math.inf, -math.inf))
    found = False

    for obj in objects:
        if obj.type not in {"MESH", "CURVE", "FONT"}:
            continue
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            min_corner.x = min(min_corner.x, world.x)
            min_corner.y = min(min_corner.y, world.y)
            min_corner.z = min(min_corner.z, world.z)
            max_corner.x = max(max_corner.x, world.x)
            max_corner.y = max(max_corner.y, world.y)
            max_corner.z = max(max_corner.z, world.z)
            found = True

    if not found:
        raise ValueError("No visible geometry found in asset")
    return min_corner, max_corner


def import_glb(asset_path: Path) -> dict[str, Any]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(asset_path))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    geometry = [obj for obj in imported if obj.type in {"MESH", "CURVE", "FONT"}]
    if not geometry:
        raise ValueError(f"GLB imported no renderable geometry: {asset_path}")

    root = bpy.data.objects.new("ProductAssetRoot", None)
    bpy.context.collection.objects.link(root)
    top_level = [obj for obj in imported if obj.parent is None or obj.parent not in imported]
    for obj in top_level:
        obj.parent = root
        obj.matrix_parent_inverse = root.matrix_world.inverted()

    min_corner, max_corner = world_bbox(geometry)
    center = (min_corner + max_corner) * 0.5
    dimensions = max_corner - min_corner
    max_dim = max(dimensions.x, dimensions.y, dimensions.z)
    scale = 2.55 / max_dim

    root.scale = (scale, scale, scale)
    root.location = Vector((-center.x * scale, -center.y * scale, 0.18 - center.z * scale))
    bpy.context.view_layer.update()

    fitted_min, fitted_max = world_bbox(geometry)
    fitted_dimensions = fitted_max - fitted_min
    target = (fitted_min + fitted_max) * 0.5
    return {
        "object": root,
        "target": target,
        "visible_width": max(fitted_dimensions.x, fitted_dimensions.y),
        "visible_height": fitted_dimensions.z,
        "alpha_bbox": None,
    }


def add_stage(template: str, subject: dict[str, Any]) -> None:
    bg_mat = make_material("DarkStageMat", (0.016, 0.019, 0.03, 1))
    floor_mat = make_material("FloorMat", (0.024, 0.026, 0.032, 1), roughness=0.75)
    cyan_mat = make_material("CyanAccent", (0.33, 0.88, 1.0, 1), emission=1.1)
    magenta_mat = make_material("MagentaAccent", (1.0, 0.30, 0.58, 1), emission=0.75)

    if template == "character_intro":
        bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 1.3, 1.3), rotation=(math.radians(90), 0, 0))
        backdrop = bpy.context.object
        backdrop.name = "DarkBackdrop"
        backdrop.data.materials.append(bg_mat)

    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 1.2, -1.28))
    floor = bpy.context.object
    floor.name = "StageFloor"
    floor.data.materials.append(floor_mat)

    radius = max(subject["visible_width"] * 0.58, 1.05)
    ring_z = subject["target"].z
    bpy.ops.mesh.primitive_torus_add(
        major_radius=radius,
        minor_radius=0.018,
        major_segments=128,
        minor_segments=8,
        location=(0, 0.2, ring_z),
        rotation=(math.radians(90), 0, 0),
    )
    ring = bpy.context.object
    ring.name = "TemplateBackRing"
    ring.data.materials.append(cyan_mat)

    if template == "character_intro":
        bpy.ops.mesh.primitive_torus_add(
            major_radius=max(radius * 0.68, 0.82),
            minor_radius=0.011,
            major_segments=128,
            minor_segments=8,
            location=(0, 0.16, ring_z),
            rotation=(math.radians(90), 0, 0),
        )
        inner = bpy.context.object
        inner.name = "TemplateInnerRing"
        inner.scale.x = 1.08
        inner.scale.z = 0.86
        inner.data.materials.append(magenta_mat)

    random.seed(11)
    glint_mat = make_material("StageGlints", (0.85, 0.93, 1.0, 1), emission=1.4)
    for index in range(18):
        x = random.uniform(-2.8, 2.8)
        z = random.uniform(-0.9, 2.2)
        if abs(x) < 0.75 and -0.55 < z < 1.35:
            x += 1.15 if x >= 0 else -1.15
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=10,
            ring_count=5,
            radius=random.uniform(0.012, 0.03),
            location=(x, random.uniform(0.0, 0.55), z),
        )
        glint = bpy.context.object
        glint.name = f"StageGlint_{index:02d}"
        glint.data.materials.append(glint_mat)


def add_lighting(template: str) -> None:
    bpy.ops.object.light_add(type="AREA", location=(0, -3.4, 2.7))
    key = bpy.context.object
    key.name = "SoftKeyLight"
    key.data.energy = 170 if template == "product_orbit" else 140
    key.data.size = 4.7

    bpy.ops.object.light_add(type="POINT", location=(-2.0, 0.7, 1.7))
    rim_left = bpy.context.object
    rim_left.name = "CyanRimLight"
    rim_left.data.energy = 220
    rim_left.data.color = (0.55, 0.95, 1.0)

    bpy.ops.object.light_add(type="POINT", location=(2.0, 0.8, 1.2))
    rim_right = bpy.context.object
    rim_right.name = "MagentaBackLight"
    rim_right.data.energy = 150
    rim_right.data.color = (1.0, 0.35, 0.65)

    bpy.ops.object.light_add(type="AREA", location=(0, 2.2, 3.1))
    back = bpy.context.object
    back.name = "BackLight"
    back.data.energy = 115
    back.data.size = 3.1


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def set_bezier_interpolation(obj: bpy.types.Object) -> None:
    animation_data = getattr(obj, "animation_data", None)
    action = getattr(animation_data, "action", None)
    fcurves = getattr(action, "fcurves", None)
    if not fcurves:
        return
    for fcurve in fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = "BEZIER"


def add_dolly_camera(project: dict[str, Any], subject: dict[str, Any]) -> float:
    output = project["output"]
    aspect = int(output["width"]) / int(output["height"])
    end_view_width = max(subject["visible_width"] * 1.75, 3.0)
    end_ortho_scale = end_view_width / aspect
    start_ortho_scale = end_ortho_scale * 1.13
    target = subject["target"]

    bpy.ops.object.camera_add(location=(0, -7.2, target.z + 0.25))
    camera = bpy.context.object
    camera.name = "JsonDollyCamera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = start_ortho_scale
    look_at(camera, target)
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    camera.keyframe_insert(data_path="location", frame=scene.frame_start)
    camera.data.keyframe_insert(data_path="ortho_scale", frame=scene.frame_start)

    camera.location = (0, -5.8, target.z + 0.30)
    camera.data.ortho_scale = end_ortho_scale
    look_at(camera, target + Vector((0, 0, 0.04)))
    camera.keyframe_insert(data_path="location", frame=scene.frame_end)
    camera.data.keyframe_insert(data_path="ortho_scale", frame=scene.frame_end)
    set_bezier_interpolation(camera)
    return end_ortho_scale


def add_orbit_camera(project: dict[str, Any], subject: dict[str, Any]) -> float:
    output = project["output"]
    aspect = int(output["width"]) / int(output["height"])
    target = subject["target"]
    orbit_diameter = max(subject["visible_width"], subject["visible_height"])
    view_height = max(subject["visible_height"] * 2.1, orbit_diameter / aspect * 1.8, 4.2)

    target_empty = bpy.data.objects.new("OrbitTarget", None)
    target_empty.location = target
    bpy.context.collection.objects.link(target_empty)

    pivot = bpy.data.objects.new("OrbitPivot", None)
    pivot.location = target
    bpy.context.collection.objects.link(pivot)

    bpy.ops.object.camera_add(location=(0, -7.0, target.z + 0.55))
    camera = bpy.context.object
    camera.name = "JsonOrbitCamera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = view_height
    look_at(camera, target)
    camera.parent = pivot
    camera.matrix_parent_inverse = pivot.matrix_world.inverted()
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.name = "TrackProduct"
    constraint.target = target_empty
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    pivot.rotation_euler = (0, 0, math.radians(-18))
    pivot.keyframe_insert(data_path="rotation_euler", frame=scene.frame_start)
    pivot.rotation_euler = (0, 0, math.radians(22))
    pivot.keyframe_insert(data_path="rotation_euler", frame=scene.frame_end)
    set_bezier_interpolation(pivot)
    return view_height


def add_text_overlay(project: dict[str, Any], view_height: float) -> None:
    text = project.get("text", {})
    title = str(text.get("title", "")).strip()
    subtitle = str(text.get("subtitle", "")).strip()
    if not title and not subtitle:
        return

    output = project["output"]
    aspect = int(output["width"]) / int(output["height"])
    view_width = view_height * aspect
    if project["template"] == "product_orbit":
        title_size = min(max(view_width * 0.052, 0.14), 0.24)
        subtitle_size = min(max(view_width * 0.032, 0.09), 0.15)
    else:
        title_size = min(max(view_width * 0.074, 0.16), 0.34)
        subtitle_size = min(max(view_width * 0.044, 0.10), 0.20)

    title_mat = make_material("TitleTextMaterial", (0.93, 0.96, 1.0, 1), emission=0.55)
    subtitle_mat = make_material("SubtitleTextMaterial", (0.55, 0.92, 1.0, 1), emission=0.35)

    y = -0.22
    x = 0
    if project["template"] == "product_orbit":
        x = -view_width * 0.14
        title_z = view_height * 0.28
    else:
        title_z = -view_height * 0.36
    subtitle_z = title_z - max(subtitle_size * 1.75, 0.22)

    if title:
        bpy.ops.object.text_add(location=(x, y, title_z), rotation=(math.radians(90), 0, 0))
        title_obj = bpy.context.object
        title_obj.name = "JsonTitle"
        title_obj.data.body = title
        title_obj.data.align_x = "CENTER"
        title_obj.data.align_y = "CENTER"
        title_obj.data.size = title_size
        title_obj.data.materials.append(title_mat)

    if subtitle:
        bpy.ops.object.text_add(location=(x, y, subtitle_z), rotation=(math.radians(90), 0, 0))
        subtitle_obj = bpy.context.object
        subtitle_obj.name = "JsonSubtitle"
        subtitle_obj.data.body = subtitle
        subtitle_obj.data.align_x = "CENTER"
        subtitle_obj.data.align_y = "CENTER"
        subtitle_obj.data.size = subtitle_size
        subtitle_obj.data.materials.append(subtitle_mat)


def animate_character(obj: bpy.types.Object) -> None:
    scene = bpy.context.scene
    obj.rotation_euler = (0, 0, math.radians(-1.0))
    obj.keyframe_insert(data_path="rotation_euler", frame=scene.frame_start)
    obj.location.z += 0.02
    obj.keyframe_insert(data_path="location", frame=scene.frame_start)

    mid = (scene.frame_start + scene.frame_end) // 2
    obj.rotation_euler = (0, 0, math.radians(1.0))
    obj.location.z += 0.05
    obj.keyframe_insert(data_path="rotation_euler", frame=mid)
    obj.keyframe_insert(data_path="location", frame=mid)

    obj.rotation_euler = (0, 0, math.radians(-0.5))
    obj.location.z -= 0.035
    obj.keyframe_insert(data_path="rotation_euler", frame=scene.frame_end)
    obj.keyframe_insert(data_path="location", frame=scene.frame_end)
    set_bezier_interpolation(obj)


def build_scene(project: dict[str, Any]) -> dict[str, Any]:
    asset = project["asset"]
    asset_path = resolve_under_spike(asset["path"], must_exist=True)

    if asset["type"] == "image":
        image, bbox = load_image_alpha_bbox(asset_path)
        subject = make_png_plane(image, bbox)
        animate_character(subject["object"])
    else:
        subject = import_glb(asset_path)

    add_stage(str(project["template"]), subject)
    add_lighting(str(project["template"]))

    motion = project["camera"]["motion"]
    if motion == "orbit":
        view_height = add_orbit_camera(project, subject)
    else:
        view_height = add_dolly_camera(project, subject)

    add_text_overlay(project, view_height)
    subject["asset_path"] = str(asset_path)
    return subject


def main() -> None:
    args = parse_args()
    project = load_project(args.project)
    frames_dir = resolve_output_path(project["output"]["frames_dir"])
    video_path = resolve_output_path(project["output"]["video_path"])

    clear_frames_dir(frames_dir)
    reset_scene()
    configure_render(project, frames_dir)
    subject = build_scene(project)

    start = time.perf_counter()
    bpy.ops.render.render(animation=True)
    elapsed = time.perf_counter() - start

    scene = bpy.context.scene
    expected_frames = int(round(float(project["duration"]) * int(project["fps"])))
    supported_fields = [
        "template",
        "asset.type",
        "asset.path",
        "camera.motion",
        "duration",
        "fps",
        "output.width",
        "output.height",
        "output.frames_dir",
        "output.video_path",
        "text.title",
        "text.subtitle",
    ]

    print(f"ROUTE2_PROJECT={project['_project_path']}")
    print(f"ROUTE2_TEMPLATE={project['template']}")
    print(f"ROUTE2_ASSET_TYPE={project['asset']['type']}")
    print(f"ROUTE2_ASSET_PATH={subject['asset_path']}")
    print(f"ROUTE2_CAMERA_MOTION={project['camera']['motion']}")
    print(f"ROUTE2_RENDER_ENGINE={scene.render.engine}")
    print(f"ROUTE2_RESOLUTION={scene.render.resolution_x}x{scene.render.resolution_y}")
    print(f"ROUTE2_DURATION={project['duration']}")
    print(f"ROUTE2_FPS={project['fps']}")
    print(f"ROUTE2_EXPECTED_FRAMES={expected_frames}")
    print(f"ROUTE2_FRAMES_DIR={frames_dir}")
    print(f"ROUTE2_VIDEO_PATH={video_path}")
    print(f"ROUTE2_RENDER_SECONDS={elapsed:.2f}")
    print(f"ROUTE2_ALPHA_BBOX={subject['alpha_bbox']}")
    print(f"ROUTE2_SUPPORTED_FIELDS={','.join(supported_fields)}")


if __name__ == "__main__":
    main()
