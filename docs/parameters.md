# CineAnchor V0.1 — 参数表（可经 Project JSON 调整）

> 范围：模型 Transform · 灯光 · 相机（本 loop 解耦项）
> 延迟：舞台/背景元素（光环 / glints / cloth）· font_style（后续 loop）
>
> 约定：所有新增参数均为 **optional override** — 不填则使用默认值（与当前硬编码行为一致），向后兼容。

---

## 1. 模型 Transform（`scene.model_transform`）

控制主体模型的位置、旋转、缩放。PNG 与 GLB 均适用。

| JSON 路径 | 含义 | 类型 | 取值范围 / 单位 | 默认值 | 示例值 |
|-----------|------|------|-----------------|--------|--------|
| `scene.model_transform.location` | 世界坐标覆写 | `[x, y, z]` 或省略 | 浮点数，Blender 世界单位 | `null`（自动居中） | `[0, 0, 0.5]` |
| `scene.model_transform.rotation` | 欧拉角旋转 | `[rx, ry, rz]` 或省略 | 度 (°) | `null`（自动朝向相机） | `[0, 0, 45]` — Z 轴旋转 45° |
| `scene.model_transform.scale` | 等比缩放覆写 | 正浮点数或省略 | `> 0`，1.0 = 原始大小 | `null`（GLB: `2.55/max_dim`，PNG: `1.85` 可见宽） | `1.5` — 放大 50% |

**注意：**
- `location` 直接设置模型的世界坐标，覆盖自动计算的居中位置。
- `rotation` 覆盖自动朝向。GLB 默认 Z 轴旋转 180°（面朝相机），PNG 默认无旋转。
- `scale` 覆盖自动适配。GLB 默认按边界框 `2.55 / max_dim` 等比缩放，PNG 默认可见宽度 1.85 世界单位。

---

## 2. 灯光覆写（`scene.lighting_overrides`）

每盏灯独立覆写。不填该灯则完全使用模板默认值。

### 2.1 主光 Key（`key`）

AREA 光源，位于主体正前方偏上，是场景最主要的光源。

| JSON 路径 | 含义 | 类型 | 取值范围 / 单位 | 默认值 | 示例值 |
|-----------|------|------|-----------------|--------|--------|
| `lighting_overrides.key.enabled` | 是否启用 | `bool` | — | `true` | `false` |
| `lighting_overrides.key.location` | 光源位置 | `[x, y, z]` | 世界单位 | `[0, -3.4, 2.7]` | `[0, -4.0, 3.0]` |
| `lighting_overrides.key.energy` | 光照强度 | 浮点数 | `> 0` | 170 (product) / 140 (character) | `300` |
| `lighting_overrides.key.color` | 光源颜色 | hex 字符串 | `^#[0-9a-fA-F]{6}$` | `#FFFFFF` | `#FFD700`（金色） |
| `lighting_overrides.key.size` | 面积光尺寸 | 浮点数 | `> 0` | `4.7` | `6.0` |

### 2.2 左轮廓光 Rim Left（`rim_left`）

POINT 光源，青色调，位于主体左前方。

| JSON 路径 | 含义 | 类型 | 取值范围 / 单位 | 默认值 | 示例值 |
|-----------|------|------|-----------------|--------|--------|
| `lighting_overrides.rim_left.enabled` | 是否启用 | `bool` | — | `true` | `false` |
| `lighting_overrides.rim_left.location` | 光源位置 | `[x, y, z]` | 世界单位 | `[-2.0, 0.7, 1.7]` | `[-3.0, 1.0, 2.0]` |
| `lighting_overrides.rim_left.energy` | 光照强度 | 浮点数 | `> 0` | `220` | `150` |
| `lighting_overrides.rim_left.color` | 光源颜色 | hex 字符串 | `^#[0-9a-fA-F]{6}$` | `#8CF2FF`（青色） | `#FF8800`（橙色） |

### 2.3 右轮廓光 Rim Right（`rim_right`）

POINT 光源，品红色调，位于主体右前方。

| JSON 路径 | 含义 | 类型 | 取值范围 / 单位 | 默认值 | 示例值 |
|-----------|------|------|-----------------|--------|--------|
| `lighting_overrides.rim_right.enabled` | 是否启用 | `bool` | — | `true` | `false` |
| `lighting_overrides.rim_right.location` | 光源位置 | `[x, y, z]` | 世界单位 | `[2.0, 0.8, 1.2]` | `[3.0, 1.0, 2.0]` |
| `lighting_overrides.rim_right.energy` | 光照强度 | 浮点数 | `> 0` | `150` | `200` |
| `lighting_overrides.rim_right.color` | 光源颜色 | hex 字符串 | `^#[0-9a-fA-F]{6}$` | `#FF59A6`（品红） | `#00FF88`（绿色） |

### 2.4 背光 Back（`back`）

