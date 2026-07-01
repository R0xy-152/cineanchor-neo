/**
 * Camera preset library — cinematic camera moves.
 *
 * Generates keyframe lists from named presets + scene parameters.
 * Uses camera_math for interpolation (pure JS, no rendering dependency).
 *
 * Presets are demo/validation material — not a committed product feature.
 * Ported from blender/scripts/camera_presets.py.
 */

import { interpolateKeyframes } from './camera_math.js';

/**
 * Generate a quaternion (x, y, z, w) from camera position and look-at target.
 * Default up=(0, 0, 1) is Blender Z-up.
 */
export function quatFromLook(pos, target, up = [0, 0, 1]) {
    const dx = target[0] - pos[0];
    const dy = target[1] - pos[1];
    const dz = target[2] - pos[2];
    const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
    if (dist < 1e-6) {
        return [0, 0, 0, 1];
    }

    const forward = [dx / dist, dy / dist, dz / dist];
    const [ux, uy, uz] = up;

    // Right = forward × up
    let rx = forward[1] * uz - forward[2] * uy;
    let ry = forward[2] * ux - forward[0] * uz;
    let rz = forward[0] * uy - forward[1] * ux;
    const rlen = Math.sqrt(rx * rx + ry * ry + rz * rz);
    if (rlen < 1e-6) {
        rx = 1; ry = 0; rz = 0;
    } else {
        rx /= rlen; ry /= rlen; rz /= rlen;
    }

    // Up = right × forward
    const ux2 = ry * forward[2] - rz * forward[1];
    const uy2 = rz * forward[0] - rx * forward[2];
    const uz2 = rx * forward[1] - ry * forward[0];

    // Build quaternion from the 3×3 rotation matrix columns: right, up, -forward
    const nfx = -forward[0];
    const nfy = -forward[1];
    const nfz = -forward[2];

    const trace = rx + uy2 - nfz;
    const EPS = 1e-10;

    let qx, qy, qz, qw;

    if (trace > 0) {
        const s = Math.max(Math.sqrt(trace + 1) * 2, EPS);
        qw = 0.25 * s;
        qx = (uz2 + nfy) / s;
        qy = (nfx + rz) / s;
        qz = (ry - rx) / s;
    } else if (rx > uy2 && rx > -nfz) {
        const s = Math.max(Math.sqrt(1 + rx - uy2 + nfz) * 2, EPS);
        qw = (uz2 + nfy) / s;
        qx = 0.25 * s;
        qy = (rx + ry) / s;
        qz = (nfx + rz) / s;
    } else if (uy2 > -nfz) {
        const s = Math.max(Math.sqrt(1 + uy2 - rx + nfz) * 2, EPS);
        qw = (nfx + rz) / s;
        qx = (rx + ry) / s;
        qy = 0.25 * s;
        qz = (uz2 + nfy) / s;
    } else {
        const s = Math.max(Math.sqrt(1 + nfz + rx + uy2) * 2, EPS);
        qw = (ry - rx) / s;
        qx = (nfx + rz) / s;
        qy = (uz2 + nfy) / s;
        qz = 0.25 * s;
    }

    const qnorm = Math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw);
    return [qx / qnorm, qy / qnorm, qz / qnorm, qw / qnorm];
}

// ── Preset registry ────────────────────────────────────────────────────

export const PRESETS = {
    "nolan_orbit": {
        name: "Nolan Orbit",
        description: "环绕主体 180°, 低角度仰拍, 缓慢推进",
        params: { orbit_angle: 180, pitch: -15, distance_ratio: 1.2, duration: 6 },
    },
    "anime_closeup": {
        name: "Anime Close-up",
        description: "快速推近主体, 微幅晃动, 浅景深特写",
        params: { start_distance: 8, end_distance: 2, fov_start: 45, fov_end: 35, duration: 3 },
    },
    "dolly_reveal": {
        name: "Dolly Reveal",
        description: "侧向平移, 主体逐渐入画, 广角",
        params: { lateral_distance: 10, fov: 70, duration: 5 },
    },
    "drone_ascend": {
        name: "Drone Ascend",
        description: "从地面升到鸟瞰, 向下俯拍, 广角",
        params: { start_height: 1.5, end_height: 15, fov: 60, duration: 8 },
    },
    "hero_tracking": {
        name: "Hero Tracking",
        description: "从主体前方低角度跟拍, 后退拉开揭示环境",
        params: { start_distance: 3, end_distance: 7, pitch: -10, duration: 5 },
    },
    "suspense_pan": {
        name: "Suspense Pan",
        description: "缓慢水平横扫, 悬疑感, 长焦",
        params: { pan_angle: 90, fov: 35, duration: 7 },
    },
    "god_eye": {
        name: "God's Eye",
        description: "极高鸟瞰, 极慢自转, 全景",
        params: { height_ratio: 6, rotation_speed: 20, fov: 50, duration: 10 },
    },
    "whip_pan": {
        name: "Whip Pan",
        description: "快速甩镜, 90° 急转视线方向",
        params: { swing_angle: 90, fov: 55, duration: 1.5 },
    },
};

const DEG = Math.PI / 180;

// ── Preset application ──────────────────────────────────────────────────

