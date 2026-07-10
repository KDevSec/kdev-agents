# frontend-design：让 Claude 写出不像"AI 味"的前端

> 技术分享文档 · 基于 Anthropic 官方 **frontend-design** skill
> 面向读者：已在使用 Claude Code 的同事

**一句话介绍**：frontend-design 是 Anthropic 官方的一个 Claude Code 技能，只做一件事——当你让 Claude 建 web 组件 / 页面 / 应用时，让它**先定一个大胆的审美方向再写代码**，主动避开那种一眼假的"AI 泔水审美"（千篇一律的 Inter 字体、白底紫渐变、可预测的居中卡片布局），产出有记忆点、成品级、每次都不一样的界面。

**阅读指引**：正文只有两章——**第 1 章装起来，第 2 章用起来**，读完即可上手。想了解它反的到底是什么、SKILL.md 逐条原文、和 ieidev 版的关系，按需翻附录 A–C。

---

## 1. 安装与接入

### 1.1 安装技能

frontend-design 走 Claude Code 官方插件市场安装：

```
/plugin marketplace add anthropics/claude-plugins-official
/plugin install frontend-design@claude-plugins-official
```

装完重启会话生效。技能全名是 `frontend-design:frontend-design`（`插件名:技能名`）。

> 这是个**极简技能**——整个插件就一份 `skills/frontend-design/SKILL.md`（约 40 行纯指令），没有 references / 模板 / 示例代码 / 脚本。它是"纯提示词注入"型技能：触发后把这 40 行设计准则塞进 Claude 的上下文，改变它写前端时的审美决策，仅此而已。作者是 Anthropic 的 Prithvi Rajasekaran 与 Alexander Bricken。

### 1.2 接入原理：靠语义自动触发

frontend-design **不需要你手打斜杠命令**。它的 description 写着：

> "Create distinctive, production-grade frontend interfaces with high design quality. **Use this skill when the user asks to build web components, pages, or applications.** Generates creative, polished code that avoids generic AI aesthetics."

只要你的请求语义命中"建 web 组件 / 页面 / 应用 / 界面"，Claude 就会自动加载它。你正常提需求即可。

### 1.3 验证接入成功

新开一个会话，说一句：

> "帮我做一个音乐流媒体 app 的 dashboard。"

如果 Claude **没有**直接甩一个 Inter 字体 + 灰白卡片的通用界面，而是先想"这个界面该走什么审美方向（极简？极繁？复古未来？）、用什么有个性的字体、主色是什么"再动手——说明技能已生效。

---

## 2. 如何使用

> 本章是核心：怎么触发（§2.1）、触发后 Claude 的行为会怎么变（§2.2）、它的设计准则清单（§2.3）、它拉黑了什么（§2.4）、适合与不适合的场景（§2.5）。

### 2.1 你只需要正常提需求

心智负担几乎为零——**你不用懂设计，也不用指挥它"别用某某字体"**。技能已经把这些准则内置了。你要做的只有两件：

**① 正常描述你要建什么。** README 给的示例就是最自然的说法：

> "给一个 AI 安全创业公司做落地页。"
> "设计一个带暗色模式的设置面板。"

**② 如果有方向偏好，顺嘴说一句。** 比如"我想要那种杂志编排感 / 极简性冷淡 / 复古像素风"——它的 Design Thinking 第一步就是定"tone（基调）"，你给了它就照着走，不给它自己挑一个大胆方向。

### 2.2 触发后 Claude 的行为会怎么变

这是这个技能最值得理解的部分——它把 Claude 从"默认安全审美"切换成"**先做审美决策，再写生产级代码**"：

**先想后写（Design Thinking 四问）。** 编码前它会先想清楚四件事：

- **Purpose**：这界面解决什么问题？谁用？
- **Tone**：挑一个**极端**方向。技能给的候选谱系是——极简到冷酷 / 极繁到混沌 / 复古未来 / 有机自然 / 奢华精致 / 玩具般俏皮 / 杂志编排 / 粗野原始 / 装饰艺术几何 / 柔和马卡龙 / 工业实用。
- **Constraints**：框架、性能、无障碍等技术约束。
- **Differentiation**：什么让它**令人过目不忘**？别人会记住的那"一个东西"是什么？

它的核心信条是 **"intentionality, not intensity"（关键是意图性，而非强度）**——极繁和极简都行，只要方向清晰、执行精确。

**然后主动规避"AI 味"、追求差异化。** 它会刻意不用那几样"一眼假"的元素（清单见 §2.4），改用有个性的字体配对、主导色 + 锐利强调色、纯 CSS / Motion 动效、非对称破格布局、渐变网格 / 噪点 / 颗粒等背景纹理；而且**每次生成都力求不同**——明暗主题、字体、风格轮换，明确不"每次都收敛到同一套常见选择"。

