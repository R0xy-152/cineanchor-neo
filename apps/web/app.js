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

// ── state ─────────────────────────────────────────────────────────────
let selectedTemplate = "character_intro";
let uploadedAsset = null; // { asset_id, path, type, filename } | null
let taskId = null;
let pollTimer = null;
let isPremium = false;
let startTime = null;
let pollCount = 0;

const TEMPLATE_DEFAULTS = {
  character_intro: { title: "New Hero Arrival", subtitle: "Limited Event", assetLabel: "PNG 图片", accept: ".png" },
  product_orbit: { title: "Product Orbit", subtitle: "GLB Showcase", assetLabel: "GLB 模型", accept: ".glb" },
};

const STATUS_LABELS = {
  PENDING: "等待开始",
  RENDERING: "3D 渲染中",
  COMPOSITING: "视频合成中",
  ENHANCING: "轻度后期处理中",
  DONE: "完成",
  FAILED: "生成失败",
};

const PROGRESS_MAP = { PENDING: 0, RENDERING: 45, COMPOSITING: 85, ENHANCING: 92, DONE: 100 };

const ERROR_MESSAGES = {
  ASSET_NOT_FOUND: "素材文件不存在，请重新上传。",
  INVALID_PROJECT_JSON: "渲染参数无效，请检查输入。",
  UNSUPPORTED_TEMPLATE: "不支持的模板。",
  UNSUPPORTED_ASSET_FORMAT: "不支持的素材格式。character_intro 仅支持 PNG，product_orbit 仅支持 GLB。",
  BLENDER_RENDER_FAILED: "3D 渲染失败，请重试。",
  FFMPEG_COMPOSE_FAILED: "视频合成失败，请重试。",
  RENDER_TIMEOUT: "渲染超时，请稍后重试。",
  AI_ENHANCE_SKIPPED: null, // handled separately as warning
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
    clearUpload();
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

uploadZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadZone.classList.add("dragover");
});

uploadZone.addEventListener("dragleave", () => {
  uploadZone.classList.remove("dragover");
});

uploadZone.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadZone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

fileClear.addEventListener("click", (e) => {
  e.stopPropagation();
  clearUpload();
});

function clearUpload() {
  uploadedAsset = null;
  fileInput.value = "";
  uploadPrompt.classList.remove("hidden");
  uploadInfo.classList.add("hidden");
  uploadError.classList.add("hidden");
  updateGenerateButton();
}

async function handleFile(file) {
  uploadError.classList.add("hidden");

  // Frontend UX hint: check extension matches template
  const expected = TEMPLATE_DEFAULTS[selectedTemplate].accept;
  const ext = "." + file.name.split(".").pop().toLowerCase();
  if (expected === ".png" && ext !== ".png") {
    showUploadError("character_intro 仅支持 PNG 图片。");
    return;
  }
  if (expected === ".glb" && ext !== ".glb") {
    showUploadError("product_orbit 仅支持 GLB 模型。");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const resp = await fetch("/api/assets/upload", { method: "POST", body: formData });
    const data = await resp.json();
    if (!resp.ok) {
      const msg = ERROR_MESSAGES[data.error_code] || data.message || "上传失败。";
      showUploadError(msg);
      return;
    }
    uploadedAsset = data;
    fileName.textContent = data.filename;
    fileType.textContent = data.type === "image" ? "PNG" : "GLB";
    uploadPrompt.classList.add("hidden");
    uploadInfo.classList.remove("hidden");
    updateGenerateButton();
  } catch (err) {
    showUploadError("上传失败，请检查网络连接。");
  }
}

function showUploadError(msg) {
  uploadError.textContent = msg;
  uploadError.classList.remove("hidden");
}

// ── render mode ───────────────────────────────────────────────────────

modeBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    modeBtns.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    isPremium = btn.dataset.mode === "premium";
  });
});

// ── generate ──────────────────────────────────────────────────────────

function updateGenerateButton() {
  if (uploadedAsset) {
    generateBtn.disabled = false;
    generateBtn.textContent = isPremium ? "生成精品版视频" : "生成视频";
  } else {
    generateBtn.disabled = true;
    generateBtn.textContent = "请先上传素材";
  }
}

modeBtns.forEach((btn) => {
  btn.addEventListener("click", updateGenerateButton);
});

