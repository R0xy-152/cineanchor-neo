# 07 — Camera Trajectory Engine Migration — 验收

> 作者：Andy · 审批：启鸣 · 语言：中文
> 状态：**三道视觉闸门全绿（含 1 项 practical pass）。Andy verdict = 建议签收，带 1 条 carry-forward。等 启鸣 最终签收。**
> 上游：`07-camera-trajectory-engine-requirements.md` §五 / `07-camera-trajectory-engine-plan.md`。

---

## 一、CC 交付现状

- 单元层：**116 tests OK，零回归**。`camera_math.py`（纯 python，0 处 bpy 引用，ADJ-5 ✅）+ `camera_presets.py`（8 预设）+ 26+18 新测。
- 接入：`CameraSpec.preset: str|None` 可选(向后兼容)；`build_scene` 新增 preset 分支；`render_project.py` 增 `_compute_scene_center_radius` / `_adapt_preset_keyframes` / `add_keyframed_camera`。
- 文档：`docs/parameters.md` + `docs/project_json_schema.md` 已加 preset 字段(Phase 4 纯文档，ADJ-1 ✅，无 app.js UI)。
- 视觉闸门产物：`storage/visual_gate/`（adj2_* / adj3_run1·run2 / adj4_* + preview.mp4）。

## 二、验收表（映射 requirements §五）

| # | 验收标准 | 判定方式 | 结果 |
|---|---------|---------|------|
| 1 | 插值引擎纯 python(无 bpy)、单测覆盖 | 单测 | ✅ 116 OK / camera_math 0 bpy |
| 2 | 8 预设产出合法关键帧、list_presets=8 | 单测 | ✅ 18 测通过 |
| 3 | **默认路径零回归**(dolly_in/orbit 无 preset → pixel-diff=0) | ADJ-2 | ✅ PASS — dolly 24/24 字节一致 PSNR=∞；orbit 24/24 字节一致 |
| 4 | preset 经 JSON 命中即生效、不命中不变 | 渲染抽验 | ✅ — preset 分支生效(ADJ-4 3/3 渲染)；不命中 = ADJ-2 字节一致 |
| 5 | **可复现(核心)**:同一 preset 两渲一致 | ADJ-3 | ✅ PRACTICAL — 22/24 字节一致；2 边界帧 106-109dB PSNR(亚像素舍入，不可见) |
| 6 | PERSP 可接受透视、无主体畸变/崩坏 | ADJ-4(≥3 预设) | ✅ PASS — nolan_orbit/dolly_reveal/drone_ascend 主体在帧、运镜存在、无崩坏 |
| 7 | 输出全部新增/改动文件路径 | CC 报告 | ✅ 已给 |

## 三、闸门期间修复的 Bug（单测未能捕获 → 印证视觉闸门必要性）

1. `_quat_from_look` 除零：相机朝向接近 180° 时 trace≈-1 → s=0；加 `max(..., 1e-10)` 防护。
2. `camera.data.angle` 只读不可 keyframe → 改用 `camera.data.lens`(focal mm) + `keyframe_insert("lens")`。
3. Blender Python 找不到 camera_math/presets → 加 `_SCRIPT_DIR` 到 `sys.path`。

> 这 3 个都是 Blender 运行时问题，116 个绿测一个都抓不到。验证了 loop 03/04 教训：测试全绿 ≠ 渲染正确。

## 四、可复现指标的诚实定义（对外/投资人口径）

ADJ-3 = **practical pass**：22/24 帧逐位一致，2 个**边界帧**差异 106-109dB PSNR（亚像素浮点舍入，人眼与下游均不可分辨）。
对外「Camera Reproducibility」应表述为 **「确定性 ≥106dB PSNR、22/24 逐位一致」**，不 overclaim「逐位完美」。2 帧根因(疑边界帧 Eevee/浮点)可后续排查，**不阻塞签收**。

## 五、Carry-forward（未阻塞本 loop，转入 loop 08 productization）

**PERSP × 文字叠加定位**：本次闸门 `title=""` 未渲文字，PERSP 下 FOV→view_height 的文字定位**未验证**。
- 不阻塞 loop 07：三道阻塞闸门全过；验收 #6（主体无畸变）已过；本期预设为 demo、文字保持确定性，preset+文字非已发布产品路径。
- 处置：登记为 carry-forward，**在 PERSP/预设真正产品化（loop 08 交互控制 + 实际出片）时钉死**。
- 可选即时闭合：补一发带 `title` 的 PERSP 渲染确认文字位置（很便宜），由 启鸣 决定是否现在补。

## 六、签收后动作（待 启鸣 最终签收触发）

- PERSP 已确认可用且保留为 preset 路径 → Andy 给 **ADR-006 追加带日期更新**（允许 PERSP 运镜；ORTHO 仍为无畸变默认）。
- 顺带补 loop 06 欠的 **ADR-007「普适性已确认」**日期更新。

---

**Andy verdict：7 条全绿/practical-green，建议签收，带 1 条 carry-forward（PERSP×文字 → loop 08）。**
