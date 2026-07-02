# Character Birthday 模板设计与 V0.2 实现

## 结论

`character_birthday` 应成为 CineAnchor V0.2 第一优先级。它把产品从“复杂镜头控制实验”推进为“游戏运营素材填充后稳定出片”的生产工具：输入角色 PNG、角色名、日期、Logo、文案，生成可发布的 9:16 MP4。主流程是确定性图层合成、关键帧和 FFmpeg 编码；不依赖 AI，也不复刻任何参考 IP 资产。

## 模板目标

面向角色生日、生贺、角色纪念日和轻量角色宣传。普通运营用户不接触自由时间线、3D 坐标、关键帧或多主体编辑，只填写模板插槽和主题参数。

## 用户输入

### V0.2 必填

| 输入 | 类型 | 约束 | 用途 |
|---|---|---|---|
| 主角色 | 透明 PNG | 1 张，建议不小于 1500 px 高 | 特写、海报、互动占位、片尾头像 |
| 角色名 | 文本 | 1–80 字符 | 姓名卡、海报背景字、片尾 |
| 生日日期 | 文本 | 1–20 字符，例如 `07.01` | 日期钩子 |
| 主标题 | 文本 | 1–80 字符 | `HAPPY BIRTHDAY` 等 ribbon 标题 |
| Logo | PNG | Web MVP 要求上传；API 可缺省 | 品牌片尾 |
| 对白 | 0–3 句 | 每句不超过 100 字符 | 互动段底部字幕 |
| 主题色 | 两个十六进制颜色 | 主色、辅助色 | 背景、文字、横幅和粒子 |

### 可选 / 后续插槽

- `support_image_1..3`：头像、表情、服装或活动图；缺省时复用主角色图。
- CTA、版权信息：缺省时不显示，不留空标签。
- BGM、实机片段：schema 设计预留，但 V0.2 实现不接受也不依赖。
- 字体文件：后续支持品牌字体白名单；V0.2 使用 `font_preset` 解析系统字体并有安全回退。

## 输出规格

- MP4 / H.264 / `yuv420p` / fast start。
- 1080×1920、24 fps、9:16。
- Web 默认 15 秒；schema 允许 4–30 秒，并可显式配置 27 秒参考结构。
- 无 BGM、无补充图、无 Logo、无 AI 时 API 渲染仍可完成；Web 为保证品牌交付质量会要求 Logo。

## 共性结构与边界

参考样片的共性不是某个角色或画风，而是六段式信息递进：日期钩子 → 姓名确认 → 生日标题和情绪特写 → 全身主视觉 → 互动 / 台词 → 白底品牌收尾。节奏是阶段式推进，不是高频混剪。

| 类型 | 典型元素 | 模板处理 |
|---|---|---|
| 视频本体 | 原始成片的画面与音频 | 分析对象 |
| 游戏实机 | 3D/2D 角色待机、表情、对白、室内外场景、UI 内角色互动 | 可选 `gameplay_clip` 插槽；V0.2 不生成、不伪造 |
| 运营包装 | 日期卡、姓名卡、标题 ribbon、立绘海报、小头像、竖排字、字幕、粒子、白场、Logo、CTA、版权 | `character_birthday` 的核心能力 |
| 平台污染 | 手机状态栏、Reels/TikTok 标题、点赞评论分享按钮、账号、说明文字、通知弹窗、底部评论框 | 分析时忽略，永不进入模板 |

## 时间轴

### 15 秒 V0.2 默认

| 组件 | 时间 | 作用 | 默认转场 |
|---|---:|---|---|
| `opening_date_card` | 0.0–2.0s | 大日期开场钩子 | fade in + blur zoom |
| `name_card` | 2.0–3.0s | 快速确认角色 | white flash / hard cut |
| `birthday_title_closeup` | 3.0–5.5s | 角色特写和主标题 | blur zoom + ribbon |
| `character_poster` | 5.5–9.0s | 封面级全身主视觉 | hard cut + dolly/scale in |
| `character_interaction` | 9.0–12.5s | 对白、补充图或主图替代 | hard cut + subtitle |
| `brand_end_card` | 12.5–15.0s | Logo、头像、CTA、版权 | smoke/cloud wipe |

### 27 秒扩展

0–2.2 日期卡；2.2–3.2 姓名卡；3.2–7.5 标题特写；7.5–12.0 海报；12.0–23.5 互动 / 可选实机；23.5–27.0 品牌片尾。27 秒不是三天 MVP 默认，因为没有实机或多张补充图时，中段容易显得拖沓。

节奏可按 120–145 BPM 估算，在段落边界或对白切换处落剪辑点；V0.2 不做音频 beat detection。

