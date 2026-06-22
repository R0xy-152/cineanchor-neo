# CineAnchor\_可行性操作文档

**CineAnchor**

MVP 可行性操作文档

*技术架构 · 验证路线 · 开发规范 · 推进框架*

---

文档版本：V1\.0  

文档版本：V1\.1\-技术和项目管理角度进行修改

---

# **一、总判断与核心问题诊断**

## **1\.1 产品定位**

**推荐定位 **CineAnchor：给「没有 3D 资产的手游/独立游戏运营」，用「模板化 3D 镜头 \+ AI 画面美化」，快速生成「可直接发抖音/小红书/Steam 的 8\-15 秒宣传短片」，取代「找外包做 AE 动画」或「用剪映硬拼静态截图」。

注意：电商产品广告方向作为第二阶段扩展，不在 MVP 范围内。

## **1\.2 最终呈现物**

MVP 的最终呈现物定义如下，这是唯一的验收对象：

|**目标产物**|一段 8\-15 秒、1080p、可直接发布的游戏角色/道具宣传短视频|
|---|---|
|**输入**|1 张透明 PNG 角色图 或 1 个 GLB 模型，1 段标题文案，可选 BGM|
|**操作步骤**|上传素材 → 选模板 → 改文案 → 点生成 → 下载 MP4，全程不超过 5 步|
|**画质标准**|看起来像手游活动宣传片，不像 PPT 截图；主体不变形；无明显闪烁|
|**不承诺**|电影级 CG、实时预览与最终渲染完全一致、多人协作、云端渲染|
|**次生产物**<br>|1. GitHub 仓库<br>2. README<br>3. 60–90 秒项目介绍视频<br>4. 系统架构图<br>5. 渲染管线图<br>6. Project JSON 示例<br>7. 技术复盘文档<br>8. AI Agent 开发记录<br>9. ComfyUI 调用流程<br>10. FFmpeg 合成规范|

## **1\.3 技术架构**

|**高风险点**|**实际需要什么**|
|---|---|
|**高风险点**|实际需要什么|
|**Blender 渲染耗时**|1080p/8秒/Cycles 在 5070Ti 上约 3\-15 分钟，严重影响产品体验设计|
|**Three\.js 预览 vs Blender 渲染差异**|需要明确 WYSIWYG gap 的边界，前端预览只做构图确认|
|**渲染队列与并发**|单卡无并发，需要串行队列 \+ 任务状态机 \+ 进度推送|
|**ComfyUI 集成稳定性**|冷启动时间、工作流版本锁定、显存共享（Blender\+ComfyUI 同跑可能 OOM）|
|**GLB 资产质量差异**|用户上传的 GLB 可能面数过高、贴图缺失、坐标轴错误，需要预校验|

## **1\.4 工程规范**

|**⚠️ 问题 **前期\.md 要求「先搭 docs/ADR/契约/Schema 全套脚手架」，但 MVP 方案又说「第 0 步先做技术验证 Demo」。两份文档自相矛盾。在最大技术风险（Blender 能否从 JSON 渲出 MP4）还未被证明之前，锁死 API 合同和数据库 Schema，是把顺序搞反了。|
|---|

正确顺序：先用「会被扔掉的 spike」打通最危险的链路，验证完再谈结构和规范。

---

# **二、技术可行性验证路线（Spike 阶段）**

|**核心原则 **验证的目的是回答「这条链路能不能通」，不是提前搭产品骨架。|
|---|

## **验证路线 0（第 1\-2 天）：3D 渲染基础闭环**

**目标问题：Blender 能否从一个 GLB 模型出发，自动控制摄像机环绕，导出 MP4？**

验证脚本结构：

spike\_render/

├─ input/model\.glb          \# 任意一个免费 GLB，如 Sketchfab 下载

├─ output/frames/           \# Blender 输出帧

├─ output/final\.mp4         \# FFmpeg 合成结果

├─ render\_orbit\.py          \# Blender headless 脚本

└─ make\_video\.sh            \# FFmpeg 合成命令