**复杂度随方向自适应。** 选了极繁方向 → 繁复代码 + 大量动效；选了极简 → 克制 + 精度 + 对间距排版细节的打磨。"优雅来自把方向执行到位"。

### 2.3 它的设计准则清单（Frontend Aesthetics Guidelines）

技能给 Claude 的五维准则，你了解它才知道产物为什么长那样：

| 维度 | 准则 |
|---|---|
| **Typography 排版** | 选**美、独特、有意思**的字体；**避开 Arial / Inter 这类通用字体**；一个有个性的展示字体 + 一个精致的正文字体**配对** |
| **Color & Theme 配色** | 定一套统一审美，用 **CSS 变量**保证一致；**主导色 + 锐利强调色，胜过怯懦、均匀分布的调色板** |
| **Motion 动效** | 高影响力时刻优先——**一次精心编排的页面载入 + 交错延迟揭示（animation-delay），比零散的微交互更讨喜**；HTML 优先纯 CSS，React 用 Motion 库；善用滚动触发和意外的悬停态 |
| **Spatial Composition 空间构图** | 非对称、重叠、对角流动、打破网格的元素；**要么大量留白，要么受控的高密度** |
| **Backgrounds 背景细节** | 营造氛围和纵深，别默认纯色——渐变网格 / 噪点纹理 / 几何图案 / 分层透明 / 戏剧化阴影 / 装饰性边框 / 自定义光标 / 颗粒叠加 |

技术偏好很轻：技术栈开放（HTML/CSS/JS、React、Vue 都行），只有两条硬偏好——**HTML 动效优先纯 CSS、React 动效用 Motion 库**，配色用 **CSS 变量**。没指定 UI 框架 / Tailwind / 组件库。

### 2.4 它拉黑了什么（NEVER 清单）

技能里有一段措辞很硬的 `NEVER`——这是它的灵魂，也是你能一眼认出"这界面用了这个技能"的地方：

> "**NEVER** use generic AI-generated aesthetics like overused font families（**Inter, Roboto, Arial, 系统字体**）, cliched color schemes（**尤其是白底紫色渐变**）, predictable layouts and component patterns, and cookie-cutter design that lacks context-specific character."

翻成大白话，它明确拒绝：

- **字体**：Inter、Roboto、Arial、系统默认字体；
- **配色**：陈词滥调方案，**尤其点名"白底紫渐变"**——这被单列为"AI 味"的头号标志；
- **布局**：可预测的居中卡片式布局、通用组件套路；
- **整体**：缺乏语境个性的"饼干模具式"设计。

还有一条针对"跨多次生成"的禁令：**NEVER 每次都收敛到同一套常见选择**——甚至点名 Space Grotesk 字体作为"别老用它"的反例。这条是为了防止它自己变成一种新的"AI 味"。

### 2.5 适合与不适合的场景

**✅ 适合**

- 落地页、营销页、dashboard、组件 / 设计原型；
- 需要"有记忆点""有品牌调性""不像模板"的独立界面；
- 追求视觉差异化和成品级观感的场合。

**❌ 不适合（或需另配约束）**

- **要严格遵循既有设计系统 / 品牌规范 / design token 的企业项目**——这个技能**鼓励打破常规、每次求异**，和"强一致性、可预测"目标相悖。这种场合要么别用它，要么在 prompt 里明确锁死设计规范（用户指令优先级高于技能）。
- **需要跨次稳定、可复现输出**——它明确追求"每次都不一样"，不利于回归对比。
- **纯后端 / 纯逻辑、无视觉产出**——用不上。
- 注意它**不含质量门 / 校验 / 测试**，也不起可运行环境——验收要另配 QA / UI 自测类技能（或本仓的 `kdev-ui-autotest`）。

---

# 附录

> 以下不影响上手，按需阅读：**A** 它反的"AI 味"到底是什么（设计哲学）· **B** SKILL.md 逐条原文 · **C** 与 ieidev 版的关系 + Q&A/资源

## 附录 A：它反的"AI 味"到底是什么（设计哲学）

用 AI 生成前端，大家应该都见过那种"一眼假"的观感：Inter 字体、白底、一坨紫色渐变按钮、内容全部居中的卡片、四平八稳没有任何记忆点。它不难看，但**没有个性、没有语境、千篇一律**——技能把它叫 **"AI slop aesthetics"（AI 泔水审美）**。

frontend-design 的整套设计就是奔着这个靶子去的，核心哲学三句话：

