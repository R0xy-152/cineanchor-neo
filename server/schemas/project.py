from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Template(str, Enum):
    CHARACTER_INTRO = "character_intro"
    PRODUCT_ORBIT = "product_orbit"


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

    duration: int = Field(ge=4, le=20)
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
    speed: float = Field(gt=0)
    start_distance: float = Field(gt=0)
    end_distance: float = Field(gt=0)
    height: float = Field(gt=0)
    focal_length: float = Field(gt=0)


class SceneSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    background: str = Field(min_length=1)
    lighting: str = Field(min_length=1)
    particles: bool
    fog: bool


class TextSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=80)
    subtitle: str = Field(default="", max_length=120)
    font_style: str = Field(min_length=1)


class AIEnhanceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    mode: AIEnhanceMode = AIEnhanceMode.CONSERVATIVE
    workflow: str | None = None


class ProjectJSON(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(pattern=r"^0\.1$")
    project_id: str = Field(min_length=1)
    template: Template
    output: OutputSpec
    assets: list[AssetSpec] = Field(min_length=1, max_length=1)
    camera: CameraSpec
    scene: SceneSpec
    text: TextSpec
    ai_enhance: AIEnhanceSpec = Field(default_factory=AIEnhanceSpec)

    @model_validator(mode="after")
    def validate_primary_asset(self) -> ProjectJSON:
        asset_ids = [asset.id for asset in self.assets]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("asset ids must be unique")

        if asset_ids != ["main_subject"]:
            raise ValueError("V0.1 requires exactly one asset with id=main_subject")

        main_asset = self.assets[0]
        if self.template == Template.CHARACTER_INTRO and main_asset.type != AssetType.IMAGE:
            raise ValueError("character_intro requires main_subject asset type=image")
        if self.template == Template.PRODUCT_ORBIT and main_asset.type != AssetType.GLB:
            raise ValueError("product_orbit requires main_subject asset type=glb")
        return self
