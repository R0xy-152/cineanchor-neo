/**
 * Recording state machine — captures camera pose samples during a take.
 *
 * Pure-JS state machine: NO Three.js, NO DOM imports (Guardrail G1).
 * Accepts a cameraAccessor interface for position/quaternion/fov queries.
 *
 * Interaction model:
 *   start()  → IDLE → RECORDING
 *   pause()  → RECORDING → PAUSED (saves current shot)
 *   resume() → PAUSED → RECORDING (starts new shot)
 *   stop()   → RECORDING/PAUSED → IDLE (fires onStop callback)
 */

// ── State constants ───────────────────────────────────────────────────

const STATE = {
    IDLE: 'IDLE',
    RECORDING: 'RECORDING',
    PAUSED: 'PAUSED',
};

// ── Factory ────────────────────────────────────────────────────────────

/**
 * Create a recorder instance.
 *
 * @param {object} cameraAccessor — { getPosition(): [x,y,z], getQuat(): [x,y,z,w], getFov(): number }
 * @param {object} [options]
 * @param {number} [options.recFps=60] — dense sampling rate (Hz)
 * @returns {object} recorder API
 */
export function createRecorder(cameraAccessor, options = {}) {
    const recFps = options.recFps || 60;
    const recInterval = 1 / recFps;

    let state = STATE.IDLE;
    let elapsed = 0;
    let timeSinceLastSample = 0;
    let shots = [];          // [{ shotIndex, samples: [{t, pos, quat, fov}] }]
    let currentSamples = []; // samples for the current recording segment
    let stopCallback = null;

    // ── State machine ────────────────────────────────────────────────

    function start() {
        if (state !== STATE.IDLE) return;
        state = STATE.RECORDING;
        elapsed = 0;
        timeSinceLastSample = 0;
        currentSamples = [];
    }

    function pause() {
        if (state !== STATE.RECORDING) return;
        state = STATE.PAUSED;
        _commitCurrentShot();
    }

    function resume() {
        if (state !== STATE.PAUSED) return;
        state = STATE.RECORDING;
        currentSamples = [];
    }

    function stop() {
        if (state === STATE.IDLE) return;
        // Commit current samples if recording
        if (currentSamples.length > 0) {
            _commitCurrentShot();
        }
        currentSamples = [];
        state = STATE.IDLE;

        // Fire callback with all shots
        if (stopCallback) {
            stopCallback([...shots]);
        }
    }

    // ── Per-frame tick ────────────────────────────────────────────────

    /**
     * Call every frame with delta time in seconds.
     * Automatically samples at recFps rate when RECORDING.
     * @param {number} dt — delta time in seconds
     */
    function tick(dt) {
        if (state !== STATE.RECORDING) return;

        elapsed += dt;
        timeSinceLastSample += dt;

        // Sample at the recording rate
        while (timeSinceLastSample >= recInterval) {
            timeSinceLastSample -= recInterval;
            const sampleTime = elapsed - timeSinceLastSample;
            currentSamples.push({
                t: sampleTime,
                pos: cameraAccessor.getPosition(),
                quat: cameraAccessor.getQuat(),
                fov: cameraAccessor.getFov(),
            });
        }
    }

    // ── Callbacks ─────────────────────────────────────────────────────

    function onStop(cb) {
        stopCallback = cb;
    }

    // ── Queries ───────────────────────────────────────────────────────

    function getState() {
        return state;
    }

    function getShots() {
        return [...shots];
    }

    function getElapsed() {
        return elapsed;
    }

    // ── Internal ──────────────────────────────────────────────────────

    function _commitCurrentShot() {
        if (currentSamples.length > 0) {
            shots.push({
                shotIndex: shots.length,
                samples: [...currentSamples],
            });
        }
        currentSamples = [];
    }

    // ── Public API ────────────────────────────────────────────────────

    return {
        start,
        pause,
        resume,
        stop,
        tick,
        onStop,
        getState,
        getShots,
        getElapsed,
    };
}
