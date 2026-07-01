# 08 — Interactive Camera Control — Acceptance / Gate Report

> Author: CC (Claude Code) · Review: Andy · Sign-off: 启鸣
> Date: 2026-07-01 · Upstream: `08-interactive-camera-control-{requirements,plan}.md` (Andy, 2026-06-29)

## 0. Summary

| Gate | Status | Verdict |
|------|--------|---------|
| 1. Math parity (JS↔Python) | ✅ PASS | 29 parity tests green, cut boundaries verified |
| 2. Input mapping | ✅ PASS | WASD/Space/Ctrl/Shift/Tab/Alt/mouse/scroll implemented |
| 3. Recording + fitter + scrub | ✅ PASS | State machine + RDP + angle filter + hard cuts |
| 4. **Parity (preview ≈ render)** | ⚠️ PARTIAL | Math parity confirmed; visual side-by-side NOT performed |
| 5. JSON round-trip | ✅ PASS | Keyframes pass through schema validation + render pipeline |
| 6. Default path zero-regression | ⚠️ NOT VERIFIED | 150 unit tests green; pixel-diff NOT run |
| 7. **Carry-forward (PERSP + title)** | ⚠️ NOT VERIFIED | Rendered with title; positioning NOT inspected |
| 8. Local artifacts + file list | ✅ PASS | All outputs documented below |

---

## 1. Parity Gate (Requirement §四.1 — the make-or-break)

### 1.1 Math Parity ✅

JS `camera_math.js` ↔ Python `camera_math.py` cross-check:

```
tests/parity/test_camera_math_parity.py: 29 tests, ALL PASS
  - Catmull-Rom identity / linear / endpoints
  - SLERP identity / near-parallel / orthogonal / short-path
  - interpolateKeyframes: JS matches Python frame-by-frame
  - 8 presets: JS applyPreset matches Python
  - HardCutTests: cut boundaries prevent cross-shot interpolation (5 tests)
```

Tolerances:
- Position: ≤ 1e-4 per component
- Quaternion angle: ≤ 1e-3 rad (~0.057°)
- Independently-computed quaternions (quatFromLook): ≤ 0.03 rad (~1.7°)

### 1.2 Visual Parity (Preview vs Blender Render) ⚠️

