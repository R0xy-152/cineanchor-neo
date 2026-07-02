# 09 — 手柄输入 + Blender 原生预览 Spike — 需求（Requirements）

> 作者：Andy（需求收敛）· 待启鸣 pass/reject
> 前置：loop 08 已验收（`08-interactive-camera-control-acceptance.md`，ADR-008）
> 锁定决策来源：启鸣 2026-07-02「都按推荐」

## 一、定位

Loop 08 打通了「人手摆 = 渲染结果」（键鼠 fly-cam）。Loop 09 干两件事，且**刻意分主次**：

- **Track A（feature）— 手柄输入。** 把飞行手感从键盘升级到手柄：模拟摇杆的连续档位感 >> 键盘离散按键，直接服务护城河 T2「精确输入」的**手感**维度。纯输入层扩展，跟预览架构无关。
- **Track B（spike）— Blender 原生预览调研。** 用一个 timebox spike 回答悬了两个 loop 的架构问题：live preview 到底该不该从 Three.js 改成 Blender 原生驱动。**只出结论，不交付。**

**明确不做（推到 loop 10）：** 3D 轨迹拖拽编辑。理由：它若建在 Three.js 上、而 spike 结论是换 Blender，就白做——等 spike 把架构定了再建，避免返工。

## 二、范围

### Track A — 手柄输入（架构无关的 feature）

- 在 loop 08 输入层（`input_controller`）上加手柄支持，**与键鼠共存**（同时可用、不互斥）。
- **映射锁定**（启鸣 2026-07-02）：
  - 左摇杆 = 平移（前后左右，等价 WASD）
  - 右摇杆 = 看向（带灵敏度曲线，**手感优先**）
  - LT / RT 扳机 = 推拉 dolly + 速度微调
  - 肩键 / 面键 = 上 / 下（等价 Space / Ctrl）
  - 面键 = 录制 / 暂停（等价鼠标左键 / 右键）
  - 速度 ramp（loop 08 Shift 降 / Tab 升的手柄等价）= 十字键或另一对肩键；**速度 HUD 实时显示**
- **死区 + 灵敏度曲线 + 映射绑定 从代码常量解耦到外部可编辑配置**（如 settings JSON），用户改参数 / 改绑定无需改代码或重编译（启鸣 2026-07-02 追加）。完整设置面板 UI 可推 loop 10，但**参数值不得硬编码**。
- 手柄录出的 take = 同一条 dense sample → **同一 fitter → 同一 JSON**，与键鼠录制无差别。

### Track B — Blender 原生预览 SPIKE（研究，timebox，不产 ADR）

- **问题：** live preview 改用 Blender 驱动（而非 Three.js）是否值得？
- **切换判定（启鸣锁定）：** Blender 预览必须同时满足 (1) 桌面壳内 **≥30–60fps 可用帧率**，(2) **飞行手感不比 Three.js 差**；两者都满足才切，parity 白嫖只是**加分**、不是切的理由。任一不满足 → 保持 Three.js。
- **产出：** spike 报告（`docs/` 下，CC 技术产物）+ 一句明确 recommendation（切 / 不切 / 有条件切），Andy 据此定 loop 10 架构走向。
- **timebox：** CC plan 阶段定具体上限，不 rathole。
- **隔离：** spike 不改 JSON、不改渲染后端、不动 loop 08 已验收代码；原型代码隔离，结论落文档。

## 三、架构约束

- CameraSpec JSON 仍是唯一真相；手柄只是新输入源，**不改数据模型**。
- 手柄 track 复用 loop 08 的 `recorder` / `fitter` / `camera_math`，**不新开第二条插值路径**（同源铁律延续）。
- **oracle 回归必须持续绿**（`tests/parity/`）；任何触到坐标/转换的改动先扩 oracle 再合并。
- 默认路径零回归延续（ADJ-2）。

## 四、不可谈判项

1. 手柄与键鼠录出的 take 走**同一 fitter / 同一 JSON**，无第二条插值路径。
2. **spike 是研究不是交付**：不得把半成品 Blender 预览合进主干；spike 代码隔离，结论只落文档。
3. **oracle + 默认路径回归保持绿。**
4. spike 判定必须用锁定的 bar（帧率 + 手感不劣化），**不许中途为了「parity 好看」就放水切**。

## 五、验收表（待 CC plan 细化判定方式）

**Track A（feature，有闸门）**

| # | 标准 | 判定方式 | 阻塞 |
|---|------|---------|------|
| A1 | 手柄接入，与键鼠共存，实时驱动预览 | 人工试用 + 启鸣手感确认 | 是 |
| A2 | 锁定映射全生效（左移/右看/扳机推拉+速度/上下/录停/速度ramp+HUD） | 启鸣 试用 | 是 |
| A3 | 死区 + 灵敏度曲线，手感可用不漂 | 启鸣 试用 | 是 |
| A4 | 手柄录制的 take 经 fitter→JSON→07 引擎容差还原，与键鼠无差别 | 单测 + 抽验 | 是 |
| A5 | oracle 全绿 + 默认路径零回归 | 单测 + pixel-diff | 是 |
| A6 | 手柄参数（死区/灵敏度/映射绑定）从外部可编辑配置读取，改参数无需改代码/重编译 | 人工改配置验证 | 是 |

**Track B（spike，产结论不产闸门）**

| # | 标准 | 判定方式 |
|---|------|---------|
| B1 | Blender 预览原型能跑，测到桌面壳帧率实数 | CC 报告实测数字 |
| B2 | 飞行手感对比（Blender vs Three.js）有明确主观评估 | 启鸣 试用二者对比 |
| B3 | 明确 recommendation（切 / 不切 / 有条件），对齐锁定 bar | Andy 据此定 loop 10 |

## 六、已拍板决策（启鸣 2026-07-02「都按推荐」→ Andy 锁定）

1. **主线 = Spike 先行 + 手柄**；3D drag-edit 推 loop 10。
2. **spike 切换 bar** = 帧率（≥30–60fps）+ 手感不劣化才切，parity 白嫖只加分。
3. **手柄映射** = §二 Track A 那套；**且死区/灵敏度/绑定从代码常量解耦到外部可编辑配置**（启鸣 2026-07-02 追加），用户可调，禁止硬编码。
4. **drag-edit 编辑范围（loop 10 预定）**：可拖轨迹控制点改位置；朝向默认沿切线自动、允许单点覆盖；**不能跨硬切拖**；改完重走 fitter→JSON，渲染路径不变。

## 七、备注

- **ADR eval（需求通过后做）：** 手柄 track 是既定模式（ADR-008 recording-take + 同源插值）的输入扩展，大概率**不触发新 ADR**；spike 按规则不产 ADR。
- 若 spike 结论是「切 Blender」，那是 loop 10 的架构级决策，**届时才产 ADR**。
