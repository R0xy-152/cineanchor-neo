const form = document.querySelector("#renderForm");
const templateInput = document.querySelector("#template");
const titleInput = document.querySelector("#title");
const subtitleInput = document.querySelector("#subtitle");
const generateButton = document.querySelector("#generateButton");
const statusBadge = document.querySelector("#statusBadge");
const taskId = document.querySelector("#taskId");
const statusText = document.querySelector("#statusText");
const messageText = document.querySelector("#messageText");
const downloadLink = document.querySelector("#downloadLink");

let pollTimer = null;

const defaults = {
  character_intro: {
    title: "New Hero Arrival",
    subtitle: "Limited Event",
  },
  product_orbit: {
    title: "Product Orbit",
    subtitle: "GLB Showcase",
  },
};

templateInput.addEventListener("change", () => {
  const preset = defaults[templateInput.value];
  titleInput.value = preset.title;
  subtitleInput.value = preset.subtitle;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  stopPolling();
  setBusy(true);
  setStatus("PENDING", "Starting render task.", "None");
  downloadLink.classList.add("hidden");

  try {
    const response = await fetch("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template: templateInput.value,
        title: titleInput.value,
        subtitle: subtitleInput.value,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = payload.detail || {};
      throw new Error(`${detail.error_code || "REQUEST_FAILED"}: ${detail.message || response.statusText}`);
    }
    taskId.textContent = payload.task_id;
    updateFromTask(payload);
    pollTimer = window.setInterval(() => pollTask(payload.task_id), 1000);
  } catch (error) {
    setBusy(false);
    setStatus("FAILED", error.message, "None");
  }
});

async function pollTask(id) {
  try {
    const response = await fetch(`/api/render/${id}`);
    const payload = await response.json();
    if (!response.ok) {
      const detail = payload.detail || {};
      throw new Error(`${detail.error_code || "POLL_FAILED"}: ${detail.message || response.statusText}`);
    }
    updateFromTask(payload);
    if (payload.status === "DONE" || payload.status === "FAILED") {
      stopPolling();
      setBusy(false);
    }
  } catch (error) {
    stopPolling();
    setBusy(false);
    setStatus("FAILED", error.message, id);
  }
}

function updateFromTask(task) {
  setStatus(task.status, task.message, task.task_id);
  if (task.status === "DONE" && task.download_url) {
    downloadLink.href = task.download_url;
    downloadLink.classList.remove("hidden");
  }
}

function setStatus(status, message, id) {
  statusBadge.textContent = status;
  statusText.textContent = status;
  messageText.textContent = message;
  taskId.textContent = id;
}

function setBusy(isBusy) {
  generateButton.disabled = isBusy;
  generateButton.textContent = isBusy ? "Generating" : "Generate";
}

function stopPolling() {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}
