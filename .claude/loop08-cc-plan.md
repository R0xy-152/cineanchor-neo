# Loop 08 — CC 细化执行 Plan

> Author: CC (Claude Code) · Review: Andy · 上游: `08-interactive-camera-control-plan.md` (Andy, 2026-06-29)
> Status: **待 Andy plan-review gate**

---

## 0. 当前进度快照

| Andy Plan Phase | 状态 | 备注 |
|-----------------|------|------|
| P1 插值移植+交叉验证 | ✅ 完成 | `camera_math.js` 已移植，24 parity tests 全绿 |
| P2 Three.js 视口 | ✅ 完成 | `viewport.js` + `viewport.html`，PERSP 场景 |
| P3 输入控制 | ⚠️ 功能可用，待决 | 录制键用 L/R 键盘而非鼠标左/右 — 见 **决策 A** |
| P4 录制+拟合+序列化 | 🔶 骨架 | 录制通，fitter 是占位（Nth抽帧），无后端端点，hard-cut schema 未落地 |
| P5 Parity 闸门 | ❌ 未开始 | |
| P6 回归测试 | ❌ 未开始 | |

**140 tests 全绿**（103 backend + 13 smoke + 24 parity）。

---

## 1. 待 Andy 拍板的三个决策

### 决策 A：录制触发键 — 键盘 L/R vs 鼠标左/右键

**背景**：Requirements 指定「左键录制、右键暂停」。但 `viewport.js` 当前实现是左键 = Pointer Lock（飞行模式），L/R 键 = 录制/暂停。原因：浏览器 Pointer Lock 必须由用户手势触发，通常绑定在 click 上。如果左键同时是"进入飞行"和"录制"，语义冲突。

**三种方案**：

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **A1. 保持键盘 L/R**（现状） | 左键=飞行，L=录 R=停 | 无冲突，已实现 | 与需求不一致，左手 WASD+L/R 手指跨度大 |
| **A2. 左键双击区分** | 单击=飞行锁定，双击=开始录制；右键=暂停 | 一鼠完成，符合需求意图 | 双击检测增加延迟，双击/单击歧义 |
| **A3. 飞行用独立按钮** | 增加一个"进入飞行"按钮，进入后左键=录制 右键=暂停，Esc=退出 | 完全符合需求，逻辑清晰 | 多一步，增加 UI 元素 |

**CC 推荐：A1 保持现状，但在 help 面板中标注清楚。**
理由：loop 08 的 make-or-break 是 parity，不是输入设备 UX。键位问题是手感优化项，可在启鸣试用后 feedback 一轮改，不阻塞核心链路。R4 自 Andy plan 中就是已知风险，plan 中说"CC to settle UX in Phase 3"。

### 决策 B：Fitter 算法选型

**背景**：当前 `fitAndSerialize()` 是 crude Nth-sample 抽帧（~2 KFs/sec），不符合 Requirements 的「稠密采样→按容差拟合成稀疏关键帧→07引擎在容差内还原」。需要替换为正式 fitter。

**两种方案**：

| 方案 | 描述 | 精度 | 复杂度 | 
|------|------|------|--------|
| **B1. RDP + 角度过滤** | Ramer-Douglas-Peucker 对位置做曲线简化 + 角度阈值过滤冗余朝向帧 | 高 | 中（~100行纯函数） |
| **B2. 固定间隔+端点保留** | 每 N 帧抽一帧 + 必保留首尾（现状的改进版） | 低 | 低（~20行改动） |

**CC 推荐：B1. RDP + 角度过滤。**
理由：这是 Requirements §二.3 的核心设计决策——"落盘前按容差拟合/抽样成稀疏关键帧，使 JSON 保持稀疏、可 diff、可版本化（护城河 T3）"。B2 不符合稀疏/可 diff 的要求。RDP (Ramer-Douglas-Peucker) 是曲线简化的标准算法，纯数学无依赖，JS 和 Python 可同源实现，复用 G4 parity 对拍策略。

RDP 参数建议：
- `pos_epsilon = scene_radius * 0.02`（位置容差 = 场景半径的 2%）
- `angle_epsilon = 0.02` rad（~1.15°，四元数角度变化阈值）
- fit 后在 Blender 端 Catmull-Rom 还原，比原稠密采样误差 ≤ 需求规定的 2%

### 决策 C：Hard-Cut Schema 增量

**背景**：Requirements §七规定「插值只在段内进行，绝不跨切点」。需要一种方式标记切点，使 JS 预览和 Python 渲染端都理解一致（R5 要求）。

