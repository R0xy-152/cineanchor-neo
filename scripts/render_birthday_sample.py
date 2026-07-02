#!/usr/bin/env python3
"""Render a 15-second character_birthday sample without starting FastAPI."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--character", required=True, type=Path, help="transparent character PNG")
    result.add_argument("--logo", type=Path, help="optional PNG logo")
    result.add_argument("--output", required=True, type=Path, help="target MP4")
    result.add_argument("--ffmpeg", default=os.environ.get("FFMPEG_PATH", "ffmpeg"))
    result.add_argument("--name", default="DEMO CHARACTER")
    result.add_argument("--date", default="07.01")
    result.add_argument("--title", default="HAPPY BIRTHDAY")
    result.add_argument("--primary", default="#C9414A")
    result.add_argument("--secondary", default="#5967B0")
    result.add_argument("--keep-frames", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    os.environ["FFMPEG_PATH"] = args.ffmpeg

    # Imports happen after FFMPEG_PATH is set because server.config is loaded once.
    from server.schemas.project import ProjectJSON
    from server.services.birthday_renderer import BirthdayFrameRenderer
    from server.services.ffmpeg_service import FFmpegService

    assets = [{"id": "main_character", "type": "image", "path": str(args.character.resolve())}]
    paths = {"main_character": args.character.resolve()}
    if args.logo:
        assets.append({"id": "logo", "type": "image", "path": str(args.logo.resolve())})
        paths["logo"] = args.logo.resolve()

    payload = {
        "version": "0.2", "project_id": "cli-birthday-sample", "template": "character_birthday",
        "output": {"duration": 15, "fps": 24, "aspect_ratio": "9:16", "resolution": "1080p"},
        "assets": assets,
        "camera": {
            "motion": "dolly_in", "speed": 1.0, "start_distance": 7.2,
            "end_distance": 5.8, "height": 1.4, "focal_length": 70.0,
        },
        "scene": {"background": "soft_poster", "lighting": "flat_graphic", "particles": None, "fog": False},
        "text": {
            "title": args.title, "subtitle": "", "font_style": "birthday_serif",
            "character_name": args.name, "birthday_date": args.date, "main_title": args.title,
            "subtitle_lines": ["Today is my birthday.", "Thank you for celebrating with me."],
            "cta": "Celebrate now",
        },
        "style": {
            "theme": "cute_school", "primary_color": args.primary,
            "secondary_color": args.secondary, "background_style": "soft_poster",
            "font_preset": "birthday_serif", "subtitle_preset": "white_black_stroke",
            "particle_preset": "petal_soft",
        },
    }
    project = ProjectJSON.model_validate(payload)
    temp_root = Path(tempfile.mkdtemp(prefix="cineanchor-birthday-"))
    frames_dir = temp_root / "frames"
    try:
        BirthdayFrameRenderer.render(project, frames_dir, paths)
        FFmpegService.compose_mp4(frames_dir, args.output.resolve(), 24, "birthday-cli", timeout=300)
        print(args.output.resolve())
        if args.keep_frames:
            kept = args.output.resolve().with_suffix("")
            shutil.copytree(temp_root, kept, dirs_exist_ok=True)
            print(f"frames: {kept}")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