AREA 光源，位于主体后上方，提供轮廓分离。

| JSON 路径 | 含义 | 类型 | 取值范围 / 单位 | 默认值 | 示例值 |
|-----------|------|------|-----------------|--------|--------|
| `lighting_overrides.back.enabled` | 是否启用 | `bool` | — | `true` | `false` |
| `lighting_overrides.back.location` | 光源位置 | `[x, y, z]` | 世界单位 | `[0, 2.2, 3.1]` | `[0, 3.0, 4.0]` |
| `lighting_overrides.back.energy` | 光照强度 | 浮点数 | `> 0` | `115` | `80` |
| `lighting_overrides.back.color` | 光源颜色 | hex 字符串 | `^#[0-9a-fA-F]{6}$` | `#FFFFFF` | `#FFEEDD`（暖白） |
| `lighting_overrides.back.size` | 面积光尺寸 | 浮点数 | `> 0` | `3.1` | `5.0` |

### 2.5 剪影边缘光 Silhouette Rim（`silhouette_rim`）

SPOT 光源，仅 `character_intro` 模板有效。位于主体后上方，打出边缘轮廓。

| JSON 路径 | 含义 | 类型 | 取值范围 / 单位 | 默认值 | 示例值 |
|-----------|------|------|-----------------|--------|--------|
| `lighting_overrides.silhouette_rim.enabled` | 是否启用 | `bool` | — | `true` | `false` |
| `lighting_overrides.silhouette_rim.location` | 光源位置 | `[x, y, z]` | 世界单位 | `[1.8, 2.5, 2.4]` | `[2.0, 3.0, 2.0]` |
| `lighting_overrides.silhouette_rim.energy` | 光照强度 | 浮点数 | `> 0` | `100` | `150` |
| `lighting_overrides.silhouette_rim.color` | 光源颜色 | hex 字符串 | `^#[0-9a-fA-F]{6}$` | `#55EEFF` | `#FFAA00` |
| `lighting_overrides.silhouette_rim.size` | 聚光角度 | 浮点数 | `> 0`，度 (°) | `45` | `30` |

**注意：** 剪影边缘光的 `spot_blend`（默认 0.3）和 `rotation`（默认 -35°/0°/-40° pitch/yaw/roll）在 `LightDefSpec` 中可通过 `size` 和内部属性调整，但常规使用中不建议修改 rotation。

---

## 3. 相机参数（`camera`）

已存在于 V0.1 schema 中，本 loop 正式接线到 Blender 渲染。**必填字段**（所有项目均需提供）。

| JSON 路径 | 含义 | Dolly 默认 | Orbit 默认 | 取值范围 | 示例值 |
|-----------|------|-----------|-----------|---------|--------|
| `camera.motion` | 运镜类型 | `dolly_in` | `orbit` | `dolly_in` / `orbit` | — |
| `camera.speed` | 速度乘数 | `1.0` | `1.0` | `> 0` | `1.5`（快 50%） |
| `camera.start_distance` | 起始距离 / 角度 | `7.2`（y 距离） | `18.0`（起始角度°） | `> 0` | `10.0`（更远推镜） |
| `camera.end_distance` | 结束距离 / 角度 | `5.8`（y 距离） | `22.0`（结束角度°） | `> 0` | `4.0`（更近结束） |
| `camera.height` | 相机 Z 偏移 | `0.25`（世界单位） | `0.55`（世界单位） | `> 0` | `0.5`（更高视角） |
| `camera.focal_length` | ortho_scale 乘数 | `1.0` | `1.0` | `> 0` | `0.8`（更广角） |

**运镜说明：**
- **Dolly（推镜）：** `start_distance` / `end_distance` 控制相机 Y 轴距离（越小越近，即从远推到近）。`height` 控制相机 Z 轴高度。
- **Orbit（环绕）：** `start_distance` / `end_distance` 控制 pivot 旋转角度范围（绝对值，度）。相机围绕目标从 `-start_angle` 旋转到 `+end_angle`。
- **Preset（预设运镜）：** 当 `camera.preset` 非空时，忽略 `motion` / `start_distance` / `end_distance` / `height`，走多关键帧 PERSP 相机路径。预设本期作为 demo/验证材料，非正式产品功能。

### 3.1 预设运镜（`camera.preset`，可选）

| 预设 ID | 名称 | 镜头语言 | 时长 |
|---------|------|---------|------|
| `nolan_orbit` | Nolan Orbit | 环绕主体 180°, 低角度仰拍, 缓慢推进 | 6s |
| `anime_closeup` | Anime Close-up | 快速推近主体, 微幅晃动, 浅景深特写 | 3s |
| `dolly_reveal` | Dolly Reveal | 侧向平移, 主体逐渐入画, 广角 | 5s |
| `drone_ascend` | Drone Ascend | 从地面升到鸟瞰, 向下俯拍, 广角 | 8s |
| `hero_tracking` | Hero Tracking | 从主体前方低角度跟拍, 后退拉开揭示环境 | 5s |
| `suspense_pan` | Suspense Pan | 缓慢水平横扫, 悬疑感, 长焦 | 7s |
| `god_eye` | God's Eye | 极高鸟瞰, 极慢自转, 全景 | 10s |
| `whip_pan` | Whip Pan | 快速甩镜, 90° 急转视线方向 | 1.5s |

