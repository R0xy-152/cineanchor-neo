from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import uvicorn


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

HOST = "127.0.0.1"
PORT = int(os.environ.get("CINEANCHOR_SMOKE_PORT", "8765"))
BASE_URL = f"http://{HOST}:{PORT}"


def main() -> None:
    config = uvicorn.Config(
        "server.app:app",
        host=HOST,
        port=PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    wait_for_page()
    run_invalid_template_check()
    run_template("character_intro", "Web Hero", "Generated through FastAPI")
    run_template("product_orbit", "Web Orbit", "Generated through FastAPI")

    server.should_exit = True
    thread.join(timeout=10)


def wait_for_page() -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            status, _ = request("GET", "/web/")
            if status == 200:
                print("ROUTE4_PAGE_STATUS=200")
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("Local web page did not become available.")


def run_invalid_template_check() -> None:
    try:
        request_json("POST", "/api/render", {"template": "missing_template"})
    except urllib.error.HTTPError as exc:
        detail = json.loads(exc.read().decode("utf-8"))["detail"]
        print(
            "ROUTE4_INVALID_TEMPLATE_STATUS="
            f"{exc.code} error_code={detail.get('error_code')}"
        )
        if exc.code == 400 and detail.get("error_code") == "UNSUPPORTED_TEMPLATE":
            return
        raise
    raise RuntimeError("Invalid template request unexpectedly succeeded.")


def run_template(template: str, title: str, subtitle: str) -> None:
    created = request_json(
        "POST",
        "/api/render",
        {"template": template, "title": title, "subtitle": subtitle},
    )
    task_id = created["task_id"]
    print(f"ROUTE4_CREATED template={template} task_id={task_id}")

    task = poll_done(task_id)
    download_status, content = request("GET", f"/api/render/{task_id}/download")
    if download_status != 200 or len(content) < 1024:
        raise RuntimeError(f"Download failed for {task_id}: status={download_status}")

    print(
        "ROUTE4_TASK "
        f"template={template} "
        f"task_id={task_id} "
        f"status={task['status']} "
        f"output={task['output_path']} "
        f"blender_seconds={task['blender_seconds']} "
        f"ffmpeg_seconds={task['ffmpeg_seconds']}"
    )
    print(
        "ROUTE4_DOWNLOAD "
        f"template={template} "
        f"status={download_status} "
        f"bytes={len(content)}"
    )


def poll_done(task_id: str) -> dict[str, object]:
    deadline = time.time() + int(os.environ.get("CINEANCHOR_SMOKE_TIMEOUT_SECONDS", "1200"))
    last_status = None
    while time.time() < deadline:
        task = request_json("GET", f"/api/render/{task_id}")
        status = str(task["status"])
        if status != last_status:
            print(f"ROUTE4_STATUS task_id={task_id} status={status}")
            last_status = status
        if status == "DONE":
            return task
        if status == "FAILED":
            raise RuntimeError(
                f"Task failed: error_code={task.get('error_code')} message={task.get('message')}"
            )
        time.sleep(1)
    raise RuntimeError(f"Task timed out: {task_id}")


def request_json(method: str, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    status, content = request(method, path, payload)
    if status < 200 or status >= 300:
        raise RuntimeError(f"HTTP {status}: {content.decode('utf-8', errors='replace')}")
    return json.loads(content.decode("utf-8"))


def request(
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
) -> tuple[int, bytes]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.status, response.read()


if __name__ == "__main__":
    main()
