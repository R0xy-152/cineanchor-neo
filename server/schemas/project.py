from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Template(str, Enum):
    CHARACTER_INTRO = "character_intro"
    PRODUCT_ORBIT = "product_orbit"
    CHARACTER_BIRTHDAY = "character_birthday"


class AssetType(str, Enum):
    IMAGE = "image"
    GLB = "glb"


class AspectRatio(str, Enum):
    NINE_SIXTEEN = "9:16"
    SIXTEEN_NINE = "16:9"
    ONE_ONE = "1:1"


class Resolution(str, Enum):
    P1080 = "1080p"


class CameraMotion(str, Enum):
    DOLLY_IN = "dolly_in"
    ORBIT = "orbit"


class AIEnhanceMode(str, Enum):
    CONSERVATIVE = "conservative"


RESOLUTION_MAP: dict[tuple[AspectRatio, Resolution], tuple[int, int]] = {
    (AspectRatio.NINE_SIXTEEN, Resolution.P1080): (1080, 1920),
    (AspectRatio.SIXTEEN_NINE, Resolution.P1080): (1920, 1080),
    (AspectRatio.ONE_ONE, Resolution.P1080): (1080, 1080),
}


def resolve_dimensions(
    aspect_ratio: AspectRatio | str,
    resolution: Resolution | str,
) -> tuple[int, int]:
    key = (AspectRatio(aspect_ratio), Resolution(resolution))
    return RESOLUTION_MAP[key]


class OutputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration: int = Field(ge=4, le=30)
    fps: Literal[24]
    aspect_ratio: AspectRatio
    resolution: Resolution

    @property
    def dimensions(self) -> tuple[int, int]:
        return resolve_dimensions(self.aspect_ratio, self.resolution)

    @property
    def frame_count(self) -> int:
        return self.duration * self.fps


class AssetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: AssetType
    path: str = Field(min_length=1)


class CameraSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motion: CameraMotion
    preset: str | None = None  # ADJ-7: optional, overrides motion/distances when set
    speed: float = Field(gt=0)
    start_distance: float = Field(gt=0)
    end_distance: float = Field(gt=0)
    height: float = Field(gt=0)
    focal_length: float = Field(gt=0)
    # Loop 08: interactive keyframes
    keyframes: list[dict[str, Any]] | None = None  # [{t, pos: [x,y,z], quat: [x,y,z,w], fov}]
    shots: list[dict[str, Any]] | None = None      # [{index, keyframes, cut}]


class ParticlesSpec(BaseModel):
    """Particle overlay configuration for post-render compositing.

    All parameters are tunable without 3D re-render (acceptance #7).
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    density: float = Field(default=1.0, ge=0.0, le=2.0)
    speed: float = Field(default=1.0, ge=0.0, le=3.0)
    opacity: float = Field(default=0.6, ge=0.0, le=1.0)
    color: str = Field(default="#FF8C2E", pattern=r"^#[0-9a-fA-F]{6}$")


class BackgroundEnhanceSpec(BaseModel):
    """Deterministic background enhancements baked at Blender render time."""

    model_config = ConfigDict(extra="forbid")

    rim_light: bool = True
    rim_light_color: str = Field(default="#55EEFF", pattern=r"^#[0-9a-fA-F]{6}$")
    rim_light_energy: float = Field(default=100.0, ge=20.0, le=300.0)
    cloth_texture: bool = True
    cloth_mix: float = Field(default=0.07, ge=0.0, le=0.5)
    glints: bool = True
    text_overlay: bool = True
    stage_ring: bool = True


class ModelTransformSpec(BaseModel):
    """Model position / rotation / scale overrides.

    All fields optional — omit to use auto-computed defaults.
    """

    model_config = ConfigDict(extra="forbid")

    location: tuple[float, float, float] | None = None
    rotation: tuple[float, float, float] | None = None  # Euler, degrees
    scale: float | None = Field(default=None, gt=0)


class LightDefSpec(BaseModel):
    """Single-light parameter overrides. All optional — omit to use template defaults."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    location: tuple[float, float, float] | None = None
    energy: float | None = Field(default=None, gt=0)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    size: float | None = Field(default=None, gt=0)


class LightingOverridesSpec(BaseModel):
    """Per-light overrides. Each light optional — None means keep the template default."""

    model_config = ConfigDict(extra="forbid")

    key: LightDefSpec | None = None
    rim_left: LightDefSpec | None = None
    rim_right: LightDefSpec | None = None
    back: LightDefSpec | None = None
    silhouette_rim: LightDefSpec | None = None


class SceneSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    background: str = Field(min_length=1)
    lighting: str = Field(min_length=1)
    particles: ParticlesSpec | None = None
    fog: bool
    background_enhance: BackgroundEnhanceSpec = Field(
        default_factory=BackgroundEnhanceSpec
    )
    model_transform: ModelTransformSpec | None = None
    lighting_overrides: LightingOverridesSpec | None = None


class TextSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="", max_length=80)
    subtitle: str = Field(default="", max_length=120)
    font_style: str = Field(min_length=1)
    character_name: str = Field(default="", max_length=80)
    birthday_date: str = Field(default="", max_length=20)
    main_title: str = Field(default="", max_length=80)
    subtitle_lines: list[str] = Field(default_factory=list, max_length=3)
    cta: str = Field(default="", max_length=80)
    copyright: str = Field(default="", max_length=160)

    @model_validator(mode="after")
    def validate_subtitle_lines(self) -> TextSpec:
        if any(not line.strip() or len(line) > 100 for line in self.subtitle_lines):
            raise ValueError("subtitle_lines must contain 1-100 character non-empty strings")
        return self