**两种方案**：

| 方案 | JSON 表示 | 改动范围 |
|------|----------|---------|
| **C1. `cut: true` flag** | keyframe 上直接加 `"cut": true` | 最小：`CameraSpec.keyframes[]` 新增一个可选 bool 字段 |
| **C2. `shots[]` 分组** | `"shots": [{"index": 0, "keyframes": [...]}, ...]` 嵌套结构 | 中等：需要 `CameraSpec.shots` + 每 shot 的 keyframes 子数组 |

**CC 推荐：C1. `cut: true` flag。**
理由：改动最小（一个 bool 字段），向前兼容（无 cut 的旧数据行为不变），两端的 `interpolateKeyframes()` 只需加一个切点检测（遇到 `cut:true` 的 KF 时重置段边界，不跨段取窗口）。C2 虽然语义更清晰，但引入了嵌套结构，需要改 `CameraSpec` schema、序列化/反序列化、及两端的插值调用方。

---

## 2. Task List（按执行顺序）

### Task 1：拆分 viewport.js 为独立模块

**目标**：将当前 446 行的单体 `viewport.js` 拆分为 plan 规定的模块结构，解除内联。

**产出文件**：
- `apps/web/src/input_controller.js` — 从 viewport.js 抽取飞行控制 + 键鼠映射 + 速度 HUD
- `apps/web/src/recorder.js` — 从 viewport.js 抽取录制状态机 + 采样 + UI
- `apps/web/src/fitter.js` — 新建，实现 RDP + 角度过滤 fitter（纯函数，不依赖 DOM/Three.js）
- `apps/web/src/viewport.js` — 保留 Scene 初始化 + 渲染循环 + 模块组装

**验收**：
- [ ] 4 个 JS 模块文件各自独立，职责清晰
- [ ] viewport.html 不改动（仍是 `<script type="module" src="/web/src/viewport.js">`）
- [ ] 功能无回归：WASD 飞行 / 录制 / 速度 HUD 行为不变
- [ ] `backend/test_assets.py` 修复（`pip install python-multipart` 或 mock 依赖）

### Task 2：实现正式 fitter（RDP + 角度过滤）

**目标**：替换 `viewport.js` 中的占位 `fitAndSerialize()`。

**算法**（在 `fitter.js` 中实现）：
```
输入: samples[{t, pos:[3], quat:[4], fov}], pos_epsilon, angle_epsilon
  ↓
对每个 shot 的 position 序列做 RDP 简化 → 保留关键位置帧
对每对相邻保留帧的 quat 做角度距离检测 → 追加朝向变化过大的帧
  ↓
输出: keyframes[{t, pos, quat, fov, cut:true/false}]
```

**验收**：
- [ ] 纯函数，不依赖 Three.js/DOM（G1 扩展）
- [ ] 单元测试：100 帧直线运动 → RDP 后 ≤ 3 KF（端点+中间最多一个）
- [ ] 单元测试：100 帧复杂曲线 → RDP 后 KF 数显著少于 100
- [ ] 单元测试：RDP → Catmull-Rom 还原 与原始采样的最大误差 < pos_epsilon
- [ ] Python 同源移植 `fitter.py`（或在 parity test 里验证拟合输出的 JSON 能被 Python 正确插值还原）

### Task 3：落地 Hard-Cut Schema + 两端对齐

**目标**：依决策 C 落地切点标记，保证 JS 和 Python 两端理解一致。

**产出**：
- `CameraSpec.keyframes[]` 支持 `cut: true`（已在 schema 中预留，Pydantic `dict[str, Any]` 自动通过）
- `camera_math.js` `interpolateKeyframes()` 支持切点：遇到 `cut:true` 的 KF 时，该 KF 作为段终点+下一段起点，不跨段取 Catmull-Rom 窗口
- `blender/scripts/camera_math.py` `interpolate_keyframes()` 同步支持
- `docs/project_json_schema.md` 更新，记录 `cut` 字段定义

**验收**：
- [ ] Parity 测试：同一份含切点的 keyframes JSON，JS 和 Python 插值结果在容差内一致
- [ ] 跨切点插值测试：两个 shot 之间无插值帧（硬切）
- [ ] 无切点的旧 JSON 行为不变（向后兼容）
- [ ] `docs/project_json_schema.md` 有 `cut` 字段说明

### Task 4：后端持久化端点 + 前端对接

**目标**：录制的 CameraSpec 能保存到 Project JSON，能被 Blender 渲染。