## 图层系统

从后到前：

1. `background`：纯色、双色渐变、轻纹理。
2. `background_typography`：低透明度角色名、日期或装饰字。
3. `support_cards`：0–3 张固定槽位的小图卡。
4. `main_character`：透明 PNG，contain / crop / scale 关键帧。
5. `title_ribbon`：主标题色块和装饰线。
6. `dialogue_subtitle`：底部安全区，两行以内。
7. `particle_overlay`：程序化花瓣 / 光点，固定随机种子。
8. `transition_mask`：白闪、模糊、云雾遮罩。
9. `brand_overlay`：Logo、CTA、版权。

所有层都由模板确定位置和运动。多素材是槽位，不是自由画布。

## 文字样式系统

| 样式 token | 字体与字重 | 颜色与效果 | 位置 / 约束 |
|---|---|---|---|
| `title.ribbon.bold` | Bold sans，约画宽 8.3% | 白字，主题色 ribbon | 中下部，大写，单行 |
| `character_name.serif` | Bold serif，约画宽 7–13% | 主色或白色 | 可分行，参与构图 |
| `date.hero` | Bold serif，约画宽 31% | 主色，高留白 | 开场居中，`.`/`/` 可断行 |
| `subtitle.white_black_stroke` | Bold sans，约画宽 4.7% | 白字、黑色粗描边、半透明黑底 | 底部安全区，最多两行 |
| `cta.pill` | Bold sans，约画宽 4.5% | 白字、辅助色圆角块 | 片尾中下部 |
| `endcard.brand` | Logo 原图 + serif 姓名 | 白底、主色姓名、灰色版权 | 最后 2–3 秒 |

`font_preset` 已接入渲染：`birthday_serif` 优先 Georgia / DejaVu Serif，sans 使用 Arial / Microsoft YaHei / DejaVu Sans。缺字体时回退 Pillow 默认字体。生产版应打包有授权的品牌字体，不能依赖任意用户机器字体。

## 转场系统

### V0.2 立即实现

- 硬切：所有结构段都可用，最稳定。
- fade in：首帧进入。
- blur zoom：日期卡和标题特写的短时进入。
- white flash：姓名、标题、海报或互动段边界，持续约 100 ms。
- petal / particle overlay：程序化确定性粒子，既做氛围也弱化切点。
- smoke / cloud wipe：程序化白色软圆遮罩进入片尾。
- logo end card transition：云雾后进入白底片尾。

### 延后

- 光流、运动补偿、复杂 motion blur、真实烟雾流体模拟。
- 根据 BGM 自动卡强拍、音频 ducking、歌词同步。
- Alpha 视频素材库、可视化 transition editor。
- 角色局部骨骼、Live2D、深度分层和自动脸部追踪。

## 组件库

### Birthday Date Card

大日期、红白 / 蓝白主题、serif 或手写预设；V0.2 支持 blur zoom 和 fade。手写字体本体需后续随授权字体包交付。

### Character Name Card

英文 / 中文角色名，serif / bold / handwritten token；白底或半透明背景。V0.2 实现 serif 和 bold，中文走 CJK fallback。

### Theme Ribbon Title

主标题置于主题色横幅，支持硬切、淡入、缩放。标题内容完全来自用户输入。

### Character Poster Stage

角色居中或偏右；背景字、主题渐变、小图卡、轻微 scale in。可直接作为封面帧。

### Dialogue Subtitle

底部居中、白字黑描边、最多两行。多句按互动段等分显示，不做花哨逐字动画。

### Petal / Particle Overlay

按项目 ID 固定随机种子；支持主题色、数量、速度和方向的 preset。V0.2 不暴露逐粒子编辑。

### Smoke / Cloud Wipe

程序化软圆 + 高斯模糊形成白云遮罩；后续可换成有授权的 alpha 视频素材。

### Brand End Card

白底、Logo、圆形角色图、角色名、CTA、版权；Logo 缺省时使用主标题文字，避免渲染失败。

## Project JSON 兼容策略

- `version` 接受 `0.1` 和 `0.2`。
- 两个旧模板继续要求唯一 `main_subject`，资产类型规则不变。
- `character_birthday` 必须使用 `0.2`、9:16 和 `main_character:image`。
- 生日模板额外允许 `logo`、`support_image_1..3`；它们全部可选且当前只接受 PNG。
- `TextSpec` 追加生日字段；旧字段保持原义。
- 新增可选 `style` 与 `timeline`。生日模板缺省时自动生成 15 秒比例时间轴。
- `camera`、`scene` 保留为顶层必填，维持现有 API 合同；生日 2D renderer 忽略自由镜头数据。

完整示例见 `samples/projects/character_birthday.json`。