render\_orbit\.py 核心逻辑（伪代码）：

import bpy, math

bpy\.ops\.import\_scene\.gltf\(filepath='input/model\.glb'\)

\# 自动计算模型包围盒，放置摄像机

\# 设置环绕动画：帧 1 到 192（8秒×24fps）

\# 设置 Cycles/Eevee，分辨率 1920x1080

bpy\.ops\.render\.render\(animation=True\)

FFmpeg 合成命令：

ffmpeg \-r 24 \-i output/frames/%04d\.png \-c:v libx264 \-crf 18 \-pix\_fmt yuv420p output/final\.mp4

验收判据：

- Blender headless 能无报错运行

- 192 帧正常生成，无黑帧

- FFmpeg 合成出 MP4，可用播放器正常播放

- 【关键】记录渲染总耗时。若超过 10 分钟，Eevee 替代 Cycles，重新测试

|**技术建议 **渲染耗时是这一步最重要的结论。Cycles（光线追踪）画质好但慢；Eevee（实时渲染）快但画质差。如果 Cycles 在 5070Ti 上渲 8 秒视频超过 5 分钟，MVP 阶段就必须用 Eevee，并在产品设计里把「等待渲染」设计进用户流程。|
|---|

## **验证路线 1（第 3\-4 天）：图片 2\.5D 视频**

**目标问题：没有 3D 模型的用户，上传一张透明 PNG，能否生成一段「不像 PPT」的视频？**

技术链路：

透明 PNG → 作为贴图贴到 Blender 平面 Mesh → 场景加背景/灯光/粒子 → 摄像机推近 → FFmpeg 合成 \+ 加标题文字

验收判据：

- PNG 贴图在 Blender 里正确显示（透明通道正常）

- 摄像机推近过程中角色始终在画面内

- 输出视频「看起来像宣传片而不像 PPT」（主观判断，给 3 个非开发者看，超过 2 个认可即通过）

|**重要性说明 **这条验证线的优先级高于 GLB 路线，因为 80% 的目标用户（游戏运营）只有角色立绘，没有 GLB 模型。如果这条线跑不通，产品的用户池会缩减 80%。|
|---|

## **验证路线 2（第 5\-7 天）：JSON 驱动模板化渲染**

**目标问题：用一个 JSON 文件控制模板、素材路径、镜头参数，能否渲出对应视频？**

这是产品差异化的核心验证。验证通过后，产品代码才有了「可驱动的引擎」。

最小 Project JSON 结构：

\{

"template": "character\_intro",

"asset\_type": "image",

"asset\_path": "input/hero\.png",

"camera\_motion": "dolly\_in",

"duration": 8,

"fps": 24,

"aspect\_ratio": "9:16",

"title": "New Hero Arrival",

"subtitle": "Limited Event"

\}

验收判据：

- render\_from\_json\.py 读取 JSON，无需改代码即可切换素材路径

- 修改 camera\_motion 字段，渲染结果中摄像机运动方式确实改变

- 修改 aspect\_ratio 字段，输出视频比例确实改变（16:9 / 9:16）

- 先做 3 个模板：character\_intro、product\_orbit、prop\_showcase

## **验证路线 3（第 8\-10 天）：ComfyUI AI 美化**

**目标问题：Blender 渲染的原始视频，经过 ComfyUI 处理后，画面是否明显提升且主体不变形？**

|**策略选择 **MVP 阶段采用「保守稳定版」：对关键帧做 AI 美化，再对全视频做调色/锐化，而不是对每一帧做 AI 重绘。「逐帧 AI 重绘」留到 V2\.0，原因是极易出现闪烁和主体变形，商用品质不可控。|
|---|

美化链路（保守版）：

Blender 原始 MP4

→ FFmpeg 抽取关键帧（每秒 1 帧）

→ ComfyUI SDXL 工作流：调色 \+ 锐化 \+ 降噪 \+ 轻度风格化

→ 提取颜色风格参数（主色调、对比度、饱和度）

→ FFmpeg 对原视频应用 LUT \+ 滤镜