**产出**：
- 新建 `POST /api/projects/{project_id}/camera` 端点（或复用现有 `POST /api/render`）
- 前端 `app.js` 接收 viewport 的 `postMessage`，将 `shots`/`keyframes` 注入 Project JSON 的 `camera.keyframes` 和 `camera.shots` 字段
- Blender 渲染链路验证：含交互式 keyframes 的 Project JSON → `render_project.py` → MP4

**验收**：
- [ ] 前端录制完成 → 可点"发送到渲染" → 后端收到含 keyframes 的 Project JSON
- [ ] `POST /api/render` 接受含 `camera.keyframes` 的有效 JSON 并正常返回 task_id
- [ ] Blender 实渲含 keyframes 的 Project JSON 出片无报错
- [ ] Smoke test: 新增含 keyframes 的 golden path 用例

### Task 5：Parity 闸门（核心验收）

**目标**：证明预览取景 ≈ Blender 实渲。

**步骤**：
1. 固定一个测试场景（同一 GLB/PNG + 同一 camera keyframes）
2. 浏览器截取预览画面（关键帧位置截图）
3. 同一份 keyframes JSON 送入 Blender 实渲 → 取对应帧截图
4. 量化对比：主体边界框中心偏移 ≤ 画幅 2%，画面四角无明显透视差异
5. PERSP + `title` 文字叠加实渲 1 发 → 验证 carry-forward（loop 07 遗留）

**闸门判定**：人眼不可分辨（practical pass, ADJ-3）+ 量化误差 ≤ 2%

**产出**：
- `storage/visual_gate/loop08_parity/` — 对比截图对（至少 3 组：开始/中间/结束帧）
- `storage/visual_gate/loop08_persp_title/` — PERSP + title 实渲

**验收**：
- [ ] 3+ 组对比截图，人眼判定通过（启鸣确认）
- [ ] 量化误差 ≤ 2%
- [ ] PERSP + title 文字定位正确（不偏不溢）

### Task 6：回归闸门 — 默认路径零回归

**目标**：不含交互 keyframes 的既有项目渲染输出逐位一致。

**步骤**：
1. 取 loop 07 基线 project JSON（无 keyframes）
2. 用当前代码渲染
3. pixel-diff vs loop 07 基线（沿用 ADJ-2 方法）
4. 确认逐位一致

**验收**：
- [ ] 至少 2 个 preset（dolly_in + orbit）pixel-diff = 0
- [ ] 含 particles 的 project 同样通过

### Task 7：清理 + 文档 + 变更报告

**目标**：代码就绪，文档完整，可交给启鸣验收。

**产出**：
- `apps/web/src/` 模块化完成（input_controller / recorder / fitter / viewport）
- `fitter.js` + 配套测试就绪
- `docs/project_json_schema.md` 更新（cut 字段 + shots 说明）
- `docs/parameters.md` 更新（交互式相机参数说明）
- `AGENTS.md` 变更报告（本 loop 改动汇总）
- CLAUDE.md 更新（loop 08 完成状态）

---

## 3. 文件变更预期

| 操作 | 文件 |
|------|------|
| 新建 | `apps/web/src/input_controller.js` |
| 新建 | `apps/web/src/recorder.js` |
| 新建 | `apps/web/src/fitter.js` |
| 新建 | `tests/frontend/test_fitter.py`（Python 端 fitter 验证） |
| 修改 | `apps/web/src/viewport.js`（抽走内联逻辑，改为 import 组装） |
| 修改 | `apps/web/src/camera_math.js`（切点支持） |
| 修改 | `blender/scripts/camera_math.py`（切点支持 — 同步 JS 改动） |
| 修改 | `apps/web/app.js`（接收 viewport message，注入 camera JSON） |
| 修改 | `server/routes/render.py`（如有新端点） |
| 修改 | `docs/project_json_schema.md`（cut/shot schema） |
| 修改 | `docs/parameters.md`（交互式相机参数） |
| 不碰 | `blender/scripts/render_project.py`（Andy plan G3 要求不动渲染逻辑） |
| 不碰 | `server/services/blender_service.py` |

---

## 4. 预计执行顺序与依赖

```
Task 1 (拆分模块)
  └─▶ Task 2 (fitter) ─▶ Task 3 (hard-cut schema)
         └─▶ Task 5 (parity 闸门) ─▶ Task 6 (回归)
                                    └─▶ Task 7 (清理+文档)

Task 4 (后端端点) ← 可与 Task 2/3 并行
```

Task 1-4 均可并行或交叉执行。Task 5/6 依赖 Task 2/3/4 完成（需要有 fitter 输出 + 后端可渲染）。
