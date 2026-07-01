/**
 * Interactive camera input controller — keyboard + mouse flight.
 *
 * Handles WASD/Space/Ctrl translation, mouse-look, scroll dolly,
 * speed ramping (Shift=slow, Tab/Alt=fast), and speed HUD.
 *
 * Pure Three.js interaction — no recording logic.
 * Guardrail G1: importable without DOM dependency for testing.
 */

// ── Constants ──────────────────────────────────────────────────────────

export const MIN_SPEED = 0.1;
export const MAX_SPEED = 5.0;
export const SPEED_DECEL = 0.4;   // per second while Shift held
export const SPEED_ACCEL = 0.8;   // per second while Tab/Alt held
const MOUSE_SENSITIVITY = 0.002;
const SCROLL_SENSITIVITY = 0.5;
const MOVE_BASE = 3.0;           // units/s at speed=1.0

// ── Internal state ─────────────────────────────────────────────────────

let THREE_NS = null;  // injected via initInput (Three.js namespace)
let camera = null;
let canvas = null;
let keys = {};
let currentSpeed = 1.0;
let isFlying = false;
let hudTimer = 0;

// HUD DOM refs (optional — set by viewport)
let speedValueEl = null;
let speedBarFillEl = null;
let helpEl = null;

// ── Public API ─────────────────────────────────────────────────────────

/**
 * Initialize the input controller.
 *
 * @param {THREE.PerspectiveCamera} cam
 * @param {HTMLCanvasElement} cv
 * @param {object} [opts]
 * @param {object} [opts.THREE]           — Three.js namespace (required, injected by caller)
 * @param {HTMLElement} [opts.speedValueEl]  — DOM element for numeric speed display
 * @param {HTMLElement} [opts.speedBarFillEl] — DOM element for speed bar fill
 * @param {HTMLElement} [opts.helpEl]         — DOM element for controls help overlay
 */
export function initInput(cam, cv, opts = {}) {
    THREE_NS = opts.THREE;
    camera = cam;
    canvas = cv;
    speedValueEl = opts.speedValueEl || null;
    speedBarFillEl = opts.speedBarFillEl || null;
    helpEl = opts.helpEl || null;

    canvas.addEventListener('click', _onCanvasClick);
    document.addEventListener('keydown', _onKeyDown);
    document.addEventListener('keyup', _onKeyUp);
    document.addEventListener('mousemove', _onMouseMove);
    canvas.addEventListener('wheel', _onWheel, { passive: false });
    _updateSpeedHUD();
}

/**
 * Per-frame update. Call from the render loop.
 * @param {number} dt — delta time in seconds
 */
export function updateFlight(dt) {
    if (!isFlying) return;

    // Speed ramp
    if (keys['Shift']) currentSpeed = Math.max(MIN_SPEED, currentSpeed - SPEED_DECEL * dt);
    if (keys['Tab'] || keys['Alt']) currentSpeed = Math.min(MAX_SPEED, currentSpeed + SPEED_ACCEL * dt);
    if (keys['Shift'] || keys['Tab'] || keys['Alt']) {
        hudTimer = 0;
        _updateSpeedHUD();
    }

    // Camera-local directions
    const forward = _getForward();
    const right = _getRight(forward);

    const moveSpeed = currentSpeed * MOVE_BASE;

    // WASD translation (camera-local)
    if (keys['KeyW']) camera.position.addScaledVector(forward, moveSpeed * dt);
    if (keys['KeyS']) camera.position.addScaledVector(forward, -moveSpeed * dt);
    if (keys['KeyA']) camera.position.addScaledVector(right, -moveSpeed * dt);
    if (keys['KeyD']) camera.position.addScaledVector(right, moveSpeed * dt);
    if (keys['Space']) camera.position.y += moveSpeed * dt;
    if (keys['Control']) camera.position.y -= moveSpeed * dt;

    // HUD auto-hide
    hudTimer += dt;
    _tickHUDVisibility();
}

/**
 * Advance HUD auto-hide timer. Call every frame even when not flying.
 * @param {number} dt
 */
export function tickHUD(dt) {
    if (!isFlying) return;
    hudTimer += dt;
    _tickHUDVisibility();
}