→ 合成最终 MP4

验收判据：

- ComfyUI 通过 API（POST /prompt）被 Python 脚本成功调用

- 美化版视频「明显更好」（同样给非开发者对比看）

- 主体（角色/产品）未变形

- 无明显帧间闪烁

- 【关键】记录 ComfyUI 处理一帧的耗时，与 Blender 是否存在显存竞争（Blender \+ ComfyUI 同时运行是否 OOM）

## **验证路线 4（第 11\-14 天）：Web 到本地渲染串联**

**目标问题：前端页面操作 → FastAPI → 调用 Blender → 返回 MP4，整条链路能否跑通？**

这是「脚本验证」到「可用产品」的最后一道关。前端只需要 4 个控件：

- 上传素材（图片/GLB）

- 选择模板（下拉框，3 个选项）

- 填写标题文字

- 点击生成 → 轮询状态 → 下载 MP4

验收判据：

- 上传素材后，文件正确保存到 /storage/assets/

- 点击生成后，后端正确生成 Project JSON 并调用 Blender

- 前端能通过轮询接口感知渲染进度（0% → 100%）

- 渲染完成后，前端提供可点击的下载链接

- 全流程无需手动干预

---

# **三、技术架构方案（基于验证结论确定）**

|**前提说明 **以下架构基于验证路线全部通过的假设。如果验证路线 0 中 Cycles 渲染超过 10 分钟，需要降级为 Eevee 并修改架构中的「画质说明」。如果验证路线 3 发现 ComfyUI \+ Blender 存在严重显存竞争，需要拆分为顺序执行而非并发。|
|---|

## **3\.1 整体技术栈**

|**层级**|**技术选型**|
|---|---|
|**层级**|技术选型|
|**前端框架**|Next\.js 14 \+ React 18（App Router）|
|**3D 预览**|React Three Fiber（Three\.js 封装），仅用于构图预览，不代表最终渲染效果|
|**状态管理**|Zustand（轻量，适合本地优先应用）|
|**样式**|Tailwind CSS|
|**后端框架**|Python FastAPI（异步支持，适合与 Blender 进程通信）|
|**数据校验**|Pydantic v2|
|**数据库**|SQLite（单机本地，足够 MVP；后期可迁移 PostgreSQL）|
|**任务队列**|Python asyncio \+ 简单内存队列（MVP 阶段不用 Celery，避免引入 Redis 依赖）|
|**3D 渲染**|Blender 4\.x Headless，Eevee 引擎（MVP），Cycles 可选|
|**AI 美化**|ComfyUI 本地部署，SDXL 模型，通过 REST API 调用|
|**视频处理**|FFmpeg（必须）\+ MoviePy（辅助，可选）|
|**桌面封装**|第一阶段：浏览器访问 localhost；第二阶段：Tauri（比 Electron 更轻）|

## **3\.2 系统数据流**

完整的一次视频生成请求的数据流如下：

【前端】用户上传素材 → 文件存 /storage/assets/\{project\_id\}/

【前端】用户选模板、填参数 → 生成 Project JSON

【前端】POST /api/render \{project\_json\}

↓

【FastAPI】验证 Project JSON（Pydantic）→ 写入 SQLite（任务状态: PENDING）

【FastAPI】调用 Blender headless 子进程

↓

【Blender】读取 Project JSON → 导入素材 → 搭建场景 → 渲染帧序列

【Blender】输出 PNG 帧到 /storage/renders/\{task\_id\}/frames/

【Blender】完成后写入 exit code 0

↓

【FastAPI】检测 Blender 完成 → 调用 FFmpeg 合成 MP4

【FastAPI】（可选）调用 ComfyUI 做 AI 美化

【FastAPI】更新任务状态: DONE，写入输出路径

↓

【前端】轮询 GET /api/render/\{task\_id\}/status → 显示进度

【前端】状态 DONE → 提供 MP4 下载链接

## **3\.3 Project JSON Schema（正式版）**

