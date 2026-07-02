#!/usr/bin/env python3
"""CineAnchor V0.1 — Environment check script.

Run this after cloning the repo to verify your environment is ready.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ALL_OK = True


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def check(ok: bool, message: str) -> None:
    global ALL_OK
    status = "OK" if ok else "FAIL"
    print(f"  [{status}]  {message}")
    if not ok:
        ALL_OK = False


def main() -> None:
    print("CineAnchor V0.1 Environment Check\n")

    # ── Python version ──────────────────────────────────────────────
    version = sys.version_info
    check(
        version >= (3, 11),
        f"Python >= 3.11 (found {version.major}.{version.minor}.{version.micro})",
    )

    # ── Required packages ───────────────────────────────────────────
    required = {"fastapi", "uvicorn", "pydantic", "python-multipart"}
    try:
        import fastapi, uvicorn, pydantic  # noqa: F401
        import multipart  # noqa: F401
        check(True, f"Required packages installed: {', '.join(sorted(required))}")
    except ImportError as exc:
        check(False, f"Missing package: {exc.name if hasattr(exc, 'name') else exc}. "
              f"Run: pip install -r server/requirements.txt")

    # ── Blender ─────────────────────────────────────────────────────
    blender_path = _env("BLENDER_PATH", "blender")
    blender_exists = Path(blender_path).exists() or bool(subprocess.run(
        ["where", blender_path], capture_output=True, text=True
    ).stdout.strip())
    check(blender_exists, f"BLENDER_PATH exists or found: {blender_path}")

    if blender_exists:
        try:
            result = subprocess.run(
                [blender_path, "--version"], capture_output=True, text=True, timeout=30
            )
            blender_version_line = result.stdout.strip().split("\n")[0] if result.stdout else "unknown"
            check(
                result.returncode == 0,
                f"Blender --version: {blender_version_line}",
            )
        except FileNotFoundError:
            check(False, f"Blender not found at: {blender_path}")
        except subprocess.TimeoutExpired:
            check(False, "Blender --version timed out")

    # ── FFmpeg ──────────────────────────────────────────────────────
    ffmpeg_path = _env("FFMPEG_PATH", "ffmpeg")
    ffmpeg_exists = Path(ffmpeg_path).exists() or bool(subprocess.run(
        ["where", ffmpeg_path], capture_output=True, text=True
    ).stdout.strip())
    check(ffmpeg_exists, f"FFMPEG_PATH exists or found: {ffmpeg_path}")

    if ffmpeg_exists:
        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"], capture_output=True, text=True, timeout=30
            )
            ffmpeg_line = result.stdout.strip().split("\n")[0] if result.stdout else "unknown"
            check(
                result.returncode == 0,
                f"FFmpeg -version: {ffmpeg_line[:80]}",
            )
        except FileNotFoundError:
            check(False, f"FFmpeg not found at: {ffmpeg_path}")
        except subprocess.TimeoutExpired:
            check(False, "FFmpeg -version timed out")

    # ── Storage directories ─────────────────────────────────────────
    storage = REPO_ROOT / "storage"
    try:
        for sub in ("assets", "renders", "exports", "projects", "logs"):
            (storage / sub).mkdir(parents=True, exist_ok=True)
        check(True, f"Storage directories created under {storage}")
    except OSError as exc:
        check(False, f"Cannot create storage directories: {exc}")

    # ── Web UI ──────────────────────────────────────────────────────
    web_index = REPO_ROOT / "apps" / "web" / "index.html"
    check(web_index.exists(), f"Web UI found: {web_index}")

    # ── Sample assets (optional) ────────────────────────────────────
    for name, path in (
        ("hero.png", REPO_ROOT / "samples" / "assets" / "hero.png"),
        ("model.glb", REPO_ROOT / "samples" / "assets" / "model.glb"),
    ):
        if path.exists():
            check(True, f"Sample asset available: {name}")
        else:
            print(f"  [INFO]  Sample asset not found: {name} (place at {path})")

    # ── ComfyUI (optional, not required) ────────────────────────────
    print(f"  [INFO]  ComfyUI: not required for V0.1 standard rendering")

    # ── Summary ─────────────────────────────────────────────────────
    print()
    if ALL_OK:
        print("Environment check PASSED. Ready to start.")
        print("  Run:   scripts\\start_server.bat")
        print("  Open:  http://127.0.0.1:8000/web/")
    else:
        print("Environment check FAILED. Fix issues above before starting.")
        sys.exit(1)


if __name__ == "__main__":
    main()
