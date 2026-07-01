from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector

# Ensure blender/scripts/ is on sys.path (needed for camera_math/presets imports
# when running inside Blender's bundled Python).
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# Import defaults (single source of truth); fall back to inline constants
# when running inside Blender's bundled Python where the package may not be
# on sys.path.
try:
    from render_defaults import (
        DEFAULT_LIGHTING,
        DEFAULT_MODEL_TRANSFORM,
            DEFAULT_PNG_TARGET_VISIBLE_WIDTH,
            DEFAULT_PNG_Z_OFFSET,
            DEFAULT_PNG_TARGET,
            DEFAULT_GLB_SCALE_DIVISOR,
            DEFAULT_GLB_ROTATION_Z_DEG,
            DEFAULT_GLB_Z_OFFSET,
            DOLLY_START_Y,
            DOLLY_END_Y,
            DOLLY_START_Z_OFFSET,
            DOLLY_END_Z_OFFSET,
            DOLLY_END_VIEW_WIDTH_MULT,
            DOLLY_END_VIEW_WIDTH_MIN,
            DOLLY_START_SCALE_FACTOR,
            ORBIT_Y,
            ORBIT_Z_OFFSET,
            ORBIT_VIEW_HEIGHT_MULT,
            ORBIT_DIAMETER_MULT,
            ORBIT_VIEW_HEIGHT_MIN,
            ORBIT_START_ANGLE_DEG,
            ORBIT_END_ANGLE_DEG,
            template_key_energy,
    )
except ImportError:
    # Fallback — keep the script self-contained for Blender subprocess use.
    DEFAULT_LIGHTING: dict[str, dict] = {
        "key": {"location": (0, -3.4, 2.7), "energy": None, "size": 4.7, "color": "#FFFFFF"},
        "rim_left": {"location": (-2.0, 0.7, 1.7), "energy": 220, "color": "#8CF2FF"},
        "rim_right": {"location": (2.0, 0.8, 1.2), "energy": 150, "color": "#FF59A6"},
        "back": {"location": (0, 2.2, 3.1), "energy": 115, "size": 3.1, "color": "#FFFFFF"},
        "silhouette_rim": {"location": (1.8, 2.5, 2.4), "energy": 100, "color": "#55EEFF",
                           "spot_size": 45, "spot_blend": 0.3, "rotation": (-35, 0, -40)},
    }
    DEFAULT_MODEL_TRANSFORM: dict = {"location": None, "rotation": None, "scale": None}
    DEFAULT_PNG_TARGET_VISIBLE_WIDTH = 1.85
    DEFAULT_PNG_Z_OFFSET = 0.28
    DEFAULT_PNG_TARGET = (0, 0, 0.12)
    DEFAULT_GLB_SCALE_DIVISOR = 2.55
    DEFAULT_GLB_ROTATION_Z_DEG = 180
    DEFAULT_GLB_Z_OFFSET = 0.18
    DOLLY_START_Y = -7.2
    DOLLY_END_Y = -5.8
    DOLLY_START_Z_OFFSET = 0.25
    DOLLY_END_Z_OFFSET = 0.30
    DOLLY_END_VIEW_WIDTH_MULT = 1.75
    DOLLY_END_VIEW_WIDTH_MIN = 3.0
    DOLLY_START_SCALE_FACTOR = 1.13
    ORBIT_Y = -7.0
    ORBIT_Z_OFFSET = 0.55
    ORBIT_VIEW_HEIGHT_MULT = 2.1
    ORBIT_DIAMETER_MULT = 1.8
    ORBIT_VIEW_HEIGHT_MIN = 4.2
    ORBIT_START_ANGLE_DEG = -18
    ORBIT_END_ANGLE_DEG = 22

    def template_key_energy(template: str) -> int:
        return 170 if template == "product_orbit" else 140


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="CineAnchor V0.1 Blender render")
    parser.add_argument("--project", required=True)
    parser.add_argument("--frames-dir", required=True)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--asset-path", required=True)
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Project JSON helpers
# ---------------------------------------------------------------------------


