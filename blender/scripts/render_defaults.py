"""
Single source of truth for all hardcoded defaults used by render_project.py.

Both the Pydantic schema (Field defaults) and the Blender render script
(.get(key, DEFAULT)) reference these constants so a refactor cannot silently
drift one side without the other.

In-scope (this loop): model transform, lighting, camera.
Deferred: stage/background elements (rings, glints, cloth noise), font_style.
"""

# ---------------------------------------------------------------------------
# Lighting defaults — one dict per light, keyed by light name
# ---------------------------------------------------------------------------

DEFAULT_LIGHTING: dict[str, dict] = {
    "key": {
        "location": (0, -3.4, 2.7),
        "energy": None,  # template-dependent: 170 (product) / 140 (character)
        "size": 4.7,
        "color": "#FFFFFF",
    },
    "rim_left": {
        "location": (-2.0, 0.7, 1.7),
        "energy": 220,
        "color": "#8CF2FF",  # (0.55, 0.95, 1.0)
    },
    "rim_right": {
        "location": (2.0, 0.8, 1.2),
        "energy": 150,
        "color": "#FF59A6",  # (1.0, 0.35, 0.65)
    },
    "back": {
        "location": (0, 2.2, 3.1),
        "energy": 115,
        "size": 3.1,
        "color": "#FFFFFF",
    },
    "silhouette_rim": {
        "location": (1.8, 2.5, 2.4),
        "energy": 100,
        "color": "#55EEFF",
        "spot_size": 45,
        "spot_blend": 0.3,
        "rotation": (-35, 0, -40),
    },
}


def template_key_energy(template: str) -> int:
    """Key light energy varies by template."""
    return 170 if template == "product_orbit" else 140


# ---------------------------------------------------------------------------
# Model transform defaults — None means auto-computed in the render script
# ---------------------------------------------------------------------------

DEFAULT_MODEL_TRANSFORM: dict = {
    "location": None,
    "rotation": None,
    "scale": None,  # auto: 2.55 / max_dim for GLB
}

# PNG plane defaults (used when asset type is "image")
DEFAULT_PNG_TARGET_VISIBLE_WIDTH = 1.85
DEFAULT_PNG_Z_OFFSET = 0.28
DEFAULT_PNG_TARGET = (0, 0, 0.12)

# GLB import defaults
DEFAULT_GLB_SCALE_DIVISOR = 2.55
DEFAULT_GLB_ROTATION_Z_DEG = 180
DEFAULT_GLB_Z_OFFSET = 0.18


# ---------------------------------------------------------------------------
# Camera defaults — what the current hardcoded behaviour produces
# ---------------------------------------------------------------------------

# Dolly camera
DOLLY_START_Y = -7.2
DOLLY_END_Y = -5.8
DOLLY_START_Z_OFFSET = 0.25
DOLLY_END_Z_OFFSET = 0.30
DOLLY_END_VIEW_WIDTH_MULT = 1.75
DOLLY_END_VIEW_WIDTH_MIN = 3.0
DOLLY_START_SCALE_FACTOR = 1.13

# Orbit camera
ORBIT_Y = -7.0
ORBIT_Z_OFFSET = 0.55
ORBIT_VIEW_HEIGHT_MULT = 2.1
ORBIT_DIAMETER_MULT = 1.8
ORBIT_VIEW_HEIGHT_MIN = 4.2
ORBIT_START_ANGLE_DEG = -18
ORBIT_END_ANGLE_DEG = 22