generateBtn.addEventListener("click", async () => {
  if (!uploadedAsset) return;

  resetUI();
  generateBtn.disabled = true;
  generateBtn.textContent = "生成中...";

  const projectJSON = {
    version: "0.1",
    project_id: crypto.randomUUID(),
    template: selectedTemplate,
    output: {
      duration: 8,
      fps: 24,
      aspect_ratio: aspectRatio.value,
      resolution: "1080p",
    },
    assets: [{
      id: "main_subject",
      type: uploadedAsset.type,
      path: uploadedAsset.path,
    }],
    camera: {
      motion: selectedTemplate === "character_intro" ? "dolly_in" : "orbit",
      speed: 1.0,
      start_distance: 7.2,
      end_distance: 5.8,
      height: 1.4,
      focal_length: 70.0,
    },
    scene: {
      background: "dark_stage",
      lighting: "rim_back",
      particles: true,
      fog: false,
    },
    text: {
      title: titleInput.value.trim() || TEMPLATE_DEFAULTS[selectedTemplate].title,
      subtitle: subtitleInput.value.trim(),
      font_style: "bold_game",
    },
    ai_enhance: {
      enabled: isPremium,
      mode: "conservative",
    },
  };

  try {
    const resp = await fetch("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(projectJSON),
    });
    const data = await resp.json();
    if (!resp.ok) {
      showError(data);
      generateBtn.disabled = false;
      updateGenerateButton();
      return;
    }
    taskId = data.task_id;
    startTime = Date.now();
    pollCount = 0;
    progressSection.classList.remove("hidden");
    startPolling();
  } catch (err) {
    showError({ error_code: "NETWORK_ERROR", message: "网络请求失败，请检查服务器是否运行。" });
    generateBtn.disabled = false;
    updateGenerateButton();
  }
});

// ── polling ───────────────────────────────────────────────────────────

function startPolling() {
  stopPolling();
  pollTask();
}

function stopPolling() {
  if (pollTimer !== null) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
}

async function pollTask() {
  if (!taskId) return;

  try {
    const resp = await fetch(`/api/render/${taskId}/status`);
    const data = await resp.json();
    if (!resp.ok) {
      showError(data);
      stopPolling();
      generateBtn.disabled = false;
      updateGenerateButton();
      return;
    }

    pollCount++;
    updateProgress(data);

    if (data.status === "DONE") {
      stopPolling();
      handleDone(data);
      return;
    }
    if (data.status === "FAILED") {
      stopPolling();
      handleFailed(data);
      return;
    }

    // Adaptive polling: 3s for first 30s, then 10s
    const interval = (Date.now() - startTime < 30000) ? 3000 : 10000;
    pollTimer = setTimeout(pollTask, interval);
  } catch (err) {
    // Network error during poll — retry at long interval
    pollTimer = setTimeout(pollTask, 10000);
  }
}

function updateProgress(data) {
  const label = STATUS_LABELS[data.status] || data.status;
  statusBadge.textContent = label;
  statusBadge.className = "status-badge status-" + data.status.toLowerCase();

  const pct = PROGRESS_MAP[data.status] !== undefined ? PROGRESS_MAP[data.status] : 0;
  progressFill.style.width = pct + "%";

  const secs = Math.floor((Date.now() - startTime) / 1000);
  const mins = Math.floor(secs / 60);
  elapsed.textContent = `${mins}:${String(secs % 60).padStart(2, "0")}`;

  progressMsg.textContent = data.message || "";
}

function handleDone(data) {
  progressFill.style.width = "100%";
  statusBadge.textContent = "完成";
  statusBadge.className = "status-badge status-done";
  progressMsg.textContent = "视频已生成！";

  // Check for warning (enhancement fallback)
  if (data.warning_code === "AI_ENHANCE_SKIPPED") {
    warningBanner.classList.remove("hidden");
  }

  downloadLink.href = `/api/render/${taskId}/download`;
  downloadSection.classList.remove("hidden");
  generateBtn.disabled = false;
  generateBtn.textContent = "重新生成";
  uploadError.classList.add("hidden");
}

function handleFailed(data) {
  statusBadge.textContent = "失败";
  statusBadge.className = "status-badge status-failed";
  showError(data);
  generateBtn.disabled = false;
  updateGenerateButton();
}

// ── error display ─────────────────────────────────────────────────────

function showError(data) {
  const code = data.error_code || "";
  let msg = ERROR_MESSAGES[code] || data.message || "未知错误。";
  if (data.detail && typeof data.detail === "string" && !ERROR_MESSAGES[code]) {
    msg += " " + data.detail;
  }
  errorBanner.textContent = msg;
  errorBanner.classList.remove("hidden");
}

function resetUI() {
  stopPolling();
  progressSection.classList.add("hidden");
  downloadSection.classList.add("hidden");
  warningBanner.classList.add("hidden");
  errorBanner.classList.add("hidden");
  progressFill.style.width = "0%";
  statusBadge.textContent = "等待中";
  statusBadge.className = "status-badge";
  elapsed.textContent = "";
  progressMsg.textContent = "";
  taskId = null;
}
