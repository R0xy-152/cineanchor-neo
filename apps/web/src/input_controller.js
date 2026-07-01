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
let skipNextMouseMove = false;  // guard against Pointer Lock garbage event
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

    const moveSpeed = currentSpeed * MOVE_BASE * dt;

    // Camera-local translation using Three.js built-in methods.
    // translateX/Y/Z move along the camera's LOCAL axes, correctly
    // handling any combination of pitch, yaw, and roll.
    // Camera looks along -Z: translateZ(-d)=forward, translateZ(+d)=backward
    //                       translateX(+d)=right,   translateX(-d)=left
    if (keys['KeyW']) camera.translateZ(-moveSpeed);
    if (keys['KeyS']) camera.translateZ(moveSpeed);
    if (keys['KeyA']) camera.translateX(-moveSpeed);
    if (keys['KeyD']) camera.translateX(moveSpeed);
    if (keys['Space']) camera.translateY(moveSpeed);
    if (keys['Control']) camera.translateY(-moveSpeed);

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
        armPointerLockGuard();   // must be BEFORE requestPointerLock
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

// Guard: reject spurious mousemove events from pointer-lock engagement.
// Some browsers fire a single mousemove with garbage movementX/Y (often
// ±hundreds of pixels) when Pointer Lock first activates.
let _pointerLockArmed = false;
let _firstMouseSkipped = false;

// Exported so viewport can call it right AFTER requestPointerLock resolves.
export function armPointerLockGuard() {
    _pointerLockArmed = true;
    _firstMouseSkipped = false;
}

function _onMouseMove(e) {
    if (!isFlying) return;

    // Skip the first mousemove after pointer-lock engage — it may carry
    // garbage movementX/Y from the cursor teleport, not real user input.
    if (_pointerLockArmed && !_firstMouseSkipped) {
        _firstMouseSkipped = true;
        console.log('[input] skipped first mousemove after pointer lock',
                    'movementX=', e.movementX, 'movementY=', e.movementY);
        return;
    }

    const dx = e.movementX * MOUSE_SENSITIVITY;
    const dy = e.movementY * MOUSE_SENSITIVITY;

    // Yaw around WORLD Y axis — critical: use world axis, not local Y
    // (local Y tilts after pitch, causing roll accumulation and WASD drift)
    const worldUp = new THREE_NS.Vector3(0, 1, 0);
    camera.rotateOnWorldAxis(worldUp, -dx);

    // Pitch around camera-local X axis (before clamping, for responsive feel)
    const pitchAxis = new THREE_NS.Vector3(1, 0, 0);
    pitchAxis.applyQuaternion(camera.quaternion);
    camera.rotateOnWorldAxis(pitchAxis, -dy);

    // ── Geometric pitch clamp ────────────────────────────────────────
    // Instead of Euler YXZ decomposition (which can flip yaw/roll at
    // extreme pitch), clamp geometrically: measure the angle of the
    // camera's look direction relative to the horizontal plane, and
    // rotate around the camera's local X axis to stay within limits.
    const _lookDir = new THREE_NS.Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
    const MAX_PITCH = Math.PI * 0.45;  // ~81°
    const geoPitch = Math.asin(_lookDir.y);  // angle above horizontal

    if (geoPitch > MAX_PITCH) {
        // Tilt down: positive rotation around local X
        const _localX = new THREE_NS.Vector3(1, 0, 0).applyQuaternion(camera.quaternion);
        camera.rotateOnWorldAxis(_localX, geoPitch - MAX_PITCH);
    } else if (geoPitch < -MAX_PITCH) {
        // Tilt up: negative rotation around local X
        const _localX = new THREE_NS.Vector3(1, 0, 0).applyQuaternion(camera.quaternion);
        camera.rotateOnWorldAxis(_localX, geoPitch + MAX_PITCH);
    }
}

function _onWheel(e) {
    e.preventDefault();
    if (!isFlying) return;
    const dollySpeed = currentSpeed * SCROLL_SENSITIVITY;
    // translateZ(-d) = forward (scroll up = dolly in), translateZ(+d) = backward
    camera.translateZ(e.deltaY > 0 ? dollySpeed : -dollySpeed);
}

// ── Movement: use camera.translateX/Y/Z (Three.js built-in, battle-tested) ──
// This is the same approach used by PointerLockControls — it moves the camera
// along its LOCAL axes, which correctly accounts for pitch, yaw, and any roll.
//
// translateX(+d) = right,  translateX(-d) = left
// translateY(+d) = up,     translateY(-d) = down
// translateZ(-d) = forward, translateZ(+d) = backward
//   (camera looks along -Z in local space)

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
