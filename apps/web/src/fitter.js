/**
 * Keyframe fitter — dense samples → sparse keyframes.
 *
 * Pure-function library: NO Three.js, NO DOM imports (Guardrail G1).
 * Algorithm: RDP (Ramer-Douglas-Peucker) for position + angle filter for quaternion.
 *
 * The fitter converts dense per-frame recording samples into a minimal set of
 * Catmull-Rom + SLERP keyframes that re-interpolate to within tolerance of the
 * original path. This keeps JSON sparse, diffable, and versionable (moat T3).
 */

// ── RDP (Ramer-Douglas-Peucker) ──────────────────────────────────────

/**
 * Simplify a point sequence using RDP.
 *
 * @param {Array<{t: number, pos: number[]}>} points  — samples with t and position
 * @param {number} epsilon  — maximum allowable perpendicular distance
 * @returns {number[]} indices into `points` of retained key positions
 */
export function rdpSimplify(points, epsilon) {
    if (points.length <= 2) {
        return points.map((_, i) => i);
    }

    // Find point with maximum distance from line segment (first → last)
    const first = points[0].pos;
    const last = points[points.length - 1].pos;
    const segLen = _dist(first, last);

    let maxDist = 0;
    let maxIdx = 0;

    for (let i = 1; i < points.length - 1; i++) {
        const d = segLen < 1e-10
            ? _dist(points[i].pos, first)
            : _perpendicularDist(points[i].pos, first, last, segLen);
        if (d > maxDist) {
            maxDist = d;
            maxIdx = i;
        }
    }

    if (maxDist <= epsilon) {
        return [0, points.length - 1];
    }

    // Recursively simplify both sides
    const left = rdpSimplify(points.slice(0, maxIdx + 1), epsilon);
    const right = rdpSimplify(points.slice(maxIdx), epsilon);

    // Merge, avoiding duplicate at the split point
    return [...left.slice(0, -1), ...right.map(i => i + maxIdx)];
}

// ── Angle filter ─────────────────────────────────────────────────────

/**
 * Insert extra keyframes where quaternion rotation angle exceeds threshold
 * between consecutive RDP-retained samples.
 *
 * @param {Array<{t: number, pos: number[], quat: number[]}>} allSamples
 * @param {number[]} retainedIndices  — indices from RDP
 * @param {number} angleEpsilon  — radians
 * @returns {number[]} augmented index set
 */
export function angleFilter(allSamples, retainedIndices, angleEpsilon) {
    const result = [retainedIndices[0]];

    for (let i = 0; i < retainedIndices.length - 1; i++) {
        const a = allSamples[retainedIndices[i]];
        const b = allSamples[retainedIndices[i + 1]];
        const angle = _quatAngle(a.quat, b.quat);

        if (angle > angleEpsilon) {
            // Insert the sample between a and b with the largest angle deviation
            const mid = _findMaxAngleSample(allSamples, retainedIndices[i], retainedIndices[i + 1]);
            if (mid !== retainedIndices[i] && mid !== retainedIndices[i + 1]) {
                result.push(mid);
            }
        }
        result.push(retainedIndices[i + 1]);
    }

    // Sort and deduplicate
    return [...new Set(result)].sort((a, b) => a - b);
}

// ── Main entry ───────────────────────────────────────────────────────

/**
 * Fit dense recording samples into sparse keyframes.
 *
 * @param {Array<{shotIndex: number, samples: Array}>} shots  — recorded shots
 * @param {Array} currentSamples  — samples of the in-progress shot (may be empty)
 * @param {object} [opts]
 * @param {number} [opts.posEpsilon=0.1]  — position tolerance for RDP
 * @param {number} [opts.angleEpsilon=0.05]  — angle tolerance in radians for quaternion
 * @returns {Array<{index: number, cut: boolean, keyframes: Array}>}
 */
export function fitSamples(shots, currentSamples, opts = {}) {
    const posEpsilon = opts.posEpsilon ?? 0.1;
    const angleEpsilon = opts.angleEpsilon ?? 0.05;

    const allShots = [...shots];
    if (currentSamples.length > 0) {
        allShots.push({ shotIndex: allShots.length, samples: [...currentSamples] });
    }

    return allShots.map((shot, shotIdx) => {
        const samples = shot.samples;
        if (samples.length <= 2) {
            return {
                index: shot.shotIndex,
                cut: shotIdx < allShots.length - 1,
                keyframes: convertToKeyframeFormat(samples, shotIdx < allShots.length - 1),
            };
        }

        // RDP position simplification
        const retained = rdpSimplify(samples, posEpsilon);

        // Angle filter on quaternions
        const withAngles = angleFilter(samples, retained, angleEpsilon);

        // Extract the retained samples as keyframes
        const keyframes = convertToKeyframeFormat(
            withAngles.map(i => samples[i]),
            shotIdx < allShots.length - 1,
        );

        return {
            index: shot.shotIndex,
            cut: shotIdx < allShots.length - 1,
            keyframes,
        };
    });
}

// ── Serialization ────────────────────────────────────────────────────

/**
 * Convert raw samples to the canonical keyframe format.
 * Rounds values to reasonable precision for JSON compactness.
 *
 * @param {Array<{t: number, pos: number[], quat: number[], fov: number}>} samples
 * @param {boolean} [lastHasCut=false] — mark the last keyframe with cut:true
 * @returns {Array<{t: number, pos: number[], quat: number[], fov: number, cut?: boolean}>}
 */
export function convertToKeyframeFormat(samples, lastHasCut = false) {
    return samples.map((s, i) => {
        const kf = {
            t: Math.round(s.t * 100) / 100,
            pos: s.pos.map(v => Math.round(v * 1000) / 1000),
            quat: s.quat.map(v => Math.round(v * 10000) / 10000),
            fov: Math.round(s.fov * 10) / 10,
        };
        if (lastHasCut && i === samples.length - 1) {
            kf.cut = true;
        }
        return kf;
    });
}

// ── Math helpers (pure, no external deps) ─────────────────────────────

function _dist(a, b) {
    const dx = a[0] - b[0];
    const dy = a[1] - b[1];
    const dz = a[2] - b[2];
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

function _perpendicularDist(p, a, b, segLen) {
    // Point-to-line distance in 3D
    const cross = [
        (p[1] - a[1]) * (p[2] - b[2]) - (p[2] - a[2]) * (p[1] - b[1]),
        (p[2] - a[2]) * (p[0] - b[0]) - (p[0] - a[0]) * (p[2] - b[2]),
        (p[0] - a[0]) * (p[1] - b[1]) - (p[1] - a[1]) * (p[0] - b[0]),
    ];
    return Math.sqrt(cross[0] * cross[0] + cross[1] * cross[1] + cross[2] * cross[2]) / segLen;
}

function _quatDot(qa, qb) {
    return Math.abs(qa[0] * qb[0] + qa[1] * qb[1] + qa[2] * qb[2] + qa[3] * qb[3]);
}

function _quatAngle(qa, qb) {
    const dot = Math.min(_quatDot(qa, qb), 1.0);
    return 2 * Math.acos(dot);
}

function _findMaxAngleSample(samples, startIdx, endIdx) {
    const qStart = samples[startIdx].quat;
    let maxAngle = 0;
    let maxIdx = startIdx;

    for (let i = startIdx + 1; i <= endIdx; i++) {
        const angle = _quatAngle(qStart, samples[i].quat);
        if (angle > maxAngle) {
            maxAngle = angle;
            maxIdx = i;
        }
    }

    return maxAngle === startIdx ? startIdx : maxIdx;
}
