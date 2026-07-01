/**
 * CineAnchor Interactive Viewport — Three.js scene + fly camera + recording.
 *
 * Phases 2–4: Scene setup, render loop, module assembly.
 * ES module loaded by viewport.html.
 *
 * Delegates to sub-modules:
 *   input_controller.js  — keyboard/mouse flight + speed HUD
 *   recorder.js          — recording state machine + sample capture
 *   fitter.js            — RDP + angle filter (dense → sparse keyframes)
 */

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { interpolateKeyframes } from './camera_math.js';
import { applyPreset, listPresets } from './camera_presets.js';
import { initInput, updateFlight, tickHUD, getIsFlying,
         getCurrentSpeed, disposeInput, isSpeedKeyHeld } from './input_controller.js';
import { createRecorder } from './recorder.js';
import { fitSamples, convertToKeyframeFormat } from './fitter.js';

// ── DOM refs ────────────────────────────────────────────────────────
const canvas = document.getElementById('viewport');
const recIndicator = document.getElementById('rec-indicator');
const recTime = document.getElementById('rec-time');
const recShots = document.getElementById('rec-shots');
const recDot = document.getElementById('rec-dot');
const helpEl = document.getElementById('help');
const speedValue = document.getElementById('speed-value');
const speedBarFill = document.getElementById('speed-bar-fill');
const fpsValue = document.getElementById('fps-value');
const fovValue = document.getElementById('fov-value');
const frameRect = document.getElementById('frame-rect');

// ── State ───────────────────────────────────────────────────────────
const ASPECT_RATIO = '9:16';
const RENDER_FPS = 24;
const REC_FPS = 60;
const SCENE_CENTER = new THREE.Vector3(0, 0, 0);
let SCENE_RADIUS = 1.0;

let camera, renderer, scene, clock;
let subjectGroup;
let subjectBBox;
let animFrameId;
let lastTime = 0;
let fpsCounter = 0;
let fpsAccum = 0;

// Sub-module instances
let recorder = null;
let recBlinkTimer = 0;

// ── Init ───────────────────────────────────────────────────────────

