// ── DOM refs ──────────────────────────────────────────────────────────
const templateCards = document.querySelectorAll(".template-card");
const uploadZone = document.getElementById("uploadZone");
const fileInput = document.getElementById("fileInput");
const uploadPrompt = document.getElementById("uploadPrompt");
const uploadInfo = document.getElementById("uploadInfo");
const fileName = document.getElementById("fileName");
const fileType = document.getElementById("fileType");
const fileClear = document.getElementById("fileClear");
const uploadError = document.getElementById("uploadError");
const assetHint = document.getElementById("assetHint");
const titleInput = document.getElementById("titleInput");
const subtitleInput = document.getElementById("subtitleInput");
const aspectRatio = document.getElementById("aspectRatio");
const generateBtn = document.getElementById("generateBtn");
const progressSection = document.getElementById("progressSection");
const statusBadge = document.getElementById("statusBadge");
const elapsed = document.getElementById("elapsed");
const progressFill = document.getElementById("progressFill");
const progressMsg = document.getElementById("progressMsg");
const warningBanner = document.getElementById("warningBanner");
const downloadSection = document.getElementById("downloadSection");
const downloadLink = document.getElementById("downloadLink");
const errorBanner = document.getElementById("errorBanner");
const modeBtns = document.querySelectorAll(".mode-btn");
const interactiveBtn = document.getElementById("interactiveBtn");
const interactiveStatus = document.getElementById("interactiveStatus");
const interactiveClear = document.getElementById("interactiveClear");
const birthdayAssetSection = document.getElementById("birthdayAssetSection");
const birthdayFields = document.getElementById("birthdayFields");
const cameraControlSection = document.getElementById("cameraControlSection");
const interactiveSection = document.getElementById("interactiveSection");
const logoUploadZone = document.getElementById("logoUploadZone");
const logoFileInput = document.getElementById("logoFileInput");
const logoUploadPrompt = document.getElementById("logoUploadPrompt");
const logoUploadInfo = document.getElementById("logoUploadInfo");
const logoFileName = document.getElementById("logoFileName");
const logoFileClear = document.getElementById("logoFileClear");
const logoUploadError = document.getElementById("logoUploadError");
const characterNameInput = document.getElementById("characterNameInput");
const birthdayDateInput = document.getElementById("birthdayDateInput");
const birthdayDialogueInput = document.getElementById("birthdayDialogueInput");
const birthdayPrimaryColor = document.getElementById("birthdayPrimaryColor");
const birthdaySecondaryColor = document.getElementById("birthdaySecondaryColor");

// ── state ─────────────────────────────────────────────────────────────
let selectedTemplate = "character_intro";
let uploadedAsset = null;
let uploadedLogo = null;
let taskId = null;
let pollTimer = null;
let isPremium = false;
let startTime = null;
let pollCount = 0;
let interactiveCamera = null;  // loop 08: { shots, keyframes } from viewport

const TEMPLATE_DEFAULTS = {
  character_intro: { title: "New Hero Arrival", subtitle: "Limited Event", assetLabel: "PNG 图片", accept: ".png" },
  product_orbit: { title: "Product Orbit", subtitle: "GLB Showcase", assetLabel: "GLB 模型", accept: ".glb" },
  character_birthday: { title: "HAPPY BIRTHDAY", subtitle: "Celebrate now", assetLabel: "角色 PNG", accept: ".png" },
};

const STATUS_LABELS = {
  PENDING: "等待开始", RENDERING: "模板渲染中", COMPOSITING: "视频合成中",
  ENHANCING: "轻度后期处理中", DONE: "完成", FAILED: "生成失败",
};

const PROGRESS_MAP = { PENDING: 0, RENDERING: 45, COMPOSITING: 85, ENHANCING: 92, DONE: 100 };

const ERROR_MESSAGES = {
  ASSET_NOT_FOUND: "素材文件不存在，请重新上传。",
  INVALID_PROJECT_JSON: "渲染参数无效，请检查输入。",
  UNSUPPORTED_TEMPLATE: "不支持的模板。",
  UNSUPPORTED_ASSET_FORMAT: "不支持的素材格式。character_intro 仅支持 PNG，product_orbit 仅支持 GLB。",
  BLENDER_RENDER_FAILED: "模板渲染失败，请重试。",
  ASSET_IMPORT_FAILED: "素材无法读取，请确认 PNG 文件有效。",
  FFMPEG_COMPOSE_FAILED: "视频合成失败，请重试。",
  RENDER_TIMEOUT: "渲染超时，请稍后重试。",
  AI_ENHANCE_SKIPPED: null,
  OUTPUT_NOT_READY: "视频尚未生成，请等待。",
  OUTPUT_NOT_FOUND: "输出文件缺失，请重新生成。",
};

