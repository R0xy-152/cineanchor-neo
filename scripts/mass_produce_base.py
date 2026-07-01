#!/usr/bin/env python3
"""
Mass-produce 3 base videos for the portfolio + 2b generality validation.

Each base is text-free, particle-free, glints-off, 1080p/24fps/4s H.264 MP4.
Output: storage/exports/mass_produce/{name}/final.mp4

Usage:
  $env:BLENDER_PATH = "..."
  $env:FFMPEG_PATH = "..."
  .venv/Scripts/python.exe scripts/mass_produce_base.py

Config: scripts/base_configs.json
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

# Project root on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from server.config import load_settings
from server.schemas.project import ProjectJSON
from server.services.blender_service import BlenderService
from server.services.ffmpeg_service import FFmpegService
from server.services.errors import CineAnchorError


def load_configs(config_path: Path) -> list[dict]:
    with open(config_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_project_json(cfg: dict, config_index: int) -> ProjectJSON:
    """Build a ProjectJSON model from a base config dict.

    Fills in all required fields with text-free / particle-free / glints-off
    defaults for Seedance-friendly base output.
    """
    project_id = f"mass-produce-{cfg['name']}-{config_index:02d}"

    return ProjectJSON.model_validate({
        "version": "0.1",
        "project_id": project_id,
        "template": cfg["template"],
        "output": cfg["output"],
        "assets": [
            {
                "id": "main_subject",
                "type": "glb",
                "path": cfg["asset_path"],
            }
        ],
        "camera": cfg["camera"],
        "scene": {
            "background": "dark_stage",
            "lighting": "rim_back",
            "particles": None,
            "fog": False,
            "background_enhance": {
                "rim_light": False,
                "rim_light_color": "#55EEFF",
                "rim_light_energy": 100,
                "cloth_texture": False,
                "cloth_mix": 0.07,
                "glints": False,
                "text_overlay": False,
            },
            "model_transform": cfg.get("model_transform"),
            "lighting_overrides": cfg.get("lighting_overrides"),
        },
        "text": {
            "title": "",
            "subtitle": "",
            "font_style": "bold_game",
        },
        "ai_enhance": {
            "enabled": False,
            "mode": "conservative",
        },
    })


def main() -> None:
    settings = load_settings()

    config_path = REPO_ROOT / "scripts" / "base_configs.json"
    configs = load_configs(config_path)
    print(f"Loaded {len(configs)} base config(s) from {config_path}")

    exports_root = settings.EXPORTS_DIR / "mass_produce"
    exports_root.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

    for idx, cfg in enumerate(configs):
        name = cfg["name"]
        task_id = f"mp-{name}-{uuid.uuid4().hex[:8]}"
        output_dir = exports_root / name
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "final.mp4"

        print(f"\n{'='*60}")
        print(f"[{idx+1}/{len(configs)}] {name}")
        print(f"  asset: {cfg['asset_path']}")
        print(f"  camera: {cfg['camera']['motion']}")
        print(f"  output: {output_path}")
        print(f"{'='*60}")

        try:
            project = build_project_json(cfg, idx)

            # Write project.json alongside for reproducibility
            project_file = output_dir / "project.json"
            project_file.write_text(
                project.model_dump_json(indent=2), encoding="utf-8"
            )
            print(f"  project.json: {project_file}")

            # ── Blender render ────────────────────────────────────
            print(f"  [1/2] Blender rendering...")
            BlenderService.render_project(project, task_id)

            # ── FFmpeg compose (no effects, no particles) ─────────
            frames_dir = settings.RENDERS_DIR / task_id / "frames"
            print(f"  [2/2] FFmpeg composing...")
            FFmpegService.compose_mp4(
                frames_dir=frames_dir,
                output_path=output_path,
                fps=project.output.fps,
                task_id=task_id,
            )

            print(f"  ✓ DONE: {output_path}")
            results.append({
                "name": name,
                "output_path": str(output_path),
                "status": "ok",
                "task_id": task_id,
            })

        except CineAnchorError as exc:
            print(f"  ✗ FAILED [{exc.code.value}]: {exc.message}")
            results.append({
                "name": name,
                "output_path": str(output_path),
                "status": "failed",
                "error_code": exc.code.value,
                "error_message": exc.message,
            })
        except Exception as exc:
            print(f"  ✗ FAILED (unexpected): {exc}")
            results.append({
                "name": name,
                "output_path": str(output_path),
                "status": "failed",
                "error_message": str(exc),
            })

    # ── Summary ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    ok = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"  {ok} succeeded, {failed} failed")

    for r in results:
        status = "✓" if r["status"] == "ok" else "✗"
        print(f"  {status} {r['name']}: {r['output_path']}")
        if r["status"] == "failed":
            print(f"       error: {r.get('error_message', 'unknown')}")

    # Output all file paths for 启鸣 retrieval (acceptance #7)
    print(f"\n--- FILE PATHS FOR RETRIEVAL ---")
    for r in results:
        print(r["output_path"])

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
