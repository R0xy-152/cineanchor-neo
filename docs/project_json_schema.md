# CineAnchor Project JSON Schema (V0.1 + additive V0.2)

This document defines the formal V0.1 Project JSON shape used by the local
render API. The Spike JSON under `spikes/render_json/` remains historical
validation code.

V0.2 is additive: it introduces `character_birthday`, named image slots,
`style`, `timeline`, and birthday text fields. The two V0.1 templates keep
their original single-asset validation and render paths.

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
    "height": 0.25,
    "focal_length": 1.0
  },
  "scene": {
    "background": "dark_stage",
    "lighting": "rim_back",
    "particles": null,
    "fog": false,
    "background_enhance": {
      "rim_light": true,
      "rim_light_color": "#55EEFF",
      "rim_light_energy": 100.0,
      "cloth_texture": true,
      "cloth_mix": 0.07,
      "glints": true,
      "text_overlay": true,
      "stage_ring": true
    },
    "model_transform": null,
    "lighting_overrides": null
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
    "start_distance": 18.0,
    "end_distance": 22.0,
    "height": 0.55,
    "focal_length": 1.0
  },
  "scene": {
    "background": "dark_stage",
    "lighting": "rim_back",
    "particles": null,
    "fog": false,
    "background_enhance": {
      "rim_light": false,
      "rim_light_color": "#55EEFF",
      "rim_light_energy": 100.0,
      "cloth_texture": false,
      "cloth_mix": 0.07,
      "glints": false,
      "text_overlay": false,
      "stage_ring": true
    },
    "model_transform": null,
    "lighting_overrides": null
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
| `version` | string | yes | Accepts `0.1` and `0.2`; `character_birthday` requires `0.2`. |
| `project_id` | string | yes | Caller-provided project identifier. |
| `template` | enum | yes | `character_intro`, `product_orbit`, or `character_birthday`. |
| `output.duration` | integer | yes | 4 to 30 seconds. |
| `output.fps` | integer | yes | V0.1 supports 24 only. |
| `output.aspect_ratio` | enum | yes | `9:16`, `16:9`, `1:1`. |
| `output.resolution` | enum | yes | `1080p`. |
| `assets[].id` | string | yes | Legacy: `main_subject`. Birthday: `main_character`, optional `logo`, `support_image_1..3`. |
| `assets[].type` | enum | yes | `image` or `glb`. |
| `assets[].path` | string | yes | Relative or configured storage path. |
| `camera.motion` | enum | yes | `dolly_in` or `orbit`. |
| `camera.preset` | string or null | no | Optional preset name (see Presets below). When set, overrides motion/distances/height. |
| `camera.speed` | number | yes | Positive number. |
| `camera.start_distance` | number | yes | Positive number. |
| `camera.end_distance` | number | yes | Positive number. |
| `camera.height` | number | yes | Positive number. |
| `camera.focal_length` | number | yes | Positive number. |
| `camera.keyframes` | array[Keyframe] or null | no | Loop 08: interactive keyframes from viewport recording. When set, overrides motion-based camera. |
| `camera.shots` | array[Shot] or null | no | Loop 08: shot groups with hard-cut boundaries (alternative to keyframes array). |
| `camera.keyframes[].t` | number | yes | Time in seconds (0-based). |
| `camera.keyframes[].pos` | [number,number,number] | yes | Camera position (Three.js Y-up coordinates). |
| `camera.keyframes[].quat` | [number,number,number,number] | yes | Camera rotation quaternion (Three.js). |
| `camera.keyframes[].fov` | number | yes | Vertical field of view in degrees. |
| `camera.keyframes[].cut` | boolean | no | Default `false`. When `true`, marks a hard-cut boundary — interpolation is NOT performed across this keyframe. The KF serves as the end of one shot and start of the next. See §Hard-Cut Semantics. |
| `scene.background` | string | yes | Initial V0.1 value: `dark_stage`. |
| `scene.lighting` | string | yes | Initial V0.1 value: `rim_back`. |
| `scene.particles` | boolean | yes | Enables template particle accents when supported. |
| `scene.fog` | boolean | yes | Enables template fog when supported. |
| `text.title` | string | yes | 0 to 80 characters (empty = no title). |
| `text.subtitle` | string | yes | 0 to 120 characters. |
| `text.font_style` | string | yes | Initial V0.1 value: `bold_game`. |
| `scene.background_enhance.rim_light` | boolean | no | Default `true`. Silhouette rim (character_intro only). |
| `scene.background_enhance.rim_light_color` | string | no | Default `#55EEFF`. Hex color. |
| `scene.background_enhance.rim_light_energy` | number | no | Default `100`. Range 20–300. |
| `scene.background_enhance.cloth_texture` | boolean | no | Default `true`. Procedural cloth on backdrop. |
| `scene.background_enhance.cloth_mix` | number | no | Default `0.07`. Range 0.0–0.5. |
| `scene.background_enhance.glints` | boolean | no | Default `true`. 18 stage glint particles. |
| `scene.background_enhance.text_overlay` | boolean | no | Default `true`. When false, suppresses text regardless of title content. |
| `scene.background_enhance.stage_ring` | boolean | no | Default `true`. Glowing cyan floor ring. |
| `scene.model_transform.location` | [number,number,number] or null | no | Override model world position. Null = auto-center. |
| `scene.model_transform.rotation` | [number,number,number] or null | no | Override model Euler rotation (degrees). Null = auto-face camera. |
| `scene.model_transform.scale` | number or null | no | Override uniform scale (>0). Null = auto-fit. |
| `scene.lighting_overrides.<light>` | object or null | no | Per-light overrides (key/rim_left/rim_right/back/silhouette_rim). Each has: enabled, location, energy, color, size. |
| `ai_enhance.enabled` | boolean | no | Defaults to `false`. |
| `ai_enhance.mode` | enum | no | `conservative` only. |
| `ai_enhance.workflow` | string or null | no | Reserved for optional future preset wiring. |

## Supported Enum Values

| Field | Values |
|---|---|
| `template` | `character_intro`, `product_orbit`, `character_birthday` |
| `asset.type` | `image`, `glb` |
| `output.aspect_ratio` | `9:16`, `16:9`, `1:1` |
| `output.resolution` | `1080p` |
| `output.fps` | `24` |
| `camera.motion` | `dolly_in`, `orbit` |
| `camera.preset` (demo) | `nolan_orbit`, `anime_closeup`, `dolly_reveal`, `drone_ascend`, `hero_tracking`, `suspense_pan`, `god_eye`, `whip_pan` |
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
- `character_birthday` requires version `0.2`, 9:16, and one `main_character:image`.
- Birthday optional asset IDs are `logo` and `support_image_1..3`, all `image`.
- Invalid template values fail validation.
- Invalid asset/template combinations fail validation.
- `duration` must be from 4 to 30 seconds.
- `fps` must be 24.

## Character Birthday V0.2

The canonical schema keeps `assets` as a list to remain compatible with the
existing upload and storage contract. A product-facing object such as
`assets.main_character` is a UI/view-model concern and is normalized into the
list before validation.

Required birthday text fields are `character_name`, `birthday_date`, and
`main_title` (or legacy `title`). `subtitle_lines` accepts up to three non-empty
strings. `cta` and `copyright` are optional.

`style` fields:

| Field | Default | Meaning |
|---|---|---|
| `theme` | `cute_school` | Named product preset |
| `primary_color` | `#C9414A` | Date, title, name accent |
| `secondary_color` | `#5967B0` | Background, poster bar, CTA |
| `background_style` | `soft_poster` | Deterministic background preset |
| `font_preset` | `birthday_serif` | Actual font resolution preset |
| `subtitle_preset` | `white_black_stroke` | Readable dialogue token |
| `particle_preset` | `petal_soft` | Deterministic particle token |

`timeline` contains six `{start,end}` ranges: `opening_date_card`, `name_card`,
`birthday_title_closeup`, `character_poster`, `character_interaction`, and
`brand_end_card`. Ranges must be ordered, non-overlapping and within
`output.duration`. If omitted, they are scaled from the 15-second MVP defaults.

See the complete runnable payload in
`samples/projects/character_birthday.json` and the product/implementation
design in `docs/templates/character_birthday_template.md`.

## Camera Keyframes (Loop 08)

When `camera.keyframes` is non-null, the renderer uses keyframe-based camera animation instead of the motion-based (`dolly_in`/`orbit`) path. Keyframes are produced by the interactive viewport recording + RDP fitting pipeline.

### Keyframe Object

```json
{
  "t": 1.23,
  "pos": [0.0, -5.0, 1.5],
  "quat": [0.0, 0.0, 0.0, 1.0],
  "fov": 55.0,
  "cut": false
}
```

- `t`: time in seconds, rounded to 0.01s.
- `pos`: position rounded to 0.001.
- `quat`: quaternion rounded to 0.0001.
- `fov`: vertical FOV rounded to 0.1°.
- `cut`: optional boolean, default `false`.

### Shot Group Object

```json
{
  "index": 0,
  "cut": true,
  "keyframes": [...]
}
```

Shots are produced by the fitter. Each shot has its own keyframe list. The last keyframe of each shot (except the final shot) has `cut: true`.

### Hard-Cut Semantics

A `cut: true` on keyframe `i` means:

1. Keyframe `i` is the **last frame** of shot N and the **first frame** of shot N+1.
2. Catmull-Rom interpolation is performed **within each shot only** — the 4-point window never crosses a cut boundary.
3. When interpolating segment `[KFi, KFi+1]` where KFi has `cut=true`: k0 is clamped to KFi (the pre-cut KF `KFi-1` is excluded).
4. When interpolating segment `[KFi-1, KFi]` where KFi has `cut=true`: k3 is clamped to KFi (the post-cut KF `KFi+1` is excluded).
5. This guarantees a true hard cut — the camera position does not blend across shot boundaries.

Backward-compatible: keyframes without `cut` fields behave as a single continuous shot (no change from loop 07 behavior).

## AI Enhancement Note

`ai_enhance` is schema-supported but defaults to `false`. Route 3 was PARTIAL:
direct full-frame AI regeneration failed for text-bearing output, and the
conservative ComfyUI reference plus FFmpeg enhancement path showed only mild
visual lift. AI enhancement is therefore optional and not the core V0.1 render
path. The standard path remains Blender Eevee + FFmpeg.