// ── template selection ────────────────────────────────────────────────
templateCards.forEach((card) => {
  card.addEventListener("click", () => {
    templateCards.forEach((c) => c.classList.remove("selected"));
    card.classList.add("selected");
    selectedTemplate = card.dataset.template;
    const preset = TEMPLATE_DEFAULTS[selectedTemplate];
    titleInput.value = preset.title;
    subtitleInput.value = preset.subtitle;
    assetHint.textContent = preset.assetLabel;
    fileInput.accept = preset.accept;
    const birthdayMode = selectedTemplate === "character_birthday";
    birthdayAssetSection.classList.toggle("hidden", !birthdayMode);
    birthdayFields.classList.toggle("hidden", !birthdayMode);
    cameraControlSection.classList.toggle("hidden", birthdayMode);
    interactiveSection.classList.toggle("hidden", birthdayMode);
    aspectRatio.value = "9:16";
    aspectRatio.disabled = birthdayMode;
    clearUpload();
    clearLogoUpload();
    clearInteractiveCamera();
    updateGenerateButton();
  });
});

// ── upload ────────────────────────────────────────────────────────────
uploadZone.addEventListener("click", (e) => {
  if (e.target === fileClear) return;
  fileInput.click();
});
fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (file) handleFile(file);
});
uploadZone.addEventListener("dragover", (e) => { e.preventDefault(); uploadZone.classList.add("dragover"); });
uploadZone.addEventListener("dragleave", () => { uploadZone.classList.remove("dragover"); });
uploadZone.addEventListener("drop", (e) => {
  e.preventDefault(); uploadZone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});
fileClear.addEventListener("click", (e) => { e.stopPropagation(); clearUpload(); });

function clearUpload() {
  uploadedAsset = null; fileInput.value = "";
  uploadPrompt.classList.remove("hidden"); uploadInfo.classList.add("hidden");
  uploadError.classList.add("hidden"); updateGenerateButton();
}

async function handleFile(file) {
  uploadError.classList.add("hidden");
  const expected = TEMPLATE_DEFAULTS[selectedTemplate].accept;
  const ext = "." + file.name.split(".").pop().toLowerCase();
  if (expected === ".png" && ext !== ".png") { showUploadError("当前模板仅支持 PNG 图片。"); return; }
  if (expected === ".glb" && ext !== ".glb") { showUploadError("product_orbit 仅支持 GLB 模型。"); return; }
  const formData = new FormData(); formData.append("file", file);
  try {
    const resp = await fetch("/api/assets/upload", { method: "POST", body: formData });
    const data = await resp.json();
    if (!resp.ok) { showUploadError(ERROR_MESSAGES[data.error_code] || data.message || "上传失败。"); return; }
    uploadedAsset = data; fileName.textContent = data.filename;
    fileType.textContent = data.type === "image" ? "PNG" : "GLB";
    uploadPrompt.classList.add("hidden"); uploadInfo.classList.remove("hidden");
    updateGenerateButton();
  } catch (err) { showUploadError("上传失败，请检查网络连接。"); }
}

function showUploadError(msg) { uploadError.textContent = msg; uploadError.classList.remove("hidden"); }

logoUploadZone.addEventListener("click", (event) => {
  if (event.target === logoFileClear) return;
  logoFileInput.click();
});
logoFileInput.addEventListener("change", () => {
  const file = logoFileInput.files[0];
  if (file) handleLogoFile(file);
});
logoUploadZone.addEventListener("dragover", (event) => { event.preventDefault(); logoUploadZone.classList.add("dragover"); });
logoUploadZone.addEventListener("dragleave", () => { logoUploadZone.classList.remove("dragover"); });
logoUploadZone.addEventListener("drop", (event) => {
  event.preventDefault(); logoUploadZone.classList.remove("dragover");
  const file = event.dataTransfer.files[0];
  if (file) handleLogoFile(file);
});
logoFileClear.addEventListener("click", (event) => { event.stopPropagation(); clearLogoUpload(); });