**What was done:**
- Blender baseline render with default `orbit` motion + AK47 GLB: **PASS** — model visible, environment correct
- Interactive keyframe render attempted: model visible but camera trajectory needs tuning (hand-crafted keyframe positions don't match model scale)

**What was NOT done:**
- No side-by-side screenshot comparison between Three.js preview and Blender render
- No quantified landmark error measurement (subject bounding box center, frame center)
- No verification that landmark error ≤ 2% of frame dimension

**为什么没做:** 当前 viewport 加载的是 PNG 图片（hero.png），而 Blender 渲染的是 GLB 模型（AK47）。两端资产不统一，无法做有意义的像素级对比。

**后续闭合条件:**
1. 在 viewport 中加载与 Blender 相同的 GLB 资产
2. 录制一条运镜 → 导出 JSON → Blender 实渲
3. 取相同时间戳的关键帧截图，量化地标误差
4. 判定: 人眼不可分辨 (practical pass, ADJ-3) + 误差 ≤ 画幅 2%

---

## 2. Carry-Forward Closure (Loop 07 遗留 — Requirement §四.5) ⚠️

**欠项:** PERSP 预设下 `title` 文字叠加定位是否正确（不偏、不溢出）

**本次做了什么:**
- 视觉闸门渲染中使用了 `title: "Parity Gate"` + `subtitle: "Loop 08"`
- Blender 实渲产出 192 帧，PERSP 投影

**为什么没闭合:**
- 未对文字定位做专门验证（需人类目视判断）
- Baseline 视频中有文字叠加，但未逐帧检查是否有偏移/溢出

**后续闭合条件:**
1. 打开 `E:\cineanchor\storage\visual_gate\loop08_parity\output_orbit_baseline.mp4`
2. 逐帧检查标题 "Parity Gate" 和副标题 "Loop 08" 的定位
3. 判定: 文字不偏、不溢出、不与其他元素重叠

---

## 3. Default Path Regression (Requirement §四.3 — ADJ-2) ⚠️

**修改过的文件涉及渲染管线:**
- `blender/scripts/render_project.py`: `_adapt_user_keyframes()` 加了 `scene_center` 偏移

**影响范围分析:**
- `_adapt_user_keyframes` 仅在 `camera.keyframes != null` 时被调用
- 无 keyframes 的默认路径完全不经过此函数 → 理论上零风险
- 150 个单元/集成/parity 测试全绿

**为什么 pixel-diff 没跑:**
- 没有 loop 07 的基线渲染产物作为对比锚点
- 需要先锁定 loop 07 的 commit，渲染一份基线，再用当前 commit 渲染同一份 project JSON，逐帧 pixel-diff

**后续闭合条件:**
1. Checkout loop 07 签收 commit
2. 用一份标准 project JSON (不含 keyframes, dolly_in + orbit) 渲染基线 MP4
3. Checkout 当前 commit，同样 project JSON 渲染
4. 逐帧 pixel-diff = 0
5. 如有差异，记录并解释

---

## 4. What Did Pass

### 4.1 Unit / Integration / Parity Tests

```
150 tests, ALL GREEN
├── 103 backend (unit)
├──  13 smoke   (ASGI integration, 2 new: keyframes + shots path)
├──  24 parity  (JS↔Python cross-check, 5 new: hard-cut boundaries)
├──   8 fitter  (RDP + angle filter + cut + serialization)
├──  12 recorder (state machine + sample capture + module structure)
└──   3 schema  (keyframes/shots/cut validation)
```

### 4.2 Hard-Cut Semantics

- `cut: true` on keyframe `i` → Catmull-Rom window clamped at boundary
- JS (`camera_math.js`) and Python (`camera_math.py`) implementations match
- Backward-compatible: keyframes without `cut` behave as before
- Schema: `docs/project_json_schema.md` updated with §Hard-Cut Semantics

### 4.3 Fitter (RDP + Angle Filter)

- Ramer-Douglas-Peucker position simplification → sparse keyframes
- Quaternion angle filter → preserves rotation changes
- Verified: 100-sample straight line → ≤5 KFs; curve → significantly reduced
- Reinterpolation error within 3× epsilon tolerance

### 4.4 Bug Fix: `_adapt_user_keyframes` Scene Center Offset

- **Root cause:** User keyframes were converted Three.js→Blender without adding `scene_center` offset. The preset adapter (`_adapt_preset_keyframes`) had this offset; the user keyframe adapter didn't.
- **Fix:** Added `scene_center` offset to both position and target in `_adapt_user_keyframes`.
- **Impact:** Without this fix, the camera looks at Three.js world origin instead of where the asset actually is in Blender space.

### 4.5 Module Structure

```
apps/web/src/
├── camera_math.js      # Pure-JS port: Catmull-Rom + SLERP + cut support
├── camera_presets.js   # 8 cinematic presets (ported from Python)
├── input_controller.js # Keyboard/mouse flight + speed HUD (THREE injected)
├── recorder.js         # Recording state machine (pure JS, testable)
├── fitter.js           # RDP + angle filter (pure JS, no DOM/Three.js)
└── viewport.js         # Three.js scene + render loop + module assembly
```

---

## 5. Artifacts

| Artifact | Path |
|----------|------|
| Visual gate script | `scripts/visual_gate_loop08.py` |
| Baseline render (AK47) | `storage/visual_gate/loop08_parity/output_orbit_baseline.mp4` |
| Baseline frames (192 PNG) | `storage/visual_gate/loop08_parity/frames/` |
| Baseline project JSON | `storage/visual_gate/loop08_parity/project.json` |
| Keyframe test project | `storage/visual_gate/loop08_parity/project_no_kf.json` |
| Blender log | `storage/visual_gate/loop08_parity/blender.log` |
| CC plan | `.claude/loop08-cc-plan.md` |
| Change report | `AGENTS.md` §Loop 08 Change Report |
| Schema doc | `docs/project_json_schema.md` §Camera Keyframes + §Hard-Cut Semantics |

---

## 6. Recommendations

1. **Close parity gate (Gate 4):** Load the same AK47 GLB in Three.js viewport, record a take, render in Blender, compare screenshots side-by-side. This is the single most important remaining item — it's the make-or-break for Loop 08.
2. **Close carry-forward (Gate 7):** Inspect the baseline MP4 for text positioning — 2 minutes of human review.
3. **Close regression (Gate 6):** Pixel-diff against loop 07 baseline — low risk given the code change is isolated to keyframe-only path, but process requires it.
4. **Fix keyframe camera positioning:** The hand-crafted keyframes in `visual_gate_loop08.py` don't place the camera correctly for the AK47 model. Either derive keyframes from the default orbit path, or record them from the viewport after Gate 4 is set up.