预设使用示例：
```json
"camera": {
  "preset": "nolan_orbit",
  "motion": "dolly_in",
  "speed": 1.0,
  "start_distance": 7.2,
  "end_distance": 5.8,
  "height": 0.25,
  "focal_length": 1.0
}
```

当 `preset` 非 `null` 时，`motion`/`start_distance`/`end_distance`/`height` 字段保留（向后兼容）但被忽略；相机使用 PERSP 镜头 + 多关键帧轨迹。

### 3.2 交互式关键帧（`camera.keyframes` / `camera.shots`，Loop 08）

通过浏览器 Three.js viewport 录制并自动保存的相机轨迹。当 `keyframes` 或 `shots` 存在时，忽略 `motion` / `preset`，走交互式 PERSP 相机路径。

| JSON 路径 | 含义 | 类型 | 示例 |
|-----------|------|------|------|
| `camera.keyframes` | 单镜头关键帧列表 | `[{t, pos, quat, fov}]` 或 `null` | `[{"t":0,"pos":[0,-5,2],"quat":[0,0,0,1],"fov":50}]` |
| `camera.keyframes[].t` | 时间位置（秒） | `float` | `0.0` |
| `camera.keyframes[].pos` | 相机世界坐标 | `[x, y, z]` | `[0, -5, 2]` |
| `camera.keyframes[].quat` | 相机旋转四元数 | `[x, y, z, w]` | `[0, 0, 0, 1]` |
| `camera.keyframes[].fov` | 视场角（度） | `float` | `50.0` |
| `camera.shots` | 多镜头分段列表 | `[{index, keyframes, cut}]` 或 `null` | `[{"index":0,"keyframes":[...],"cut":false}]` |
| `camera.shots[].cut` | 硬切标记 | `bool` | `true` = 瞬切，`false` = 过渡动画 |

**注意：** 关键帧四元数使用 `[x, y, z, w]` 内部约定。写入 Blender `rotation_quaternion` 时需转换为 `(w, x, y, z)`。

---

## 4. 文本控制（`text` & `scene.background_enhance.text_overlay`）

| JSON 路径 | 含义 | 类型 | 默认值 | 说明 |
|-----------|------|------|--------|------|
| `text.title` | 标题文字 | `string` | `""` | 最大 80 字符。空字符串 = 无标题 |
| `text.subtitle` | 副标题文字 | `string` | `""` | 最大 120 字符 |
| `text.font_style` | 字体样式 | `string` | 必填 | 当前仅占位（Blender 默认字体），后续 loop 接线 |
| `scene.background_enhance.text_overlay` | 文字叠加开关 | `bool` | `true` | `false` 时无论 title/subtitle 内容如何，均不渲染文字 |
| `scene.background_enhance.stage_ring` | 舞台发光圆环 | `bool` | `true` | `false` 时去除地板上的青色发光圆环 |

**text-free 渲染：** 设置 `text_overlay=false` 即可。即使 title/subtitle 为非空字符串，也不会渲染文字（ADJ-6 安全网）。

---

## 附录：完整 project.json 示例（character_intro + 全部覆写参数）

```json
{
  "version": "0.1",
  "project_id": "example-character",
  "template": "character_intro",
  "output": {
    "duration": 4,
    "fps": 24,
    "aspect_ratio": "16:9",
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
    "fog": false,
    "particles": null,
    "background_enhance": {
      "rim_light": true,
      "rim_light_color": "#55EEFF",
      "rim_light_energy": 100,
      "cloth_texture": true,
      "cloth_mix": 0.07,
      "glints": true,
      "text_overlay": true,
      "stage_ring": true
    },
    "model_transform": {
      "location": [0, 0, 0.3],
      "rotation": [0, 0, 0],
      "scale": 1.1
    },
    "lighting_overrides": {
      "key": {
        "enabled": true,
        "energy": 200,
        "color": "#FFD700",
        "location": [0, -3.4, 2.7]
      },
      "rim_left": {
        "enabled": true,
        "energy": 180,
        "color": "#FF8800"
      },
      "rim_right": {
        "enabled": true,
        "energy": 120,
        "color": "#00AAFF"
      }
    }
  },
  "text": {
    "title": "My Hero",
    "subtitle": "Limited Edition",
    "font_style": "bold_game"
  },
  "ai_enhance": {
    "enabled": false,
    "mode": "conservative"
  }
}
```
