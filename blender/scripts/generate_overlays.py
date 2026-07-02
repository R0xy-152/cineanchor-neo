"""
Generate deterministic particle and bokeh overlay MP4s for post compositing.

One-time utility — outputs to assets/overlays/.
Renders PNG frames via Blender, then composes to MP4 via FFmpeg.
Usage: blender --background --python blender/scripts/generate_overlays.py
"""
from __future__ import annotations

import math
import random
import subprocess
import tempfile
from pathlib import Path

import bpy

OUT_DIR = Path(__file__).resolve().parents[2] / "assets" / "overlays"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG_PATH = (
    "E:/cineanchor/.tools/ffmpeg/ffmpeg-8.1.1-essentials_build/bin/ffmpeg.exe"
)

# ── shared constants ──────────────────────────────────────────────────
WIDTH = 1080
HEIGHT = 1920
FPS = 24
FRAME_COUNT = 48  # 2-second loop


# ── helpers ───────────────────────────────────────────────────────────


def _reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def _configure_render(frames_dir: Path) -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = FRAME_COUNT
    scene.render.fps = FPS
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(frames_dir / "####.png")
    scene.render.engine = "BLENDER_EEVEE"
    # NO film_transparent — in Blender 5.1 EEVEE it suppresses emission
    # rendering. Screen blend (black→no-op) handles the "transparency."
    # Raw view transform — needed for true black (0) background so
    # screen blend is a no-op over dark areas. Particle emission is
    # reduced to stay in the same perceived range as the main render.
    scene.view_settings.view_transform = "Raw"
    world = bpy.data.worlds.new("OverlayWorld")
    scene.world = world
    scene.world.color = (0, 0, 0)


