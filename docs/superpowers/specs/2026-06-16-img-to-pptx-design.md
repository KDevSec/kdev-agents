# img-to-pptx 设计（SVG / 位图 → 可编辑高复刻 PPTX，html-to-pptx 姊妹 skill）

- 日期：2026-06-16
- 状态：✅ 用户已逐项确认，可转 writing-plans
- 上游：`~/.claude/skills/html-to-pptx`（独立 repo，remote `github.com/KDevSec/html-to-pptx`，当前单 skill 布局）
- 关联：[html-to-pptx SKILL](file:///home/lyadmin/.claude/skills/html-to-pptx/SKILL.md) / [V4 HTML→全原生 PPTX spec](2026-06-14-V4-HTML转全原生可编辑PPTX-design.md)

## 1. 目标（一句话）

新增 `img-to-pptx` skill，作为 `html-to-pptx` 的**独立平行仓库**（各自维护），把**图片文件（SVG 矢量 / PNG·JPG 位图）**转成可编辑、尽量高复刻的 16:9 PPTX。img-to-pptx **自带一份脚本副本**（从 html-to-pptx 复制基线 + 新增 raster），两库零耦合、零软链。

## 2. 已对齐的决策（用户逐项确认）

| 项 | 决策 |
|---|---|
| 输入范围 | SVG **和**位图都收，都要"可编辑高复刻 PPT" |
| SVG 策略 | 内联进 HTML 壳 → **复用 html-to-pptx 全原生重建管线**（结构现成、提取即重建） |
| 位图策略 | **忠实背景 + 文字可编**折衷（位图物理上做不到"高复刻 + 全可编"同时成立） |
| 位图抠字整包 | **Tesseract 抠 bbox + 局部色抹除 + 模型校对**（工具解析、模型只读摘要） |
| 仓库结构 | **两个独立平行仓库，各自维护**（img-to-pptx 自带脚本副本，**html-to-pptx 零改动**）；不软链、不共享、不打包插件 |
| 代价（已接受） | 脚本（capture/pptx_helpers/verify/check_deps）**重复一份**，日后修 bug 需**手动同步两边**——换取两库彻底解耦、迁移风险归零 |
| 命名 | skill 名用 `img-to-pptx`（连字符，跟 `html-to-pptx` 对齐；用户口语 `img_to_ppt` 统一为此） |

## 3. 核心原则（继承 html-to-pptx）

- **大文件先脚本降维、模型只读产物**：源文件大到一次读不下（SVG / 大 JSON 同理）时，正确动作不是"分块读原文"，而是先用脚本把它降成「结构摘要(geo.json/boxes.json) + 参考图」再进上下文。模型读摘要和图，**禁止直接 Read 源文件**。
- **文字永远原生在最上层**：能画的原生、画不出的烤成 PNG，文字始终原生可编辑叠在最上。
- **同一仿射对齐**：沿用 html-to-pptx 坐标系——1280×720 / dsf=1 渲染，`1 css px = 9525 EMU`，`pt = css px × 0.75`；原生文字、原生形状、PNG 切片来自同一次 capture，自动对位。

## 4. 仓库结构（两个独立平行仓库，各自维护）

两个互不依赖的独立 repo，各自就是标准裸个人 skill（SKILL.md 在 repo 根，与现状完全一致）：

```
~/.claude/skills/
├── html-to-pptx/      ← 维持现状，一行不碰（github KDevSec/html-to-pptx）
│   ├── SKILL.md
│   ├── scripts/        check_deps.py / capture.py / pptx_helpers.py / verify.py
│   └── references/     playbook.md
│
└── img-to-pptx/       ← 新建独立 repo（新建 github KDevSec/img-to-pptx）
    ├── SKILL.md
    ├── scripts/        ← 从 html-to-pptx 复制基线副本 + 新增 raster.py
    │                     check_deps.py(+RASTER 档) / capture.py / pptx_helpers.py(+取色 helper) / verify.py / raster.py
    └── references/     ← 复制 playbook.md + 新增 raster 笔记
```

- **html-to-pptx 零改动**：不挪位、不改布局、SKILL.md 仍在其 repo 根 → **迁移风险归零**（这是改成平行仓库相对"共享+symlink"方案的最大收益）。
- **img-to-pptx 完全自包含**：自带全套脚本副本，**不依赖 html-to-pptx 是否安装**；`<skill>/scripts/...` 路径约定与 html-to-pptx 一致。
- 两个 skill 名字无插件前缀（`html-to-pptx` / `img-to-pptx`）；**不引入 plugin/marketplace、不触发 G-004 cache 重刷**。
- **代价（用户已确认接受）**：`capture.py`/`pptx_helpers.py`/`verify.py`/`check_deps.py` 在两库各存一份，日后修 bug / 加能力需**手动同步**。建议在 img-to-pptx 复制来的脚本头部留一行注释标"基线 fork 自 html-to-pptx@<commit>"，便于日后比对同步。

## 5. 触发路由（两个独立 skill 不互相抢）

- `html-to-pptx`：维持现状,触发于 `.html` / 粘贴的 HTML。**因 html-to-pptx 零改动,不动它的 description**——靠 img-to-pptx 自身描述精确划界即可(文件类型本就不重叠,无碰撞)。
- `img-to-pptx`：触发于 `.svg` / `.png` / `.jpg` / `.jpeg` / `.webp` / "把这张图 / 截图 / SVG 转可编辑 PPT / 图片转 ppt"。description 里**明确写"仅图片/SVG;HTML 请用 html-to-pptx"**,且**不触发 `.html`**。
- 若实测出现触发歧义(罕见),再考虑给 html-to-pptx 加一行路由提示——但那是**事后按需**的独立小改,不在本次范围,保持 html-to-pptx 零改动。

## 6. img-to-pptx 内部分流

### 6.1 `.svg` → 矢量路（= 复用 html-to-pptx 管线）

1. **内联**：把 SVG 内联进一个最小 HTML 壳（`<svg>` 进 DOM，而非 `<img src=svg>`——内联才能逐元素取 rect，`<img>` 只能整块切一张图）。ASCII 文件名避免中文 `file://` 坑。
2. **几何采集**：跑自带 `scripts/capture.py geom WRAP.html WORK/ --region <svg容器>` → `geo.json`（每元素 rect/text/font/color/bg）+ `full_3x.png`。
3. **分类**：按决策表——SVG `<text>`→原生 textbox；`<rect>`/简单 `<path>` 直角/圆角矩形→原生；复杂多 path / 滤镜 / 渐变 / mesh→透明 PNG 切片（`capture.py slice --isolate`）。理由：python-pptx **不能导入 SVG 矢量 path**，复杂矢量一律切片。
4. **组装**：`pptx_helpers` 背景→切片→原生形状→原生文字（最上层）。
5. **自检**：`verify.py` 原生 office 渲染比对。
6. 子模式：默认"内联全原生重建"（高复刻可编辑）；若用户只要忠实嵌入，`<img src=svg>`→单张 cutout 一页（不可编，作为降级选项，不是默认）。

### 6.2 `.png/.jpg/...` → 位图路（忠实背景 + 文字可编）

1. **摆放**：默认**整图等比缩放完整放入 16:9 版心**（保宽高比、不裁切，留白用版心底色补；"忠实"优先不丢内容）；图本就 16:9 则满幅。
2. **OCR**：`raster.py ocr IMG WORK/` → Tesseract（`chi_sim+eng`）出 `boxes.json`：每条 `{text, bbox(px), conf}`；字号由 bbox 高度估算；文字色采样 bbox 内主色。
3. **抹除**：`raster.py erase` 对每个文字 bbox 用**周边采样色填充**（Pillow/numpy 实现的简易 inpaint）→ 生成"去字背景图" `bg.png`。
4. **花背景兜底**：对每个文字 bbox 测周边局部方差 / 边缘密度；**超阈值** → 该块**跳过抹除+叠字、保留原样像素（不可编）**，并在产物报告里记录"哪些块未编辑化"。保证任何情况下不比原图难看。
5. **模型校对**：模型读 `boxes.json` 摘要 + `full` 渲染图 → 修明显 OCR 错字、把碎行合并成逻辑 textbox、校字号/颜色。**模型只读摘要 + 图，不 parse 原始像素**。
6. **组装**：`bg_image(bg.png)` → 在各 bbox 原位叠原生 textbox（`target_cjk_font` 按受众 OS 选字体）→ `verify.py` 比对。

## 7. img-to-pptx 自带脚本（复制基线 + 改动；均在 img-to-pptx 自己的 `scripts/` 内，html-to-pptx 不动）

- **复制基线**：从 html-to-pptx 原样拷 `capture.py` / `pptx_helpers.py` / `verify.py` / `check_deps.py`（头部标 `# 基线 fork 自 html-to-pptx@<commit>`）。
- `check_deps.py`：新增 **RASTER 档** —— 装 Tesseract（Linux apt/dnf/pacman + sudo · macOS brew · Windows winget）+ `chi_sim`/`eng` 语言包 + `pytesseract`；inpaint/方差优先 **Pillow 纯实现**（省掉 numpy/opencv 重依赖，装不上时再退 numpy）。分档：CORE（建 pptx 必需，沿用）/ VERIFY（office 渲染，沿用）/ **RASTER（仅位图路需要）**——位图路才装 Tesseract，矢量路不强求。
- 新增 `raster.py`：`ocr`（→ boxes.json）/ `erase`（→ bg.png）/ 花背景检测 helper。
- `pptx_helpers.py`：复用 `picture`/`textbox`/`bg_image`/`target_cjk_font`；补一个局部取色 helper（`sample_bg_color(img, rect)`）。
- `references/`：复制 playbook.md，加"位图路 + SVG 入口"小节（内联 vs `<img>`、双影/抹除天花板、花背景兜底）。

## 8. 物理天花板与取舍（写进 SKILL 与 references）

- **位图"文字可编"只在简单背景成立**：抹除是用周边色填补丁，平/简单底干净，花/纹理底会露痕 → 那块退原样保留。这是死像素的物理极限，非 bug。
- **位图图形永远不可编辑**：位图无结构可提，图形只能烤在背景里；要可编辑图形必须给矢量源（SVG）。
- **"高复刻 + 全可编"对位图不可兼得**：高复刻就贴真实像素（图形不可编），可编辑文字靠 OCR+抹除近似（花背景退化）。SVG 无此限制（结构现成）。
- 字体：CJK 用受众 OS 字体或嵌入；Linux 自检渲染仅供版面比对，最终观感以目标 office 为准（沿用 html-to-pptx）。

## 9. 验收标准

1. **两独立 skill 各自可触发**：`html-to-pptx` 与 `img-to-pptx` 均可独立触发，互不影响；触发不互抢（`.html` 走前者，`.svg/.png/.jpg` 走后者）。
2. **img-to-pptx 自包含**：自带全套脚本副本，**在 html-to-pptx 未安装时也能独立跑通**（自检它能独立完成一张 SVG→pptx 与一张 HTML→pptx）。
3. **html-to-pptx 零改动**：`git status` 证明 html-to-pptx repo 未被触碰（无任何文件改动），既有功能照常。
4. **SVG 路**：一张含文字+矢量图形的 SVG → 文字为原生可选中可编辑 textbox（解包 `<a:t>` > 阈值），复杂矢量为切片，版面与源 SVG 对位。
5. **位图路**：一张含文字的 PNG → 简单背景区文字变原生可编 textbox 且观感与原图一致；花背景区退原样（产物报告列出未编辑化的块）；整体不比原图难看。
6. **check_deps**：RASTER 档能自动装 Tesseract + 语言包；缺包时打印精确手动命令。

## 10. 后续（plan 阶段拆批次提示）

- 批次切分建议：① 建 img-to-pptx 独立 repo 骨架 + 复制 html-to-pptx 的 scripts/references 基线副本 + 装成裸 skill，自检"复制来的脚本完整、能独立跑通一张 HTML→pptx"；② img-to-pptx SVG 路（复用复制来的 capture.py，最快）；③ check_deps RASTER 档 + raster.py（OCR/erase/花背景检测）；④ img-to-pptx 位图路组装 + 模型校对 + verify；⑤ 触发路由（img-to-pptx description 精确化）+ references/playbook 文档。
- **全程不碰 html-to-pptx**：批次①只往 img-to-pptx 新 repo 复制，不修改源 repo。
- 测试取材：找一张含中文文字的简单背景 PNG（验抠字+抹除）、一张花背景 PNG（验兜底退化）、一张含 `<text>`+`<path>` 的 SVG（验矢量全原生）。