产品层可以继续使用需求中的友好视图：`assets.main_character`、`assets.logo`、
`assets.support_images[]`、`assets.gameplay_clip`、`assets.bgm`。提交现有 API 前由
Web adapter 将非空图片槽位正规化为 `assets[]`。`gameplay_clip` 和 `bgm` 在 V0.2
必须保持 `null` / 不提交；等上传、校验和合成路径完成后再扩展 `AssetType`，避免
schema 先承诺一个无法渲染的能力。

## 与现有架构的接入

```text
Web 表单
  -> POST /api/assets/upload（主角色、Logo）
  -> POST /api/render（Project JSON 0.2）
  -> Pydantic 条件校验
  -> BlenderService 渲染分派边界
       - character_intro / product_orbit：原 Blender Eevee 路径
       - character_birthday：Pillow 确定性 2D 图层帧
  -> 原 FFmpegService：PNG 序列编码 H.264 MP4
  -> 原任务状态 / 错误码 / 下载接口
```

生日模板使用 2D compositor 是有意的：它的主体是平面设计、文字和遮罩；使用 Blender 只会增加字体、描边和渲染成本。原 Blender 路径完全保留，服务边界、任务队列、存储、FFmpeg 和 API 均复用。

## V0.2 必须实现

- 三个模板并存，旧模板回归通过。
- 主角色、Logo 上传；角色名、日期、标题、0–3 句对白和主题色输入。
- 六段时间轴和七个确定性视觉组件。
- 15 秒 1080×1920 MP4；无 AI、BGM、补充图时仍可导出。
- 字体 preset 真正影响渲染；字幕黑描边可读。
- 渲染 manifest 记录组件时间、分辨率、素材和 AI 依赖状态。
- 失败沿用 `ASSET_NOT_FOUND`、`ASSET_IMPORT_FAILED`、`BLENDER_RENDER_FAILED`、`FFMPEG_COMPOSE_FAILED`。

## 延后

- BGM / 实机视频上传、混音、自动裁切和 beat sync。
- 自动抠图、背景生成、角色局部动效、ComfyUI。
- 项目历史、批量 CSV、品牌包和模板版本锁定。
- 更完整的小图卡布局、文字自动避让和多语言排版 QA。

## 不应该做

- 自由多轨剪辑器、逐帧编辑器、复杂自由镜头控制。
- 把 AI 视频生成放在成功路径上。
- 复刻参考 IP 的 Logo、角色、字体、UI 或画面资产。
- 把平台录屏 UI 烧进模板。
- 接受无限素材后让用户自行摆放。

## 三天 MVP 取舍

只保留主角色、Logo、角色名、日期、主标题、两句对白、两种颜色、15 秒固定时间轴和 MP4 导出。删除 BGM、实机片段、support images UI、27 秒默认、自动卡点、字体上传、手写字体、AI、角色动作、自由镜头和历史项目。API 可保留 support image 槽位，但不为它做复杂 UI。

## 走向生产工具的下一步

优先补“品牌包 + 批量生成 + 预检”，不是更多镜头控制：

1. BGM / 实机片段插槽和许可证提示。
2. 项目保存、可重复渲染、模板版本与素材哈希。
3. CSV 批量任务、队列持久化、取消 / 重试和磁盘配额。
4. 品牌字体、Logo 安全区、颜色 contrast、文案溢出预检。
5. 低分辨率快速预览与封面帧导出。
6. Golden render 视觉回归、FFprobe 输出验收和失败日志下载。

## 优先判断问题回答

1. 共性结构：日期 / 姓名钩子、情绪特写、海报主视觉、互动对白、亮场品牌收尾。
2. 实机是角色模型动作、对话和场景；其余日期卡、海报、字幕、粒子、片尾属于运营包装；手机和平台控件是污染。
3. 最适合模板化的是固定时序、固定安全区、文字样式、图片槽位、粒子和片尾。
4. 日期、姓名、标题、海报、字幕、粒子、白闪、云雾和 Logo 都不需要 AI。
5. FFmpeg 稳定负责编码 / 混音 / 基础滤镜；Blender 稳定处理 GLB / 3D；2D 生日包装由 Pillow / Canvas 类图层器更合适。
6. 必须延后 BGM 卡点、实机自动剪辑、自动抠图、角色局部动画、AI 背景和视频生成。
7. 是，`character_birthday` 是 V0.2 第一优先级，因为输入标准、结果可验收、与运营需求直接对齐。
8. 三天 MVP 删除所有可选智能功能、自由编辑和复杂素材，仅做 15 秒固定模板。
9. 下一步补品牌资产治理、批量任务、持久化、预检、快速预览和视觉回归。