function clearLogoUpload() {
  uploadedLogo = null; logoFileInput.value = "";
  logoUploadPrompt.classList.remove("hidden"); logoUploadInfo.classList.add("hidden");
  logoUploadError.classList.add("hidden"); updateGenerateButton();
}

async function handleLogoFile(file) {
  logoUploadError.classList.add("hidden");
  if (!file.name.toLowerCase().endsWith(".png")) {
    logoUploadError.textContent = "Logo 仅支持 PNG。"; logoUploadError.classList.remove("hidden"); return;
  }
  const formData = new FormData(); formData.append("file", file);
  try {
    const response = await fetch("/api/assets/upload", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "Logo 上传失败");
    uploadedLogo = data; logoFileName.textContent = data.filename;
    logoUploadPrompt.classList.add("hidden"); logoUploadInfo.classList.remove("hidden");
    updateGenerateButton();
  } catch (error) {
    logoUploadError.textContent = error.message || "Logo 上传失败。";
    logoUploadError.classList.remove("hidden");
  }
}

// ── render mode ───────────────────────────────────────────────────────
modeBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    modeBtns.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active"); isPremium = btn.dataset.mode === "premium";
  });
});

// ── interactive camera (loop 08) ──────────────────────────────────────
interactiveBtn.addEventListener("click", () => {
  if (!uploadedAsset) { showUploadError("请先上传素材再打开交互预览。"); return; }
  const vp = window.open("/web/viewport.html", "cineanchor-viewport", "width=1400,height=900,left=100,top=50");
  if (!vp) { showUploadError("无法打开预览窗口，请检查浏览器弹窗设置。"); }
});
interactiveClear.addEventListener("click", () => { clearInteractiveCamera(); });
window.addEventListener("message", (e) => {
  if (e.data && e.data.type === "camera-data") { interactiveCamera = e.data.camera; updateInteractiveStatus(); }
});
function clearInteractiveCamera() { interactiveCamera = null; updateInteractiveStatus(); }
function updateInteractiveStatus() {
  if (interactiveCamera && (interactiveCamera.shots || interactiveCamera.keyframes)) {
    interactiveStatus.textContent = "已录制"; interactiveStatus.style.color = "#55EEFF";
    interactiveClear.classList.remove("hidden");
  } else {
    interactiveStatus.textContent = "未录制"; interactiveStatus.style.color = "#888";
    interactiveClear.classList.add("hidden");
  }
}

// ── generate ──────────────────────────────────────────────────────────
function updateGenerateButton() {
  const birthdayReady = selectedTemplate !== "character_birthday" || uploadedLogo;
  if (uploadedAsset && birthdayReady) { generateBtn.disabled = false; generateBtn.textContent = isPremium ? "生成精品版视频" : "生成视频"; }
  else if (selectedTemplate === "character_birthday" && uploadedAsset && !uploadedLogo) { generateBtn.disabled = true; generateBtn.textContent = "请上传 Logo"; }
  else { generateBtn.disabled = true; generateBtn.textContent = "请先上传素材"; }
}
modeBtns.forEach((btn) => { btn.addEventListener("click", updateGenerateButton); });

