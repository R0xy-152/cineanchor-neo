"""Camera preset library — cinematic camera moves.

Generates keyframe lists from named presets + scene parameters.
Uses camera_math for interpolation (pure Python, no bpy dependency).

Presets are demo/validation material — not a committed product feature
(requirements §四 #2). Ported from D:\\CineAnchor\\cineanchor\\core\\camera_presets.py.
"""

from __future__ import annotations

import math
from typing import Optional

try:
    from camera_math import interpolate_keyframes
except ImportError:
    from blender.scripts.camera_math import interpolate_keyframes  # test env


def _quat_from_look(
    pos: list[float],
    target: list[float],
    up: tuple[float, float, float] = (0, 0, 1),
) -> list[float]:
    """Generate a quaternion (x, y, z, w) from camera position and look-at target.

    Default ``up=(0, 0, 1)`` is Blender Z-up.
    """
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    dz = target[2] - pos[2]
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    if dist < 1e-6:
        return [0, 0, 0, 1]

    forward = (dx / dist, dy / dist, dz / dist)
    ux, uy, uz = up

    # Right = forward × up
    rx = forward[1] * uz - forward[2] * uy
    ry = forward[2] * ux - forward[0] * uz
    rz = forward[0] * uy - forward[1] * ux
    rlen = math.sqrt(rx * rx + ry * ry + rz * rz)
    if rlen < 1e-6:
        rx, ry, rz = 1, 0, 0
    else:
        rx, ry, rz = rx / rlen, ry / rlen, rz / rlen

    # Up = right × forward
    ux2 = ry * forward[2] - rz * forward[1]
    uy2 = rz * forward[0] - rx * forward[2]
    uz2 = rx * forward[1] - ry * forward[0]

    # Build quaternion from the 3×3 rotation matrix columns: right, up, -forward
    # (Blender camera looks down -Z, so the look-at direction is -forward)
    nfx, nfy, nfz = -forward[0], -forward[1], -forward[2]

    trace = rx + uy2 - nfz
    _EPS = 1e-10
    if trace > 0:
        s = max(math.sqrt(trace + 1) * 2, _EPS)
        qw = 0.25 * s
        qx = (uz2 + nfy) / s
        qy = (nfx + rz) / s
        qz = (ry - rx) / s
    elif rx > uy2 and rx > -nfz:
        s = max(math.sqrt(1 + rx - uy2 + nfz) * 2, _EPS)
        qw = (uz2 + nfy) / s
        qx = 0.25 * s
        qy = (rx + ry) / s
        qz = (nfx + rz) / s
    elif uy2 > -nfz:
        s = max(math.sqrt(1 + uy2 - rx + nfz) * 2, _EPS)
        qw = (nfx + rz) / s
        qx = (rx + ry) / s
        qy = 0.25 * s
        qz = (uz2 + nfy) / s
    else:
        s = max(math.sqrt(1 + nfz + rx + uy2) * 2, _EPS)
        qw = (ry - rx) / s
        qx = (nfx + rz) / s
        qy = (uz2 + nfy) / s
        qz = 0.25 * s

    qnorm = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    return [qx / qnorm, qy / qnorm, qz / qnorm, qw / qnorm]


# ── Preset registry ────────────────────────────────────────────────────