这是驱动整个渲染管线的核心数据结构，前后端共同约定，不可随意改动。

\{

"version": "1\.0",

"project\_id": "uuid\-string",

"project\_type": "game\_showcase \| product\_ad",

"template": "character\_intro \| product\_orbit \| prop\_showcase",

"output": \{

"duration": 10,          // 秒

"fps": 24,

"aspect\_ratio": "9:16",  // 或 "16:9"

"resolution": "1080"     // 1080p

\},

"assets": \[

\{

"id": "main\_subject",

"type": "image \| glb",

"path": "storage/assets/\{project\_id\}/hero\.png"

\}

\],

"camera": \{

"motion": "dolly\_in \| orbit \| slide",

"start\_distance": 5\.0,

"end\_distance": 3\.0,

"height": 1\.5,

"focal\_length": 50

\},

"scene": \{

"background": "dark\_stage \| cyber\_grid \| gradient",

"lighting": "studio\_softbox \| backlight\_drama \| rim\_light",

"particles": true,

"fog": true

\},

"text": \{

"title": "New Hero Arrival",

"subtitle": "Limited Event",

"font\_style": "impact \| cinematic \| clean"

\},

"ai\_enhance": \{

"enabled": true,

"mode": "conservative",  // MVP 只用 conservative

"style": "premium\_ad \| game\_cg"

\}

\}

## **3\.4 任务状态机**

|**状态**|说明|
|---|---|
|**PENDING**|任务已创建，等待 Blender 空闲|
|**RENDERING**|Blender 正在渲染帧序列|
|**COMPOSITING**|FFmpeg 正在合成 MP4|
|**ENHANCING**|ComfyUI 正在做 AI 美化（可选步骤）|
|**DONE**|全部完成，MP4 可下载|
|**FAILED**|任一步骤失败，附错误码|

## **3\.5 错误码规范（前期必须定义）**

不要等后期再补错误码。Blender 脚本报错后，FastAPI 必须能给出明确原因，否则调试极难。

|**错误码**|触发场景|
|---|---|
|**ASSET\_NOT\_FOUND**|Project JSON 中的资产路径文件不存在|
|**INVALID\_PROJECT\_JSON**|JSON 校验失败（Pydantic 抛出）|
|**ASSET\_IMPORT\_FAILED**|Blender 无法加载 GLB 文件（格式错误/损坏）|
|**CAMERA\_SETUP\_FAILED**|摄像机关键帧生成失败|
|**BLENDER\_RENDER\_FAILED**|Blender 渲染过程中崩溃（返回非 0 exit code）|
|**FFMPEG\_COMPOSE\_FAILED**|FFmpeg 合成 MP4 失败|
|**COMFY\_ENHANCE\_FAILED**|ComfyUI API 调用失败或超时|
|**TASK\_ALREADY\_RUNNING**|同一个渲染任务已在队列中，拒绝重复提交|
|**RENDER\_TIMEOUT**|渲染超过最大等待时间（建议设 30 分钟）|

## **3\.6 存储路径规范**

路径必须统一，不允许硬编码绝对路径。所有路径从配置文件读取。

storage/

├─ assets/\{project\_id\}/        \# 用户上传的原始素材

├─ renders/\{task\_id\}/

│  ├─ frames/                  \# Blender 输出帧（0001\.png\.\.\.）

│  ├─ raw\.mp4                  \# FFmpeg 合成的原始视频

│  └─ enhanced\.mp4             \# ComfyUI 处理后的最终视频

├─ exports/\{task\_id\}/          \# 最终对外下载的版本

└─ projects/\{project\_id\}/

└─ project\.json             \# 保存的项目配置

---

# **四、项目目录结构**

以下目录结构为 MVP 阶段推荐结构。Spike 验证阶段不需要这个结构，用简单脚本即可。

cineanchor/

├─ AGENTS\.md                       \# AI 开发规范（见第五章）

├─ README\.md

├─ Makefile                         \# make check / make smoke / make dev

│

├─ docs/

│  ├─ 00\_project\_overview\.md       \# 产品定位（一句话）