generateBtn.addEventListener("click", async () => {
  if (!uploadedAsset) return;
  resetUI(); generateBtn.disabled = true; generateBtn.textContent = "生成中...";

  const cameraSpec = {
    motion: selectedTemplate === "character_intro" ? "dolly_in" : "orbit",
    speed: currentSpeed, start_distance: 7.2, end_distance: 5.8, height: 1.4, focal_length: 70.0,
  };
  if (interactiveCamera) {
    if (interactiveCamera.shots) cameraSpec.shots = interactiveCamera.shots;
    if (interactiveCamera.keyframes) cameraSpec.keyframes = interactiveCamera.keyframes;
  }

  const birthdayMode = selectedTemplate === "character_birthday";
  const projectJSON = birthdayMode ? {
    version: "0.2", project_id: crypto.randomUUID(), template: selectedTemplate,
    output: { duration: 15, fps: 24, aspect_ratio: "9:16", resolution: "1080p" },
    assets: [
      { id: "main_character", type: "image", path: uploadedAsset.path },
      { id: "logo", type: "image", path: uploadedLogo.path },
    ],
    camera: { motion: "dolly_in", speed: 1.0, start_distance: 7.2, end_distance: 5.8, height: 1.4, focal_length: 70.0 },
    scene: { background: "soft_poster", lighting: "flat_graphic", particles: null, fog: false },
    text: {
      title: titleInput.value.trim() || "HAPPY BIRTHDAY", subtitle: "", font_style: "birthday_serif",
      character_name: characterNameInput.value.trim(), birthday_date: birthdayDateInput.value.trim(),
      main_title: titleInput.value.trim() || "HAPPY BIRTHDAY",
      subtitle_lines: birthdayDialogueInput.value.split("\n").map((line) => line.trim()).filter(Boolean).slice(0, 3),
      cta: subtitleInput.value.trim(),
    },
    style: {
      theme: "cute_school", primary_color: birthdayPrimaryColor.value,
      secondary_color: birthdaySecondaryColor.value, background_style: "soft_poster",
      font_preset: "birthday_serif", subtitle_preset: "white_black_stroke", particle_preset: "petal_soft",
    },
    ai_enhance: { enabled: isPremium, mode: "conservative" },
  } : {
    version: "0.1", project_id: crypto.randomUUID(), template: selectedTemplate,
    output: { duration: 8, fps: 24, aspect_ratio: aspectRatio.value, resolution: "1080p" },
    assets: [{ id: "main_subject", type: uploadedAsset.type, path: uploadedAsset.path }],
    camera: cameraSpec,
    scene: { background: "dark_stage", lighting: "rim_back", particles: true, fog: false },
    text: { title: titleInput.value.trim() || TEMPLATE_DEFAULTS[selectedTemplate].title,
            subtitle: subtitleInput.value.trim(), font_style: "bold_game" },
    ai_enhance: { enabled: isPremium, mode: "conservative" },
  };

  try {
    const resp = await fetch("/api/render", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(projectJSON) });
    const data = await resp.json();
    if (!resp.ok) { showError(data); generateBtn.disabled = false; updateGenerateButton(); return; }
    taskId = data.task_id; startTime = Date.now(); pollCount = 0;
    progressSection.classList.remove("hidden"); startPolling();
  } catch (err) {
    showError({ error_code: "NETWORK_ERROR", message: "网络请求失败，请检查服务器是否运行。" });
    generateBtn.disabled = false; updateGenerateButton();
  }
});

// ── polling ───────────────────────────────────────────────────────────
function startPolling() { stopPolling(); pollTask(); }
function stopPolling() { if (pollTimer !== null) { clearTimeout(pollTimer); pollTimer = null; } }

async function pollTask() {
  if (!taskId) return;
  try {
    const resp = await fetch(`/api/render/${taskId}/status`);
    const data = await resp.json();
    if (!resp.ok) { showError(data); stopPolling(); generateBtn.disabled = false; updateGenerateButton(); return; }
    pollCount++; updateProgress(data);
    if (data.status === "DONE") { stopPolling(); handleDone(data); return; }
    if (data.status === "FAILED") { stopPolling(); handleFailed(data); return; }
    const interval = (Date.now() - startTime < 30000) ? 3000 : 10000;
    pollTimer = setTimeout(pollTask, interval);
  } catch (err) { pollTimer = setTimeout(pollTask, 10000); }
}

function updateProgress(data) {
  statusBadge.textContent = STATUS_LABELS[data.status] || data.status;
  statusBadge.className = "status-badge status-" + data.status.toLowerCase();
  progressFill.style.width = (PROGRESS_MAP[data.status] !== undefined ? PROGRESS_MAP[data.status] : 0) + "%";
  const secs = Math.floor((Date.now() - startTime) / 1000);
  elapsed.textContent = `${Math.floor(secs/60)}:${String(secs%60).padStart(2,"0")}`;
  progressMsg.textContent = data.message || "";
}

function handleDone(data) {
  progressFill.style.width = "100%"; statusBadge.textContent = "完成";
  statusBadge.className = "status-badge status-done"; progressMsg.textContent = "视频已生成！";
  if (data.warning_code === "AI_ENHANCE_SKIPPED") warningBanner.classList.remove("hidden");
  downloadLink.href = `/api/render/${taskId}/download`; downloadSection.classList.remove("hidden");
  generateBtn.disabled = false; generateBtn.textContent = "重新生成"; uploadError.classList.add("hidden");
}

function handleFailed(data) {
  statusBadge.textContent = "失败"; statusBadge.className = "status-badge status-failed";
  showError(data); generateBtn.disabled = false; updateGenerateButton();
}

