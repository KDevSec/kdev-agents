# img-to-pptx 设计（SVG / 位图 → 可编辑高复刻 PPTX，html-to-pptx 姊妹 skill）

- 日期：2026-06-16
- 状态：✅ 用户已逐项确认，可转 writing-plans
- 上游：`~/.claude/skills/html-to-pptx`（独立 repo，remote `github.com/KDevSec/html-to-pptx`，当前单 skill 布局）
- 关联：[html-to-pptx SKILL](file:///home/lyadmin/.claude/skills/html-to-pptx/SKILL.md) / [V4 HTML→全原生 PPTX spec](2026-06-14-V4-HTML转全原生可编辑PPTX-design.md)

## 1. 目标（一句话）

新增 `img-to-pptx` skill，与 `html-to-pptx` 同处一个 repo、构成"两条命令"，把**图片文件（SVG 矢量 / PNG·JPG 位图）**转成可编辑、尽量高复刻的 16:9 PPTX。两个 skill 共用同一套 `scripts/`。

## 2. 已对齐的决策（用户逐项确认）

| 项 | 决策 |
|---|---|
| 输入范围 | SVG **和**位图都收，都要"可编辑高复刻 PPT" |
| SVG 策略 | 内联进 HTML 壳 → **复用 html-to-pptx 全原生重建管线**（结构现成、提取即重建） |
| 位图策略 | **忠实背景 + 文字可编**折衷（位图物理上做不到"高复刻 + 全可编"同时成立） |
| 位图抠字整包 | **Tesseract 抠 bbox + 局部色抹除 + 模型校对**（工具解析、模型只读摘要） |
| 仓库结构 | **双 skill 目录 + scripts 共享 + symlink**；两者仍是裸个人 skill，不打包成插件、不走 marketplace 重装 |
| 命名 | skill 名用 `img-to-pptx`（连字符，跟 `html-to-pptx` 对齐；用户口语 `img_to_ppt` 统一为此） |

## 3. 核心原则（继承 html-to-pptx）

- **大文件先脚本降维、模型只读产物**：源文件大到一次读不下（SVG / 大 JSON 同理）时，正确动作不是"分块读原文"，而是先用脚本把它降成「结构摘要(geo.json/boxes.json) + 参考图」再进上下文。模型读摘要和图，**禁止直接 Read 源文件**。
- **文字永远原生在最上层**：能画的原生、画不出的烤成 PNG，文字始终原生可编辑叠在最上。
- **同一仿射对齐**：沿用 html-to-pptx 坐标系——1280×720 / dsf=1 渲染，`1 css px = 9525 EMU`，`pt = css px × 0.75`；原生文字、原生形状、PNG 切片来自同一次 capture，自动对位。

## 4. 仓库结构（双 skill + 共享脚本 + symlink）

```
KDevSec/html-to-pptx  （repo 从 ~/.claude/skills/html-to-pptx 挪到中性目录，例如 ~/.claude/skills-src/html-img-to-pptx）
├── README.md / LICENSE / .gitignore        （留根）
├── shared/
│   ├── scripts/        ← git mv 现有 scripts/ 过来：check_deps.py / capture.py / pptx_helpers.py / verify.py + 新增 raster.py
│   └── references/     ← git mv 现有 references/ 过来：playbook.md + 新增 raster 笔记
├── html-to-pptx/
│   ├── SKILL.md        ← git mv 现有根 SKILL.md 过来
│   ├── scripts      → ../shared/scripts      （symlink）
│   └── references   → ../shared/references   （symlink）
└── img-to-pptx/
    ├── SKILL.md        ← 新建
    ├── scripts      → ../shared/scripts      （symlink）
    └── references   → ../shared/references   （symlink）
```

安装侧（保持裸个人 skill 模型不变）：
```
~/.claude/skills/html-to-pptx  → <repo>/html-to-pptx   （symlink）
~/.claude/skills/img-to-pptx   → <repo>/img-to-pptx    （symlink）
```

- 每个 skill 目录内 `scripts` 软链到 `../shared/scripts`，故 SKILL.md 里 `<skill>/scripts/check_deps.py` 等**约定不变、路径仍可解析**。
- 两个 skill 名字无插件前缀（`html-to-pptx` / `img-to-pptx`），与现状一致；**不引入 plugin/marketplace、不触发 G-004 cache 重刷**。
- **迁移风险**：repo 当前 git root == 个人 skill 目录；restructure 后 git root 不再能直接坐落在 `~/.claude/skills/` 下（那里要求 SKILL.md 在目录根）。需把 clone 挪到中性目录再 symlink 回来。这一步要在 plan 里单列一个"迁移 + 自检 skill 仍可触发"的步骤。

## 5. 触发路由（"两条命令"不互相抢）

- `html-to-pptx`：触发于 `.html` / 粘贴的 HTML。description 末尾**加一句**：图片 / SVG → 用 img-to-pptx（类比现有"Markdown→报告 PPTX 用 md-to-pptx"那句）。
- `img-to-pptx`：触发于 `.svg` / `.png` / `.jpg` / `.jpeg` / `.webp` / "把这张图 / 截图 / SVG 转可编辑 PPT / 图片转 ppt"。**不触发 `.html`**（交给 html-to-pptx）。

## 6. img-to-pptx 内部分流

### 6.1 `.svg` → 矢量路（= 复用 html-to-pptx 管线）

1. **内联**：把 SVG 内联进一个最小 HTML 壳（`<svg>` 进 DOM，而非 `<img src=svg>`——内联才能逐元素取 rect，`<img>` 只能整块切一张图）。ASCII 文件名避免中文 `file://` 坑。
2. **几何采集**：跑共享 `capture.py geom WRAP.html WORK/ --region <svg容器>` → `geo.json`（每元素 rect/text/font/color/bg）+ `full_3x.png`。
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

## 7. 共享脚本改动

- `shared/scripts/check_deps.py`：新增 **RASTER 档** —— 装 Tesseract（Linux apt/dnf/pacman + sudo · macOS brew · Windows winget）+ `chi_sim`/`eng` 语言包 + `pytesseract`；inpaint/方差用 numpy（或 Pillow 纯实现，能省一个重依赖优先 Pillow）。分档：CORE（建 pptx 必需，沿用）/ VERIFY（office 渲染，沿用）/ **RASTER（仅位路需要）**——位图路才装 Tesseract，矢量路不强求。
- 新增 `shared/scripts/raster.py`：`ocr`（→ boxes.json）/ `erase`（→ bg.png）/ 花背景检测 helper。
- `shared/scripts/pptx_helpers.py`：复用 `picture`/`textbox`/`bg_image`/`target_cjk_font`；补一个局部取色 helper（`sample_bg_color(img, rect)`）。
- `shared/references/`：playbook 加"位图路 + SVG 入口"小节（内联 vs `<img>`、双影/抹除天花板、花背景兜底）。

## 8. 物理天花板与取舍（写进 SKILL 与 references）

- **位图"文字可编"只在简单背景成立**：抹除是用周边色填补丁，平/简单底干净，花/纹理底会露痕 → 那块退原样保留。这是死像素的物理极限，非 bug。
- **位图图形永远不可编辑**：位图无结构可提，图形只能烤在背景里；要可编辑图形必须给矢量源（SVG）。
- **"高复刻 + 全可编"对位图不可兼得**：高复刻就贴真实像素（图形不可编），可编辑文字靠 OCR+抹除近似（花背景退化）。SVG 无此限制（结构现成）。
- 字体：CJK 用受众 OS 字体或嵌入；Linux 自检渲染仅供版面比对，最终观感以目标 office 为准（沿用 html-to-pptx）。

## 9. 验收标准

1. **双命令共存**：`html-to-pptx` 与 `img-to-pptx` 均可独立触发；触发描述不互抢（`.html` 走前者，`.svg/.png/.jpg` 走后者）。
2. **共享脚本生效**：两 skill 经 symlink 共用一份 `shared/scripts/`；改一处两边都拿到；`<skill>/scripts/...` 路径在两 skill 内均可解析。
3. **迁移无回归**：repo restructure + 安装 symlink 后，`html-to-pptx` 既有功能照常（自检它仍能跑通一张 HTML→pptx）。
4. **SVG 路**：一张含文字+矢量图形的 SVG → 文字为原生可选中可编辑 textbox（解包 `<a:t>` > 阈值），复杂矢量为切片，版面与源 SVG 对位。
5. **位图路**：一张含文字的 PNG → 简单背景区文字变原生可编 textbox 且观感与原图一致；花背景区退原样（产物报告列出未编辑化的块）；整体不比原图难看。
6. **check_deps**：RASTER 档能自动装 Tesseract + 语言包；缺包时打印精确手动命令。

## 10. 后续（plan 阶段拆批次提示）

- 批次切分建议：① repo restructure + symlink + 迁移自检（不改逻辑，先保 html-to-pptx 不回归）；② img-to-pptx SVG 路（复用现成脚本，最快）；③ check_deps RASTER 档 + raster.py（OCR/erase/花背景检测）；④ img-to-pptx 位图路组装 + 模型校对 + verify；⑤ 触发路由 + references/playbook 文档。
- 测试取材：找一张含中文文字的简单背景 PNG（验抠字+抹除）、一张花背景 PNG（验兜底退化）、一张含 `<text>`+`<path>` 的 SVG（验矢量全原生）。