/** @returns {boolean} */
export function getIsFlying() {
    return isFlying;
}

/** @returns {number} */
export function getCurrentSpeed() {
    return currentSpeed;
}

/** Release event listeners. */
export function disposeInput() {
    canvas.removeEventListener('click', _onCanvasClick);
    document.removeEventListener('keydown', _onKeyDown);
    document.removeEventListener('keyup', _onKeyUp);
    document.removeEventListener('mousemove', _onMouseMove);
    canvas.removeEventListener('wheel', _onWheel);
}

/**
 * Check whether a "speed modifier" key is currently held.
 * Used by the recorder to decide whether to suppress Tab's browser focus grab.
 * @returns {boolean}
 */
export function isSpeedKeyHeld() {
    return !!(keys['Shift'] || keys['Tab'] || keys['Alt']);
}

// ── Event handlers ─────────────────────────────────────────────────────

function _onCanvasClick(_e) {
    if (!isFlying) {
        canvas.requestPointerLock();
        isFlying = true;
        canvas.classList.add('fly');
        if (helpEl) {
            helpEl.classList.add('visible');
            setTimeout(() => helpEl.classList.remove('visible'), 5000);
        }
    }
}

function _onKeyDown(e) {
    keys[e.code] = true;

    // Prevent browser shortcuts
    if (e.code === 'Tab') e.preventDefault();
    if (e.code === 'Space' && isFlying) e.preventDefault();

    // Exit flight
    if (e.code === 'Escape') {
        document.exitPointerLock();
        isFlying = false;
        canvas.classList.remove('fly');
        if (helpEl) helpEl.classList.remove('visible');
    }

    // Speed HUD on any key press
    if (['Shift', 'Tab', 'Alt'].some(k => e.code === k || e.key === k)) {
        hudTimer = 0;
    }
}

function _onKeyUp(e) {
    keys[e.code] = false;
}

function _onMouseMove(e) {
    if (!isFlying) return;
    const dx = e.movementX * MOUSE_SENSITIVITY;
    const dy = e.movementY * MOUSE_SENSITIVITY;

    // Yaw (around world Y)
    camera.rotateY(-dx);

    // Pitch (around camera-local X), clamped
    const pitchAxis = new THREE_NS.Vector3(1, 0, 0);
    pitchAxis.applyQuaternion(camera.quaternion);
    camera.rotateOnWorldAxis(pitchAxis, -dy);

    // Clamp pitch to avoid flipping
    const euler = new THREE_NS.Euler().setFromQuaternion(camera.quaternion, 'YXZ');
    if (euler.x > Math.PI / 2.2) euler.x = Math.PI / 2.2;
    if (euler.x < -Math.PI / 2.2) euler.x = -Math.PI / 2.2;
    camera.quaternion.setFromEuler(euler);
}

function _onWheel(e) {
    e.preventDefault();
    if (!isFlying) return;
    const forward = _getForward();
    const dollySpeed = currentSpeed * SCROLL_SENSITIVITY;
    camera.position.addScaledVector(forward, e.deltaY > 0 ? dollySpeed : -dollySpeed);
}

// ── Helpers ────────────────────────────────────────────────────────────

function _getForward() {
    const dir = new THREE_NS.Vector3();
    camera.getWorldDirection(dir);
    return dir;
}

function _getRight(forward) {
    const r = new THREE_NS.Vector3();
    r.crossVectors(forward, camera.up).normalize();
    return r;
}

function _updateSpeedHUD() {
    if (speedValueEl) speedValueEl.textContent = currentSpeed.toFixed(1);
    if (speedBarFillEl) {
        const pct = ((currentSpeed - MIN_SPEED) / (MAX_SPEED - MIN_SPEED)) * 100;
        speedBarFillEl.style.width = pct + '%';
    }
}

function _tickHUDVisibility() {
    // Auto-hide after 2s idle on speed keys
    // (placeholder — currently handled by CSS; extend as needed)
}

// NOTE: Three.js namespace is injected via initInput({THREE}) — no static import.
// This keeps the module testable in Node.js without a browser bundle.