// ── error display ─────────────────────────────────────────────────────
function showError(data) {
  const code = data.error_code || "";
  let msg = ERROR_MESSAGES[code] || data.message || "未知错误。";
  if (data.detail && typeof data.detail === "string" && !ERROR_MESSAGES[code]) msg += " " + data.detail;
  errorBanner.textContent = msg; errorBanner.classList.remove("hidden");
}

function resetUI() {
  stopPolling(); progressSection.classList.add("hidden"); downloadSection.classList.add("hidden");
  warningBanner.classList.add("hidden"); errorBanner.classList.add("hidden");
  progressFill.style.width = "0%"; statusBadge.textContent = "等待中"; statusBadge.className = "status-badge";
  elapsed.textContent = ""; progressMsg.textContent = ""; taskId = null;
}

// ── speed control ─────────────────────────────────────────────────────
const MIN_SPEED = 0.1, MAX_SPEED = 5.0, SPEED_ACCEL = 0.8, SPEED_DECEL = 0.4;
let currentSpeed = 1.0;
let speedKeysDown = { shift: false, tab: false, alt: false };
let speedAnimId = null, hudHideTimer = null, lastSpeedFrame = 0;
const speedValueEl = document.getElementById("speedValue"), speedBarFill = document.getElementById("speedBarFill");
const hudOverlay = document.getElementById("hudOverlay"), hudSpeed = document.getElementById("hudSpeed");
const hudBarFill = document.getElementById("hudBarFill");

function updateSpeedDisplay(speed) {
  const pct = ((speed - MIN_SPEED) / (MAX_SPEED - MIN_SPEED)) * 100;
  speedValueEl.textContent = speed.toFixed(2);
  speedBarFill.style.width = Math.max(0, Math.min(100, pct)) + "%";
  hudSpeed.textContent = speed.toFixed(2);
  hudBarFill.style.width = Math.max(0, Math.min(100, pct)) + "%";
}

function showHUD() { hudOverlay.classList.remove("hidden"); if (hudHideTimer !== null) { clearTimeout(hudHideTimer); hudHideTimer = null; } }
function scheduleHideHUD() { if (hudHideTimer !== null) clearTimeout(hudHideTimer); hudHideTimer = setTimeout(() => { hudOverlay.classList.add("hidden"); hudHideTimer = null; }, 2000); }

function speedLoop(timestamp) {
  if (!lastSpeedFrame) lastSpeedFrame = timestamp;
  const dt = Math.min((timestamp - lastSpeedFrame) / 1000, 0.1); lastSpeedFrame = timestamp;
  let changed = false;
  if (speedKeysDown.tab || speedKeysDown.alt) { currentSpeed = Math.min(MAX_SPEED, currentSpeed + SPEED_ACCEL * dt); changed = true; }
  if (speedKeysDown.shift) { currentSpeed = Math.max(MIN_SPEED, currentSpeed - SPEED_DECEL * dt); changed = true; }
  if (changed) { updateSpeedDisplay(currentSpeed); showHUD(); }
  speedAnimId = requestAnimationFrame(speedLoop);
}

function startSpeedLoop() { if (speedAnimId !== null) return; lastSpeedFrame = 0; speedAnimId = requestAnimationFrame(speedLoop); }
function stopSpeedLoop() { if (speedAnimId !== null) { cancelAnimationFrame(speedAnimId); speedAnimId = null; } }

document.addEventListener("keydown", (e) => {
  const key = e.key.toLowerCase(); let claimed = false;
  if (key === "shift") { if (speedKeysDown.shift) return; speedKeysDown.shift = true; claimed = true; }
  if (key === "tab" || key === "alt") {
    if (key === "tab") { if (speedKeysDown.tab) return; speedKeysDown.tab = true; }
    if (key === "alt") { if (speedKeysDown.alt) return; speedKeysDown.alt = true; }
    e.preventDefault(); claimed = true;
  }
  if (claimed) { startSpeedLoop(); showHUD(); }
  if (e.key === "Tab" && (speedKeysDown.shift || speedKeysDown.tab || speedKeysDown.alt)) e.preventDefault();
});
document.addEventListener("keyup", (e) => {
  const key = e.key.toLowerCase(); let released = true;
  if (key === "shift") speedKeysDown.shift = false;
  else if (key === "tab") { speedKeysDown.tab = false; e.preventDefault(); }
  else if (key === "alt") speedKeysDown.alt = false;
  else released = false;
  if (released && !speedKeysDown.shift && !speedKeysDown.tab && !speedKeysDown.alt) { stopSpeedLoop(); scheduleHideHUD(); }
});