PRESETS: dict[str, dict] = {
    "nolan_orbit": {
        "name": "Nolan Orbit",
        "description": "环绕主体 180°, 低角度仰拍, 缓慢推进",
        "params": {
            "orbit_angle": 180, "pitch": -15,
            "distance_ratio": 1.2, "duration": 6,
        },
    },
    "anime_closeup": {
        "name": "Anime Close-up",
        "description": "快速推近主体, 微幅晃动, 浅景深特写",
        "params": {
            "start_distance": 8, "end_distance": 2,
            "fov_start": 45, "fov_end": 35, "duration": 3,
        },
    },
    "dolly_reveal": {
        "name": "Dolly Reveal",
        "description": "侧向平移, 主体逐渐入画, 广角",
        "params": {"lateral_distance": 10, "fov": 70, "duration": 5},
    },
    "drone_ascend": {
        "name": "Drone Ascend",
        "description": "从地面升到鸟瞰, 向下俯拍, 广角",
        "params": {
            "start_height": 1.5, "end_height": 15,
            "fov": 60, "duration": 8,
        },
    },
    "hero_tracking": {
        "name": "Hero Tracking",
        "description": "从主体前方低角度跟拍, 后退拉开揭示环境",
        "params": {
            "start_distance": 3, "end_distance": 7,
            "pitch": -10, "duration": 5,
        },
    },
    "suspense_pan": {
        "name": "Suspense Pan",
        "description": "缓慢水平横扫, 悬疑感, 长焦",
        "params": {"pan_angle": 90, "fov": 35, "duration": 7},
    },
    "god_eye": {
        "name": "God's Eye",
        "description": "极高鸟瞰, 极慢自转, 全景",
        "params": {
            "height_ratio": 6, "rotation_speed": 20,
            "fov": 50, "duration": 10,
        },
    },
    "whip_pan": {
        "name": "Whip Pan",
        "description": "快速甩镜, 90° 急转视线方向",
        "params": {"swing_angle": 90, "fov": 55, "duration": 1.5},
    },
}


# ── Preset application ──────────────────────────────────────────────────