function init() {
    // Renderer
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x030308);
    scene.fog = new THREE.Fog(0x030308, 5, 50);

    // Camera — PERSP, Blender-matched vertical FOV
    camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, -7, 1.5);
    camera.lookAt(SCENE_CENTER);
    camera.updateProjectionMatrix();

    // Lighting — approximating dark_stage
    const ambient = new THREE.AmbientLight(0x111122, 0.3);
    scene.add(ambient);

    const keyLight = new THREE.DirectionalLight(0xffffff, 2.5);
    keyLight.position.set(0, -3.5, 2.7);
    scene.add(keyLight);

    const rimLeft = new THREE.PointLight(0x8cf2ff, 40, 15);
    rimLeft.position.set(-2.0, 0.7, 1.7);
    scene.add(rimLeft);

    const rimRight = new THREE.PointLight(0xff59a6, 30, 15);
    rimRight.position.set(2.0, 0.8, 1.2);
    scene.add(rimRight);

    const backLight = new THREE.PointLight(0xffffff, 20, 15);
    backLight.position.set(0, 2.2, 3.1);
    scene.add(backLight);

    // Ground plane
    const floorGeo = new THREE.PlaneGeometry(10, 10);
    const floorMat = new THREE.MeshStandardMaterial({
        color: 0x06070a, roughness: 0.75, metalness: 0.1,
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(0, -1.5, 0);
    scene.add(floor);

    // Grid helper
    const grid = new THREE.PolarGridHelper(4, 32, 24, 64, 0x333344, 0x222233);
    grid.position.y = -1.49;
    scene.add(grid);

    // Input controller (inject THREE namespace)
    initInput(camera, canvas, {
        THREE,
        speedValueEl: speedValue,
        speedBarFillEl: speedBarFill,
        helpEl,
    });

    // Recorder (pass camera accessor to avoid THREE dependency)
    recorder = createRecorder({
        getPosition: () => camera.position.toArray(),
        getQuat: () => camera.quaternion.toArray(),
        getFov: () => camera.fov,
    }, { recFps: REC_FPS });

    // Register recording key bindings + stop callback
    _setupRecordingControls();
    recorder.onStop((allShots) => {
        const fitted = fitSamples(allShots, [], {
            posEpsilon: SCENE_RADIUS * 0.02,
            angleEpsilon: 0.02,
        });
        if (window.opener) {
            window.opener.postMessage({
                type: 'camera-data',
                camera: { shots: fitted },
            }, '*');
            console.log('[viewport] camera data sent to opener', fitted);
        } else {
            console.log('[viewport] camera data:', fitted);
        }
    });

    // Start
    clock = new THREE.Clock();
    lastTime = performance.now();
    animate();

    window.addEventListener('resize', onResize);
    updateFrameGuide();
    fpsValue.textContent = '--';
    fovValue.textContent = Math.round(camera.fov) + '°';

    console.log('[viewport] CineAnchor interactive viewport ready');
    console.log('[viewport] Controls: click to fly, WASD move, L=rec, R=pause, Esc=exit');
}

// ── Render loop ─────────────────────────────────────────────────────

function animate() {
    animFrameId = requestAnimationFrame(animate);

    const dt = Math.min(clock.getDelta(), 0.1);
    const rawDt = dt;

    // FPS counter
    fpsAccum += rawDt;
    fpsCounter++;
    if (fpsAccum >= 1.0) {
        fpsValue.textContent = Math.round(fpsCounter / fpsAccum);
        fpsCounter = 0;
        fpsAccum = 0;
    }

    // Flight controls (delegated to input_controller)
    updateFlight(dt);

    // Recording tick (delegated to recorder)
    if (recorder.getState() === 'RECORDING') {
        recorder.tick(dt);
        recBlinkTimer += dt;

        // Update recording UI every 0.25s
        if (Math.floor(recorder.getElapsed() * 4) !==
            Math.floor((recorder.getElapsed() - dt) * 4)) {
            updateRecUI();
        }
    }

    // Render
    renderer.render(scene, camera);
    lastTime = performance.now();
}

// ── Recording key bindings ──────────────────────────────────────────

function _setupRecordingControls() {
    document.addEventListener('keydown', (e) => {
        if (e.code === 'KeyL') {
            const state = recorder.getState();
            if (state === 'IDLE') {
                recorder.start();
                recIndicator.classList.add('active');
                recIndicator.classList.remove('paused');
                recDot.classList.add('rec-blink');
                updateRecUI();
                console.log('[recorder] started');
            } else if (state === 'RECORDING') {
                recorder.stop();
                recIndicator.classList.remove('active', 'paused');
                recDot.classList.remove('rec-blink');
                updateRecUI();
                console.log('[recorder] stopped');
            } else if (state === 'PAUSED') {
                recorder.resume();
                recIndicator.classList.add('active');
                recIndicator.classList.remove('paused');
                recDot.classList.add('rec-blink');
                updateRecUI();
                console.log('[recorder] resumed');
            }
        }
        if (e.code === 'KeyR') {
            if (recorder.getState() === 'RECORDING') {
                recorder.pause();
                recIndicator.classList.remove('active');
                recIndicator.classList.add('paused');
                recDot.classList.remove('rec-blink');
                updateRecUI();
                console.log(`[recorder] paused — ${recorder.getShots().length} shots`);
            }
        }
    });
}

function updateRecUI() {
    const totalSec = recorder.getElapsed();
    const min = Math.floor(totalSec / 60);
    const sec = Math.floor(totalSec % 60);
    recTime.textContent = `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
    const shots = recorder.getShots();
    recShots.textContent = `镜头: ${shots.length + (recorder.getState() === 'RECORDING' ? 1 : 0)}`;
}

// ── Resize handler ──────────────────────────────────────────────────

function onResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    updateFrameGuide();
}

// ── Frame guide ─────────────────────────────────────────────────────

function updateFrameGuide() {
    const [targetW, targetH] = ASPECT_RATIO === '16:9' ? [16, 9]
        : ASPECT_RATIO === '1:1' ? [1, 1]
        : [9, 16];
    const winW = window.innerWidth;
    const winH = window.innerHeight;
    const winRatio = winW / winH;
    const targetRatio = targetW / targetH;

    let w, h;
    if (winRatio > targetRatio) {
        h = winH * 0.85;
        w = h * targetRatio;
    } else {
        w = winW * 0.85;
        h = w / targetRatio;
    }
    frameRect.style.width = w + 'px';
    frameRect.style.height = h + 'px';
}

// ── Start ───────────────────────────────────────────────────────────

init();