def load_project(path_text: str) -> dict[str, Any]:
    with open(path_text, "r", encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------------------
# Scene management
# ---------------------------------------------------------------------------


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def configure_render(
    project: dict[str, Any],
    width: int,
    height: int,
    frames_dir: Path,
) -> None:
    scene = bpy.context.scene
    output = project["output"]
    duration = int(output["duration"])
    fps = int(output["fps"])

    scene.frame_start = 1
    scene.frame_end = duration * fps
    scene.frame_set(1)
    scene.render.fps = fps
    scene.render.resolution_x = width
    scene.render.resolution_y = height
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
            "taa_render_samples": 48,
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


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Asset loading
# ---------------------------------------------------------------------------


def load_image_alpha_bbox(
    image_path: Path,
) -> tuple[bpy.types.Image, tuple[int, int, int, int]]:
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


def make_png_plane(
    image: bpy.types.Image,
    bbox: tuple[int, int, int, int],
    project: dict[str, Any] | None = None,
) -> dict[str, Any]:
    width_px, height_px = image.size
    min_x, min_y, max_x, max_y = bbox
    visible_w_norm = (max_x - min_x + 1) / width_px
    visible_h_norm = (max_y - min_y + 1) / height_px
    visible_center_x = ((min_x + max_x + 1) / 2) / width_px
    visible_center_y = ((min_y + max_y + 1) / 2) / height_px

    mt = _get_model_transform(project)
    scale_override = (mt or {}).get("scale") if mt else None
    target_visible_width = scale_override if scale_override is not None else DEFAULT_PNG_TARGET_VISIBLE_WIDTH
    plane_width = target_visible_width / visible_w_norm
    plane_height = plane_width * (height_px / width_px)

    x_offset = -((visible_center_x - 0.5) * plane_width)
    z_offset = -((0.5 - visible_center_y) * plane_height) + DEFAULT_PNG_Z_OFFSET

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

    # Apply model transform overrides (location / rotation)
    auto_loc = Vector(DEFAULT_PNG_TARGET)
    auto_rot = (0, 0, 0)
    if mt and (mt.get("location") is not None or mt.get("rotation") is not None):
        if mt.get("location") is not None:
            obj.location = Vector(mt["location"])
        else:
            obj.location = auto_loc
        if mt.get("rotation") is not None:
            obj.rotation_euler = tuple(math.radians(r) for r in mt["rotation"])
    else:
        obj.location = auto_loc

    visible_width = plane_width * visible_w_norm
    visible_height = plane_height * visible_h_norm
    return {
        "object": obj,
        "target": Vector(DEFAULT_PNG_TARGET),
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


def import_glb(asset_path: Path, project: dict[str, Any] | None = None) -> dict[str, Any]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(asset_path))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    geometry = [obj for obj in imported if obj.type in {"MESH", "CURVE", "FONT"}]
    if not geometry:
        raise ValueError(f"GLB imported no renderable geometry: {asset_path}")

    root = bpy.data.objects.new("ProductAssetRoot", None)
    bpy.context.collection.objects.link(root)
    top_level = [
        obj for obj in imported
        if obj.parent is None or obj.parent not in imported
    ]
    for obj in top_level:
        obj.parent = root
        obj.matrix_parent_inverse = root.matrix_world.inverted()

    min_corner, max_corner = world_bbox(geometry)
    center = (min_corner + max_corner) * 0.5
    dimensions = max_corner - min_corner
    max_dim = max(dimensions.x, dimensions.y, dimensions.z)

    # Auto-computed defaults (current hardcoded behaviour)
    mt = _get_model_transform(project)
    scale_val = (mt or {}).get("scale") if mt else None
    auto_scale = scale_val if scale_val is not None else DEFAULT_GLB_SCALE_DIVISOR / max_dim
    auto_location = Vector((
        -center.x * auto_scale,
        -center.y * auto_scale,
        DEFAULT_GLB_Z_OFFSET - center.z * auto_scale,
    ))
    auto_rotation = (0, 0, math.radians(DEFAULT_GLB_ROTATION_Z_DEG))

    _apply_model_transform(
        root, project,
        auto_location=auto_location,
        auto_rotation_euler=auto_rotation,
        auto_scale=(auto_scale, auto_scale, auto_scale),
    )

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


# ---------------------------------------------------------------------------
# Scene construction
# ---------------------------------------------------------------------------


# ── Stage construction ───────────────────────────────────────────────


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color string (e.g. '#FF59A6') to (r, g, b) in 0-1 range."""
    hex_val = hex_color.lstrip("#")
    return (
        int(hex_val[0:2], 16) / 255.0,
        int(hex_val[2:4], 16) / 255.0,
        int(hex_val[4:6], 16) / 255.0,
    )


def _get_lighting_overrides(project: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return lighting_overrides dict from project JSON, or None."""
    if not project:
        return None
    return project.get("scene", {}).get("lighting_overrides", None)


def _apply_light_override(
    light_obj: bpy.types.Object,
    light_name: str,
    overrides: dict[str, Any] | None,
    template: str,
) -> None:
    """Apply JSON lighting overrides to a Blender light object.

    Reads ``lighting_overrides.<light_name>`` from the project JSON.
    Falls back to DEFAULT_LIGHTING hardcoded values when no override is provided.
    """
    defaults = DEFAULT_LIGHTING.get(light_name, {})
    override = (overrides or {}).get(light_name, None) or {}

    # --- enabled ---
    if not override.get("enabled", True):
        light_obj.data.energy = 0
        return

    # --- energy ---
    if override.get("energy") is not None:
        light_obj.data.energy = override["energy"]
    elif defaults.get("energy") is not None:
        light_obj.data.energy = defaults["energy"]
    elif light_name == "key":
        light_obj.data.energy = template_key_energy(template)

    # --- color ---
    color_hex = override.get("color") or defaults.get("color")
    if color_hex:
        light_obj.data.color = _hex_to_rgb(color_hex)

    # --- size ---
    size = override.get("size") if override.get("size") is not None else defaults.get("size")
    if size is not None and hasattr(light_obj.data, "size"):
        light_obj.data.size = size

    # --- spot_size / spot_blend (silhouette_rim only) ---
    for attr in ("spot_size", "spot_blend"):
        val = override.get(attr) if override.get(attr) is not None else defaults.get(attr)
        if val is not None and hasattr(light_obj.data, attr):
            light_obj.data.__setattr__(attr, math.radians(val) if attr == "spot_size" else val)

    # --- rotation override (silhouette_rim) ---
    rot = override.get("rotation") if override.get("rotation") is not None else defaults.get("rotation")
    if rot is not None:
        light_obj.rotation_euler = tuple(math.radians(r) for r in rot)

    # --- location override ---
    loc = override.get("location") or defaults.get("location")
    if loc:
        light_obj.location = loc


def _get_model_transform(project: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return model_transform dict from project JSON, or None."""
    if not project:
        return None
    return project.get("scene", {}).get("model_transform", None)


def _apply_model_transform(
    obj: bpy.types.Object,
    project: dict[str, Any] | None,
    *,
    auto_location: Vector,
    auto_rotation_euler: tuple[float, float, float],
    auto_scale: tuple[float, float, float],
) -> None:
    """Apply model transform overrides on top of auto-computed defaults.

    Only overrides fields that are explicitly provided; everything else stays
    at the auto-computed value.
    """
    mt = _get_model_transform(project)
    if mt is None:
        return

    if mt.get("location") is not None:
        obj.location = Vector(mt["location"])
    else:
        obj.location = auto_location

    if mt.get("rotation") is not None:
        obj.rotation_euler = tuple(math.radians(r) for r in mt["rotation"])
    else:
        obj.rotation_euler = auto_rotation_euler

    if mt.get("scale") is not None:
        s = mt["scale"]
        obj.scale = (s, s, s)
    else:
        obj.scale = auto_scale


def _add_cloth_texture(material: bpy.types.Material, mix_factor: float) -> None:
    """Add subtle procedural cloth/fabric texture to a backdrop material.

    Noise Texture → ColorRamp → MixRGB(MULTIPLY) at *mix_factor* opacity,
    so the pattern faintly overlays the original flat color.
    """
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    base_color = (0.016, 0.019, 0.03, 1.0)

    # Disconnect any existing Base Color link so our chain takes over
    for link in list(bsdf.inputs["Base Color"].links):
        links.remove(link)

    # Noise Texture — large scale for woven/cloth look
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 10.0
    noise.inputs["Detail"].default_value = 2.0
    noise.location = (-400, 200)

    # ColorRamp — subtle dark-to-light weave variation
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.40
    ramp.color_ramp.elements[0].color = (0.20, 0.20, 0.24, 1.0)
    ramp.color_ramp.elements[1].position = 0.60
    ramp.color_ramp.elements[1].color = (0.40, 0.42, 0.46, 1.0)
    ramp.location = (-200, 200)

    # RGB node — the original flat color
    rgb = nodes.new("ShaderNodeRGB")
    rgb.outputs[0].default_value = base_color
    rgb.location = (-600, -100)

    # MixRGB — blend cloth pattern with base at configured strength
    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = mix_factor
    mix.location = (0, 0)

    links.new(noise.outputs["Fac"], ramp.inputs[0])
    links.new(ramp.outputs["Color"], mix.inputs["Color2"])
    links.new(rgb.outputs[0], mix.inputs["Color1"])
    links.new(mix.outputs[0], bsdf.inputs["Base Color"])


def add_stage(
    template: str,
    subject: dict[str, Any],
    project: dict[str, Any] | None = None,
) -> None:
    bg_mat = make_material("DarkStageMat", (0.016, 0.019, 0.03, 1))
    floor_mat = make_material("FloorMat", (0.024, 0.026, 0.032, 1), roughness=0.75)
    cyan_mat = make_material("CyanAccent", (0.33, 0.88, 1.0, 1), emission=1.1)
    magenta_mat = make_material("MagentaAccent", (0.33, 0.88, 1.0, 1), emission=0.75)

    bg_enhance = (project or {}).get("scene", {}).get("background_enhance", {})

    if template == "character_intro":
        bpy.ops.mesh.primitive_plane_add(
            size=12, location=(0, 1.3, 1.3), rotation=(math.radians(90), 0, 0)
        )
        backdrop = bpy.context.object
        backdrop.name = "DarkBackdrop"
        backdrop.data.materials.append(bg_mat)

        # ── Cloth texture on backdrop (Step 1b) ───────────────────
        if bg_enhance.get("cloth_texture", True):
            _add_cloth_texture(bg_mat, bg_enhance.get("cloth_mix", 0.07))

    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 1.2, -1.28))
    floor = bpy.context.object
    floor.name = "StageFloor"
    floor.data.materials.append(floor_mat)

    radius = max(subject["visible_width"] * 0.58, 1.05)
    ring_z = subject["target"].z
    if bg_enhance.get("stage_ring", True):
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
    if bg_enhance.get("glints", True):
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


def add_lighting(template: str, project: dict[str, Any] | None = None) -> None:
    overrides = _get_lighting_overrides(project)

    # --- Key light (AREA) ---
    key_override = (overrides or {}).get("key") or {}
    key_loc = key_override.get("location") or DEFAULT_LIGHTING["key"]["location"]
    bpy.ops.object.light_add(type="AREA", location=key_loc)
    key = bpy.context.object
    key.name = "SoftKeyLight"
    key.data.energy = template_key_energy(template)
    key.data.size = DEFAULT_LIGHTING["key"]["size"]
    _apply_light_override(key, "key", overrides, template)

    # --- Rim left / cyan (POINT) ---
    rim_left_override = (overrides or {}).get("rim_left") or {}
    rim_left_loc = rim_left_override.get("location") or DEFAULT_LIGHTING["rim_left"]["location"]
    bpy.ops.object.light_add(type="POINT", location=rim_left_loc)
    rim_left = bpy.context.object
    rim_left.name = "CyanRimLight"
    rim_left.data.energy = DEFAULT_LIGHTING["rim_left"]["energy"]
    rim_left.data.color = _hex_to_rgb(DEFAULT_LIGHTING["rim_left"]["color"])
    _apply_light_override(rim_left, "rim_left", overrides, template)

    # --- Rim right / magenta (POINT) ---
    rim_right_override = (overrides or {}).get("rim_right") or {}
    rim_right_loc = rim_right_override.get("location") or DEFAULT_LIGHTING["rim_right"]["location"]
    bpy.ops.object.light_add(type="POINT", location=rim_right_loc)
    rim_right = bpy.context.object
    rim_right.name = "MagentaBackLight"
    rim_right.data.energy = DEFAULT_LIGHTING["rim_right"]["energy"]
    rim_right.data.color = _hex_to_rgb(DEFAULT_LIGHTING["rim_right"]["color"])
    _apply_light_override(rim_right, "rim_right", overrides, template)

    # --- Back light (AREA) ---
    back_override = (overrides or {}).get("back") or {}
    back_loc = back_override.get("location") or DEFAULT_LIGHTING["back"]["location"]
    bpy.ops.object.light_add(type="AREA", location=back_loc)
    back = bpy.context.object
    back.name = "BackLight"
    back.data.energy = DEFAULT_LIGHTING["back"]["energy"]
    back.data.size = DEFAULT_LIGHTING["back"]["size"]
    _apply_light_override(back, "back", overrides, template)

    # ── Silhouette rim light (Step 1a) ────────────────────────────
    # Only active for templates that have a background plane.
    bg_enhance = (project or {}).get("scene", {}).get("background_enhance", {})
    if template == "character_intro" and bg_enhance.get("rim_light", True):
        sil_defaults = DEFAULT_LIGHTING["silhouette_rim"]
        sil_override = (overrides or {}).get("silhouette_rim") or {}
        sil_loc = sil_override.get("location") or sil_defaults["location"]
        bpy.ops.object.light_add(type="SPOT", location=sil_loc)
        rim = bpy.context.object
        rim.name = "SilhouetteRimLight"
        rim.data.energy = bg_enhance.get("rim_light_energy", sil_defaults["energy"])
        hex_val = bg_enhance.get("rim_light_color", sil_defaults["color"]).lstrip("#")
        rim.data.color = (
            int(hex_val[0:2], 16) / 255.0,
            int(hex_val[2:4], 16) / 255.0,
            int(hex_val[4:6], 16) / 255.0,
        )
        rim.data.spot_size = math.radians(sil_defaults["spot_size"])
        rim.data.spot_blend = sil_defaults["spot_blend"]
        rim.rotation_euler = tuple(math.radians(r) for r in sil_defaults["rotation"])
        _apply_light_override(rim, "silhouette_rim", overrides, template)


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


def add_dolly_camera(
    width: int,
    height: int,
    project: dict[str, Any],
    subject: dict[str, Any],
) -> float:
    scene = bpy.context.scene
    aspect = width / height
    target = subject["target"]

    # Read camera params from project JSON (fall back to hardcoded defaults)
    cam = project.get("camera", {})
    start_distance = float(cam.get("start_distance", abs(DOLLY_START_Y)))
    end_distance = float(cam.get("end_distance", abs(DOLLY_END_Y)))
    height_offset = float(cam.get("height", DOLLY_START_Z_OFFSET))
    focal_mult = float(cam.get("focal_length", 1.0))

    end_view_width = max(subject["visible_width"] * DOLLY_END_VIEW_WIDTH_MULT, DOLLY_END_VIEW_WIDTH_MIN)
    end_ortho_scale = (end_view_width / aspect) * focal_mult
    start_ortho_scale = end_ortho_scale * DOLLY_START_SCALE_FACTOR

    start_y = -start_distance
    end_y = -end_distance
    start_z = target.z + height_offset
    end_z = target.z + height_offset + (DOLLY_END_Z_OFFSET - DOLLY_START_Z_OFFSET)

    # ── Speed adjustment ────────────────────────────────────────
    # speed scales the frame range over which the camera completes its move.
    # speed=1.0 → normal (start→end over full duration).
    # speed=2.0 → reaches end at 50% of duration, then holds.
    # speed=0.5 → only gets halfway by the end.
    speed = float(cam.get("speed", 1.0))
    anim_end = int(scene.frame_start + max(1, (scene.frame_end - scene.frame_start) / max(speed, 0.01)))
    anim_end = max(scene.frame_start + 1, min(anim_end, scene.frame_end))

    bpy.ops.object.camera_add(location=(0, start_y, start_z))
    camera = bpy.context.object
    camera.name = "JsonDollyCamera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = start_ortho_scale
    look_at(camera, target)
    scene.camera = camera

    camera.keyframe_insert(data_path="location", frame=scene.frame_start)
    camera.data.keyframe_insert(
        data_path="ortho_scale", frame=scene.frame_start
    )

    camera.location = (0, end_y, end_z)
    camera.data.ortho_scale = end_ortho_scale
    look_at(camera, target + Vector((0, 0, 0.04)))
    camera.keyframe_insert(data_path="location", frame=anim_end)
    camera.data.keyframe_insert(data_path="ortho_scale", frame=anim_end)
    set_bezier_interpolation(camera)
    return end_ortho_scale


def add_orbit_camera(
    width: int,
    height: int,
    project: dict[str, Any],
    subject: dict[str, Any],
) -> float:
    scene = bpy.context.scene
    aspect = width / height
    target = subject["target"]

    # Read camera params from project JSON
    cam = project.get("camera", {})
    height_offset = float(cam.get("height", ORBIT_Z_OFFSET))
    focal_mult = float(cam.get("focal_length", 1.0))
    start_angle = float(cam.get("start_distance", abs(ORBIT_START_ANGLE_DEG)))
    end_angle = float(cam.get("end_distance", abs(ORBIT_END_ANGLE_DEG)))

    orbit_diameter = max(subject["visible_width"], subject["visible_height"])
    view_height = max(
        subject["visible_height"] * ORBIT_VIEW_HEIGHT_MULT,
        orbit_diameter / aspect * ORBIT_DIAMETER_MULT,
        ORBIT_VIEW_HEIGHT_MIN,
    )
    ortho_scale = view_height * focal_mult

    target_empty = bpy.data.objects.new("OrbitTarget", None)
    target_empty.location = target
    bpy.context.collection.objects.link(target_empty)

    pivot = bpy.data.objects.new("OrbitPivot", None)
    pivot.location = target
    bpy.context.collection.objects.link(pivot)

    bpy.ops.object.camera_add(location=(0, ORBIT_Y, target.z + height_offset))
    camera = bpy.context.object
    camera.name = "JsonOrbitCamera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale
    look_at(camera, target)
    camera.parent = pivot
    camera.matrix_parent_inverse = pivot.matrix_world.inverted()
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.name = "TrackProduct"
    constraint.target = target_empty
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    scene.camera = camera

    # Map start_distance / end_distance to pivot rotation angles
    # Positive end_angle → clockwise, negative start_angle → counter-clockwise
    # ── Speed adjustment ────────────────────────────────────────
    # Speed scales the frame range: higher speed = faster rotation (completes sooner)
    speed = float(cam.get("speed", 1.0))
    anim_end = int(scene.frame_start + max(1, (scene.frame_end - scene.frame_start) / max(speed, 0.01)))
    anim_end = max(scene.frame_start + 1, min(anim_end, scene.frame_end))

    pivot.rotation_euler = (0, 0, math.radians(-start_angle))
    pivot.keyframe_insert(data_path="rotation_euler", frame=scene.frame_start)
    pivot.rotation_euler = (0, 0, math.radians(end_angle))
    pivot.keyframe_insert(data_path="rotation_euler", frame=anim_end)
    set_bezier_interpolation(pivot)
    return view_height


# ---------------------------------------------------------------------------
# Preset camera — multi-keyframe cinematic moves
# ---------------------------------------------------------------------------


def _compute_scene_center_radius(subject: dict[str, Any]) -> tuple[list[float], float]:
    """Extract scene center and visible radius from the subject dict.

    ADJ-6: tested on both PNG (character_intro) and GLB (product_orbit).
    """
    target = subject["target"]  # Vector
    vw = subject.get("visible_width", 1.85)
    vh = subject.get("visible_height", 1.85)
    scene_center = [target.x, target.y, target.z]
    scene_radius = max(vw, vh) * 0.65
    return scene_center, scene_radius


def _adapt_preset_keyframes(
    kfs: list[dict],
    scene_center: list[float],
) -> list[dict]:
    """Swap X↔Y in preset keyframes to match Blender scene convention.

    The legacy presets use X as the primary viewing axis; our Blender scene
    uses Y (camera at negative Y looking toward +Y).  We swap X↔Y on both
    position and target, then regenerate the quaternion so the camera
    orientation stays consistent with the adapted position.
    """
    try:
        from camera_presets import _quat_from_look as qfl
    except ImportError:
        from blender.scripts.camera_presets import _quat_from_look as qfl  # type: ignore[import-untyped]

    adapted: list[dict] = []
    for kf in kfs:
        pos = kf["pos"]
        target = kf.get("target") or scene_center
        adapted_pos = [pos[1], pos[0], pos[2]]
        adapted_target = [target[1], target[0], target[2]]
        adapted_quat = qfl(adapted_pos, adapted_target)
        adapted.append({
            "t": kf["t"],
            "pos": adapted_pos,
            "quat": adapted_quat,
            "fov": kf["fov"],
        })
    return adapted


def add_keyframed_camera(
    width: int,
    height: int,
    project: dict[str, Any],
    subject: dict[str, Any],
    preset_name: str,
) -> float:
    """Create a PERSP camera driven by a preset's multi-keyframe trajectory.

    Uses the interpolation engine (camera_math) to generate per-frame
    location + quaternion data.  Returns *view_height* for downstream
    text-overlay sizing (approximated from FOV and scene radius).

    ADJ-7: PERSP is created *only* on the preset branch.  The default
    ``preset = null`` path stays ORTHO + 2-KF Bezier, unchanged.
    """
    scene = bpy.context.scene
    aspect = width / height

    # ── Generate & adapt keyframes ──────────────────────────────────
    try:
        from camera_presets import apply_preset
    except ImportError:
        from blender.scripts.camera_presets import apply_preset

    try:
        from camera_math import interpolate_keyframes
    except ImportError:
        from blender.scripts.camera_math import interpolate_keyframes

    scene_center, scene_radius = _compute_scene_center_radius(subject)
    raw_kfs = apply_preset(preset_name, scene_center, scene_radius)
    adapted_kfs = _adapt_preset_keyframes(raw_kfs, scene_center)

    fps = int(project["output"]["fps"])
    frames = interpolate_keyframes(adapted_kfs, fps)

    # ── Create PERSP camera ─────────────────────────────────────────
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "JsonPresetCamera"
    camera.data.type = "PERSP"
    camera.data.sensor_fit = "VERTICAL"

    first = frames[0]
    camera.location = first["pos"]
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = first["quat"]

    scene.camera = camera

    # ── Keyframe per-frame pose ─────────────────────────────────────
    start_frame = scene.frame_start
    for i, fr in enumerate(frames):
        frame_num = start_frame + i
        if frame_num > scene.frame_end:
            break
        camera.location = fr["pos"]
        camera.rotation_quaternion = fr["quat"]
        camera.keyframe_insert(data_path="location", frame=frame_num)
        camera.keyframe_insert(
            data_path="rotation_quaternion", frame=frame_num,
        )
        # Animate lens focal length from FOV
        sensor_h = camera.data.sensor_height or 24.0
        fov_rad = math.radians(fr.get("fov", 55))
        new_lens = (sensor_h * 0.5) / math.tan(fov_rad * 0.5) if math.tan(fov_rad * 0.5) > 0.001 else 50.0
        camera.data.lens = new_lens
        camera.data.keyframe_insert(data_path="lens", frame=frame_num)

    # ── Approximate view_height for text overlay ────────────────────
    # For PERSP: 2 * distance * tan(FOV/2) at the median distance
    mid_idx = len(frames) // 2
    mid_pos = frames[mid_idx]["pos"] if frames else first["pos"]
    mid_fov = frames[mid_idx].get("fov", 55) if frames else 55
    dist_to_target = math.sqrt(
        (mid_pos[0] - scene_center[0]) ** 2
        + (mid_pos[1] - scene_center[1]) ** 2
        + (mid_pos[2] - scene_center[2]) ** 2
    )
    view_height = max(
        2 * dist_to_target * math.tan(math.radians(mid_fov) / 2),
        scene_radius * 2,
    )
    return view_height


def _adapt_user_keyframes(
    kfs: list[dict],
    scene_center: list[float],
) -> list[dict]:
    """Convert Three.js (Y-up) keyframes to Blender (Z-up).

    Three.js: +Y=up, -Z=forward.  Blender: +Z=up, -Y=forward.
    Converts position via coordinate swap, offset to scene_center,
    and regenerates quaternion from converted position + derived target
    via _quat_from_look.
    """
    try:
        from camera_math import target_from_quat
    except ImportError:
        from blender.scripts.camera_math import target_from_quat

    try:
        from camera_presets import _quat_from_look as qfl
    except ImportError:
        from blender.scripts.camera_presets import _quat_from_look as qfl

    cx, cy, cz = scene_center
    adapted: list[dict] = []
    for kf in kfs:
        # Position: Three.js (x, y, z) → Blender (x + cx, -z + cy, y + cz)
        tx, ty, tz = kf["pos"]
        blender_pos = [tx + cx, -tz + cy, ty + cz]

        # Derive target in Three.js coords, convert to Blender coords
        three_target = target_from_quat(kf["pos"], kf.get("quat", [0, 0, 0, 1]))
        blender_target = [
            three_target[0] + cx,
            -three_target[2] + cy,
            three_target[1] + cz,
        ]

        # Regenerate quaternion in Blender coords
        quat = qfl(blender_pos, blender_target)

        adapted.append({
            "t": kf["t"],
            "pos": blender_pos,
            "quat": quat,
            "fov": kf.get("fov", 55),
        })
    return adapted


def _persp_camera_from_frames(
    frames: list[dict],
    fps: int,
    scene: Any,
) -> tuple[Any, float]:
    """Create a PERSP camera with per-frame keyframes from pre-computed frames.

    Returns (camera, view_height).
    """
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "JsonInteractiveCamera"
    camera.data.type = "PERSP"
    camera.data.sensor_fit = "VERTICAL"

    first = frames[0]
    camera.location = first["pos"]
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = first["quat"]
    scene.camera = camera

    start_frame = scene.frame_start
    for i, fr in enumerate(frames):
        frame_num = start_frame + i
        if frame_num > scene.frame_end:
            break
        camera.location = fr["pos"]
        camera.rotation_quaternion = fr["quat"]
        camera.keyframe_insert(data_path="location", frame=frame_num)
        camera.keyframe_insert(data_path="rotation_quaternion", frame=frame_num)
        # FOV → lens
        sensor_h = camera.data.sensor_height or 24.0
        fov_rad = math.radians(fr.get("fov", 55))
        new_lens = (sensor_h * 0.5) / math.tan(fov_rad * 0.5) if math.tan(fov_rad * 0.5) > 0.001 else 50.0
        camera.data.lens = new_lens
        camera.data.keyframe_insert(data_path="lens", frame=frame_num)

    # Approximate view_height
    try:
        from camera_math import interpolate_keyframes
    except ImportError:
        from blender.scripts.camera_math import interpolate_keyframes
    scene_center, scene_radius = [0.0, 0.0, 0.0], 1.0  # approx
    mid_idx = len(frames) // 2
    mid_pos = frames[mid_idx]["pos"] if frames else first["pos"]
    mid_fov = frames[mid_idx].get("fov", 55) if frames else 55
    dist_to_origin = math.sqrt(mid_pos[0]**2 + mid_pos[1]**2 + mid_pos[2]**2)
    view_height = max(
        2 * dist_to_origin * math.tan(math.radians(mid_fov) / 2),
        2.0,
    )
    return camera, view_height


def add_keyframed_camera_from_data(
    width: int,
    height: int,
    project: dict[str, Any],
    subject: dict[str, Any],
    user_keyframes: list[dict],
) -> float:
    """Create PERSP camera from user-recorded interactive keyframes.

    Converts Three.js coords → Blender coords, then creates per-frame
    keyframes using the same FOV→lens formula as add_keyframed_camera.
    """
    scene = bpy.context.scene
    scene_center, _scene_radius = _compute_scene_center_radius(subject)

    adapted = _adapt_user_keyframes(user_keyframes, scene_center)

    try:
        from camera_math import interpolate_keyframes
    except ImportError:
        from blender.scripts.camera_math import interpolate_keyframes

    fps = int(project["output"]["fps"])
    frames = interpolate_keyframes(adapted, fps)
    _camera, view_height = _persp_camera_from_frames(frames, fps, scene)
    return view_height


def add_keyframed_camera_from_shots(
    width: int,
    height: int,
    project: dict[str, Any],
    subject: dict[str, Any],
    shots: list[dict],
) -> float:
    """Create PERSP camera from user-recorded multi-shot interactive keyframes.

    Each shot is a hard cut — interpolation does NOT cross shot boundaries.
    """
    scene = bpy.context.scene
    scene_center, _scene_radius = _compute_scene_center_radius(subject)

    try:
        from camera_math import interpolate_keyframes
    except ImportError:
        from blender.scripts.camera_math import interpolate_keyframes

    fps = int(project["output"]["fps"])

    # Interpolate each shot independently, then concatenate
    all_frames: list[dict] = []
    for shot in shots:
        shot_kfs = shot.get("keyframes", [])
        if not shot_kfs:
            continue
        adapted = _adapt_user_keyframes(shot_kfs, scene_center)
        shot_frames = interpolate_keyframes(adapted, fps)
        all_frames.extend(shot_frames)

    if not all_frames:
        # Fallback: no valid keyframes
        return add_dolly_camera(width, height, project, subject)

    _camera, view_height = _persp_camera_from_frames(all_frames, fps, scene)
    return view_height


def add_text_overlay(
    width: int,
    height: int,
    project: dict[str, Any],
    view_height: float,
) -> None:
    text_spec = project.get("text", {})
    title = str(text_spec.get("title", "")).strip()
    subtitle = str(text_spec.get("subtitle", "")).strip()
    if not title and not subtitle:
        return

    aspect = width / height
    view_width = view_height * aspect
    template = project["template"]

    if template == "product_orbit":
        title_size = min(max(view_width * 0.052, 0.14), 0.24)
        subtitle_size = min(max(view_width * 0.032, 0.09), 0.15)
    else:
        title_size = min(max(view_width * 0.074, 0.16), 0.34)
        subtitle_size = min(max(view_width * 0.044, 0.10), 0.20)

    title_mat = make_material(
        "TitleTextMaterial", (0.93, 0.96, 1.0, 1), emission=0.55
    )
    subtitle_mat = make_material(
        "SubtitleTextMaterial", (0.55, 0.92, 1.0, 1), emission=0.35
    )

    y = -0.22
    if template == "product_orbit":
        x = -view_width * 0.14
        title_z = view_height * 0.28
    else:
        x = 0
        title_z = -view_height * 0.36
    subtitle_z = title_z - max(subtitle_size * 1.75, 0.22)

    if title:
        bpy.ops.object.text_add(
            location=(x, y, title_z), rotation=(math.radians(90), 0, 0)
        )
        title_obj = bpy.context.object
        title_obj.name = "JsonTitle"
        title_obj.data.body = title
        title_obj.data.align_x = "CENTER"
        title_obj.data.align_y = "CENTER"
        title_obj.data.size = title_size
        title_obj.data.materials.append(title_mat)

    if subtitle:
        bpy.ops.object.text_add(
            location=(x, y, subtitle_z), rotation=(math.radians(90), 0, 0)
        )
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


def build_scene(
    width: int,
    height: int,
    project: dict[str, Any],
    asset_path: Path,
) -> None:
    template = project["template"]
    asset_type = project["assets"][0]["type"]

    if asset_type == "image":
        image, bbox = load_image_alpha_bbox(asset_path)
        subject = make_png_plane(image, bbox, project)
        if template == "character_intro":
            animate_character(subject["object"])
    else:
        subject = import_glb(asset_path, project)

    add_stage(template, subject, project)
    add_lighting(template, project)

    cam_spec = project.get("camera", {})
    user_keyframes = cam_spec.get("keyframes")  # loop 08: [{t, pos, quat, fov}]
    user_shots = cam_spec.get("shots")          # loop 08: [{index, keyframes, cut}]
    preset_name = cam_spec.get("preset") if cam_spec else None

    if user_shots:
        # User-recorded multi-shot interactive keyframes (loop 08)
        view_height = add_keyframed_camera_from_shots(
            width, height, project, subject, user_shots,
        )
    elif user_keyframes:
        # User-recorded interactive keyframes (loop 08, single shot)
        view_height = add_keyframed_camera_from_data(
            width, height, project, subject, user_keyframes,
        )
    elif preset_name:
        # ADJ-7: preset branch — PERSP camera, multi-keyframe trajectory.
        view_height = add_keyframed_camera(
            width, height, project, subject, preset_name,
        )
    else:
        motion = cam_spec.get("motion", "dolly_in")
        if motion == "orbit":
            view_height = add_orbit_camera(width, height, project, subject)
        else:
            view_height = add_dolly_camera(width, height, project, subject)

    # ADJ-6: text_overlay=false must suppress text even if title is non-empty
    bg_enhance = project.get("scene", {}).get("background_enhance", {})
    if bg_enhance.get("text_overlay", True):
        add_text_overlay(width, height, project, view_height)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()
    project = load_project(args.project)
    frames_dir = Path(args.frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    reset_scene()
    configure_render(project, args.width, args.height, frames_dir)
    build_scene(args.width, args.height, project, Path(args.asset_path))

    start = time.perf_counter()
    bpy.ops.render.render(animation=True)
    elapsed = time.perf_counter() - start

    scene = bpy.context.scene
    total_frames = (
        int(project["output"]["duration"]) * int(project["output"]["fps"])
    )
    print(f"RENDER_COMPLETE frames_dir={frames_dir}")
    print(f"RENDER_SECONDS={elapsed:.2f}")
    print(f"RENDER_ENGINE={scene.render.engine}")
    print(f"RENDER_RESOLUTION={scene.render.resolution_x}x{scene.render.resolution_y}")
    print(f"RENDER_EXPECTED_FRAMES={total_frames}")


if __name__ == "__main__":
    main()