1. **intentionality, not intensity（意图性，而非强度）**——不是"堆特效"，是"选一个清晰方向并精确执行"。极简和极繁都能出彩，前提是有明确概念方向。
2. **Dominant colors with sharp accents outperform timid, evenly-distributed palettes**——主导色 + 锐利强调，胜过怯懦均匀的配色。"不敢下决定"本身就是 AI 味的来源。
3. **No design should be the same**——审美要在多次生成间轮换，绝不收敛到同一套安全选择。

收尾还有一句态度性指令，很能代表它的气质：

> "Claude is capable of extraordinary creative work. **Don't hold back**, show what can truly be created when thinking outside the box and committing fully to a distinctive vision."（Claude 有能力做出非凡的创意——**别收着**，跳出框、完全投入一个鲜明的愿景，展示真正能做到什么。）

## 附录 B：SKILL.md 逐条原文（可直接引用的金句）

整份 SKILL.md 结构：开场 → `## Design Thinking` → `## Frontend Aesthetics Guidelines` → NEVER 反模式段 → 差异化段 → 复杂度匹配段 → 收尾激励段。撰稿 / 引用时可用的原文：

- "avoid generic **'AI slop'** aesthetics"
- Design Thinking CRITICAL 段："Choose a clear conceptual direction and execute it with precision. **Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.**"
- Typography："**Avoid generic fonts like Arial and Inter**; opt instead for distinctive choices … **Pair a distinctive display font with a refined body font.**"
- Color："**Dominant colors with sharp accents outperform timid, evenly-distributed palettes.**"
- Motion："**one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions.**"
- Spatial："Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. **Generous negative space OR controlled density.**"
- NEVER 段："NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (**particularly purple gradients on white backgrounds**) …"
- 差异化："**No design should be the same.** … NEVER converge on common choices (**Space Grotesk, for example**) across generations."
- 复杂度："**Match implementation complexity to the aesthetic vision.**"
- 收尾："**Don't hold back**, show what can truly be created when thinking outside the box."

## 附录 C：与 ieidev 版的关系 + Q&A

### C.1 ieidev-frontend-design 是什么

本机还有一个 `ieidev-team:ieidev-frontend-design`。经逐行比对确认：它是官方 frontend-design 的**逐字复刻分支（Apache-2.0 fork），设计方法论一字未改**——你可能以为 ieidev 版加了 design token / 8px 网格 / 字体白名单之类约束，**并没有**。全文只有 3 处差异，且无一触及设计方法论：

1. frontmatter `name` 改为 `ieidev-frontend-design`；
2. `license` 改为 Apache-2.0；
3. 顶部加了一段 fork 溯源声明。

**为什么要 fork**：ieidev-team 是一个"洁净室"数字员工集群，要**去掉对第三方插件的运行时依赖**——它的原型设计 agent（`req-architect-prototype`）改调 `ieidev-team:ieidev-frontend-design`，不再外挂上游。方法论价值完全等同官方版，区别只在命名空间和许可合规。

### C.2 Q&A

**Q：我不满意它选的风格，能干预吗？**
A：能。用户指令优先级高于技能——在 prompt 里直接说"用 XX 字体 / 走 XX 风格 / 遵守我们的设计规范"，它照做。技能只是在你**没给方向**时替你做一个大胆决策。

**Q：它保证好看吗？**
A：它保证"不套 AI 味模板、有明确审美方向"，但"大胆"有时也意味着"用力过猛"或"不符合你的品牌"。它适合探索和原型，正式交付前仍要人过一遍审美关。

**Q：企业项目有严格设计系统，还能用吗？**
A：不建议裸用——它的默认倾向是"打破常规、每次求异"，会和"强一致"打架。要用就在 prompt 里锁死规范（token / 字体 / 间距），把它的"求异"约束在你的系统内。

**Q：它管测试和可运行吗？**
A：不管。它只产设计导向的代码，不含质量门、不起环境。验收另配 QA / UI 自测技能。

### 资源

- 插件源：`anthropics/claude-plugins-public/tree/main/plugins/frontend-design`（Anthropic 官方，作者 Prithvi Rajasekaran / Alexander Bricken）
- 安装：`/plugin install frontend-design@claude-plugins-official`
- 技能本体：`skills/frontend-design/SKILL.md`（就这一份，约 40 行）
- 延伸阅读：Anthropic Cookbook《Prompting for frontend aesthetics》notebook（README 里唯一外链，讲"如何为高质量前端写提示词"）

---

*文档基于 Anthropic 官方 frontend-design skill 源码编写，用于团队技术分享。*
