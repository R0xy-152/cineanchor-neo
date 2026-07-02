from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from server.schemas.project import BirthdayTimelineSpec, ProjectJSON
from server.services.errors import CineAnchorError, ErrorCode


class BirthdayFrameRenderer:
    """Deterministic 2D compositor for the character_birthday template.

    Pillow generates predictable PNG frames; the existing FFmpeg service remains
    responsible for H.264 encoding. No AI service or network request is involved.
    """

    @classmethod
    def render(
        cls,
        project: ProjectJSON,
        frames_dir: Path,
        asset_paths: dict[str, Path],
    ) -> None:
        try:
            renderer = cls(project, asset_paths)
        except (OSError, ValueError) as exc:
            raise CineAnchorError(
                ErrorCode.ASSET_IMPORT_FAILED,
                f"Birthday template asset import failed: {exc}",
            ) from exc

        frames_dir.mkdir(parents=True, exist_ok=True)
        try:
            for frame_index in range(project.output.frame_count):
                image = renderer.render_frame(frame_index)
                image.convert("RGB").save(
                    frames_dir / f"{frame_index + 1:04d}.png",
                    format="PNG",
                    compress_level=2,
                )
        except Exception as exc:
            raise CineAnchorError(
                ErrorCode.BLENDER_RENDER_FAILED,
                f"Birthday template frame generation failed: {exc}",
            ) from exc

        manifest = {
            "template": "character_birthday",
            "renderer": "deterministic_pillow_layers",
            "frame_count": project.output.frame_count,
            "resolution": list(project.output.dimensions),
            "components": [
                {"name": name, "start": span.start, "end": span.end}
                for name, span in renderer.timeline.ordered_items()
            ],
            "assets_present": sorted(asset_paths),
            "ai_required": False,
            "bgm_present": False,
        }
        (frames_dir.parent / "render_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def __init__(self, project: ProjectJSON, asset_paths: dict[str, Path]) -> None:
        self.project = project
        self.width, self.height = project.output.dimensions
        self.fps = project.output.fps
        self.timeline = project.timeline or BirthdayTimelineSpec.for_duration(project.output.duration)
        self.text = project.text
        self.style = project.style
        self.primary = self._hex(self.style.primary_color if self.style else "#C9414A")
        self.secondary = self._hex(self.style.secondary_color if self.style else "#5967B0")
        self.main_character = self._open_rgba(asset_paths["main_character"])
        self.logo = self._open_rgba(asset_paths["logo"]) if "logo" in asset_paths else None
        self.support_images = [
            self._open_rgba(asset_paths[key])
            for key in sorted(asset_paths)
            if key.startswith("support_image_")
        ]
        self._soft_background = self._make_gradient(
            self._mix(self.primary, (255, 255, 255), 0.86),
            self._mix(self.secondary, (255, 255, 255), 0.90),
        )
        self._strong_background = self._make_gradient(
            self._mix(self.secondary, (255, 255, 255), 0.18),
            self._mix(self.primary, (255, 255, 255), 0.12),
        )

    @staticmethod
    def _open_rgba(path: Path) -> Image.Image:
        with Image.open(path) as image:
            return image.convert("RGBA").copy()

    @staticmethod
    def _hex(value: str) -> tuple[int, int, int]:
        value = value.lstrip("#")
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]

    @staticmethod
    def _mix(a: tuple[int, int, int], b: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
        return tuple(round(left * (1 - amount) + right * amount) for left, right in zip(a, b))  # type: ignore[return-value]

    def _make_gradient(self, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
        strip = Image.new("RGB", (1, self.height))
        pixels = strip.load()
        for y in range(self.height):
            amount = y / max(1, self.height - 1)
            pixels[0, y] = self._mix(top, bottom, amount)
        return strip.resize((self.width, self.height)).convert("RGBA")

    def _font(self, size: int, *, serif: bool = False, bold: bool = False) -> ImageFont.ImageFont:
        preset = self.style.font_preset if self.style else "birthday_serif"
        use_serif = serif or "serif" in preset
        candidates: list[Path] = []
        if use_serif:
            candidates.extend([
                Path("C:/Windows/Fonts/georgiab.ttf" if bold else "C:/Windows/Fonts/georgia.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
            ])
        else:
            candidates.extend([
                Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
                Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            ])
        for candidate in candidates:
            if candidate.exists():
                return ImageFont.truetype(str(candidate), size=max(8, size))
        return ImageFont.load_default()

    def component_at(self, seconds: float) -> tuple[str, float]:
        items = self.timeline.ordered_items()
        for name, span in items:
            if span.start <= seconds < span.end or (
                name == items[-1][0] and math.isclose(seconds, span.end)
            ):
                return name, (seconds - span.start) / (span.end - span.start)
        prior = [(name, span) for name, span in items if span.end <= seconds]
        if prior:
            name, span = prior[-1]
            return name, 1.0
        return items[0][0], 0.0

    def render_frame(self, frame_index: int) -> Image.Image:
        seconds = frame_index / self.fps
        component, progress = self.component_at(seconds)
        method = getattr(self, f"_draw_{component}")
        frame = method(max(0.0, min(1.0, progress)), seconds)

        # Blur-zoom is strongest at the first entry and relaxes within 0.35 s.
        span = dict(self.timeline.ordered_items())[component]
        entry_age = max(0.0, seconds - span.start)
        if component in {"opening_date_card", "birthday_title_closeup"} and entry_age < 0.35:
            amount = 1.0 - entry_age / 0.35
            frame = self._zoom(frame, 1.0 + amount * 0.035).filter(
                ImageFilter.GaussianBlur(radius=amount * 7)
            )

        # A short white flash marks structural changes without hiding content.
        if component not in {"opening_date_card", "brand_end_card"} and entry_age < 0.10:
            flash = Image.new("RGBA", frame.size, (255, 255, 255, round(210 * (1 - entry_age / 0.10))))
            frame = Image.alpha_composite(frame, flash)

        if seconds < 0.35:
            black = Image.new("RGBA", frame.size, (255, 255, 255, 255))
            frame = Image.blend(black, frame, seconds / 0.35)
        return frame

    def _zoom(self, image: Image.Image, scale: float) -> Image.Image:
        resized = image.resize((round(self.width * scale), round(self.height * scale)), Image.Resampling.LANCZOS)
        left = (resized.width - self.width) // 2
        top = (resized.height - self.height) // 2
        return resized.crop((left, top, left + self.width, top + self.height))

    def _paste_contain(
        self,
        canvas: Image.Image,
        source: Image.Image,
        box: tuple[int, int, int, int],
        *,
        scale: float = 1.0,
        anchor: str = "center",
        opacity: float = 1.0,
    ) -> None:
        left, top, right, bottom = box
        target_w, target_h = right - left, bottom - top
        ratio = min(target_w / source.width, target_h / source.height) * scale
        image = source.resize(
            (max(1, round(source.width * ratio)), max(1, round(source.height * ratio))),
            Image.Resampling.LANCZOS,
        )
        if opacity < 1:
            image.putalpha(ImageEnhance.Brightness(image.getchannel("A")).enhance(opacity))
        x = left + (target_w - image.width) // 2
        y = top + (target_h - image.height) // 2
        if anchor == "bottom":
            y = bottom - image.height
        elif anchor == "top":
            y = top
        canvas.alpha_composite(image, (x, y))

    def _center_text(
        self,
        draw: ImageDraw.ImageDraw,
        xy: tuple[int, int],
        text: str,
        font: ImageFont.ImageFont,
        fill: tuple[int, int, int] | str,
        *,
        stroke_width: int = 0,
        stroke_fill: tuple[int, int, int] | str = "black",
    ) -> None:
        draw.text(
            xy, text, font=font, fill=fill, anchor="mm", align="center",
            stroke_width=stroke_width, stroke_fill=stroke_fill,
        )

    @staticmethod
    def _wrap_text(
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.ImageFont,
        max_width: int,
        max_lines: int = 2,
    ) -> str:
        tokens = text.split() if " " in text.strip() else list(text.strip())
        separator = " " if " " in text.strip() else ""
        lines: list[str] = []
        current = ""
        for token in tokens:
            candidate = token if not current else current + separator + token
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = token
            if len(lines) == max_lines - 1:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        return "\n".join(lines[:max_lines])

    def _draw_opening_date_card(self, progress: float, seconds: float) -> Image.Image:
        frame = self._soft_background.copy()
        draw = ImageDraw.Draw(frame)
        margin = round(self.width * 0.08)
        draw.rounded_rectangle(
            (margin, round(self.height * 0.18), self.width - margin, round(self.height * 0.82)),
            radius=36,
            fill=(255, 255, 255, 205),
            outline=self.primary,
            width=5,
        )
        date = self.text.birthday_date.replace(".", "\n").replace("/", "\n")
        self._center_text(
            draw,
            (self.width // 2, round(self.height * 0.49)),
            date,
            self._font(round(self.width * 0.31), serif=True, bold=True),
            self.primary,
        )
        self._center_text(
            draw,
            (self.width // 2, round(self.height * 0.76)),
            "BIRTHDAY / ANNIVERSARY",
            self._font(round(self.width * 0.045), bold=True),
            self.secondary,
        )
        return frame

    def _draw_name_card(self, progress: float, seconds: float) -> Image.Image:
        frame = Image.new("RGBA", (self.width, self.height), "white")
        draw = ImageDraw.Draw(frame)
        name = self.text.character_name.upper()
        draw.rectangle((0, round(self.height * 0.47), self.width, round(self.height * 0.53)), fill=self.primary)
        self._center_text(
            draw,
            (self.width // 2, round(self.height * 0.40)),
            name,
            self._font(round(self.width * 0.095), serif=True, bold=True),
            self.primary,
        )
        self._center_text(
            draw,
            (self.width // 2, round(self.height * 0.60)),
            self.text.birthday_date,
            self._font(round(self.width * 0.07), bold=True),
            self.secondary,
        )
        return frame

    def _draw_birthday_title_closeup(self, progress: float, seconds: float) -> Image.Image:
        frame = self._soft_background.copy()
        scale = 1.05 + 0.06 * progress
        self._paste_contain(
            frame,
            self.main_character,
            (-round(self.width * 0.18), round(self.height * 0.03), round(self.width * 1.18), round(self.height * 0.94)),
            scale=scale,
            anchor="top",
        )
        draw = ImageDraw.Draw(frame)
        ribbon_y = round(self.height * 0.72)
        draw.polygon(
            [(0, ribbon_y), (self.width, ribbon_y - 35), (self.width, ribbon_y + 190), (0, ribbon_y + 225)],
            fill=(*self.primary, 238),
        )
        title = self.text.main_title or self.text.title
        self._center_text(
            draw,
            (self.width // 2, ribbon_y + 85),
            title.upper(),
            self._font(round(self.width * 0.083), bold=True),
            "white",
        )
        self._draw_particles(frame, seconds, density=30)
        return frame

    def _draw_character_poster(self, progress: float, seconds: float) -> Image.Image:
        frame = self._soft_background.copy()
        draw = ImageDraw.Draw(frame)
        name = self.text.character_name.upper()
        for row, alpha in enumerate((36, 25, 18)):
            draw.text(
                (-20, round(self.height * (0.11 + row * 0.10))),
                name,
                font=self._font(round(self.width * 0.13), serif=True, bold=True),
                fill=(*self.primary, alpha),
            )
        self._paste_contain(
            frame,
            self.main_character,
            (round(self.width * 0.18), round(self.height * 0.08), round(self.width * 1.02), round(self.height * 0.94)),
            scale=0.92 + progress * 0.04,
            anchor="bottom",
        )
        self._draw_support_cards(frame)
        draw = ImageDraw.Draw(frame)
        draw.rectangle((0, round(self.height * 0.88), self.width, self.height), fill=(*self.secondary, 232))
        draw.text(
            (round(self.width * 0.055), round(self.height * 0.905)),
            name,
            font=self._font(round(self.width * 0.067), serif=True, bold=True),
            fill="white",
        )
        draw.text(
            (round(self.width * 0.058), round(self.height * 0.955)),
            self.text.birthday_date,
            font=self._font(round(self.width * 0.043), bold=True),
            fill=self._mix(self.secondary, (255, 255, 255), 0.72),
        )
        self._draw_particles(frame, seconds, density=24)
        return frame

    def _draw_support_cards(self, frame: Image.Image) -> None:
        sources = self.support_images or [self.main_character]
        card_w, card_h = round(self.width * 0.19), round(self.height * 0.12)
        for index, source in enumerate(sources[:3]):
            thumb = ImageOps.fit(source, (card_w, card_h), method=Image.Resampling.LANCZOS)
            card = Image.new("RGBA", (card_w + 12, card_h + 12), (255, 255, 255, 238))
            card.alpha_composite(thumb, (6, 6))
            x = round(self.width * 0.035)
            y = round(self.height * (0.55 + index * 0.135))
            frame.alpha_composite(card, (x, y))

    def _draw_character_interaction(self, progress: float, seconds: float) -> Image.Image:
        frame = self._strong_background.copy()
        sources = self.support_images or [self.main_character]
        source_index = min(len(sources) - 1, int(progress * len(sources)))
        source = sources[source_index]
        self._paste_contain(
            frame,
            source,
            (-round(self.width * 0.08), 0, round(self.width * 1.08), round(self.height * 0.92)),
            scale=1.0 + 0.035 * math.sin(seconds * 1.2),
            anchor="center",
        )
        lines = self.text.subtitle_lines or ([self.text.subtitle] if self.text.subtitle else [])
        if lines:
            line_index = min(len(lines) - 1, int(progress * len(lines)))
            self._draw_dialogue(frame, lines[line_index])
        self._draw_particles(frame, seconds, density=18)
        return frame

    def _draw_dialogue(self, frame: Image.Image, text: str) -> None:
        draw = ImageDraw.Draw(frame)
        y = round(self.height * 0.84)
        font = self._font(round(self.width * 0.047), bold=True)
        wrapped = self._wrap_text(draw, text, font, round(self.width * 0.78), max_lines=2)
        draw.rounded_rectangle(
            (round(self.width * 0.05), y - 70, round(self.width * 0.95), y + 110),
            radius=28,
            fill=(0, 0, 0, 105),
        )
        self._center_text(
            draw,
            (self.width // 2, y + 18),
            wrapped,
            font,
            "white",
            stroke_width=max(3, round(self.width * 0.004)),
            stroke_fill="black",
        )

    def _draw_brand_end_card(self, progress: float, seconds: float) -> Image.Image:
        frame = Image.new("RGBA", (self.width, self.height), "white")
        draw = ImageDraw.Draw(frame)
        if self.logo is not None:
            self._paste_contain(
                frame,
                self.logo,
                (round(self.width * 0.16), round(self.height * 0.09), round(self.width * 0.84), round(self.height * 0.27)),
            )
        else:
            self._center_text(
                draw,
                (self.width // 2, round(self.height * 0.18)),
                (self.text.main_title or self.text.title).upper(),
                self._font(round(self.width * 0.07), bold=True),
                self.secondary,
            )

        circle_size = round(self.width * 0.55)
        avatar = ImageOps.fit(self.main_character, (circle_size, circle_size), method=Image.Resampling.LANCZOS)
        mask = Image.new("L", (circle_size, circle_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, circle_size - 1, circle_size - 1), fill=255)
        avatar.putalpha(mask)
        x = (self.width - circle_size) // 2
        y = round(self.height * 0.31)
        draw.ellipse((x - 8, y - 8, x + circle_size + 8, y + circle_size + 8), fill=self._mix(self.secondary, (255, 255, 255), 0.78))
        frame.alpha_composite(avatar, (x, y))
        self._center_text(
            draw,
            (self.width // 2, round(self.height * 0.72)),
            self.text.character_name,
            self._font(round(self.width * 0.073), serif=True, bold=True),
            self.primary,
        )
        if self.text.cta:
            draw.rounded_rectangle(
                (round(self.width * 0.20), round(self.height * 0.78), round(self.width * 0.80), round(self.height * 0.845)),
                radius=30,
                fill=self.secondary,
            )
            self._center_text(
                draw,
                (self.width // 2, round(self.height * 0.812)),
                self.text.cta,
                self._font(round(self.width * 0.045), bold=True),
                "white",
            )
        if self.text.copyright:
            self._center_text(
                draw,
                (self.width // 2, round(self.height * 0.94)),
                self.text.copyright,
                self._font(round(self.width * 0.026)),
                (90, 90, 90),
            )
        if progress < 0.32:
            self._draw_cloud_wipe(frame, progress / 0.32)
        return frame

    def _draw_particles(self, frame: Image.Image, seconds: float, *, density: int) -> None:
        overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        seed = sum(ord(char) for char in self.project.project_id)
        randomizer = random.Random(seed)
        for index in range(density):
            origin_x = randomizer.random() * self.width
            origin_y = randomizer.random() * self.height
            speed = self.height * (0.018 + randomizer.random() * 0.025)
            x = (origin_x + math.sin(seconds * 0.8 + index) * self.width * 0.05) % self.width
            y = (origin_y + seconds * speed) % (self.height + 80) - 40
            size = round(self.width * (0.007 + randomizer.random() * 0.012))
            color = self._mix(self.primary, (255, 255, 255), 0.35 + randomizer.random() * 0.35)
            draw.ellipse((x - size, y - size // 2, x + size, y + size // 2), fill=(*color, 150))
        frame.alpha_composite(overlay)

    def _draw_cloud_wipe(self, frame: Image.Image, progress: float) -> None:
        overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        edge = round((-0.15 + progress * 1.30) * self.width)
        draw.rectangle((min(self.width, edge + 130), 0, self.width, self.height), fill=(255, 255, 255, 245))
        for index in range(14):
            y = round((index + 0.5) * self.height / 14)
            radius = round(self.width * (0.13 + (index % 3) * 0.025))
            draw.ellipse((edge - radius, y - radius, edge + radius, y + radius), fill=(255, 255, 255, 230))
        frame.alpha_composite(overlay.filter(ImageFilter.GaussianBlur(radius=18)))