/**
 * Generate keyframes for a named preset around a scene subject.
 *
 * @param {string} presetName - One of the 8 preset IDs.
 * @param {number[]} sceneCenter - [cx, cy, cz] world-space center of the subject.
 * @param {number} sceneRadius - Approximate visible radius of the subject.
 * @param {number|null} numKeyframes - Override default keyframe count.
 * @returns {Array<{t: number, pos: number[], quat: number[], fov: number}>}
 */
export function applyPreset(presetName, sceneCenter, sceneRadius, numKeyframes = null) {
    if (!(presetName in PRESETS)) {
        throw new Error(
            `Unknown preset '${presetName}'. Available: ${Object.keys(PRESETS).join(', ')}`
        );
    }

    const preset = PRESETS[presetName];
    const params = preset.params;
    const duration = params.duration ?? 5;
    const nk = numKeyframes || Math.max(3, duration * 2);
    const [cx, cy, cz] = sceneCenter;
    const r = sceneRadius;
    const keyframes = [];

    function makeKF(t, pos, quat, fov) {
        return {
            t: Math.round(t * duration * 100) / 100,
            pos: pos.map(v => Math.round(v * 1000) / 1000),
            quat: quat.map(v => Math.round(v * 10000) / 10000),
            fov: typeof fov === 'number' && fov % 1 !== 0 ? Math.round(fov * 10) / 10 : fov,
        };
    }

    for (let i = 0; i < nk; i++) {
        const t = i / (nk - 1);
        let pos, quat, fov;

        switch (presetName) {
            case "nolan_orbit": {
                const orbit = params.orbit_angle * DEG;
                const pitch = params.pitch * DEG;
                const dist = r * params.distance_ratio;
                const angle = Math.PI / 2 - orbit / 2 + t * orbit;
                pos = [
                    cx + Math.cos(angle) * dist,
                    cy + Math.sin(angle) * dist,
                    cz + Math.sin(pitch) * dist,
                ];
                quat = quatFromLook(pos, [cx, cy, cz * 0.7]);
                fov = 50;
                break;
            }
            case "anime_closeup": {
                const dStart = r * params.start_distance;
                const dEnd = r * params.end_distance;
                const et = t * t * (3 - 2 * t); // smoothstep
                const dist = dStart + (dEnd - dStart) * et;
                const wobble = Math.sin(t * 7) * 0.15 * r * (1 - t);
                pos = [cx - dist, cy + wobble, cz + r * 0.4];
                quat = quatFromLook(pos, [cx, cy, cz + r * 0.3]);
                fov = params.fov_start + (params.fov_end - params.fov_start) * t;
                break;
            }
            case "dolly_reveal": {
                const lat = r * params.lateral_distance;
                pos = [
                    cx - lat * (1 - t) + lat * 0.3 * t,
                    cy + lat * 0.5 * (1 - t) - lat * 0.5 * t,
                    cz + r * 0.6,
                ];
                quat = quatFromLook(pos, [cx, cy, cz + r * 0.2]);
                fov = params.fov;
                break;
            }
            case "drone_ascend": {
                const hStart = r * params.start_height;
                const hEnd = r * params.end_height;
                pos = [
                    cx - r * 2 * (1 - t),
                    cy - r * 1.5 * t,
                    hStart + (hEnd - hStart) * t,
                ];
                quat = quatFromLook(pos, [cx, cy, cz + r * 0.3]);
                fov = params.fov;
                break;
            }
            case "hero_tracking": {
                const dStart = r * params.start_distance;
                const dEnd = r * params.end_distance;
                const pitch = params.pitch * DEG;
                const dist = dStart + (dEnd - dStart) * t;
                pos = [
                    cx - dist * Math.cos(pitch),
                    cy,
                    cz + dist * Math.sin(-pitch),
                ];
                quat = quatFromLook(pos, [cx, cy, cz + r * 0.4]);
                fov = 45;
                break;
            }
            case "suspense_pan": {
                const pan = params.pan_angle * DEG;
                const dist = r * 3.5;
                const angle = -pan / 2 + t * pan;
                pos = [
                    cx + Math.sin(angle) * dist,
                    cy - Math.cos(angle) * dist,
                    cz + r * 0.5,
                ];
                quat = quatFromLook(pos, [cx, cy, cz + r * 0.3]);
                fov = params.fov;
                break;
            }
            case "god_eye": {
                const height = r * params.height_ratio;
                const rotSpeed = params.rotation_speed * DEG;
                const angle = t * rotSpeed;
                pos = [
                    cx + Math.cos(angle) * r * 0.3,
                    cy + Math.sin(angle) * r * 0.3,
                    cz + height,
                ];
                quat = quatFromLook(pos, [cx, cy, cz]);
                fov = params.fov;
                break;
            }
            case "whip_pan": {
                const swing = params.swing_angle * DEG;
                const dist = r * 3;
                const et = t * t * (3 - 2 * t); // smoothstep
                const angle = swing * (et - 0.5);
                pos = [
                    cx + Math.sin(angle) * dist,
                    cy - Math.cos(angle) * dist,
                    cz + r * 0.5,
                ];
                quat = quatFromLook(pos, [cx, cy, cz + r * 0.2]);
                fov = params.fov;
                break;
            }
        }

        keyframes.push(makeKF(t, pos, quat, fov));
    }

    return keyframes;
}

/**
 * Return all available preset IDs with name and description.
 * @returns {Array<{id: string, name: string, description: string}>}
 */
export function listPresets() {
    return Object.entries(PRESETS).map(([id, v]) => ({
        id,
        name: v.name,
        description: v.description,
    }));
}