│  ├─ 01\_mvp\_scope\.md              \# MVP 范围（不做什么和做什么一样重要）

│  ├─ 02\_api\_contract\.md           \# API 接口约定（由验证结论确定后锁定）

│  ├─ 03\_project\_json\_schema\.md    \# Project JSON 完整 Schema

│  ├─ 04\_error\_codes\.md            \# 错误码全表

│  ├─ 05\_storage\_layout\.md         \# 存储路径规范

│  └─ adr/                         \# 架构决策记录

│     ├─ ADR\-001\-use\-fastapi\.md

│     ├─ ADR\-002\-use\-eevee\-for\-mvp\.md

│     └─ ADR\-003\-blender\-headless\-not\-ue\.md

│

├─ apps/

│  └─ web/                         \# Next\.js 前端

│     ├─ app/

│     │  ├─ page\.tsx               \# 首页

│     │  ├─ editor/page\.tsx        \# 编辑器主界面

│     │  └─ queue/page\.tsx         \# 渲染队列

│     ├─ components/

│     │  ├─ TemplateSelector/

│     │  ├─ AssetUploader/

│     │  ├─ PreviewCanvas/         \# Three\.js 预览

│     │  └─ RenderQueue/

│     └─ lib/

│        ├─ api\.ts                 \# FastAPI 调用封装

│        └─ project\-schema\.ts      \# Project JSON 类型定义

│

├─ server/

│  ├─ main\.py                      \# FastAPI 入口

│  ├─ config\.py                    \# 路径配置（不硬编码）

│  ├─ routes/

│  │  ├─ projects\.py

│  │  ├─ assets\.py

│  │  ├─ render\.py

│  │  └─ export\.py

│  ├─ services/

│  │  ├─ blender\_service\.py        \# 调用 Blender 子进程

│  │  ├─ ffmpeg\_service\.py

│  │  ├─ comfy\_service\.py

│  │  └─ task\_queue\.py             \# 简单串行队列

│  ├─ schemas/

│  │  ├─ project\.py                \# Pydantic Project JSON 校验

│  │  └─ render\_task\.py

│  └─ db/

│     ├─ models\.py

│     └─ cineanchor\.sqlite

│

├─ blender/

│  ├─ scripts/

│  │  ├─ render\_project\.py         \# 主入口，读取 Project JSON

│  │  ├─ import\_assets\.py          \# 导入 GLB / PNG 平面

│  │  ├─ setup\_camera\.py           \# 根据模板生成摄像机关键帧

│  │  ├─ setup\_lighting\.py         \# 灯光预设

│  │  ├─ setup\_scene\.py            \# 背景/粒子/雾气

│  │  └─ setup\_text\.py             \# 标题/字幕叠加

│  └─ scenes/

│     ├─ dark\_stage\.blend          \# 基础场景模板

│     └─ cyber\_grid\.blend

│

├─ comfy/

│  └─ workflows/

│     ├─ image\_enhance\.json        \# 关键帧美化工作流

│     └─ upscale\.json

│

├─ storage/                        \# 运行时数据（不入 git）

│  ├─ assets/

│  ├─ renders/

│  └─ exports/

│

└─ tests/

├─ backend/

│  ├─ test\_render\_api\.py

│  └─ test\_project\_schema\.py

└─ smoke/

└─ test\_golden\_path\.py       \# 黄金路径：一次完整渲染

---

# **五、开发规范（AGENTS\.md 内容）**

以下内容应完整写入仓库根目录的 AGENTS\.md 文件。每个 AI Agent 开始工作前必须先读这个文件。

## **5\.1 分支策略**

|**分支**|**规范**|
|---|---|
|**main**|只放经过完整测试的稳定版本，不直接推送|
|**develop**|集成分支，所有 feature 先合并到这里|
|**feature/\***|每个 Agent 一个任务分支，完成后合并到 develop|
|**spike/\***|验证阶段专用，完成后可直接删除，不合并 develop|
|**docs/\***|文档、README、作品集材料|

