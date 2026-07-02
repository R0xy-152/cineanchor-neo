# 08 — 交互式运镜控制 — 验收（Acceptance）

> 作者：Andy · 签收：启鸣（2026-07-02）
> 上游：`08-interactive-camera-control-{requirements,plan}.md`（Andy, 2026-06-29）
> 执行分支：`feature/loop08-interactive-camera` HEAD `4604384`

## 一、总判定

Loop 08 **通过验收**。

「人手摆 = 渲染结果」打通：Three.js PERSP 浏览器预览 + 键鼠 fly-cam + recording-take 模型（左录 / 右停，允许硬切，段内插值）+ 稠密采样→稀疏关键帧拟合 + parity 闸门。渲染后端未动，CameraSpec JSON 仍是唯一真相。这补上了 loop 07（能**算**轨迹）到 loop 08（人能**用手摆且摆=渲**）的缺口，是护城河 T2「精确输入」这一维的落地。

**最难一关 = 门 4 视觉 parity。** 一度因坐标手性 bug 卡住：数学对拍全绿但取景仍错。靠 Andy 让 CC 建的 **golden-pose oracle**（Three→Blender 真值锚）定位到 2 个确切 bug 并修复，154 测试全绿，启鸣 2026-07-02 人眼确认预览与实渲不可分辨。

> **教训升级（新护栏）：** JS↔python 数学对拍绿 ≠ 坐标变换正确——29 个对拍只证明两端**插值一致**，它们可以**一起错**。oracle 才是抓手性 bug 的东西，永久留在 `tests/parity/` 作回归。

## 二、验收表逐条（对应需求 §五）

| # | 标准 | 判定方式 | 结果 |
|---|------|---------|------|
| 1 | 视口加载资产 + 实时显示当前机位 | 人工 + 截图 | ✅ GLB 加载，实时预览，启鸣确认 |
| 2 | 键鼠映射全生效、手感可用 | 启鸣 试用 | ✅ WASD/Space/Ctrl/Shift 降速/Tab(Alt) 升速/mouse look/左录右停/滚轮推拉，速度 HUD 实时 |
| 3 | 录制 + 续录 + scrub；稠密→稀疏拟合，07 引擎容差还原；同源插值 | 单测 + 人工 | ✅ 状态机 + RDP + 角度滤波；29 JS↔python 对拍；拟合还原 ≤3×epsilon；硬切 5 测试 |
| 4 | **parity：预览取景 ≈ Blender 实渲**（核心） | 视觉闸门 | ✅ oracle 6 golden pose 转绿，坐标手性 2 bug 修复，启鸣 2026-07-02 人眼确认不可分辨 |
| 5 | JSON 往返无损 + 交互关键帧原样渲染 | 单测 + 抽验 | ✅ schema 校验 + 渲染管线贯通 |
| 6 | 默认路径零回归（无交互关键帧→逐位一致） | pixel-diff（ADJ-2） | ✅ ≤0.0003%（0–6 像素浮点噪声，最大通道差 2/255）；调用链隔离静态证明 |
| 7 | carry-forward：PERSP + `title` 文字定位正确 | 实渲 + 人工 | ✅ 白像素集中顶部 1/3，不偏不溢，启鸣确认 |
| 8 | 本地产物 + 全部新增/改动文件路径 | CC 报告 | ✅ `docs/08-interactive-camera-acceptance.md`（gate 报告）+ artifacts |

## 三、交付物

- 前端模块 `apps/web/src/`：`camera_math.js` / `camera_presets.js` / `input_controller.js` / `recorder.js` / `fitter.js` / `viewport.js`
- python（复用 loop 07）：`camera_math.py` / `camera_presets.py`；`render_project.py::_adapt_user_keyframes` 修复（补 scene_center 偏移 + 保留录制朝向 + 用真实机位距离）
- **`tests/parity/test_three_to_blender_oracle.py`** = 永久回归真值锚（6 axis-aligned golden pose）
- 154 测试全绿（HEAD `4604384`）

## 四、已知边界 / carry-forward → loop 09

- 视觉 parity 的最终判定是「人眼不可分辨」（ADJ-3 practical pass）+ 干净剪影/bbox 上 landmark ≤2%；**刻意不追求**均匀光照 Eevee 场景下的全自动像素检测（不可靠，且是过度工程）。
- CC 无法在 CLI 驱动浏览器，门 4 的人工 A/B 由启鸣完成。
- 手柄、3D 轨迹拖拽编辑 = 明确 deferred。
- 「是否改用 Blender 原生驱动预览」= loop 09 独立 **spike**（parity 可白嫖，但护城河是浏览器 60fps 飞行手感 + 零安装可演示；本 loop 保持 Three.js，不做中途 pivot）。

## 五、沉淀

本 loop → **ADR-008**（recording-take 模型 + 稠密→稀疏 fitter + JS/python 同源插值 + oracle 纪律）。见 `docs/adr/ADR-008-*`。
