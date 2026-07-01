/**
 * Camera trajectory interpolation engine.
 *
 * Pure-JS math library — MUST NOT import Three.js, DOM, or any rendering module.
 * Ported from blender/scripts/camera_math.py.
 * Guardrail G1: testable headless without a browser.
 *
 * All functions match their Python counterparts exactly.
 */

/**
 * Catmull-Rom interpolation (4-point) — C¹ continuous, smooth velocity.
 * Used for Euclidean quantities: position components, Euler angles, FOV.
 */
export function catmullRom(p0, p1, p2, p3, t) {
    const t2 = t * t;
    const t3 = t2 * t;
    return 0.5 * (
        (2 * p1)
        + (-p0 + p2) * t
        + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
        + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
    );
}

/**
 * Catmull-Rom per-component over equal-length vectors.
 */
export function catmullRomVec(v0, v1, v2, v3, t) {
    return v0.map((_, i) => catmullRom(v0[i], v1[i], v2[i], v3[i], t));
}

/**
 * Spherical linear interpolation — constant angular velocity.
 *
 * - dot < 0: takes the short path (q and -q represent the same rotation).
 * - dot > 0.9995: near-parallel fallback to LERP + renormalise (avoids
 *   acos numerical instability).
 */
export function slerp(q0, q1, t) {
    let dot = q0[0] * q1[0] + q0[1] * q1[1] + q0[2] * q1[2] + q0[3] * q1[3];

    // Short-path flip
    let q1Adj = q1;
    if (dot < 0) {
        q1Adj = q1.map(v => -v);
        dot = -dot;
    }

    // Near-parallel → degenerate to LERP
    if (dot > 0.9995) {
        const result = q0.map((v, i) => v + t * (q1Adj[i] - v));
        const length = Math.sqrt(result.reduce((s, v) => s + v * v, 0));
        if (length < 1e-12) {
            return [...q0];
        }
        return result.map(v => v / length);
    }

    const theta0 = Math.acos(dot);
    const sinTheta0 = Math.sin(theta0);
    const s0 = Math.sin((1 - t) * theta0) / sinTheta0;
    const s1 = Math.sin(t * theta0) / sinTheta0;
    return q0.map((v, i) => s0 * v + s1 * q1Adj[i]);
}

/**
 * Interpolate keyframes into per-frame pose data.
 *
 * Position → Catmull-Rom (C¹ continuous, passes through all control points).
 * Quaternion → SLERP (constant angular velocity, always unit quaternion).
 * FOV → Catmull-Rom (scalar).
 * Optional target → Catmull-Rom per-component if all 4 control KFs have it.
 *
 * @param {Array<{t: number, pos: number[], quat: number[], fov?: number, target?: number[]}>} keyframes
 * @param {number} fps
 * @returns {Array<{t: number, pos: number[], quat: number[], fov: number, target?: number[]}>}
 */
export function interpolateKeyframes(keyframes, fps) {
    if (keyframes.length < 2) {
        return keyframes;
    }

    const totalDuration = keyframes[keyframes.length - 1].t;
    const totalFrames = Math.max(Math.floor(totalDuration * fps), 1);
    const frames = [];

    for (let fi = 0; fi <= totalFrames; fi++) {
        const t = fi / fps;

        // Find the segment [idx, idx+1] that contains t
        let idx = 0;
        for (let i = 0; i < keyframes.length; i++) {
            if (keyframes[i].t <= t) {
                idx = i;
            } else {
                break;
            }
        }

        if (idx >= keyframes.length - 1) {
            const kf = keyframes[keyframes.length - 1];
            const frame = {
                t,
                pos: [...kf.pos],
                quat: [...kf.quat],
                fov: kf.fov ?? 55,
            };
            if (kf.target !== undefined) {
                frame.target = [...kf.target];
            }
            frames.push(frame);
            continue;
        }

        // Build 4-point window around the segment.
        // Hard-cut gate: never let k0/k3 cross a cut boundary (R5).
        // When keyframes[idx] has cut=true, it starts a new shot —
        //   k0 must be k1 (the pre-cut KF is in a different shot).
        // When keyframes[idx+1] has cut=true, it ends a shot —
        //   k3 must be k2 (the post-cut KF is in a different shot).
        let k0;
        if (idx > 0 && keyframes[idx].cut) {
            k0 = keyframes[idx];
        } else {
            k0 = keyframes[Math.max(0, idx - 1)];
        }
        const k1 = keyframes[idx];
        const k2 = keyframes[Math.min(keyframes.length - 1, idx + 1)];
        let k3;
        if (idx + 2 < keyframes.length && keyframes[idx + 1].cut) {
            k3 = keyframes[idx + 1];
        } else {
            k3 = keyframes[Math.min(keyframes.length - 1, idx + 2)];
        }

        const segStart = k1.t;
        const segEnd = k2.t;
        const segDuration = segEnd - segStart;
        const localT = segDuration < 0.001 ? 0.0 : (t - segStart) / segDuration;

        const pos = catmullRomVec(k0.pos, k1.pos, k2.pos, k3.pos, localT);
        const quat = slerp(k1.quat, k2.quat, localT);

        const fov = catmullRom(
            k0.fov ?? 55,
            k1.fov ?? 55,
            k2.fov ?? 55,
            k3.fov ?? 55,
            localT,
        );

        const frame = { t, pos, quat, fov };

        // Target: only interpolate if all four window KFs have it
        const allHaveTarget = [k0, k1, k2, k3].every(k => k.target !== undefined);
        if (allHaveTarget) {
            frame.target = catmullRomVec(k0.target, k1.target, k2.target, k3.target, localT);
        }
        frames.push(frame);
    }

    return frames;
}

/**
 * Convert Three.js (Y-up) pose to Blender (Z-up).
 *
 * Three.js: +Y = up, -Z = forward.
 * Blender:  +Z = up, -Y = forward.
 *
 * @returns {[number[], number[]]} [blenderPos, blenderTarget]
 */
export function threeToBlenderPose(threePos, threeTarget) {
    const bx = threePos[0];
    const by = -threePos[2];
    const bz = threePos[1];
    const tx = threeTarget[0];
    const ty = -threeTarget[2];
    const tz = threeTarget[1];
    return [[bx, by, bz], [tx, ty, tz]];
}

/**
 * Estimate a look-at target from a Three.js camera quaternion.
 *
 * Useful when legacy data has quaternion but no target field.
 * Converts quaternion → rotation matrix forward column → target along -Z.
 */
export function targetFromQuat(threePos, threeQuat, targetDist = 5.0) {
    const [qx, qy, qz, qw] = threeQuat;
    const fx = -2 * (qx * qz + qw * qy);
    const fy = -2 * (qy * qz - qw * qx);
    const fz = -1 + 2 * (qx * qx + qy * qy);
    const flen = Math.sqrt(fx * fx + fy * fy + fz * fz);
    if (flen < 0.001) {
        return [threePos[0], threePos[1], threePos[2] - targetDist];
    }
    return [
        threePos[0] + (fx / flen) * targetDist,
        threePos[1] + (fy / flen) * targetDist,
        threePos[2] + (fz / flen) * targetDist,
    ];
}
