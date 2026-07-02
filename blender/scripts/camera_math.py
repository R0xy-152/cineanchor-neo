"""Camera trajectory interpolation engine.

Pure-Python math library — MUST NOT import bpy or any Blender module.
ADJ-5: tested without the Blender environment.

Ported from D:\\CineAnchor\\cineanchor\\core\\coordinate.py.
"""

from __future__ import annotations

import math


def catmull_rom(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
    """Catmull-Rom interpolation (4-point) — C¹ continuous, smooth velocity.

    Used for Euclidean quantities: position components, Euler angles, FOV.
    """
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2 * p1)
        + (-p0 + p2) * t
        + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
        + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
    )


def catmull_rom_vec(
    v0: list[float], v1: list[float], v2: list[float], v3: list[float], t: float,
) -> list[float]:
    """Catmull-Rom per-component over equal-length vectors."""
    return [catmull_rom(v0[i], v1[i], v2[i], v3[i], t) for i in range(len(v0))]


def slerp(q0: list[float], q1: list[float], t: float) -> list[float]:
    """Spherical linear interpolation — constant angular velocity.

    - dot < 0: takes the short path (q and -q represent the same rotation).
    - dot > 0.9995: near-parallel fallback to LERP + renormalise (avoids
      acos numerical instability).
    - Per-element Catmull-Rom on quaternions would break unit length and
      produce uneven rotational speed — SLERP is required.
    """
    dot = q0[0] * q1[0] + q0[1] * q1[1] + q0[2] * q1[2] + q0[3] * q1[3]

    # Short-path flip
    if dot < 0:
        q1 = [-v for v in q1]
        dot = -dot

    # Near-parallel → degenerate to LERP
    if dot > 0.9995:
        result = [q0[i] + t * (q1[i] - q0[i]) for i in range(4)]
        length = math.sqrt(sum(v * v for v in result))
        if length < 1e-12:
            return q0[:]
        return [v / length for v in result]

    theta_0 = math.acos(dot)
    sin_theta_0 = math.sin(theta_0)
    s0 = math.sin((1 - t) * theta_0) / sin_theta_0
    s1 = math.sin(t * theta_0) / sin_theta_0
    return [s0 * q0[i] + s1 * q1[i] for i in range(4)]


def interpolate_keyframes(
    keyframes: list[dict],
    fps: int,
) -> list[dict]:
    """Interpolate keyframes into per-frame pose data.

    Position → Catmull-Rom (C¹ continuous, passes through all control points).
    Quaternion → SLERP (constant angular velocity, always unit quaternion).
    FOV → Catmull-Rom (scalar).
    Optional target → Catmull-Rom per-component if all 4 control KFs have it.

    Returns one dict per frame: ``{"t", "pos", "quat", "fov"[, "target"]}``.
    """
    if len(keyframes) < 2:
        return keyframes

    total_duration = keyframes[-1]["t"]
    total_frames = max(int(total_duration * fps), 1)

    frames: list[dict] = []
    for fi in range(total_frames + 1):
        t = fi / fps

        # Find the segment [idx, idx+1] that contains t
        idx = 0
        for i, kf in enumerate(keyframes):
            if kf["t"] <= t:
                idx = i
            else:
                break

        if idx >= len(keyframes) - 1:
            kf = keyframes[-1]
            frame: dict = {
                "t": t,
                "pos": list(kf["pos"]),
                "quat": list(kf["quat"]),
                "fov": kf.get("fov", 55),
            }
            if "target" in kf:
                frame["target"] = list(kf["target"])
            frames.append(frame)
            continue

        # Build 4-point window around the segment.
        # Hard-cut gate: never let k0/k3 cross a cut boundary (§4.2 / R5).
        # When keyframes[idx] has cut=true, it starts a new shot —
        #   k0 must be k1 (the pre-cut KF is in a different shot).
        # When keyframes[idx+1] has cut=true, it ends a shot —
        #   k3 must be k2 (the post-cut KF is in a different shot).
        if idx > 0 and keyframes[idx].get("cut"):
            k0 = keyframes[idx]
        else:
            k0 = keyframes[max(0, idx - 1)]
        k1 = keyframes[idx]
        k2 = keyframes[min(len(keyframes) - 1, idx + 1)]
        if idx + 2 < len(keyframes) and keyframes[idx + 1].get("cut"):
            k3 = keyframes[idx + 1]
        else:
            k3 = keyframes[min(len(keyframes) - 1, idx + 2)]

        seg_start = k1["t"]
        seg_end = k2["t"]
        seg_duration = seg_end - seg_start
        local_t = 0.0 if seg_duration < 0.001 else (t - seg_start) / seg_duration

        pos = catmull_rom_vec(k0["pos"], k1["pos"], k2["pos"], k3["pos"], local_t)
        quat = slerp(k1["quat"], k2["quat"], local_t)

        fov = catmull_rom(
            k0.get("fov", 55),
            k1.get("fov", 55),
            k2.get("fov", 55),
            k3.get("fov", 55),
            local_t,
        )

        frame = {"t": t, "pos": pos, "quat": quat, "fov": fov}

        target: list[float] | None = None
        if all("target" in k for k in (k0, k1, k2, k3)):
            target = catmull_rom_vec(
                k0["target"], k1["target"], k2["target"], k3["target"], local_t,
            )
        if target is not None:
            frame["target"] = target
        frames.append(frame)

    return frames


def three_to_blender_pose(
    three_pos: list[float],
    three_target: list[float],
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Convert Three.js (Y-up) pose to Blender (Z-up).

    Three.js: +Y = up, -Z = forward.
    Blender:  +Z = up, -Y = forward.
    """
    bx, by, bz = three_pos[0], -three_pos[2], three_pos[1]
    tx, ty, tz = three_target[0], -three_target[2], three_target[1]
    return (bx, by, bz), (tx, ty, tz)


def target_from_quat(
    three_pos: list[float],
    three_quat: list[float],
    target_dist: float = 5.0,
) -> list[float]:
    """Estimate a look-at target from a Three.js camera quaternion.

    Useful when legacy data has quaternion but no target field.
    Converts quaternion → rotation matrix forward column → target along -Z.
    """
    qx, qy, qz, qw = three_quat
    fx = -2 * (qx * qz + qw * qy)
    fy = -2 * (qy * qz - qw * qx)
    fz = -1 + 2 * (qx * qx + qy * qy)
    flen = math.sqrt(fx * fx + fy * fy + fz * fz)
    if flen < 0.001:
        return [three_pos[0], three_pos[1], three_pos[2] - target_dist]
    return [
        three_pos[0] + fx / flen * target_dist,
        three_pos[1] + fy / flen * target_dist,
        three_pos[2] + fz / flen * target_dist,
    ]
