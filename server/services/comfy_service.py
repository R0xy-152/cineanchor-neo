from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Route 3 is PARTIAL. Direct full-frame img2img is forbidden (text corruption).
# Conservative ComfyUI reference + FFmpeg enhancement is validated but mild.
# ComfyService is a future hook — NOT part of the standard V0.1 render path.

ROUTE3_STATUS = "PARTIAL"


class ComfyService:
    """Optional future AI enhancement service.

    V0.1 does not require ComfyUI. The standard enhancement path uses FFmpeg
    filters only (see FFmpegService.enhance_mp4). This stub exists so the
    API contract can reference ComfyUI errors without importing a real
    ComfyUI client.
    """

    @staticmethod
    def is_available() -> bool:
        """Check whether ComfyUI is reachable. Always returns False in V0.1."""
        return False

    @staticmethod
    def enhance() -> None:
        """Future hook for ComfyUI-based enhancement.

        Raises NotImplementedError — ComfyUI is not wired in V0.1.
        """
        raise NotImplementedError(
            "ComfyUI is not part of the standard V0.1 render path. "
            "Use FFmpegService.enhance_mp4 for conservative enhancement."
        )