## **5\.2 Prompt 任务模板**

每次给 AI Agent 分配任务时，必须使用以下固定格式：

Branch: feature/cineanchor\-\{task\-name\}

Scope: \{一句话描述\}

Allowed files:

\- server/routes/render\.py

\- server/services/render\_service\.py

\- tests/backend/test\_render\_api\.py

Forbidden:

\- 不允许修改前端代码

\- 不允许修改 Blender 脚本

\- 不允许新增依赖（如必须新增，需说明理由）

\- 不允许修改 Project JSON Schema

Acceptance:

\- pytest tests/backend/test\_render\_api\.py 全部通过

\- make check 通过

\- API 有变动时必须更新 docs/02\_api\_contract\.md

Output（完成后必须提供）:

\- 修改了哪些文件

\- 运行了哪些测试

\- API 是否变动：yes/no

\- Schema 是否变动：yes/no

\- 已知风险

## **5\.3 不可合并条件（10 条硬性规则）**

只要出现以下任意一条，主 Agent 拒绝合并：

|**条件**|**说明**|
|---|---|
|**规则 1**|修改了任务 Prompt 范围外的文件|
|**规则 2**|没有写测试（除非任务明确是「只写测试」的后续实现任务）|
|**规则 3**|测试写了但没有运行，或运行失败|
|**规则 4**|修改了 API 接口但没有更新 docs/02\_api\_contract\.md|
|**规则 5**|修改了 Project JSON Schema 但没有更新 docs/03\_project\_json\_schema\.md|
|**规则 6**|新增了 Python 依赖但没有说明为什么必须引入|
|**规则 7**|删除了已有测试|
|**规则 8**|代码中存在绑过错误处理（bare except / 忽略异常）|
|**规则 9**|硬编码了绝对路径（应从 config\.py 读取）|
|**规则 10**|破坏了黄金路径（tests/smoke/test\_golden\_path\.py 失败）|

## **5\.4 主 Agent 合并前检查清单**

代码范围检查：

- 这个分支有没有改不该改的文件？

- 有没有顺手重构？（不允许）

- 有没有把已有逻辑删掉？

- 有没有引入新依赖？

合同检查：

- Project JSON Schema 有没有变？

- API 接口字段有没有变？

- 数据库 Schema 有没有变？

- 错误码有没有变？

黄金路径检查（CineAnchor 专项）：

- 能否用 sample\.png 跑通 character\_intro 模板？

- 能否生成帧序列？

- 能否用 FFmpeg 导出 MP4？

- 任务状态是否正确流转（PENDING → RENDERING → DONE）？

## **5\.5 先写测试，再写实现**

AI Agent 开始写功能代码前，必须先完成：

1. 写测试文件，明确「这个功能通过什么测试算完成」

2. 写 fixtures 和 mock 数据

3. 运行测试，确认测试在没有实现的情况下会失败（红灯）

4. 写实现代码，让测试通过（绿灯）

5. 重构，确保测试仍然通过

|**为什么 **AI 最容易犯的错是「写出了代码，但写出的不是要求的代码」。先写测试是让 AI 先理解需求，再动手。|
|---|

## **5\.6 每次变更后必须输出变更报告**

格式固定，不允许省略：

Changed:

files\_modified:

\- server/routes/render\.py

behavior\_changed: 新增了 /api/render/status 轮询接口

api\_changed: yes

schema\_changed: no

tests\_added:

\- tests/backend/test\_render\_status\.py（3 个测试用例）

commands\_run:

\- pytest tests/backend/ → 全部通过

\- make check → 通过

known\_risks:

\- 轮询接口目前是 1 秒 1 次，高并发下可能有性能问题（MVP 阶段可接受）

## **5\.7 Spike 阶段规则**

Spike 阶段允许：

- 写一次性脚本

- 写临时代码

- 不写完整单元测试

- 不设计完整 API

- 不建数据库

- 不做前端页面

- 不追求代码复用

    

Spike 阶段禁止：

- 把临时代码直接合并到 main

- 在 Spike 中提前设计完整架构

