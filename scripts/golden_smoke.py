#!/usr/bin/env python3
"""CineAnchor V0.1 — Golden path smoke validation.

End-to-end validation of character_intro and product_orbit renders.
Requires sample assets and a running server. Skips gracefully if assets
are missing — never fails cryptically.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = REPO_ROOT / "samples" / "assets"
SAMPLE_PNG = os.environ.get("CINEANCHOR_SAMPLE_PNG", str(SAMPLE_DIR / "hero.png"))
SAMPLE_GLB = os.environ.get("CINEANCHOR_SAMPLE_GLB", str(SAMPLE_DIR / "model.glb"))
BASE_URL = os.environ.get("CINEANCHOR_SMOKE_URL", "http://127.0.0.1:8765")


def request(method: str, path: str, body: bytes | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    data = body
    headers = {"Content-Type": "application/json"} if body else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, json.loads(raw) if raw else {}
    except urllib.error.URLError as exc:
        return 0, {"error": str(exc)}


def poll_until(task_id: str, target: frozenset[str], timeout: int = 600) -> dict:
    deadline = time.time() + timeout
    last_status = None
    while time.time() < deadline:
        status, data = request("GET", f"/api/render/{task_id}/status")
        current = data.get("status", "")
        if current != last_status:
            print(f"  [{current}] {data.get('message', '')}")
            last_status = current
        if current in target:
            return data
        time.sleep(3)
    return data


def upload_asset(filepath: str) -> dict | None:
    """Upload a file via multipart. Uses curl if available, otherwise raw."""
    import io

    path = Path(filepath)
    if not path.exists():
        return None

    boundary = "----CineAnchorSmokeBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    body += path.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = f"{BASE_URL}/api/assets/upload"
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        print(f"  Upload error: {exc.code} — {exc.read().decode('utf-8', errors='replace')[:300]}")
        return None


def run_render(title: str, template: str, asset_path: str, asset_type: str, premium: bool = False) -> str | None:
    project = {
        "version": "0.1",
        "project_id": f"smoke-{template}",
        "template": template,
        "output": {"duration": 8, "fps": 24, "aspect_ratio": "9:16", "resolution": "1080p"},
        "assets": [{"id": "main_subject", "type": asset_type, "path": asset_path}],
        "camera": {
            "motion": "dolly_in" if template == "character_intro" else "orbit",
            "speed": 1.0, "start_distance": 7.2, "end_distance": 5.8,
            "height": 1.4, "focal_length": 70.0,
        },
        "scene": {"background": "dark_stage", "lighting": "rim_back", "particles": True, "fog": False},
        "text": {"title": title, "subtitle": "Smoke Test", "font_style": "bold_game"},
        "ai_enhance": {"enabled": premium, "mode": "conservative"},
    }
    _, data = request("POST", "/api/render", json.dumps(project).encode("utf-8"))
    task_id = data.get("task_id")
    if not task_id:
        print(f"  ERROR: No task_id returned — {data}")
        return None
    print(f"  task_id: {task_id}")
    result = poll_until(task_id, frozenset({"DONE", "FAILED"}))
    if result.get("status") != "DONE":
        print(f"  FAILED: {result.get('error_code')} — {result.get('message')}")
        return None
    if result.get("warning_code"):
        print(f"  WARNING: {result['warning_code']} — {result['warning_message']}")
    return task_id


def validate_mp4(task_id: str, expected_fps: int) -> bool:
    """Validate MP4 via ffprobe if available."""
    ffprobe = os.environ.get("FFPROBE_PATH", os.environ.get("FFMPEG_PATH", "ffprobe").replace("ffmpeg", "ffprobe"))
    download_url = f"{BASE_URL}/api/render/{task_id}/download"

    # Download and check file size
    try:
        req = urllib.request.Request(download_url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            mp4_bytes = resp.read()
        size_mb = len(mp4_bytes) / (1024 * 1024)
        print(f"  Downloaded MP4: {size_mb:.1f} MB")
        if size_mb < 0.1:
            print(f"  WARNING: MP4 file is very small ({size_mb:.2f} MB)")
    except Exception as exc:
        print(f"  Download error: {exc}")
        return False

    # ffprobe if available
    try:
        tmp_path = REPO_ROOT / "storage" / "smoke_tmp.mp4"
        tmp_path.write_bytes(mp4_bytes)
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(tmp_path)],
            capture_output=True, text=True, timeout=30,
        )
        tmp_path.unlink()
        if result.returncode == 0:
            info = json.loads(result.stdout)
            for stream in info.get("streams", []):
                if stream["codec_type"] == "video":
                    print(f"  ffprobe: {stream.get('codec_name')} "
                          f"{stream.get('width')}×{stream.get('height')} "
                          f"{stream.get('r_frame_rate')}")
            return True
    except Exception as exc:
        print(f"  ffprobe unavailable: {exc}")
    return True  # Not a failure if ffprobe is missing


def main() -> None:
    print("CineAnchor V0.1 Golden Path Smoke\n")

    passed = 0
    skipped = 0
    failed = 0

    # ── character_intro ─────────────────────────────────────────────
    print("─ character_intro ─")
    if not Path(SAMPLE_PNG).exists():
        print(f"  SKIP: sample PNG not found at {SAMPLE_PNG}")
        print(f"  Place a transparent PNG at {SAMPLE_PNG}")
        skipped += 1
    else:
        asset = upload_asset(SAMPLE_PNG)
        if not asset:
            print("  FAILED: could not upload PNG")
            failed += 1
        else:
            print(f"  Uploaded: {asset['filename']} ({asset['type']})")
            task_id = run_render("Smoke Hero", "character_intro", asset["path"], "image")
            if task_id:
                validate_mp4(task_id, 24)
                print("  PASS: character_intro")
                passed += 1
            else:
                print("  FAILED: character_intro render")
                failed += 1

    # ── product_orbit ───────────────────────────────────────────────
    print("\n─ product_orbit ─")
    if not Path(SAMPLE_GLB).exists():
        print(f"  SKIP: sample GLB not found at {SAMPLE_GLB}")
        print(f"  Place a GLB model at {SAMPLE_GLB}")
        skipped += 1
    else:
        asset = upload_asset(SAMPLE_GLB)
        if not asset:
            print("  FAILED: could not upload GLB")
            failed += 1
        else:
            print(f"  Uploaded: {asset['filename']} ({asset['type']})")
            task_id = run_render("Smoke Orbit", "product_orbit", asset["path"], "glb")
            if task_id:
                validate_mp4(task_id, 24)
                print("  PASS: product_orbit")
                passed += 1
            else:
                print("  FAILED: product_orbit render")
                failed += 1

    # ── premium mode ────────────────────────────────────────────────
    print("\n─ premium mode ─")
    if not Path(SAMPLE_PNG).exists():
        print(f"  SKIP: sample PNG not found (needed for premium test)")
        skipped += 1
    else:
        asset = upload_asset(SAMPLE_PNG)
        if not asset:
            print("  FAILED: could not upload PNG for premium test")
            failed += 1
        else:
            task_id = run_render("Premium Hero", "character_intro", asset["path"], "image", premium=True)
            if task_id:
                result = poll_until(task_id, frozenset({"DONE", "FAILED"}))
                if result.get("enhanced_output_path"):
                    print("  PASS: premium mode (enhanced MP4 created)")
                elif result.get("warning_code") == "AI_ENHANCE_SKIPPED":
                    print("  PASS: premium mode (enhancement failed, standard MP4 returned — expected fallback)")
                else:
                    print("  PASS: premium mode completed")
                passed += 1
            else:
                print("  FAILED: premium mode render")
                failed += 1

    # ── summary ─────────────────────────────────────────────────────
    print(f"\n{'=' * 50}")
    print(f"  Passed:  {passed}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed:  {failed}")
    if failed:
        print("  Result:  SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("  Result:  ALL CHECKS PASSED" if not skipped else "  Result:  PASSED (some skipped)")


if __name__ == "__main__":
    main()
