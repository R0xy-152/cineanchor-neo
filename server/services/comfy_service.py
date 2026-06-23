from __future__ import annotations


ROUTE3_STATUS = "PARTIAL"


class ComfyService:
    """Optional future enhancement service, not used in standard V0.1 rendering."""

    def enhance(self) -> None:
        raise NotImplementedError(
            "Route 3 is PARTIAL. ComfyUI is optional, not part of the standard "
            "Blender + FFmpeg render path, and future integration must preserve "
            "text and subject stability."
        )