- 引入大量依赖

- 写超过验证目标范围的功能

- 把 Spike 成功误判为产品可用

---

# **六、版本规划与 Kill 判据**

|**核心原则 **每个版本必须绑定「可证伪的 Kill 判据」——如果这个条件不满足，不进入下一个版本，可以停止项目。Kill 判据不是「功能做完了」，而是「用真实用户验证了价值」。|
|---|

## **Spike（当前阶段）：技术可行性验证**

|**维度**|**内容**|
|---|---|
|**时间**|2 周|
|**目标**|验证路线 0\-4 全部通过|
|**产物**|spike\_results\.md（每条验证的结论 \+ 关键数据）|
|**Kill 判据**|如果验证路线 0（基础渲染）无法在 15 分钟内出一段 8 秒视频，需要重新评估 Blender 方案；如果验证路线 1（PNG 2\.5D）主体严重变形，需要重新评估图片用户的支持方式|

## **V0\.1（Spike 通过后）：单模板闭环**

|**维度**|**内容**|
|---|---|
|**时间**|3\-4 周|
|**目标**|只做 character\_intro 一个模板，完整跑通前端 → 后端 → Blender → FFmpeg → 下载|
|**P0 功能**|上传 PNG、选模板、改标题、点生成、下载 MP4；渲染进度可见；错误时有明确错误提示|
|**产物**|可运行的本地 Web App，能出一段 8\-15 秒游戏角色宣传视频|
|**Kill 判据**|找 3\-5 个真实游戏运营，展示生成结果。如果超过 3 人的反馈是「比我现在用剪映方式做的差太多」，重新评估产品差异化|

## **V0\.2：3 模板 \+ AI 美化**

|**维度**|**内容**|
|---|---|
|**时间**|4\-6 周|
|**目标**|新增 product\_orbit、prop\_showcase 模板；加入 ComfyUI 保守版美化|
|**P0 功能**|美化对比（原始 vs 美化）可在前端展示；用户可选择是否开启 AI 美化|
|**Kill 判据**|AI 美化后的视频，相比原始版本，非开发用户有明显正向反馈（「这个能发」）|

## **V0\.3：GLB 3D 模型支持**

|**维度**|**内容**|
|---|---|
|**时间**|3\-4 周|
|**目标**|支持 GLB 模型导入，自动校验资产质量（面数警告、贴图检查）|
|**Kill 判据**|用 3 个真实 GLB 模型（包括 Meshy 生成的）正常渲出产品环绕视频|

## **V1\.0：桌面正式版（Tauri 封装）**

|**维度**|**内容**|
|---|---|
|**时间**|6\-8 周|
|**目标**|Tauri 封装，本地模型管理，渲染队列，批量导出，用户授权声明|
|**Kill 判据**|10 个真实用户安装并使用，至少 6 人表示愿意付费或推荐给同事|

|**关于后续版本 **V1\.5（AI 辅助 3D 生成）、V2\.0（控制图驱动 AI 视频生成）、V3\.0（平台化/云端）请在 V1\.0 Kill 判据通过后再规划。当前不锁定这些版本的具体功能，因为用户反馈会改变方向。|
|---|

---

# **七、已知风险与规避策略**

|**风险**|**风险说明**|**规避策略**|
|---|---|---|
|**风险**|风险说明|规避策略|
|**渲染速度**|Blender Cycles 渲 8 秒视频可能需要 10\-30 分钟，严重影响体验|MVP 默认用 Eevee；产品设计里把「等待渲染」设计成可接受体验（进度条\+预计时间）|
|**WYSIWYG 差距**|Three\.js 预览 ≠ Blender 最终渲染，用户可能对结果感到意外|UI 上明确标注「预览仅供参考，最终效果以渲染结果为准」；提供缩略渲染预览（低分辨率快速渲）|
|**显存竞争**|Blender \+ ComfyUI 同时运行可能导致 OOM（5070Ti 12GB 显存）|串行执行：先完成 Blender 渲染，释放显存，再启动 ComfyUI|
|**GLB 资产质量**|用户上传的 GLB 可能面数过高（\>100万面）、贴图缺失、坐标轴错误|上传时做预校验：面数警告、贴图检查、自动归一化坐标|
|**PNG 透明通道**|用户上传的 PNG 可能没有透明通道，导致 2\.5D 效果是白色背景方块|上传后自动检测透明通道；如无透明通道，提示用户或自动运行 AI 抠图|
|**ComfyUI 版本依赖**|ComfyUI 工作流与模型版本强绑定，升级后工作流可能失效|锁定 ComfyUI 版本；工作流 JSON 入 git；提供版本检查脚本|
|**单卡无并发**|本地单 5070Ti 无法同时处理多个渲染任务|MVP 阶段串行队列，用户看到排队状态，完全合理|

