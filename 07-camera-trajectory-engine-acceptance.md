# 07 — Camera Trajectory Engine Migration — 验收（骨架·待填）

> 作者：Andy · 审批：启鸣 · 语言：中文
> 状态：**PENDING — 三道视觉闸门（ADJ-2/3/4）未跑完前不得签收。**
> 上游：`07-camera-trajectory-engine-requirements.md` §五 / `07-camera-trajectory-engine-plan.md`。

---

## 一、CC 交付现状（已确认部分）

- 单元层：**116 tests OK，零回归**。`camera_math.py`（纯 python，0 处 bpy 引用，ADJ-5 ✅）+ `camera_presets.py`（8 预设）+ 26+18 新测。
- 接入：`CameraSpec.preset: str|None` 可选字段(向后兼容)；`build_scene` 新增 preset 分支；`render_project.py` 增 `_compute_scene_center_radius` / `_adapt_preset_keyframes` / `add_keyframed_camera`。
- 文档：`docs/parameters.md` + `docs/project_json_schema.md` 已加 preset 字段(Phase 4 纯文档，ADJ-1 ✅，无 app.js UI)。

## 二、验收表（映射 requirements §五，待闸门填）

| # | 验收标准 | 判定方式 | 结果 |
|---|---------|---------|------|
| 1 | 插值引擎纯 python(无 bpy)、单测覆盖 | 单测 | ✅ 116 OK / camera_math 0 bpy |
| 2 | 8 预设产出合法关键帧、list_presets=8 | 单测 | ✅ 18 测通过 |
| 3 | **默认路径零回归**(dolly_in/orbit 无 preset → pixel-diff=0) | ADJ-2 视觉闸门 | ⏳ PENDING |
| 4 | preset 经 JSON 命中即生效、不命中不变 | 渲染抽验 | ⏳ PENDING |
| 5 | **可复现(核心)**:同一 preset 两渲一致 | ADJ-3 视觉闸门 | ⏳ PENDING |
| 6 | PERSP 可接受透视、无主体畸变/崩坏 | ADJ-4 视觉闸门(≥3 预设) | ⏳ PENDING |
| 7 | 输出全部新增/改动文件路径 | CC 报告 | ✅ 已给 |

## 三、闸门待查清单（跑前必读）

设 `BLENDER_PATH` + `FFMPEG_PATH` 后执行:
- **ADJ-2**：dolly_in + orbit（无 preset）渲染 vs 改动前 → pixel-diff = 0。
- **ADJ-3**：同一 preset 渲两次 → 输出一致。
- **ADJ-4**：nolan_orbit / dolly_reveal / drone_ascend → 主体在画面、透视可接受、无几何崩坏。

**CC 已自标、ADJ-4 必须重点盯的两个雷:**
1. `_adapt_preset_keyframes` 的 X-forward→Y-forward 坐标交换「逻辑验证过、未视觉验证」→ 若相机朝向反/主体出画,即此 swap 错,修后重跑闸门。
2. PERSP 的 FOV→view_height 近似可能需调(影响文字叠加定位)→ ADJ-4 过后专查文字位置。

## 四、签收后动作（全绿才做）

- 填本表 → 启鸣 最终签收。
- 若 PERSP 确定保留为常用路径 → Andy 给 **ADR-006 追加带日期更新**(允许 PERSP 运镜、ORTHO 仍为无畸变默认)。
- 顺带补 loop 06 欠的 **ADR-007「普适性已确认」**日期更新。

---

> ⚠️ 提醒：116 绿测不碰像素。loop 03/04 教训——测试全绿仍可能渲出黑层/主体崩。**未过 ADJ-2/3/4 不得签收。**
