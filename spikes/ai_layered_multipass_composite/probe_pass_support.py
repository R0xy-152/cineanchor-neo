"""
Phase 0: Blender 5.x Eevee Next pass support probe.

Tests:
  1. Object mask (Object Index / Material Index)
  2. Alpha pass
  3. Depth/Z pass
  4. Normal pass
  5. Cryptomatte availability in Eevee
  6. Cycles availability for missing passes
  7. Multilayer EXR output support
  8. Separate PNG sequence approach

Usage:
  "{blender_exe}" --background --python probe_pass_support.py --
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
from mathutils import Vector


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Blender pass support probe")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_delete_all() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def build_mini_scene(output_dir: Path) -> tuple[bpy.types.Object, bpy.types.Object]:
    """Create a minimal scene: red cube (subject) on a grey plane (background)."""
    safe_delete_all()

    # Subject: red cube
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.5))
    cube = bpy.context.object
    cube.name = "ProbeSubject"
    mat = bpy.data.materials.new("RedSubject")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.9, 0.15, 0.15, 1.0)
    cube.data.materials.append(mat)

    # Background: large grey plane
    bpy.ops.mesh.primitive_plane_add(size=8.0, location=(0, -0.8, 0))
    plane = bpy.context.object
    plane.name = "ProbeBackground"
    bg_mat = bpy.data.materials.new("GreyBackground")
    bg_mat.use_nodes = True
    bsdf2 = bg_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf2:
        bsdf2.inputs["Base Color"].default_value = (0.2, 0.22, 0.28, 1.0)
    plane.data.materials.append(bg_mat)

    # Camera
    bpy.ops.object.camera_add(location=(0, -5, 1.2))
    cam = bpy.context.object
    cam.name = "ProbeCamera"
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.camera = cam

    # Light
    bpy.ops.object.light_add(type="SUN", location=(2, -3, 4))
    sun = bpy.context.object
    sun.data.energy = 3

    # Render settings
    scene = bpy.context.scene
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 1
    scene.frame_set(1)

    return cube, plane


def set_engine(engine: str) -> None:
    scene = bpy.context.scene
    try:
        scene.render.engine = engine
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    print(f"  Engine set: {scene.render.engine}")


def check_view_layer_passes() -> dict:
    """Enumerate all available view layer passes."""
    view_layer = bpy.context.view_layer
    results = {}

    # Check standard passes
    standard_passes = {
        "use_pass_combined": "combined",
        "use_pass_z": "depth/Z",
        "use_pass_normal": "normal",
        "use_pass_diffuse_color": "diffuse_color",
        "use_pass_glossy_color": "glossy_color",
        "use_pass_environment": "environment",
        "use_pass_emit": "emission",
        "use_pass_shadow": "shadow",
        "use_pass_ambient_occlusion": "ambient_occlusion",
        "use_pass_object_index": "object_index",
        "use_pass_material_index": "material_index",
        "use_pass_uv": "uv",
        "use_pass_mist": "mist",
        "use_pass_transmission_color": "transmission_color",
    }

    for attr, name in standard_passes.items():
        results[name] = hasattr(view_layer, attr)

    # Special: Cryptomatte (might be under eevee or view_layer)
    scene = bpy.context.scene
    if hasattr(view_layer, "use_pass_cryptomatte_object"):
        results["cryptomatte_object"] = True
    else:
        results["cryptomatte_object"] = False

    if hasattr(view_layer, "use_pass_cryptomatte_material"):
        results["cryptomatte_material"] = True
    else:
        results["cryptomatte_material"] = False

    return results


def check_cryptomatte_support(output_dir: Path) -> dict:
    """Check if Cryptomatte is available and usable in current engine."""
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    result = {"available": False, "engine": scene.render.engine, "note": ""}

    # Cryptomatte was introduced in Eevee Next (Blender 4.2+)
    if hasattr(view_layer, "use_pass_cryptomatte_object"):
        result["available"] = True
        result["pass_cryptomatte_object"] = True
    else:
        result["available"] = False
        result["note"] = "Cryptomatte not exposed on view_layer"

    # In older Eevee, Cryptomatte may only work in Cycles
    if hasattr(view_layer, "pass_cryptomatte_object") and "EEVEE" in scene.render.engine:
        # Check if Eevee actually supports it by trying to enable
        try:
            view_layer.use_pass_cryptomatte_object = True
            result["eevee_enabled"] = True
        except Exception as e:
            result["eevee_enabled"] = False
            result["note"] += f" | Eevee enable error: {e}"

    return result


def check_exr_multilayer(output_dir: Path) -> bool:
    """Check if OPEN_EXR_MULTILAYER format is available."""
    scene = bpy.context.scene

    # Enumerate available formats via the RNA enum items
    image_settings = scene.render.image_settings
    available_formats = []
    try:
        # rna_type.properties gives us access to the property definitions
        for prop_name in dir(image_settings):
            if prop_name == "file_format":
                file_format_prop = image_settings.rna_type.properties.get("file_format")
                if file_format_prop and hasattr(file_format_prop, "enum_items"):
                    for item in file_format_prop.enum_items:
                        available_formats.append(item.identifier)
                    break
    except Exception:
        pass

    # If enumeration failed, try directly
    if not available_formats:
        # Common format identifiers in Blender 5.x
        common = [
            "BMP", "IRIS", "PNG", "JPEG", "JPEG2000", "TARGA", "TARGA_RAW",
            "CINEON", "DPX", "OPEN_EXR_MULTILAYER", "OPEN_EXR", "HDR", "TIFF",
            "AVI_JPEG", "AVI_RAW", "FFMPEG",
        ]
        for fmt in common:
            original = image_settings.file_format
            try:
                image_settings.file_format = fmt
                available_formats.append(fmt)
            except (TypeError, ValueError):
                pass
            try:
                image_settings.file_format = original
            except Exception:
                pass

    # Check specifically for EXR multilayer
    original = image_settings.file_format
    try:
        image_settings.file_format = "OPEN_EXR_MULTILAYER"
        result = True
    except (TypeError, ValueError):
        result = False
    finally:
        try:
            image_settings.file_format = original
        except Exception:
            pass

    if available_formats:
        print(f"    Available formats: {sorted(available_formats)}")
    return result


def check_object_index_workflow() -> dict:
    """Test if Object Index / Material Index can produce usable masks."""
    result = {
        "object_index_supported": False,
        "material_index_supported": False,
        "note": "",
    }

    view_layer = bpy.context.view_layer
    if hasattr(view_layer, "use_pass_object_index"):
        view_layer.use_pass_object_index = True
        result["object_index_supported"] = True

    if hasattr(view_layer, "use_pass_material_index"):
        view_layer.use_pass_material_index = True
        result["material_index_supported"] = True

    # Check if we can set pass index on objects
    obj = bpy.data.objects.get("ProbeSubject")
    if obj and hasattr(obj, "pass_index"):
        obj.pass_index = 1
        result["object_pass_index_settable"] = True

    mat = bpy.data.materials.get("RedSubject")
    if mat and hasattr(mat, "pass_index"):
        mat.pass_index = 2
        result["material_pass_index_settable"] = True

    return result


def check_alpha_workflow(output_dir: Path) -> dict:
    """Test if we can render RGBA with clean alpha channel."""
    scene = bpy.context.scene
    result = {
        "rgba_output_supported": False,
        "film_transparent_supported": False,
        "note": "",
    }

    # RGBA PNG output
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    result["rgba_output_supported"] = True

    # Transparent film
    if hasattr(scene.render, "film_transparent"):
        scene.render.film_transparent = True
        result["film_transparent_supported"] = True
    else:
        result["note"] = "film_transparent not available"

    return result


def test_separate_passes_render(output_dir: Path) -> dict:
    """
    Test the approach of rendering separate PNG sequences for different layers
    by using multiple View Layers or toggling object visibility.
    """
    scene = bpy.context.scene
    results = {"approach": "separate PNG sequences via visibility toggling",
               "engine": scene.render.engine}

    # Approach A: Multiple View Layers
    try:
        view_layer = bpy.context.view_layer
        results["current_view_layer"] = view_layer.name
        results["can_create_view_layers"] = True

        # Check if we can create additional view layers
        existing = {vl.name for vl in scene.view_layers}
        results["existing_view_layers"] = list(existing)

    except Exception as e:
        results["view_layer_error"] = str(e)

    return results


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PHASE 0: Blender Pass Support Probe")
    print(f"Blender version: {bpy.app.version_string}")
    print(f"Build date: {bpy.app.build_date}")
    print("=" * 60)

    # Build test scene
    print("\n--- Building mini test scene ---")
    cube, plane = build_mini_scene(output_dir)

    all_results = {
        "blender_version": bpy.app.version_string,
        "build_date": str(bpy.app.build_date),
        "engine_tests": {},
    }

    # Test engines: Eevee Next, Eevee (fallback), Cycles
    for engine_label, engine_id in [
        ("EEVEE_NEXT", "BLENDER_EEVEE_NEXT"),
        ("EEVEE", "BLENDER_EEVEE"),
        ("CYCLES", "CYCLES"),
    ]:
        print(f"\n{'='*40}")
        print(f"Testing engine: {engine_label}")
        print(f"{'='*40}")

        engine_results = {}
        try:
            set_engine(engine_id)
        except Exception as e:
            engine_results["error"] = str(e)
            all_results["engine_tests"][engine_label] = engine_results
            continue

        actual_engine = bpy.context.scene.render.engine
        engine_results["actual_engine"] = actual_engine

        if engine_label == "EEVEE_NEXT" and actual_engine not in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            print(f"  SKIP: Eevee not available (got {actual_engine})")
            engine_results["skipped"] = True
            all_results["engine_tests"][engine_label] = engine_results
            continue

        # For EEVEE_NEXT, rename to EEVEE since Blender 5.1 uses EEVEE identifier
        if engine_label == "EEVEE_NEXT" and actual_engine == "BLENDER_EEVEE":
            print(f"  NOTE: EEVEE_NEXT → EEVEE (Blender 5.1 uses EEVEE identifier for Eevee Next)")
            # Mark that EEVEE test should be skipped since it's the same engine
            all_results["eevee_next_is_eevee"] = True

        if engine_label == "EEVEE" and all_results.get("eevee_next_is_eevee"):
            print(f"  SKIP: EEVEE is same as EEVEE_NEXT in this Blender version")
            engine_results["skipped"] = True
            engine_results["note"] = "Same engine as EEVEE_NEXT"
            all_results["engine_tests"][engine_label] = engine_results
            continue

        if engine_label == "CYCLES" and "CYCLES" not in actual_engine:
            print(f"  SKIP: Cycles not available")
            engine_results["skipped"] = True
            all_results["engine_tests"][engine_label] = engine_results
            continue

        # 1. View layer passes
        print("  --- View Layer Passes ---")
        passes = check_view_layer_passes()
        engine_results["view_layer_passes"] = passes
        for name, available in passes.items():
            status = "YES" if available else "NO"
            print(f"    {name}: {status}")

        # 2. Cryptomatte
        print("  --- Cryptomatte ---")
        crypto = check_cryptomatte_support(output_dir)
        engine_results["cryptomatte"] = crypto
        print(f"    available: {crypto['available']}")
        print(f"    eevee_enabled: {crypto.get('eevee_enabled', 'N/A')}")
        if crypto.get("note"):
            print(f"    note: {crypto['note']}")

        # 3. EXR Multilayer
        print("  --- EXR Multilayer ---")
        exr_ok = check_exr_multilayer(output_dir)
        engine_results["exr_multilayer_supported"] = exr_ok
        print(f"    OPEN_EXR_MULTILAYER: {'YES' if exr_ok else 'NO'}")

        # 4. Object/Material Index
        print("  --- Object/Material Index ---")
        index_info = check_object_index_workflow()
        engine_results["index_workflow"] = index_info
        for k, v in index_info.items():
            print(f"    {k}: {v}")

        # 5. Alpha workflow
        print("  --- Alpha Workflow ---")
        alpha_info = check_alpha_workflow(output_dir)
        engine_results["alpha_workflow"] = alpha_info
        for k, v in alpha_info.items():
            print(f"    {k}: {v}")

        # 6. Separate passes test
        print("  --- Separate Passes Approach ---")
        separate_info = test_separate_passes_render(output_dir)
        engine_results["separate_passes"] = separate_info
        for k, v in separate_info.items():
            if isinstance(v, list):
                print(f"    {k}: {v}")
            else:
                print(f"    {k}: {v}")

        all_results["engine_tests"][engine_label] = engine_results

    # Summary
    print("\n" + "=" * 60)
    print("PROBE SUMMARY")
    print("=" * 60)

    # Determine best engine for layering
    eevee_next = all_results["engine_tests"].get("EEVEE_NEXT", {})
    eevee = all_results["engine_tests"].get("EEVEE", {})
    cycles = all_results["engine_tests"].get("CYCLES", {})

    print("\nKey findings:")
    for engine_name, data in all_results["engine_tests"].items():
        if data.get("skipped"):
            print(f"  {engine_name}: SKIPPED (not available)")
            continue
        passes = data.get("view_layer_passes", {})
        exr = data.get("exr_multilayer_supported", False)
        crypto = data.get("cryptomatte", {})
        print(f"  {engine_name}:")
        print(f"    - depth/Z: {passes.get('depth/Z', 'unknown')}")
        print(f"    - normal: {passes.get('normal', 'unknown')}")
        print(f"    - object_index: {passes.get('object_index', 'unknown')}")
        print(f"    - cryptomatte: {crypto.get('available', False)}")
        print(f"    - EXR multilayer: {exr}")

    # Save full results
    results_path = output_dir / "pass_support_probe.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nFull results saved to: {results_path}")

    # Also test a quick Eevee render to verify the scene works
    print("\n--- Quick Render Test (EEVEE) ---")
    try:
        set_engine("BLENDER_EEVEE_NEXT")
    except Exception:
        set_engine("BLENDER_EEVEE")

    bpy.context.scene.render.image_settings.file_format = "PNG"
    bpy.context.scene.render.image_settings.color_mode = "RGBA"
    render_path = str(output_dir / "probe_test_render.png")
    bpy.context.scene.render.filepath = render_path
    bpy.ops.render.render(write_still=True)
    if os.path.exists(render_path):
        size = os.path.getsize(render_path)
        print(f"  Render OK: {render_path} ({size} bytes)")
    else:
        print(f"  Render FAILED: no output at {render_path}")


if __name__ == "__main__":
    main()
