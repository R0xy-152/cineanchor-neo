# CineAnchor V0.1 Project JSON Schema

This document defines the formal V0.1 Project JSON shape used by the local
render API. The Spike JSON under `spikes/render_json/` remains historical
validation code.

## Character Intro Example

```json
{
  "version": "0.1",
  "project_id": "demo-character-intro",
  "template": "character_intro",
  "output": {
    "duration": 8,
    "fps": 24,
    "aspect_ratio": "9:16",
    "resolution": "1080p"
  },
  "assets": [
    {
      "id": "main_subject",
      "type": "image",
      "path": "storage/assets/hero.png"
    }
  ],
  "camera": {
    "motion": "dolly_in",
    "speed": 1.0,
    "start_distance": 7.2,
    "end_distance": 5.8,
    "height": 1.4,
    "focal_length": 70.0
  },
  "scene": {
    "background": "dark_stage",
    "lighting": "rim_back",
    "particles": true,
    "fog": false
  },
  "text": {
    "title": "New Hero Arrival",
    "subtitle": "Limited Event",
    "font_style": "bold_game"
  },
  "ai_enhance": {
    "enabled": false,
    "mode": "conservative",
    "workflow": null
  }
}
```

## Product Orbit Example

```json
{
  "version": "0.1",
  "project_id": "demo-product-orbit",
  "template": "product_orbit",
  "output": {
    "duration": 8,
    "fps": 24,
    "aspect_ratio": "16:9",
    "resolution": "1080p"
  },
  "assets": [
    {
      "id": "main_subject",
      "type": "glb",
      "path": "storage/assets/model.glb"
    }
  ],
  "camera": {
    "motion": "orbit",
    "speed": 1.0,
    "start_distance": 7.0,
    "end_distance": 7.0,
    "height": 1.5,
    "focal_length": 70.0
  },
  "scene": {
    "background": "dark_stage",
    "lighting": "rim_back",
    "particles": false,
    "fog": false
  },
  "text": {
    "title": "Product Orbit",
    "subtitle": "GLB Showcase",
    "font_style": "bold_game"
  }
}
```

If `ai_enhance` is omitted, it defaults to:

```json
{
  "enabled": false,
  "mode": "conservative",
  "workflow": null
}
```

## Field Table

| Field | Type | Required | Notes |
|---|---:|---:|---|
| `version` | string | yes | V0.1 accepts `0.1`. |
| `project_id` | string | yes | Caller-provided project identifier. |
| `template` | enum | yes | `character_intro` or `product_orbit`. |
| `output.duration` | integer | yes | 4 to 20 seconds. |
| `output.fps` | integer | yes | V0.1 supports 24 only. |
| `output.aspect_ratio` | enum | yes | `9:16`, `16:9`, `1:1`. |
| `output.resolution` | enum | yes | `1080p`. |
| `assets[].id` | string | yes | V0.1 primary subject must be `main_subject`. |
| `assets[].type` | enum | yes | `image` or `glb`. |
| `assets[].path` | string | yes | Relative or configured storage path. |
| `camera.motion` | enum | yes | `dolly_in` or `orbit`. |
| `camera.speed` | number | yes | Positive number. |
| `camera.start_distance` | number | yes | Positive number. |
| `camera.end_distance` | number | yes | Positive number. |
| `camera.height` | number | yes | Positive number. |
| `camera.focal_length` | number | yes | Positive number. |
| `scene.background` | string | yes | Initial V0.1 value: `dark_stage`. |
| `scene.lighting` | string | yes | Initial V0.1 value: `rim_back`. |
| `scene.particles` | boolean | yes | Enables template particle accents when supported. |
| `scene.fog` | boolean | yes | Enables template fog when supported. |
| `text.title` | string | yes | 1 to 80 characters. |
| `text.subtitle` | string | yes | 0 to 120 characters. |
| `text.font_style` | string | yes | Initial V0.1 value: `bold_game`. |
| `ai_enhance.enabled` | boolean | no | Defaults to `false`. |
| `ai_enhance.mode` | enum | no | `conservative` only. |
| `ai_enhance.workflow` | string or null | no | Reserved for optional future preset wiring. |

## Supported Enum Values

| Field | Values |
|---|---|
| `template` | `character_intro`, `product_orbit` |
| `asset.type` | `image`, `glb` |
| `output.aspect_ratio` | `9:16`, `16:9`, `1:1` |
| `output.resolution` | `1080p` |
| `output.fps` | `24` |
| `camera.motion` | `dolly_in`, `orbit` |
| `ai_enhance.mode` | `conservative` |

## Resolution Mapping

| Aspect ratio | Resolution | Width | Height |
|---|---|---:|---:|
| `9:16` | `1080p` | 1080 | 1920 |
| `16:9` | `1080p` | 1920 | 1080 |
| `1:1` | `1080p` | 1080 | 1080 |

`1:1` is not V0.1 P0 UI scope, but it is included in the schema mapping because
the implementation cost is low.

## Validation Rules

- `character_intro` requires exactly one `main_subject` asset with `type=image`.
- `product_orbit` requires exactly one `main_subject` asset with `type=glb`.
- `assets[].id` must be unique.
- V0.1 requires exactly one asset and its id must be `main_subject`.
- Invalid template values fail validation.
- Invalid asset/template combinations fail validation.
- `duration` must be from 4 to 20 seconds.
- `fps` must be 24.

## AI Enhancement Note

`ai_enhance` is schema-supported but defaults to `false`. Route 3 was PARTIAL:
direct full-frame AI regeneration failed for text-bearing output, and the
conservative ComfyUI reference plus FFmpeg enhancement path showed only mild
visual lift. AI enhancement is therefore optional and not the core V0.1 render
path. The standard path remains Blender Eevee + FFmpeg.
