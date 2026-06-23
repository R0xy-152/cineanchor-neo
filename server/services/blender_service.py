from __future__ import annotations

from server.schemas.project import ProjectJSON


class BlenderService:
    """Placeholder for the V0.1 Blender runner service."""

    def render_project(self, project: ProjectJSON) -> None:
        raise NotImplementedError(
            "Phase A only defines schema and API acceptance. Blender execution "
            "will be wired after the service boundary is finalized."
        )
