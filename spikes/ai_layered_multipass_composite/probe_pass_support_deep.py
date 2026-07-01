"""
Phase 0b: Deep pass rendering probe (Blender 5.x API).

Tests actual rendering of Cryptomatte, depth, normal passes in Eevee,
and validates the visibility-toggling approach for layered rendering.

Key Blender 5.x API changes:
- Compositor: bpy.data.node_groups.new(name, 'CompositorNodeTree')
- scene.compositing_node_group = ng
- File Output: fo.directory (not base_path), fo.file_output_items (not file_slots)

Usage:
  "{blender_exe}" --background --python probe_pass_support_deep.py --
    --output-dir "spikes/ai_layered_multipass_composite/output/probe"
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Blender deep pass probe")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def safe_delete_all() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def build_test_scene(output_dir: Path) -> None:
    """Build a 3-layer scene: background, subject sphere, text object."""
    safe_delete_all()

    # Background plane
    bpy.ops.mesh.primitive_plane_add(size=8.0, location=(0, -0.6, 0))
    bg = bpy.context.object
    bg.name = "BackgroundPlane"
    bg_mat = bpy.data.materials.new("BG_Mat")
    bg_mat.diffuse_color = (0.15, 0.18, 0.25, 1.0)
    bg.data.materials.append(bg_mat)
    bg.pass_index = 0

    # Subject sphere
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55, location=(0, 0, 0.4))
    subject = bpy.context.object
    subject.name = "SubjectSphere"
    subj_mat = bpy.data.materials.new("Subject_Mat")
    subj_mat.diffuse_color = (0.9, 0.15, 0.15, 1.0)
    subject.data.materials.append(subj_mat)
    subject.pass_index = 1

    # Text object
    bpy.ops.object.text_add(location=(0, 0.05, 0.95))
    text_obj = bpy.context.object
    text_obj.name = "TestText"
    text_obj.data.body = "LAYER TEST"
    text_obj.data.align_x = "CENTER"
    text_obj.data.size = 0.2
    text_obj.rotation_euler = (math.radians(90), 0, 0)
    text_mat = bpy.data.materials.new("Text_Mat")
    text_mat.diffuse_color = (1.0, 1.0, 1.0, 1.0)
    text_obj.data.materials.append(text_mat)
    text_obj.pass_index = 2

    # Floor plane
    bpy.ops.mesh.primitive_plane_add(size=10.0, location=(0, 0.0, -1.0))
    floor = bpy.context.object
    floor.name = "FloorPlane"
    floor_mat = bpy.data.materials.new("Floor_Mat")
    floor_mat.diffuse_color = (0.06, 0.08, 0.12, 1.0)
    floor.data.materials.append(floor_mat)

    # Ring accent
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.75, minor_radius=0.02,
        major_segments=64, minor_segments=8,
        location=(0, 0.1, 0.4)
    )
    ring = bpy.context.object
    ring.name = "AccentRing"
    ring_mat = bpy.data.materials.new("Ring_Mat")
    ring_mat.diffuse_color = (0.3, 0.85, 1.0, 1.0)
    ring.data.materials.append(ring_mat)

    # Camera
    bpy.ops.object.camera_add(location=(0, -5.5, 0.5))
    cam = bpy.context.object
    cam.name = "MainCamera"
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = cam

    # Lights
    bpy.ops.object.light_add(type="SUN", location=(2, -4, 5))
    bpy.context.object.data.energy = 2.5
    bpy.ops.object.light_add(type="POINT", location=(-2, 1, 2))
    bpy.context.object.data.energy = 80

    # Render settings
    scene = bpy.context.scene
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 1
    scene.frame_set(1)

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"

    print(f"Scene built. Engine: {scene.render.engine}")


def test_cryptomatte_render(output_dir: Path) -> dict:
    """Test Cryptomatte rendering in Eevee using Blender 5.x compositor API."""
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    result = {}

    # Enable Cryptomatte passes
    passes_enabled = {}
    for pass_name in ["use_pass_cryptomatte_object", "use_pass_cryptomatte_material",
                       "use_pass_cryptomatte_asset"]:
        if hasattr(view_layer, pass_name):
            try:
                setattr(view_layer, pass_name, True)
                passes_enabled[pass_name] = True
            except Exception as e:
                passes_enabled[pass_name] = f"ERROR: {e}"

    result["crypto_passes_enabled"] = passes_enabled

    # Set up compositor using Blender 5.x API
    try:
        ng = bpy.data.node_groups.new("CryptoTest", "CompositorNodeTree")
        scene.compositing_node_group = ng
        result["compositor_created"] = True

        rl = ng.nodes.new("CompositorNodeRLayers")
        rl.location = (0, 0)

        # List all outputs
        outputs = {}
        for o in rl.outputs:
            if not o.hide:
                outputs[o.name] = o.enabled
        result["rl_outputs"] = outputs

        # Check specifically for Cryptomatte outputs
        crypto_outputs = {k: v for k, v in outputs.items() if "rypto" in k.lower() or "Crypto" in k}
        result["crypto_outputs_on_rl"] = crypto_outputs

        # Try to output Crypto to file
        if crypto_outputs:
            fo = ng.nodes.new("CompositorNodeOutputFile")
            fo.location = (300, 100)
            fo.directory = str(output_dir / "crypto_test")
            fo.format.file_format = "OPEN_EXR"
            fo.format.color_depth = "32"

            crypto_socket_name = list(crypto_outputs.keys())[0]
            print(f"  Linking {crypto_socket_name} to File Output")
            ng.links.new(rl.outputs[crypto_socket_name], fo.inputs["Image"])

            scene.render.filepath = str(output_dir / "crypto_test" / "combined.png")
            scene.render.image_settings.file_format = "PNG"
            # Don't use compositor for main render, only for crypto output
            # (the compositor writes its own files)
            bpy.ops.render.render(write_still=True)
            result["crypto_rendered"] = True
        else:
            result["crypto_rendered"] = False
            result["crypto_note"] = "No Cryptomatte outputs on Render Layers node"

    except Exception as e:
        result["compositor_error"] = str(e)

    # Check output files
    crypto_files = []
    crypto_dir = output_dir / "crypto_test"
    if crypto_dir.exists():
        for f in crypto_dir.rglob("*"):
            if f.is_file():
                crypto_files.append({"name": f.name, "size": f.stat().st_size})
    result["crypto_output_files"] = crypto_files

    return result


def test_visibility_toggling(output_dir: Path) -> dict:
    """Render layers by toggling object visibility: full, background, subject, text."""
    scene = bpy.context.scene
    result = {}

    # Clear compositor
    scene.compositing_node_group = None

    # Identify scene objects
    all_mesh_names = []
    for obj in bpy.data.objects:
        if obj.type in {"MESH", "CURVE", "FONT", "SURFACE", "META"}:
            all_mesh_names.append(obj.name)

    subject_names = ["SubjectSphere"]
    text_names = ["TestText"]
    background_names = [n for n in all_mesh_names if n not in subject_names + text_names]

    result["objects"] = {
        "background": background_names,
        "subject": subject_names,
        "text": text_names,
        "all": all_mesh_names,
    }

    vis_dir = output_dir / "visibility_test"
    vis_dir.mkdir(parents=True, exist_ok=True)

    # Helper
    def set_visibility(visible_names, hide_others=True):
        for name in all_mesh_names:
            obj = bpy.data.objects.get(name)
            if obj:
                if hide_others:
                    obj.hide_render = name not in visible_names
                else:
                    obj.hide_render = False

    rendered_files = {}

    # ── Full scene (baseline) ──
    set_visibility(all_mesh_names, hide_others=False)
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(vis_dir / "full.png")
    bpy.ops.render.render(write_still=True)
    if (vis_dir / "full.png").exists():
        rendered_files["full"] = (vis_dir / "full.png").stat().st_size

    # ── Background only ──
    set_visibility(background_names)
    scene.render.film_transparent = False
    scene.render.filepath = str(vis_dir / "background.png")
    bpy.ops.render.render(write_still=True)
    if (vis_dir / "background.png").exists():
        rendered_files["background"] = (vis_dir / "background.png").stat().st_size

    # ── Subject only (with alpha) ──
    set_visibility(subject_names)
    scene.render.film_transparent = True
    scene.render.filepath = str(vis_dir / "subject.png")
    bpy.ops.render.render(write_still=True)
    if (vis_dir / "subject.png").exists():
        rendered_files["subject"] = (vis_dir / "subject.png").stat().st_size

    # ── Text only (with alpha) ──
    set_visibility(text_names)
    scene.render.film_transparent = True
    scene.render.filepath = str(vis_dir / "text.png")
    bpy.ops.render.render(write_still=True)
    if (vis_dir / "text.png").exists():
        rendered_files["text"] = (vis_dir / "text.png").stat().st_size

    result["rendered_files"] = rendered_files

    # ── Restore ──
    set_visibility(all_mesh_names, hide_others=False)
    scene.render.film_transparent = False

    return result


def test_view_layer_passes(output_dir: Path) -> dict:
    """Test enabling and rendering with Object Index and Material Index passes."""
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    result = {}

    # Enable passes
    for pass_attr in ["use_pass_object_index", "use_pass_material_index",
                       "use_pass_z", "use_pass_normal"]:
        if hasattr(view_layer, pass_attr):
            try:
                setattr(view_layer, pass_attr, True)
                result[pass_attr] = True
            except Exception as e:
                result[pass_attr] = f"ERROR: {e}"

    # Try to output via compositor
    try:
        ng = bpy.data.node_groups.new("PassTest", "CompositorNodeTree")
        scene.compositing_node_group = ng

        rl = ng.nodes.new("CompositorNodeRLayers")
        rl.location = (0, 0)

        # Check available outputs
        available = {o.name: o.enabled for o in rl.outputs if not o.hide}
        result["available_outputs"] = available

        # Try to output each pass
        pass_outputs = {}
        for pass_name in ["IndexOB", "IndexMA", "Depth", "Normal"]:
            if pass_name in available:
                fo = ng.nodes.new("CompositorNodeOutputFile")
                fo.location = (300, 100 - len(pass_outputs) * 200)
                fo.directory = str(output_dir / "pass_test" / pass_name.lower())
                fo.format.file_format = "PNG"
                fo.format.color_mode = "RGB"
                ng.links.new(rl.outputs[pass_name], fo.inputs["Image"])
                pass_outputs[pass_name] = "linked"

        result["pass_outputs"] = pass_outputs

        if pass_outputs:
            scene.render.filepath = str(output_dir / "pass_test" / "combined.png")
            scene.render.image_settings.file_format = "PNG"
            bpy.ops.render.render(write_still=True)
            result["rendered"] = True
        else:
            result["rendered"] = False
            result["note"] = "No pass outputs to link"

    except Exception as e:
        result["compositor_error"] = str(e)

    # Check files
    pass_files = []
    pass_dir = output_dir / "pass_test"
    if pass_dir.exists():
        for f in pass_dir.rglob("*.png"):
            pass_files.append({"name": f.name, "size": f.stat().st_size, "dir": f.parent.name})
    result["pass_files"] = pass_files

    return result


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PHASE 0b: Deep Pass Rendering Probe (Blender 5.x)")
    print(f"Blender: {bpy.app.version_string}")
    print("=" * 60)

    print("\n--- Building test scene ---")
    build_test_scene(output_dir)

    print("\n--- Test 1: Cryptomatte Rendering ---")
    crypto = test_cryptomatte_render(output_dir)
    for k, v in crypto.items():
        print(f"  {k}: {v}")

    print("\n--- Test 2: View Layer Passes (Object Index, Z, Normal) ---")
    passes = test_view_layer_passes(output_dir)
    for k, v in passes.items():
        print(f"  {k}: {v}")

    print("\n--- Test 3: Visibility Toggling Layers ---")
    vis = test_visibility_toggling(output_dir)
    for k, v in vis.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for k2, v2 in v.items():
                if isinstance(v2, list) and len(v2) > 5:
                    print(f"    {k2}: [{len(v2)} items]")
                else:
                    print(f"    {k2}: {v2}")
        else:
            print(f"  {k}: {v}")

    # Save results
    all_results = {
        "blender_version": bpy.app.version_string,
        "engine": bpy.context.scene.render.engine,
        "cryptomatte": crypto,
        "view_layer_passes": passes,
        "visibility_toggling": vis,
    }

    results_path = output_dir / "deep_pass_probe.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults saved to: {results_path}")

    # Summary
    print("\n" + "=" * 60)
    print("DEEP PROBE SUMMARY")
    print("=" * 60)

    crypto_files = crypto.get("crypto_output_files", [])
    print(f"Cryptomatte output files: {len(crypto_files)}")
    for cf in crypto_files:
        print(f"  - {cf['name']}: {cf['size']} bytes")

    pass_files = passes.get("pass_files", [])
    print(f"Pass output files: {len(pass_files)}")
    for pf in pass_files:
        print(f"  - [{pf['dir']}] {pf['name']}: {pf['size']} bytes")

    vis_files = vis.get("rendered_files", {})
    print(f"Visibility-toggled layers: {len(vis_files)}")
    for name, size in vis_files.items():
        print(f"  - {name}: {size} bytes")


if __name__ == "__main__":
    main()