def _make_emissive_material(
    name: str, color: tuple[float, float, float, float],
    emission_strength: float = 2.5,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Emission Color"].default_value = color
        bsdf.inputs["Emission Strength"].default_value = emission_strength
        bsdf.inputs["Alpha"].default_value = color[3]
    mat.blend_method = "BLEND"
    return mat


def _make_transparent_material(name: str) -> bpy.types.Material:
    """Fully transparent material — hides the emitter mesh at render time."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Alpha"].default_value = 0.0
    mat.blend_method = "BLEND"
    return mat


def _setup_glow() -> None:
    """Add Glare node in compositor for bloom/glow (Blender 5.1 EEVEE Next).

    Guarded — in Blender 5.1, the compositor API (scene.node_tree) is not
    available for EEVEE renders. Ember visibility comes from emissive
    material + particle size + no film_transparent; glow is additive only.
    """
    # Compositor node tree is not accessible in 5.1 EEVEE — skip.
    # Particles are already visible via emission strength.
    print("Glow setup skipped (compositor not available in 5.1 EEVEE)")


def _frames_to_mp4(frames_dir: Path, output_path: Path) -> None:
    """Compose PNG frames to MP4 using system FFmpeg."""
    cmd = [
        FFMPEG_PATH, "-y",
        "-framerate", str(FPS),
        "-i", str(frames_dir / "%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-crf", "18",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr[-500:]}")
        raise RuntimeError(f"FFmpeg failed with code {result.returncode}")


def _validate_non_black(video_path: Path, label: str) -> float:
    """Fail generation if overlay video is all or near-all black.

    Extracts 3 sample frames as raw RGB, counts non-black pixels.
    Returns the fraction of pixels above threshold (0.0–1.0).
    """
    import struct

    cmd = [
        FFMPEG_PATH,
        "-i", str(video_path),
        "-vframes", "3",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode != 0 or len(result.stdout) == 0:
        raise RuntimeError(
            f"Cannot decode {label} overlay: {video_path}"
        )

    # Each pixel is 3 bytes (R,G,B). Count pixels where max(R,G,B) > 15.
    total_pixels = len(result.stdout) // 3
    bright_pixels = 0
    for i in range(0, len(result.stdout), 3):
        r = result.stdout[i]
        g = result.stdout[i + 1]
        b = result.stdout[i + 2]
        if r > 15 or g > 15 or b > 15:
            bright_pixels += 1

    fraction = bright_pixels / total_pixels if total_pixels > 0 else 0.0
    if fraction < 0.0001:  # fewer than 0.01% of pixels are non-black
        raise RuntimeError(
            f"{label} overlay is near-black: only {bright_pixels}/{total_pixels} "
            f"pixels ({fraction*100:.4f}%) above threshold. "
            f"Generation produced empty output: {video_path}"
        )
    print(f"{label}_BRIGHT_FRACTION={fraction:.6f} ({bright_pixels}/{total_pixels})")
    return fraction


# ── ember generation ──────────────────────────────────────────────────


def generate_embers(output_path: Path) -> None:
    """Warm orange ember particles rising upward from a plane emitter."""
    frames_dir = Path(tempfile.mkdtemp(prefix="embers_"))
    _reset_scene()
    _configure_render(frames_dir)
    _setup_glow()

    # Camera
    bpy.ops.object.camera_add(location=(0, 0, 10))
    bpy.context.scene.camera = bpy.context.object

    # ── Phase 1a: emitter plane with transparent material ──────────
    bpy.ops.mesh.primitive_plane_add(size=2.4, location=(0, 0, -0.8))
    emitter = bpy.context.object
    emitter.name = "EmberEmitter"
    # hide_render = False (default) — must render so particle modifier evaluates
    emitter.data.materials.append(_make_transparent_material("EmitterTransparent"))

    # ── Phase 1b: OBJECT render type with UV sphere instances ──────
    # Instance radius * particle_size = visible size.
    # radius=0.08 * size=1.0 = 0.08 unit diameter → ~12 pixels at cam dist 10.
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=8, ring_count=6, radius=0.08,
        location=(0, 0, -10),  # far away — instance object itself is never rendered
    )
    instance_obj = bpy.context.object
    instance_obj.name = "EmberParticleInstance"
    instance_obj.hide_viewport = True
    instance_obj.hide_render = True
    # Emissive material on the instance (particles clone this material)
    # Pre-tinted warm orange — color tint is baked, not applied in FFmpeg.
    ember_mat = _make_emissive_material(
        "EmberMat", (1.0, 0.65, 0.15, 1.0), emission_strength=5.0,
    )
    instance_obj.data.materials.append(ember_mat)

    # ── Particle system ────────────────────────────────────────────
    emitter.modifiers.new("EmberParticles", "PARTICLE_SYSTEM")
    psys = emitter.particle_systems[0]
    settings = psys.settings
    settings.count = 150
    settings.frame_start = 1.0
    settings.frame_end = float(FRAME_COUNT)
    settings.lifetime = float(FRAME_COUNT)
    settings.lifetime_random = 0.5
    settings.normal_factor = 1.8
    settings.factor_random = 0.7
    settings.emit_from = "FACE"
    settings.physics_type = "NEWTON"
    settings.effector_weights.gravity = 0.25
    # Phase 1b: OBJECT instead of HALO
    settings.render_type = "OBJECT"
    settings.instance_object = instance_obj
    # Phase 1c: particle size (scales instance object)
    settings.particle_size = 1.0
    settings.size_random = 0.5
    settings.use_rotations = True
    settings.effector_weights.turbulence = 0.3

    # Wind/turbulence field for drift
    bpy.ops.object.effector_add(type="TURBULENCE", location=(0, 0, 0.5))
    turbulence = bpy.context.object
    turbulence.name = "EmberTurbulence"
    turbulence.field.strength = 12.0
    turbulence.field.size = 4.0
    turbulence.field.flow = 0.5
    turbulence.field.noise = 0.6

    bpy.ops.render.render(animation=True)
    _frames_to_mp4(frames_dir, output_path)

    # Phase 1e: non-black validation
    _validate_non_black(output_path, "EMBER")
    print(f"EMBER_OVERLAY={output_path}")


# ── bokeh generation ──────────────────────────────────────────────────


def generate_bokeh(output_path: Path) -> None:
    """Soft white bokeh circles scattered with varying sizes and opacity."""
    frames_dir = Path(tempfile.mkdtemp(prefix="bokeh_"))
    _reset_scene()
    _configure_render(frames_dir)

    # Camera
    bpy.ops.object.camera_add(location=(0, 0, 10))
    bpy.context.scene.camera = bpy.context.object

    random.seed(42)

    for i in range(25):
        x = random.uniform(-3.5, 3.5)
        z = random.uniform(-3.5, 3.5)
        y = random.uniform(-1.5, 1.5)
        radius = random.uniform(0.02, 0.08)
        alpha = random.uniform(0.05, 0.15)

        bpy.ops.mesh.primitive_circle_add(
            vertices=32,
            radius=radius,
            fill_type="NGON",
            location=(x, z, y),
        )
        circle = bpy.context.object
        circle.name = f"Bokeh_{i:02d}"

        mat = _make_emissive_material(
            f"BokehMat_{i:02d}",
            (1.0, 1.0, 1.0, alpha),
            emission_strength=0.15,
        )
        circle.data.materials.append(mat)

        # Subtle drift animation
        circle.keyframe_insert("location", frame=1, index=2)
        drift_z = z + random.uniform(0.05, 0.2)
        circle.location.z = drift_z
        circle.keyframe_insert("location", frame=FRAME_COUNT, index=2)

    bpy.ops.render.render(animation=True)
    _frames_to_mp4(frames_dir, output_path)

    # Non-black validation
    _validate_non_black(output_path, "BOKEH")
    print(f"BOKEH_OVERLAY={output_path}")


# ── main ──────────────────────────────────────────────────────────────


def main() -> None:
    print("Generating overlay assets…")
    print(f"Output directory: {OUT_DIR}")

    ember_path = OUT_DIR / "embers_default.mp4"
    bokeh_path = OUT_DIR / "bokeh_default.mp4"

    print("→ Generating ember loop…")
    generate_embers(ember_path)

    print("→ Generating bokeh loop…")
    generate_bokeh(bokeh_path)

    print("Overlay generation complete.")
    print(f"  {ember_path}")
    print(f"  {bokeh_path}")


if __name__ == "__main__":
    main()