def apply_preset(
    preset_name: str,
    scene_center: list[float],
    scene_radius: float,
    num_keyframes: Optional[int] = None,
) -> list[dict]:
    """Generate keyframes for a named preset around a scene subject.

    Args:
        preset_name: One of the 8 preset IDs (e.g. ``"nolan_orbit"``).
        scene_center: ``[cx, cy, cz]`` — world-space center of the subject.
        scene_radius: Approximate visible radius of the subject (used to
            scale distances so the camera doesn't clip through or fly away).
        num_keyframes: Override the default keyframe count (default: at
            least 3, scaled by duration).

    Returns:
        List of keyframe dicts: ``{"t", "pos", "quat", "fov"}``.
    """
    if preset_name not in PRESETS:
        raise KeyError(
            f"Unknown preset '{preset_name}'. "
            f"Available: {list(PRESETS.keys())}"
        )

    preset = PRESETS[preset_name]
    params = preset["params"]
    duration = params.get("duration", 5)
    nk = num_keyframes or max(3, duration * 2)
    cx, cy, cz = scene_center
    r = scene_radius
    keyframes: list[dict] = []

    if preset_name == "nolan_orbit":
        orbit = math.radians(params["orbit_angle"])
        pitch = math.radians(params["pitch"])
        dist = r * params["distance_ratio"]
        for i in range(nk):
            t = i / (nk - 1)
            angle = math.pi / 2 - orbit / 2 + t * orbit
            px = cx + math.cos(angle) * dist
            py = cy + math.sin(angle) * dist
            pz = cz + math.sin(pitch) * dist
            quat = _quat_from_look([px, py, pz], [cx, cy, cz * 0.7])
            keyframes.append({
                "t": round(t * duration, 2),
                "pos": [round(px, 3), round(py, 3), round(pz, 3)],
                "quat": [round(q, 4) for q in quat],
                "fov": 50,
            })

    elif preset_name == "anime_closeup":
        d_start = r * params["start_distance"]
        d_end = r * params["end_distance"]
        fov_s, fov_e = params["fov_start"], params["fov_end"]
        for i in range(nk):
            t = i / (nk - 1)
            # Smoothstep ease-in-out
            et = t * t * (3 - 2 * t)
            dist = d_start + (d_end - d_start) * et
            fov = fov_s + (fov_e - fov_s) * t
            wobble = math.sin(t * 7) * 0.15 * r * (1 - t)
            pos = [cx - dist, cy + wobble, cz + r * 0.4]
            quat = _quat_from_look(pos, [cx, cy, cz + r * 0.3])
            keyframes.append({
                "t": round(t * duration, 2),
                "pos": [round(v, 3) for v in pos],
                "quat": [round(q, 4) for q in quat],
                "fov": round(fov, 1),
            })

    elif preset_name == "dolly_reveal":
        lat = r * params["lateral_distance"]
        fov = params["fov"]
        for i in range(nk):
            t = i / (nk - 1)
            pos = [
                cx - lat * (1 - t) + lat * 0.3 * t,
                cy + lat * 0.5 * (1 - t) - lat * 0.5 * t,
                cz + r * 0.6,
            ]
            quat = _quat_from_look(pos, [cx, cy, cz + r * 0.2])
            keyframes.append({
                "t": round(t * duration, 2),
                "pos": [round(v, 3) for v in pos],
                "quat": [round(q, 4) for q in quat],
                "fov": fov,
            })

    elif preset_name == "drone_ascend":
        h_start = r * params["start_height"]
        h_end = r * params["end_height"]
        fov = params["fov"]
        for i in range(nk):
            t = i / (nk - 1)
            pos = [
                cx - r * 2 * (1 - t),
                cy - r * 1.5 * t,
                h_start + (h_end - h_start) * t,
            ]
            quat = _quat_from_look(pos, [cx, cy, cz + r * 0.3])
            keyframes.append({
                "t": round(t * duration, 2),
                "pos": [round(v, 3) for v in pos],
                "quat": [round(q, 4) for q in quat],
                "fov": fov,
            })

    elif preset_name == "hero_tracking":
        d_start = r * params["start_distance"]
        d_end = r * params["end_distance"]
        pitch = math.radians(params["pitch"])
        for i in range(nk):
            t = i / (nk - 1)
            dist = d_start + (d_end - d_start) * t
            pos = [
                cx - dist * math.cos(pitch),
                cy,
                cz + dist * math.sin(-pitch),
            ]
            quat = _quat_from_look(pos, [cx, cy, cz + r * 0.4])
            keyframes.append({
                "t": round(t * duration, 2),
                "pos": [round(v, 3) for v in pos],
                "quat": [round(q, 4) for q in quat],
                "fov": 45,
            })

    elif preset_name == "suspense_pan":
        pan = math.radians(params["pan_angle"])
        fov = params["fov"]
        dist = r * 3.5
        for i in range(nk):
            t = i / (nk - 1)
            angle = -pan / 2 + t * pan
            pos = [
                cx + math.sin(angle) * dist,
                cy - math.cos(angle) * dist,
                cz + r * 0.5,
            ]
            quat = _quat_from_look(pos, [cx, cy, cz + r * 0.3])
            keyframes.append({
                "t": round(t * duration, 2),
                "pos": [round(v, 3) for v in pos],
                "quat": [round(q, 4) for q in quat],
                "fov": fov,
            })

    elif preset_name == "god_eye":
        height = r * params["height_ratio"]
        rot_speed = math.radians(params["rotation_speed"])
        fov = params["fov"]
        for i in range(nk):
            t = i / (nk - 1)
            angle = t * rot_speed
            pos = [
                cx + math.cos(angle) * r * 0.3,
                cy + math.sin(angle) * r * 0.3,
                cz + height,
            ]
            quat = _quat_from_look(pos, [cx, cy, cz])
            keyframes.append({
                "t": round(t * duration, 2),
                "pos": [round(v, 3) for v in pos],
                "quat": [round(q, 4) for q in quat],
                "fov": fov,
            })

    elif preset_name == "whip_pan":
        swing = math.radians(params["swing_angle"])
        fov = params["fov"]
        dist = r * 3
        for i in range(nk):
            t = i / (nk - 1)
            et = t * t * (3 - 2 * t)  # smoothstep
            angle = swing * (et - 0.5)
            pos = [
                cx + math.sin(angle) * dist,
                cy - math.cos(angle) * dist,
                cz + r * 0.5,
            ]
            quat = _quat_from_look(pos, [cx, cy, cz + r * 0.2])
            keyframes.append({
                "t": round(t * duration, 2),
                "pos": [round(v, 3) for v in pos],
                "quat": [round(q, 4) for q in quat],
                "fov": fov,
            })

    return keyframes


def list_presets() -> list[dict]:
    """Return all available preset IDs with name and description."""
    return [
        {"id": k, "name": v["name"], "description": v["description"]}
        for k, v in PRESETS.items()
    ]