class BirthdayStyleSpec(BaseModel):
    """Deterministic visual preset for the character birthday template."""

    model_config = ConfigDict(extra="forbid")

    theme: str = Field(default="cute_school", min_length=1, max_length=40)
    primary_color: str = Field(default="#C9414A", pattern=r"^#[0-9a-fA-F]{6}$")
    secondary_color: str = Field(default="#5967B0", pattern=r"^#[0-9a-fA-F]{6}$")
    background_style: str = Field(default="soft_poster", min_length=1, max_length=40)
    font_preset: str = Field(default="birthday_serif", min_length=1, max_length=40)
    subtitle_preset: str = Field(default="white_black_stroke", min_length=1, max_length=40)
    particle_preset: str = Field(default="petal_soft", min_length=1, max_length=40)


class TimeRangeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: float = Field(ge=0)
    end: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_order(self) -> TimeRangeSpec:
        if self.end <= self.start:
            raise ValueError("timeline range end must be greater than start")
        return self


class BirthdayTimelineSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opening_date_card: TimeRangeSpec
    name_card: TimeRangeSpec
    birthday_title_closeup: TimeRangeSpec
    character_poster: TimeRangeSpec
    character_interaction: TimeRangeSpec
    brand_end_card: TimeRangeSpec

    @classmethod
    def for_duration(cls, duration: float) -> BirthdayTimelineSpec:
        # The 15 s MVP rhythm scales cleanly for 27 s custom exports.
        stops = [0.0, 2.0, 3.0, 5.5, 9.0, 12.5, 15.0]
        scale = duration / 15.0
        ranges = [TimeRangeSpec(start=a * scale, end=b * scale) for a, b in zip(stops, stops[1:])]
        return cls(
            opening_date_card=ranges[0],
            name_card=ranges[1],
            birthday_title_closeup=ranges[2],
            character_poster=ranges[3],
            character_interaction=ranges[4],
            brand_end_card=ranges[5],
        )

    def ordered_items(self) -> list[tuple[str, TimeRangeSpec]]:
        return [
            ("opening_date_card", self.opening_date_card),
            ("name_card", self.name_card),
            ("birthday_title_closeup", self.birthday_title_closeup),
            ("character_poster", self.character_poster),
            ("character_interaction", self.character_interaction),
            ("brand_end_card", self.brand_end_card),
        ]


class AIEnhanceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    mode: AIEnhanceMode = AIEnhanceMode.CONSERVATIVE
    workflow: str | None = None


class ProjectJSON(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(pattern=r"^0\.[12]$")
    project_id: str = Field(min_length=1)
    template: Template
    output: OutputSpec
    assets: list[AssetSpec] = Field(min_length=1, max_length=5)
    camera: CameraSpec
    scene: SceneSpec
    text: TextSpec
    style: BirthdayStyleSpec | None = None
    timeline: BirthdayTimelineSpec | None = None
    ai_enhance: AIEnhanceSpec = Field(default_factory=AIEnhanceSpec)

    @model_validator(mode="after")
    def validate_primary_asset(self) -> ProjectJSON:
        asset_ids = [asset.id for asset in self.assets]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("asset ids must be unique")

        if self.template in {Template.CHARACTER_INTRO, Template.PRODUCT_ORBIT}:
            if asset_ids != ["main_subject"]:
                raise ValueError("legacy templates require exactly one asset with id=main_subject")
            main_asset = self.assets[0]
            if self.template == Template.CHARACTER_INTRO and main_asset.type != AssetType.IMAGE:
                raise ValueError("character_intro requires main_subject asset type=image")
            if self.template == Template.PRODUCT_ORBIT and main_asset.type != AssetType.GLB:
                raise ValueError("product_orbit requires main_subject asset type=glb")
            return self

        if self.version != "0.2":
            raise ValueError("character_birthday requires Project JSON version 0.2")
        if self.output.aspect_ratio != AspectRatio.NINE_SIXTEEN:
            raise ValueError("character_birthday requires aspect_ratio=9:16")
        allowed_ids = {"main_character", "logo", "support_image_1", "support_image_2", "support_image_3"}
        unknown_ids = set(asset_ids) - allowed_ids
        if unknown_ids:
            raise ValueError(f"unsupported character_birthday asset ids: {sorted(unknown_ids)}")
        if "main_character" not in asset_ids:
            raise ValueError("character_birthday requires main_character")
        if any(asset.type != AssetType.IMAGE for asset in self.assets):
            raise ValueError("character_birthday V0.2 assets must be PNG images")
        if not self.text.character_name.strip():
            raise ValueError("character_birthday requires text.character_name")
        if not self.text.birthday_date.strip():
            raise ValueError("character_birthday requires text.birthday_date")
        if not (self.text.main_title.strip() or self.text.title.strip()):
            raise ValueError("character_birthday requires text.main_title or text.title")
        if self.style is None:
            self.style = BirthdayStyleSpec()
        if self.timeline is None:
            self.timeline = BirthdayTimelineSpec.for_duration(self.output.duration)

        previous_end = 0.0
        for name, time_range in self.timeline.ordered_items():
            if time_range.start < previous_end - 1e-6:
                raise ValueError(f"timeline component {name} overlaps the previous component")
            if time_range.end > self.output.duration + 1e-6:
                raise ValueError(f"timeline component {name} exceeds output.duration")
            previous_end = time_range.end
        return self