---

# **八、MVP 明确不做的事**

「不做什么」和「做什么」一样重要。以下功能在 V1\.0 之前坚决不碰：

|**不做的功能**|**理由**|
|---|---|
|**不做**|理由|
|**逐帧 AI 视频生成（AI 重绘每一帧）**|闪烁/变形问题不可控，无法商用|
|**实时预览与最终渲染完全一致（WYSIWYG）**|Three\.js vs Blender 本质差异，做到会让 MVP 严重延期|
|**云端渲染 / SaaS 部署**|单卡本地验证阶段，云端带来的成本/延迟问题先不处理|
|**多人协作 / 团队项目**|MVP 面向个人用户|
|**Celery \+ Redis 任务队列**|引入 Redis 依赖不必要，简单 asyncio 队列够用|
|**Unreal Engine 渲染后端**|引擎集成复杂度极高，放到 V2\+|
|**电商批量生成**|属于第二阶段场景，不在游戏宣传 MVP 范围内|
|**模板市场 / 素材市场**|平台化需求，放到 V3|
|**用户账号系统**|本地优先应用，MVP 阶段不需要账号|

## **关于 Anchor（UE5 沙盒游戏）的建议**

|**核心建议 **建议在 CineAnchor V0\.1 Kill 判据通过之前，不启动 Anchor 项目的任何开发工作。两个项目同时推进几乎必然导致两个都做不出来。CineAnchor 的技术底座（Blender \+ ComfyUI \+ FastAPI）与 Anchor（UE5 \+ AI 生成 3D 资产）完全不同技术栈，无法共享开发资源。|
|---|

---

# **九、立即行动清单**

按以下顺序执行，不要跳步：

|**优先级**|**行动**|
|---|---|
|**优先级**|行动|
|**🔴 今天**|确认产品定位（用第一章 1\.1 的测试过一遍，写出一句话定位）|
|**🔴 今天**|安装 Blender 4\.x，下载一个免费 GLB 模型，准备 spike 环境|
|**🟠 第 1\-2 天**|完成验证路线 0（3D 基础渲染闭环），记录渲染耗时|
|**🟠 第 3\-4 天**|完成验证路线 1（PNG 2\.5D 视频），给 3 个人看结果|
|**🟡 第 5\-7 天**|完成验证路线 2（JSON 模板化渲染），跑通 3 个模板|
|**🟡 第 8\-10 天**|完成验证路线 3（ComfyUI AI 美化），记录显存使用情况|
|**🟢 第 11\-14 天**|完成验证路线 4（Web → FastAPI → Blender 串联）|
|**🟢 Spike 完成后**|根据验证结论更新本文档，锁定 API 合同和 Project JSON Schema|
|**🟢 Spike 完成后**|按第四章目录结构搭建真正的项目骨架，开始 V0\.1 开发|

|**最重要的一件事 **Spike 阶段的代码是用来「得出结论」的，不是用来「交付产品」的。Spike 结束后扔掉这些代码是正常的，不是浪费时间。用 2 周时间证明技术链路可行，比用 3 个月做出来才发现不通好得多。|
|---|

---

*文档结束*

*本文档基于 MVP 方案、轻量验证路线、前期工程规范、评审纪要综合整理*

