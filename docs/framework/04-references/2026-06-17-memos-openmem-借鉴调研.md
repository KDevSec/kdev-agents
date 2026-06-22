# memos / OpenMem / OpenClaw 借鉴调研 —— 对 kdev-memory 的可借鉴性研判

| 项 | 值 |
|---|---|
| 文档性质 | 技术调研 + 架构借鉴分析（只调研，不改 kdev-memory 任何代码）|
| lifecycle | reference |
| 日期 | 2026-06-17 |
| 调研对象 | `usememos/memos`（自托管 markdown 笔记 app）/ `openmem.net`（MemOS，LLM 记忆 OS）/ OpenClaw（agent 框架）|
| 顶着的 kdev-memory 约束 | markdown 主存不引入 JSONL（叙事层）· git nested repo 无 server（Q-009）· hook 驱动非查询 API · scope 拓扑 + subject 路由 + F-NNN · P-C2 正在加「只读复用 events 的 JSONL 操作层」|
| 一句话结论 | **基本不适用整体采纳**（memos 的 server+DB+多用户账号根与 kdev-memory 的 serverless/git/file 根直接冲突）；**可借的是「概念/字段语义」而非「机制」，落地价值集中在 3 点**（见 §5 verdict）|

---

## 1. 三名关系澄清（重要纠偏：三者是无关项目）

调研的最大发现:**`memos` / `openmem.net` / `OpenClaw` 是三个互相独立的项目，名字相似纯属巧合 + 文档域名误导**，不是同一个东西的不同层。

| 名称 | 归属 | 是什么 | 与本调研关系 |
|---|---|---|---|
| **`usememos/memos`** | GitHub `usememos` 组织 | 开源**自托管 markdown 笔记/备忘录 app**（Go 后端 + React 前端，单二进制/docker）| **本调研主体**（任务原意指向它）|
| **`openmem.net` / MemOS** | GitHub `MemTensor` 组织 | 面向 **LLM/AI Agent 的「记忆操作系统」**（Python 包 + 云服务），文档站 `memos-docs.openmem.net` 是它的 | 同名巧合，**与 usememos/memos 零关系**；但它本身是「AI agent 记忆系统」反而和 kdev-memory **赛道更近** |
| **OpenClaw** | 独立 agent 执行框架（非主流开源） | AI agent 执行框架，有插件生态 | 与 usememos/memos 无关；MemOS Cloud 为它出了个**记忆后端插件**（recall+capture 两阶段，宣称省 ~72% token）|

**误导根源**:任务给的 `memos-docs.openmem.net/cn/openclaw/guide` 域名里有 "memos"，看起来像是 usememos/memos 的文档，**实际是 MemOS（openmem.net）的文档站**。`openclaw/guide` 讲的是「MemOS Cloud 给 OpenClaw agent 出的记忆插件」，跟 markdown 笔记 app `usememos/memos` 毫无关系。

> 实务影响:下面 §2~§5 的对照与借鉴**主体是 `usememos/memos`**（笔记 app，任务原意）。MemOS/OpenClaw 那条线作为「另一个 AI-agent 记忆系统」单列 §6 旁证——它和 kdev-memory 是同赛道竞品思路，其 recall/capture 两阶段 + 省 token 叙事反而比 memos 更值得一瞥，但**也是 server/cloud 形态**，借鉴结论同样落在「借语义不借机制」。

来源:
- https://github.com/usememos/memos
- https://memos-docs.openmem.net/cn/openclaw/guide
- https://github.com/MemTensor/MemOS-Cloud-OpenClaw-Plugin

---

## 2. memos 逐维度事实（带来源）

| 维度 | usememos/memos 事实 | 来源 |
|---|---|---|
| **存储模型** | **DB 三选一:SQLite / MySQL / PostgreSQL**；附件走本地文件;**Protobuf 为单一 schema 真相源**;tag 存 memo payload 的 JSON 字段（Postgres 可 JSONB 算子查）| README / DeepWiki API doc / v0.27.0 |
| **部署形态** | **常驻 server**（默认端口 5230），docker（镜像 ~20MB）/ 单 Go 二进制 / K8s Helm;**多用户 + 账号系统**;Bearer Token(PAT)认证;**自托管可全离线**（无遥测）| README / usememos.com/features |
| **数据模型** | memo = markdown content + visibility + 时间 + **tag** + **relations** + reactions;**relations**:memo 间建关系 + @mention 引用并发通知;**附件**:拖拽图/视频/音频/文档;**visibility 三档:Public / Protected(分享链接) / Private** | v0.27.0 changelog |
| **检索/召回** | **原生全文搜索**（跨内容+tag，底层引擎未公开披露，疑 SQLite FTS/DB FTS）;tag 过滤;**查询 filter 遵循 Google AIP-160**（如 `row_status=="NORMAL"`），list 支持 filter+ordering+分页 | features / API doc |
| **API / 集成** | **REST(`/api/v1`) + gRPC**（grpc-gateway 从 Protobuf 自动双暴露）;**webhook**（v0.27.0:comment/attachment/relation 事件）;**官方内置 MCP server**（`/mcp`，Streamable HTTP，PAT 认证，暴露 memo/comment/attachment/relation/tag CRUD）| API doc / v0.27.0 / DeepWiki |
| **同步/多端** | **中心 server 模型**:所有客户端连同一实例;v0.27.0 起 **SSE 实时推送**;**无 P2P / 无 CRDT / 无 local-first**;Web UI(React)+ API 供第三方客户端 | v0.27.0 / features |
| **AI 集成** | 官方内置 MCP server + AI 音频转录(实例级 provider/BYOK/Gemini);社区另有 3+ 个第三方 MCP server（Red5d/memos_mcp 等，search/create/get/list_tags）| v0.27.0 / github.com/Red5d/memos_mcp |

来源链接:
- https://github.com/usememos/memos · https://usememos.com/features · https://usememos.com/docs/api
- https://usememos.com/changelog/0-27-0 · https://github.com/usememos/memos/releases/tag/v0.27.0-rc.1
- https://deepwiki.com/usememos/memos/4.5-api-documentation-and-protocols
- https://github.com/Red5d/memos_mcp

---

## 3. 对照表:memos vs kdev-memory

| 维度 | usememos/memos | kdev-memory | 根性冲突? |
|---|---|---|---|
| **存储** | DB（SQLite/MySQL/PG），Protobuf schema | **markdown 主存**（4 段 Step 叙事）+ P-C2 只读复用 kdev-core 的 events.jsonl;**刻意不引入 DB、叙事层不 JSONL 化**（记忆底座 §8）| 🔴 **根冲突** |
| **部署** | 常驻 server + 多用户账号 + PAT | **无 server**;文件即真相;离线/任意 worktree 可用;无账号系统 | 🔴 **根冲突** |
| **数据模型** | memo + tag + relations + visibility 三档 + 附件 | Step/Q/G/R/F 条目 + `subject`/`phase` 归因 + `[[wiki-link]]` + scope 拓扑 + F-NNN 通道 | 🟡 部分可类比（见 §4）|
| **检索/召回** | server 端全文搜索 + AIP-160 filter API（查询式 pull）| **hook 驱动**:UserPromptSubmit 扫条目 `triggers:` 字段关键词命中 → 注入 `<recall>` 指针（push 式渐进披露）;聚合靠 grep | 🟡 思路可借、机制不可搬（见 §4）|
| **API/集成** | REST+gRPC+webhook+官方 MCP server | 无对外 API;集成点 = Claude Code hooks(SessionStart/UserPromptSubmit/PreCompact/SessionEnd)| 🔴 机制根冲突 |
| **同步/多端** | 中心 server + SSE | **git nested repo**（Q-009）:clone/pull/push;多 worktree symlink;**coordination-free**（Q-020 时间戳 ID）| 🔴 根冲突（但目标相同:跨机一致）|
| **AI-agent 友好度** | MCP server 让 agent CRUD memo（但要起 server + 账号 + 网络）| 原生为 agent 续航而生（hook 注入 + scope + recall reader），**无网络/无 server 依赖** | — kdev-memory 在「serverless agent 续航」这条更专 |

**一句话**:memos 是「给**人**用的、server 托管的多用户笔记产品，顺手开了 MCP 口给 agent」;kdev-memory 是「给**长周期 agent 工程**用的、file-based/serverless 的续航+蒸馏制度」。形态根上不同,**不能整体对标**。

---

## 4. 可借鉴清单（逐候选研判:借什么 + 怎么嫁接不破根 + 价值 / 或判不可借）

> 研判准绳:任何借鉴**不得引入 server / DB / 账号 / 网络查询依赖**，不得把叙事层 JSONL/DB 化（守记忆底座 §8 + Q-009 serverless 根）。

### 候选 1:tag/标签体系 ↔ subject/phase 路由 —— ⚪ **已自有更强，不借机制;可借「枚举集中管理」一个小点**
- memos:扁平 tag 存 JSON、按 tag 过滤。
- kdev-memory 现状:`subject`（评谁,7 类枚举 + 三级推断）+ `phase`（10 值工作性质）+ `phase_node`/`active_skills`，**正交双轴 + 自动推断**，已**远比 memos 扁平 tag 强**（memos tag 无语义分轴、无自动推断、无 subject/phase 正交）。
- **可借的极小点**:memos 把 tag 做成「实例级可枚举 + list_memo_tags API 让 agent 拿全集」。kdev-memory 的 subject/phase 枚举散在 SKILL/references，**可借「枚举集中成一份可被 recall reader / distill 读到的清单」**（纯 markdown/yaml,不上 server）。**价值:低**(锦上添花,非缺口)。
- **结论:机制不借**(自有体系更强),**仅记一个「枚举集中化」念头**,优先级低。

### 候选 2:memo relations/references ↔ `[[wiki-link]]` —— ⚪ **同构,已自有;借鉴价值低**
- memos:memo 间建 relation + @mention,**靠 DB 存关系 + server 渲染反向链接/通知**。
- kdev-memory:`[[wiki-link]]` + 满地 `承/连/关/修订` 交叉引用(决策日志里随处可见,如 `承 Q-009`/`修 G-011`)。**语义上已是同一回事**,且 kdev-memory 的引用**带类型**（承/连/关/修订/否决），比 memos 无类型 relation 表达力更强。
- memos 的「反向链接(backlink)自动计算 + @mention 通知」要 server 端建反向索引。kdev-memory 若要反向链接 = grep 一遍 `[[X]]` 即可,**不需要 server**。
- **结论:不借**(自有 wiki-link + 带类型引用已覆盖)。**唯一可记一笔**:若将来想要「某条 Q 被谁引用了」的 backlink 视图 → 纯 grep 派生即可(给 HUD 用,见候选 5),不学 memos 的 DB relation 表。

### 候选 3:全文搜索/查询 API ↔ grep 式 hook 召回 —— 🟢 **borrow 语义给 P-C2 recall reader,这是最实的一点**
- memos:server 端全文搜索 + **AIP-160 结构化 filter**（`field op value` + ordering + pagination）。这是「**结构化查询语言**」抽象。
- kdev-memory 现状:召回 = `triggers:` 字段关键词命中(push) + 聚合靠 grep(pull),**无结构化过滤表达**。P-C2 正在建 **recall reader**:`recall(scope, node)` 跨 `features/*/events.jsonl` 按 `actor==scope`+`node` 过滤捞行。
- **可借且不破根**:把 memos 的 **AIP-160 filter 抽象「借语义」给 P-C2 recall reader 的过滤参数设计**——recall reader 本就要按 `actor`/`node`/时间范围过滤 JSONL,**借鉴一个规范化的、可组合的 filter 形态**（如 `actor==X AND node==D2 AND ts>=...`,实现是本地 Python 谓词,不是 server SQL）会让 recall API 更清爽、可扩展、agent 好拼查询。**纯本地、读 file、零 server**,完全守 serverless 根。
- **价值:中-高**(直接喂给正在设计的 P-C2 recall reader,把「过滤参数怎么定」从拍脑袋升级成有参照的规范)。
- **不可借的部分**:memos 的全文搜索引擎(SQLite FTS)本身 → kdev-memory 叙事层是 markdown、量级小(几百 KB)、grep/ripgrep 足够,**上 FTS 索引是过度工程**,且会引入「索引 = 第二本账」破不双写原则。**只借 filter 语义,不借搜索引擎**。
- **结论:🟢 借「AIP-160 filter 语义」给 P-C2 recall reader 的过滤参数设计;不借搜索引擎实现。**

### 候选 4:visibility/sharing 模型 ↔ 团队共享记忆 + Q-009 §9.5 隐私脱敏待定 —— 🟢 **borrow 三档分级的「概念」给悬而未决的隐私问题**
- memos:**Public / Protected(分享链接) / Private 三档 visibility**,server 端按登录态 gate 渲染。
- kdev-memory 现状:Q-009 §9.5 **明确标了一个未决问题**——「记忆含用户 verbatim 原话,推到团队共享记忆仓 = 原话进团队仓,必要时脱敏或限私有」,但**没给分级模型**。scope 拓扑里 `shared/` vs `staff/<员工>/` 是**功能归属**分轴,不是**可见性/敏感度**分轴。
- **可借且不破根**:借 memos「**一条记录带一个可见性/敏感度级别字段**」的概念,给 kdev-memory 条目加一个**轻量 `visibility` / `sensitivity` frontmatter 字段**（如 `private`(仅本机不进 git push)/ `team`(可进共享仓)/ `redact`(脱敏后才进)）。**落地完全 file-based**:push hook(kdev-sync-push.py)按字段决定哪些条目/段落跳过 push 或脱敏,**不需要 server gate**——把 memos「server 运行时按登录态 gate」换成「git push 时按字段 gate」。
- **价值:中-高**(直接给 §9.5 那个悬了的隐私待定题一个**有参照的、不上 server 的解法骨架**;团队共享记忆仓落地前这是必须回答的问题)。
- **不可借**:memos 的「分享链接 + 登录态 + 多用户账号」整套 → 那是 server 产品形态,kdev-memory 不要。**只借「记录带敏感度级别」这一个字段概念 + push-time gate 思路。**
- **结论:🟢 借「per-记录 visibility/sensitivity 字段」概念,落成 frontmatter + push hook gate,回答 Q-009 §9.5 隐私待定。**

### 候选 5:Web UI 浏览 ↔「记忆的 HUD」/人读日志的浏览器 —— 🟡 **借「浏览/检索/relation 图」的 UI 范式给 kdev-hud,不借 memos 技术栈**
- memos:React Web UI,explore 页 / tag 过滤 / 全文搜 / memo 卡片 / relation 视图。
- kdev-memory 现状:人读日志靠直接读 markdown;项目另有 **kdev-hud**（`docs/framework/01-design/2026-06-10-04-...-HUD驾驶舱-...` + `设计参考-hud-dashboard.html`）做实时驾驶舱,但 HUD 当前焦点是 **flow/feature 实时态**,不是「**记忆条目浏览器**」。
- **可借且不破根**:借 memos Web UI 的**交互范式**（不是代码）——记忆条目卡片化浏览 + 按 subject/phase/scope **faceted 过滤** + `[[wiki-link]]` relation 图谱 + 时间线。落成 **kdev-hud 的一个「记忆浏览」视图**:**静态生成 / 本地渲染**（读 markdown + 派生,像 hud.html 那样本机派生、不托管、可再生）,**绝不引入 memos 的 server+DB**。
- **价值:中**(改善人读体验,但属增强非缺口;且 HUD 已是独立设计轨,这是「给 HUD 加一个记忆视图」的 backlog 念头,不是 kdev-memory 本体改动)。
- **结论:🟡 借 UI/交互范式给 kdev-hud 的「记忆浏览视图」backlog,本机静态派生,不借 server/DB/技术栈。**

### 候选 6:MCP / AI 集成模式 —— 🔴 **不借(机制根冲突)**;⚪ MemOS 的 recall/capture 两阶段叙事可作旁证参考
- memos 官方 MCP server:agent 通过 `/mcp`(Streamable HTTP + PAT)CRUD memo。**要起 server + 账号 + 网络**——与 kdev-memory「hook 注入、无 server、无网络」的集成根**直接冲突**,不借。
- kdev-memory 的「集成」本就是 Claude Code hook 原生通道(SessionStart brief / UserPromptSubmit recall / PreCompact),**比 MCP 更贴合「agent 续航」且零依赖**。给 kdev-memory 套 MCP = 凭空加 server/网络依赖,**纯倒退**。
- **唯一可记的旁证**:MemOS-Cloud-OpenClaw-Plugin 的 **recall(执行前检索)+ capture(执行后存储)两阶段 + 宣称省 72% token** 的**叙事**,和 P-C2「recall reader(执行前读 events 切片)+ rollup deriver(执行后派生 Step)」**形状高度一致**——可作为「我们方向对了」的外部旁证,**但它是 cloud 形态,机制不借,只看叙事印证**。
- **结论:🔴 MCP 不借**(server 根冲突);⚪ MemOS recall/capture 两阶段叙事作 P-C2 方向的外部旁证。

---

## 5. 冲突清单（memos 核心 × kdev-memory 根,直接冲突、不该整体采纳）

| memos 核心 | kdev-memory 的根 | 为什么不该采纳 |
|---|---|---|
| **常驻 server**（5230 端口）| **serverless·文件即真相·离线/任意 worktree 可用**（Q-009）| 上 server = 砍掉「任意 worktree/离线/换机即用」,引入运维负担,违背设计根 |
| **DB（SQLite/MySQL/PG）+ Protobuf schema** | **markdown 主存,叙事层刻意不 JSONL/DB 化**（记忆底座 §8）| DB = 人不可直读 + git diff 不友好 + 「第二本账」,违 §8 旧决策与「不双记」§7 |
| **多用户账号系统 + PAT 认证** | **无账号;scope = 工作流身份(协作者/员工/分支),git 同步**(Q-020 coordination-free)| 账号体系 = 中心化身份权威,与「分布式写手 + 时间戳 ID coordination-free」根冲突 |
| **中心 server + SSE 多端同步** | **git nested repo clone/pull/push**(Q-009)| server 同步 = 单点 + 在线依赖;git 同步天然离线/分布式/可审计,不换 |
| **MCP server / REST / gRPC 对外 API** | **Claude Code hook 原生通道**(无网络) | 对外 API = 凭空加 server/网络面,hook 已覆盖 agent 续航集成需求 |
| **全文搜索引擎(FTS 索引)** | **markdown 量级小,grep/ripgrep 足够** | FTS 索引 = 第二本账 + 过度工程,叙事层规模用不上 |

**核心冲突一句话**:memos 是「**server + DB + 多用户账号**」三位一体的托管笔记产品;kdev-memory 是「**serverless + git + file + 分布式写手**」的 agent 续航制度。这两组根**互斥**,任何「整体采纳 memos」都等于推翻 Q-009 + 记忆底座 §8——**不可行**。

---

## 6. 旁证:MemOS / OpenClaw 那条线(同赛道,但同样 server/cloud 形态)

虽与 usememos/memos 无关,但 MemOS(openmem.net)本身是「**AI agent 记忆系统**」,和 kdev-memory **同赛道**,比笔记 app memos 更值得一瞥:
- **形状一致**:OpenClaw 插件做 **recall(pre-exec 检索)+ capture(post-exec 存储)**,宣称智能检索替代批量上下文 load **省 ~72% token**——这正是 kdev-memory P-C2「recall reader + 两层表示省 token」的同形思路,**外部印证我们方向对**。
- **但根仍冲突**:MemOS 是 **Python 包 + 云服务(MemOS Cloud)**,recall/capture 走它的 MCP service / cloud 后端——**还是 server/cloud 形态**,机制不借,只取「方向印证」。
- **claude-mem / ClawMem** 等社区工具走 MEMORY.md hooks + 本地 MCP + hybrid RAG——**其中「MEMORY.md hooks 模式」与 kdev-memory 的 hook 驱动 + markdown 同源**(Claude Code 生态通用打法),不算 memos 独有可借点。

来源:
- https://github.com/MemTensor/MemOS-Cloud-OpenClaw-Plugin · https://memos-docs.openmem.net/cn/openclaw/guide
- https://github.com/thedotmack/claude-mem · https://github.com/yoloshii/ClawMem

---

## 7. 明确 verdict

**结论:基本不整体采纳;借具体 3 点(均为「借语义/概念,不借机制」,全程守 serverless/git/file/markdown 根)。**

**一句话**:memos 是 server+DB+多用户的托管笔记产品,与 kdev-memory 的 serverless/git/file 根**直接互斥**,**整体采纳不可行**;但它在「结构化检索表达、可见性分级、浏览 UI 范式」上的**概念**可被剥离机制后嫁接,落地价值集中在下面 top 3。

**可借鉴 top 3(按价值/契合度排序)**:
1. 🟢 **AIP-160 filter 语义 → P-C2 recall reader 的过滤参数设计**(候选 3):把 recall reader 的 `actor/node/时间范围` 过滤从拍脑袋升级成规范化可组合 filter,实现仍是本地 Python 谓词读 JSONL,零 server。**最实、正中正在设计的 P-C2。**
2. 🟢 **per-记录 visibility/sensitivity 字段 → 回答 Q-009 §9.5 隐私待定**(候选 4):给条目加 `private/team/redact` frontmatter,push hook 按字段 gate(脱敏/跳过),把 memos「server 运行时 gate」换成「git push 时 gate」。**给悬而未决的团队共享隐私题一个不上 server 的解法骨架。**
3. 🟡 **Web UI 浏览/faceted 过滤/relation 图范式 → kdev-hud 的「记忆浏览视图」backlog**(候选 5):借交互范式不借技术栈,本机静态派生(像 hud.html),改善人读体验。**增强项,非缺口,挂 HUD 轨。**

**不借**:tag 机制(候选 1,自有 subject/phase 更强)、relation 表(候选 2,自有带类型 wiki-link 已覆盖)、MCP/REST/gRPC server(候选 6,机制根冲突)、DB/账号/常驻 server(§5 整套根冲突)、FTS 搜索引擎(规模用不上+第二本账)。

**诚实附注**:本调研最大价值其实是**纠偏了三名关系**(memos≠openmem≠openclaw,任务原假设它们是一个东西的不同层是误的)。剥离这层误导后,真正与 kdev-memory 同赛道的是 MemOS(§6)而非笔记 app memos;而 MemOS 同样是 cloud 形态、机制不可借,只印证 P-C2 方向。**所以「有借鉴」是真实的但价值有限(3 个概念级小点),没有为了凑借鉴而硬抬——诚实结论是「基本不适用,捡 3 个概念」。**

---

## 8. 来源汇总

- https://github.com/usememos/memos · https://usememos.com/features · https://usememos.com/docs/api · https://usememos.com/changelog/0-27-0
- https://github.com/usememos/memos/releases/tag/v0.27.0-rc.1 · https://deepwiki.com/usememos/memos/4.5-api-documentation-and-protocols
- https://github.com/Red5d/memos_mcp
- https://memos-docs.openmem.net/cn/openclaw/guide · https://memos-docs.openmem.net/cn/open_source/getting_started/installation
- https://github.com/MemTensor/MemOS-Cloud-OpenClaw-Plugin · https://github.com/thedotmack/claude-mem · https://github.com/yoloshii/ClawMem
- 内部:记忆底座合稿 v1.0 §8/§9（`docs/framework/01-design/2026-06-10-05-...`）· P-C2 spec（`docs/superpowers/specs/2026-06-13-P-C2-...`）· Q-009/Q-002/Q-019/Q-020（`.kdev/memory/决策日志.md`）

---
---

# Part 2：MemOS 深评 + 自托管闸 + 集成可行性（2026-06-17 追加）

> **本轮定向**（用户纠偏后）：Part 1 把笔记 app `usememos/memos` 当主体、MemOS 只列旁证（§6）。**本轮主角换成 MemOS（openmem.net / MemTensor），专钻「能否做 kdev 数字员工的『员工操作记忆』后端」**，核心闸 = 开源 / 内网私有化自托管。前提（Part 1 已厘清，不复议）：三名互不相关，`usememos/memos` 已排除；MemOS = LLM agent 记忆 OS；OpenClaw = 独立 agent 框架，MemOS 给它出过记忆插件（云版 + 本地版）。
>
> **标注约定**：✅证实（官方 repo/docs/npm 实锤）· �amber宣称（官方营销口径，未独立验证）· ❓存疑（文档未明）。

---

## P2.1 一句话结论（先给 go/no-go）

**自托管 go/no-go：🟢「有条件可行」——但走的是 MemOS 的「本地插件档（local-plugin）」而非「服务器档（server）」。** 关键条件：① 用 `@memtensor/memos-local-openclaw-plugin` 那一档（SQLite+FTS5+vector 单文件、in-process Xenova 嵌入、规则化兜底摘要、零强制云调用），**不是**重型 FastAPI+Qdrant+Neo4j server 档；② 接受它仍是「常驻进程 + SQLite 二进制库 + Node 运行时」——与 kdev「纯 file / git / 零依赖 / 任意 worktree」根有真冲突，需当**第二存储层旁挂**而非替换 git 叙事层。**重型 server 档 = 不可行**（Qdrant+Neo4j+8GB RAM+FastAPI 常驻，直接砸穿 serverless/离线/worktree 根）。

---

## P2.2 A 闸：开源与自托管（最关键，逐条证实）

### A.1 是否开源 / license / 成熟度 —— ✅ 真开源、活跃

| 项 | 事实 | 标注 |
|---|---|---|
| repo | `github.com/MemTensor/MemOS`（PyPI 包名 `MemoryOS`）| ✅ |
| **license** | **Apache 2.0**（无商用限制、可私有化、可改）| ✅ 这是 go 闸的第一块绿灯 |
| 成熟度 | ~9.9k star / 903 fork / 1823 commit / 30 release（最新 v2.0.19，2026-06-12）/ 143 open issue | ✅ 活跃，非玩具，但仍年轻（2.0 系「Stardust」刚出）|
| 论文背书 | arXiv 2507.03724（MemOS: A Memory OS for AI System）+ 2604.07877（MemReader 主动抽取）| ✅ 有学术支撑 |

**判**：开源闸完全通过——Apache 2.0 + 活跃社区 + 论文。**license 不是 blocker。**

### A.2 能否完全内网/离线/air-gapped —— ⚠️ 分两档，结论天差地别

MemOS 有**两个截然不同的部署形态**，自托管可行性完全取决于选哪档。**Part 1 §6 只看到了「cloud 形态」那半张脸，漏了 local-plugin 这半张——这是本轮最重要的纠正。**

#### 档 A：重型 server 档（self-hosted REST API server）—— 🔴 自托管「技术可行但代价过重」

- **组件**：FastAPI server（uvicorn，默认 8000 口）+ **Qdrant**（向量库）+ **Neo4j**（图库，`tree-mem` 树记忆刚需）+ 可选 Redis（MemScheduler 异步队列）。✅
- **足迹**：docker-compose 一键起，但**预期 8GB+ RAM**（Neo4j 是吃内存大户）。✅
- **嵌入**：`MOS_EMBEDDER_BACKEND` 可选 `ollama`（本地）或 `universal_api`（远程）→ **嵌入能本地化**（Ollama）。✅
- **LLM（chat + MemReader 抽取）**：默认要 `OPENAI_API_KEY` / `CHAT_MODEL_LIST`，但 provider 列表含 **Ollama / HuggingFace / vLLM** → **理论可全本地 LLM**。✅（官方安装文档默认示例用 Bailian/阿里云，本地化要自己改配置）
- **license server / 联网激活**：**无**（Apache 2.0，无 license server）。✅
- **判**：技术上 air-gapped 可行（Ollama 嵌入 + Ollama/vLLM 推理 + 本地 Qdrant/Neo4j），**但这是一套「FastAPI + 向量库 + 图库 + 本地 LLM 推理服务」的重型常驻栈**，运维负担 ≈ 起一个微服务集群。**对 kdev = 过重，🔴 不取。**

#### 档 B：本地插件档（`@memtensor/memos-local-openclaw-plugin`，v1.0.0）—— 🟢 这才是 air-gapped 正解

这是 Part 1 完全没钻到的关键档。✅ 全部来自官方 npm + repo `apps/memos-local-openclaw`：

| 维度 | 本地插件档事实 | 标注 |
|---|---|---|
| **存储** | **单个 SQLite 文件** `~/.openclaw/memos-local/memos.db`，内含 **FTS5 全文 + 向量 + memories/tasks/skills 多表**；SHA-256 前16hex 去重 | ✅ **零外部 DB**（无 Qdrant/无 Neo4j）|
| **嵌入** | 默认 **`Xenova/all-MiniLM-L6-v2` in-process 跑、零 API 调用**（transformers.js/ONNX 本地）；可换 OpenAI兼容/Gemini/Cohere/Voyage/Mistral | ✅ **默认就离线** |
| **摘要/skill 进化** | 配 summarizer 则调 LLM 出「Goal/Key Steps/Result/Key Details」结构化摘要；**不配则规则化兜底或跳过**（"falls back to rule-based logic or is skipped"）| ✅ **LLM 可选，非强制** |
| **任务边界** | 自动检测：per-turn LLM 主题判定 + 2h idle timeout 切 task（这步要 LLM；无 LLM 时降级）| ✅/❓ 自动切分依赖 LLM 判定，纯离线下降级 |
| **召回/捕获 hook** | `before_agent_start`：自动召回注入 system context；`agent_end`：消息 chunk+embed+落库。**"不依赖模型主动记录"** | ✅ **正是「不靠模型自觉」** |
| **隔离** | 每条记忆带 `owner` 字段过滤；`owner="public"` 共享；无跨 agent 串味 | ✅ |
| **强制云调用 / API key** | **无**——「local plugin operates fully offline using embedded Xenova + rule-based summarization」；所有外部 API 都是可选增强 | ✅ **air-gapped 实锤** |
| **运行时** | **Node.js ≥18 + better-sqlite3 原生模块（装时编译）** | ✅（注意：要 Node + 原生编译）|

**判 A.2**：**air-gapped 自托管 = 🟢 可行，但只在「本地插件档」**。决定性证据：默认 Xenova in-process 嵌入 + 规则化兜底摘要 = **零强制云、零外部 DB、单 SQLite 文件**。这把 Part 1 §6「MemOS 是 cloud 形态、机制不可借」的旧结论**部分推翻**——cloud 是一种封装，开源底座有完整的本地档。

### A.3 开源版是否阉割 —— �amber 基本不阉割，但「本地档 ≠ 全功能档」

- **cloud vs open-source 功能**：cloud 卖的是「托管 + 省运维 + 宣称省 72% token」；**算法/存储/召回核心都在 Apache 2.0 开源仓**（MemReader、tree-mem、hybrid retrieval、MemScheduler 全开源）。�amber→✅ 没有「核心闭源、开源是 demo」的迹象。
- **但档内有梯度**：本地插件档（SQLite+vector）**砍掉了 server 档的图记忆（Neo4j tree-mem / L3 world model）**——官方原话「lighter local plugin with SQLite + FTS5 + vector for users who don't need graph capabilities」。即：**要图谱级记忆（MemCube 树/世界模型）→ 必须上 Neo4j server 档**；只要「向量+BM25 双引擎召回 + 自动捕获 + 隔离」→ 本地档够。
- **判**：对 kdev 的「员工操作记忆」需求（召回 + 自动捕获 + 隔离），**本地档不阉割关键能力**；我们本就不需要 L3 世界模型那套重抽象。

---

## P2.3 B 闸：架构证实（核宣称 vs 证实）

| 宣称 | 证实情况 | 标注 |
|---|---|---|
| **向量 + BM25 双引擎召回** | ✅ 证实：本地档 = **FTS5 关键词 + 向量语义双通道 + RRF（Reciprocal Rank Fusion）融合**。这正是「双引擎」的工业标准实现 | ✅ 真实，且实现方式（RRF）成熟 |
| **结构化自动捕获（不靠模型自觉）** | ✅ 证实：`before_agent_start`/`agent_end` 两 hook **自动拦截全部会话轮次 + 工具输出**，chunk→embed→落库；官方明示「不依赖模型主动记录，确保关键信息不被遗漏」。**机制 = host 框架的生命周期 hook 拦截（非后处理、非靠 prompt 自觉）** | ✅ **正中 P-C2 痛点**（P-C2 还在纠结「靠 dispatch step-recorder / 靠 events rollup」，MemOS 用 host hook 拦截一步到位）|
| **多 agent 隔离** | ✅ 证实：本地档 `owner` 字段过滤 + `public` 共享；cloud/server 档 `user_id`/`agent_id` + `agentOverrides`（per-agent memoryLimit）。**隔离粒度 = agent/owner 级，能映射我们的 scope=员工** | ✅ 可映射 `scope=staff/<员工>` |
| **MemCube / 记忆类型 / scheduler** | ✅ 证实存在：MemCube=可组合记忆立方；记忆分层 L1 Trace/L2 Policy/L3 World Model + Crystallized Skills；MemScheduler=Redis Streams 异步队列。**但这套重抽象主要在 server 档** | ✅/⚠️ 本地档简化版（memories/tasks/skills 三表）|
| **省 ~72% token** | �amber **宣称，基线未公开**。72% 是 **cloud OpenClaw 插件**口径；另有「35.24% token savings」是通用口径（repo 标语）。两个数字**都没给对照基线**（vs 什么？全量 load 上下文 vs 智能召回？）。论文 2507.03724 可能有口径，未深读 | �amber **方向可信（智能召回替全量 load 必省），具体百分比当营销看，不可直接引用** |
| **接入形态** | ✅ SDK（Python，server 档）+ REST API（FastAPI）+ **MCP server**（v2.0 升级，支持记忆删除/反馈）+ **host 插件**（OpenClaw/Hermes/nanoclaw 的 npm 插件，config 驱动）。**OpenClaw 插件 = 生命周期 hook 模型**，可作「接 Claude Code / kdev」的参照模板 | ✅ 多形态，MCP + 插件 hook 都可作 kdev 接入路 |

**MemReader（自动捕获的大脑）补证**：✅ MemReader 有 0.6B（被动结构化抽取）+ 4B（主动抽取，评估「信息价值/指代歧义/完整性」后决定**写入/缓存/检索历史/丢弃闲聊**）两档。这是「结构化捕获不靠自觉」的核心——**它主动判断哪些值得记**，而非全量灌库。对 kdev = 比「events 全量 rollup」更聪明的捕获闸。

---

## P2.4 C 闸：与 kdev 的集成适配（重点产出）

### C.1 逐条对位：MemOS 能替 / 能补 P-C2 哪几件

P-C2（spec §3）真正建 4 件 + 收窄模型「三本账」。逐件对位 MemOS 本地档：

| P-C2 要建的件 | MemOS 本地档对应能力 | 替 / 补 / 无关 | 说明 |
|---|---|---|---|
| **① Recall reader**（`recall(scope,node)` 跨 events.jsonl 按 actor 过滤捞行）| **hybrid retrieval（FTS5+vector+RRF）+ `before_agent_start` 自动召回注入** | 🟢 **能补/能替召回引擎** | MemOS 召回是**语义+关键词双引擎**，远强于 P-C2 的「actor==X 谓词过滤纯 lexical」。这是 MemOS 最大增量——P-C2 recall reader 是「按字段精确过滤」，没有语义相似召回；MemOS 给的正是「语义 recall」|
| **② CEO recorder 读 events+handoffs 派生叙事** | `agent_end` 自动 capture + MemReader 结构化摘要（Goal/Steps/Result/Details）| 🟡 **部分能补「捕获」，但替不了「CEO 叙事 + 他评/评分」** | MemOS capture 出的是「任务结构化摘要」，**不含 kdev 要的「模型他评/用户评分/经验/为什么」加料层**（P-C2 §2 命题2）。叙事/加料层 MemOS 给不了 → 这层仍归 kdev-memory markdown |
| **③ Step ID 时间戳化（Q-020）** | 无关（MemOS 自有记录 ID 体系）| ⚪ **无关** | 这是 kdev 内部 ID 卫生，MemOS 不碰；Q-020 照做 |
| **④ Workflow cache（幂等 range-keyed 派生缓存）** | MemScheduler 异步 + SHA-256 去重 | 🟡 **思路印证，不直接替** | MemOS 有去重/异步，但 P-C2 的「events-offset range 续跑」是 kdev 自有粒度，不套 |
| **三本账之 events.jsonl**（机器事实流水）| MemOS 不写 events——它在 host hook 层 capture | ⚪ **不冲突** | events 仍是 kdev-core 写；MemOS 是「在 capture 点旁挂第二消费者」|
| **三本账之 handoffs（md 可读交付物）** | 无对应（MemOS 存 SQLite 不可人读 git-diff）| ⚪ **MemOS 不碰，守 kdev** | handoffs 必须留 md（人读+git）|

**一句话对位**：**MemOS 能实打实补/替的是 P-C2 的「①召回引擎」——把「精确字段过滤」升级成「向量+BM25 语义双引擎召回」**，外加「②的捕获自动化半件」（host hook 拦截，省掉 dispatch step-recorder 的人工纪律）。**替不了的是叙事/加料层（他评/评分/经验）、handoffs 人读层、events 权威层**——这些是 kdev 的「机器给不了那一维」，MemOS 结构上不产出。

### C.2 分层集成假说：边界划得开吗 —— 🟢 划得开，但有真摩擦

**假说**：MemOS（本地档）做「员工操作记忆引擎」= 高频事件捕获 + 语义召回 + 员工隔离；kdev-memory 守「CEO/叙事 markdown + git + serverless 层」。

```
┌─────────────────────────────────────────────────────────────┐
│  kdev-memory 叙事/CEO 层（守 git/file/serverless 根 · 不动） │
│  · shared/ markdown 4 段 Step（他评/评分/经验/续航）         │
│  · 决策/踩坑/F-NNN/当前状态.md · git nested repo 同步         │
└───────────────▲─────────────────────────────────────────────┘
                │ rollup 仍 markdown 派生（不从 MemOS 取叙事）
┌───────────────┴─────────────────────────────────────────────┐
│  kdev-core 机器层（权威 · 不动）                             │
│  · features/<slug>/events.jsonl（actor 行内）· handoffs/ md  │
│  · flow-state.json                                            │
└───────────────▲─────────────────────────────────────────────┘
                │ events/handoffs 落盘点旁挂「第二消费者」
┌───────────────┴─────────────────────────────────────────────┐
│  【新】MemOS 本地档 = 员工操作记忆引擎（旁挂 · 可丢弃重建） │
│  · 自动 capture events/handoff 摘要 → SQLite(FTS5+vector)    │
│  · 员工 recall = 向量+BM25 双引擎召回（owner=scope 隔离）    │
│  · ~/.kdev/memos-local/memos.db（本机派生缓存，不进 git）    │
└──────────────────────────────────────────────────────────────┘
```

- **events/handoffs 怎么喂 MemOS**：在 kdev-core 写 events.jsonl / handoffs 的落盘点（或一个 watcher），把「actor + node + 产出摘要」喂给 MemOS local 的 capture API（`agent_end` 等价调用）。**单向：kdev-core → MemOS，MemOS 不反写权威账。**
- **agent recall 怎么从 MemOS 取**：员工 subagent 派单时（或 `before_agent_start` 等价点），调 MemOS hybrid retrieval（query=当前任务，owner=该员工 scope）→ 注入相关历史。**替掉 P-C2 recall reader 的「精确字段过滤」为「语义召回」。**
- **叙事层要不要也从 MemOS 派生**：🔴 **不要**。叙事/他评/评分是 kdev 的 markdown 加料层，MemOS 的 SQLite 摘要**不可人读、不进 git-diff、跨机要 DB 备份**——让叙事层依赖 MemOS = 砸穿 git/file 根。**叙事仍 markdown rollup（从 events，不从 MemOS）。** MemOS 只服务「机器/员工高频召回」，不服务「人读叙事」。

**边界判**：🟢 **划得开**——MemOS 占「员工操作记忆引擎（②层 P-C2 候选位）」，kdev-memory 守「①CEO/叙事 markdown+git 层」。这正对应记忆底座的两层切分。**关键纪律：MemOS 的 SQLite 必须是「本机派生缓存、可丢弃可重建、不进 git、不承载权威」**——一旦哪个权威数据只在 MemOS DB 里，就破了 git/离线根。

### C.3 冲突与代价（诚实，不淡化）

| 冲突点 | kdev 的根 | MemOS（本地档）的现实 | 严重度 |
|---|---|---|---|
| **常驻进程 + Node 运行时** | 纯 file，零常驻，hook 即用 | 要 Node≥18 + better-sqlite3 原生编译 + 插件进程 | 🟡 **中**：比 server 档轻得多，但仍引入「装机 + 运行时」，破「git clone 即带记忆、零依赖」。worktree 里能否共享同一 db？要设计 |
| **SQLite 二进制 ≠ git 友好** | markdown git-diff 可审计 | memos.db 是二进制，git 不可 diff | 🟢 **可控**：只要 db 定位为「本机派生缓存不进 git」，就不冲突——跟 hud.html、kdev-core 的 state 同性质（本机派生、可再生）|
| **跨机同步从 git 变 DB** | git clone/pull/push 天然分布式离线 | 若 db 要跨机一致 → 要 DB 备份/同步 | 🟢 **设计上回避**：db 不跨机同步——它是**本机从 events（git 同步的权威）重建的派生缓存**。换机 = 重新 capture 一遍 events（events 随 git 来）。**权威仍走 git，MemOS 只是本机加速层** |
| **verbatim 用户原话进向量库**（Q-009 §9.5 隐私） | 用户原话进团队仓要脱敏/限私有 | MemOS capture 会把会话原文 chunk 进 SQLite + embed | 🔴 **真风险**：原话进向量库 = 又一处 verbatim 副本。但**好处**：db 本机不进 git → 原话**不外泄到团队仓**（比 markdown 进 git 反而更私密）。需确认 capture 范围（能否只喂摘要不喂原文）|
| **离线/air-gapped** | 任意 worktree、离线可跑 | 本地档默认 Xenova in-process 嵌入 = **离线 OK** ✅ | 🟢 **不冲突**（本地档已证实零强制云）|
| **运维/装机负担** | 本来零依赖 file | 现在多一个「Node 插件 + SQLite + 嵌入模型权重（MiniLM ~90MB）」| 🟡 **中**：一次性装机成本，非每用。但 CI / 新克隆 / worktree 都要这套在场，否则召回降级 |
| **二阶依赖膨胀** | kdev-memory 当前 Python+hook 纯本地 | 引入 Node 生态 + transformers.js + 原生模块 | 🟡 **中**：技术栈跨语言（kdev 是 Python hook，MemOS local 是 Node），集成要跨进程/跨语言桥 |

**冲突一句话**：本地档把 Part 1 那张「server+DB+cloud 根冲突」清单**砍掉了一大半**（无 Qdrant/Neo4j/云/8GB），但**仍剩三块真摩擦**：① Node 运行时 + 原生编译（破「零依赖 file」）② SQLite 二进制（靠「定位为本机派生缓存不进 git」化解）③ 跨语言桥（Python hook ↔ Node 插件）。这三块**可工程化回避/接受**，但不是「免费午餐」。

### C.4 替换 vs 互补 vs 不用

| 选项 | 判定 | 理由 |
|---|---|---|
| **替掉半成品 P-C2 JSONL 层** | 🔴 **不该全替** | events.jsonl 是 kdev-core 权威机器账（HUD/CQO审计/resume 都依赖），MemOS 不能替；handoffs 人读 md 不能替；叙事加料层不能替。P-C2 的「三本账」结构是对的，不推翻 |
| **只补召回引擎（+捕获自动化）** | 🟢 **推荐** | MemOS 本地档**精确命中** P-C2 最弱的一环：①recall reader 从「字段精确过滤」升级到「向量+BM25 语义双引擎」，②capture 从「靠 dispatch step-recorder 人工纪律」升级到「host hook 自动拦截」。**这俩正是 kdev 当前的真短板** |
| **整体不用** | 🟡 **退路（若摩擦不可接受）** | 若团队判「Node 运行时 + 跨语言桥 + SQLite 派生层」装机/运维代价超过「语义召回」收益，则退回 Part 1 的 3 个借语义小点（AIP-160 filter / visibility 字段 / HUD 浏览），P-C2 自己用纯 Python 实现一个轻量向量召回（如 sqlite-vec + 本地 MiniLM）——**等于「自己造一个迷你 MemOS」**，省了跨语言桥但要自己维护召回质量 |

---

## P2.5 修订版 verdict

### go/no-go（先答闸）
🟢 **内网私有化自托管 = 有条件可行。**
- **条件（必须全满足）**：① 选**本地插件档**（SQLite+FTS5+vector+in-process Xenova），**禁用 server 档**（Qdrant+Neo4j+8GB 不取）；② MemOS 的 SQLite 严格定位为「**本机从 events 派生的召回缓存、不进 git、可丢弃重建**」，权威账仍 events+handoffs+markdown 走 git；③ 接受引入 **Node≥18 运行时 + 原生模块编译 + 跨语言桥**（Python hook ↔ Node 插件）作为装机成本；④ capture 范围可控（优先喂摘要而非全量 verbatim 原话，缓解 Q-009 §9.5）。
- **blocker（命中即 no-go）**：若要求「git clone 即带完整记忆、零运行时依赖、纯 file」绝对不可破 → 则 MemOS 任何档都引入运行时，**严格意义不可行**，退 P2.4 C.4「整体不用」退路（自造 sqlite-vec 迷你召回 或 Part 1 三小点）。

### MemOS 替/补 P-C2 哪几件（精确）
- 🟢 **补/替①召回引擎**：P-C2 recall reader 的「actor 字段精确过滤（纯 lexical）」→ MemOS「向量+BM25+RRF 语义双引擎召回」。**这是最大增量，正补 P-C2 没有语义召回的短板。**
- 🟢 **补②捕获自动化**：P-C2「靠 dispatch step-recorder 人工纪律 / events rollup」→ MemOS「host 生命周期 hook 自动拦截（不靠模型自觉）」。**正中『结构化自动捕获』痛点。**
- 🔴 **替不了**：events.jsonl 权威机器账、handoffs 人读 md、叙事/他评/评分/经验加料层、Step ID 时间戳化（Q-020 照做）。

### 分层集成边界（一句话）
**MemOS 本地档占「员工操作记忆引擎」层（高频 capture + 语义 recall + owner=员工隔离，SQLite 本机派生缓存不进 git）；kdev-memory 守「CEO/叙事 markdown + git + serverless」层；分界线 = MemOS 只服务机器/员工召回、绝不承载权威与人读叙事——边界划得开。**

### 修订版总判
**MemOS 比 Part 1 结论（「cloud 形态、机制不借、只印证方向」）值钱得多——因为 Part 1 漏看了本地插件档。** 它是 Apache 2.0 真开源、有 air-gapped 本地档（零强制云/零外部 DB/in-process 嵌入）、且**精确补 P-C2 两个真短板（语义召回 + 自动捕获）**。但它**不是 P-C2 的替代品而是「召回+捕获引擎的旁挂增强」**：P-C2 的三本账结构（events 权威 / handoffs 人读 / markdown 叙事）全部该守，MemOS 只在「员工高频召回」这一层旁挂。**代价诚实**：Node 运行时 + 跨语言桥 + SQLite 派生层的装机/运维负担，是「免费午餐不存在」的真成本。

### PoC 怎么验（最小验证）
1. **装机闸**：在一个 kdev worktree 里装 `@memtensor/memos-local-openclaw-plugin`（Node≥18），确认 **离线**（断网）下 Xenova 嵌入 + 规则化摘要能跑、memos.db 生成、零云调用（抓包验证）。
2. **召回质量闸**：把一批历史 events/handoffs 摘要喂进去，对比「P-C2 字段过滤召回」vs「MemOS 语义召回」在「员工醒来问『这 feature 干到哪』」场景的命中质量。
3. **隔离闸**：两个员工 scope（owner=dev / owner=reviewer）capture 后，验 recall 不串味。
4. **集成桥闸**：验「kdev-core 写 events 落盘 → 触发 MemOS capture」与「员工 subagent 派单 → 调 MemOS recall 注入」的跨进程/跨语言桥可行性（Python hook 调 Node 插件 / 或 MemOS 暴露的 MCP/HTTP 本地口）。
5. **可丢弃闸**：删 memos.db，验「从 events 重新 capture 能完整重建召回缓存」——证明它是派生缓存不是权威。
若 1+5 过 → go/no-go 的两个关键条件（air-gapped + 派生缓存）坐实；2 决定值不值得引入跨语言桥。

### Part 1 三小点是否仍是退路
✅ **仍是有效退路**——若 PoC 的「装机/跨语言桥」摩擦判为不值，Part 1 的 ① AIP-160 filter 语义给 recall reader、② visibility 字段答 Q-009 §9.5、③ HUD 记忆浏览视图，**全部独立于 MemOS、纯 file/Python、零新依赖**，是「不引入 MemOS 也能做的务实增量」。两条路不互斥：可先做三小点，PoC 验 MemOS 召回质量后再决定是否上引擎。

---

## P2.6 Part 2 来源汇总（含宣称 vs 证实）

- ✅ `github.com/MemTensor/MemOS`（Apache 2.0 / 9.9k star / v2.0.19 / 架构概念 MemCube/L1-L3/MemScheduler / Qdrant+Neo4j）
- ✅ `memos-docs.openmem.net/open_source/getting_started/rest_api_server/`（server 档：FastAPI+Qdrant+Neo4j，env 配置 `MOS_EMBEDDER_BACKEND=ollama` 本地嵌入，无 license server）
- ✅ `memos-docs.openmem.net/open_source/getting_started/installation/`（pip `MemoryOS[all]`，Neo4j 刚需，默认要 LLM API）
- ✅ `npmjs.com/package/@memtensor/memos-local-openclaw-plugin` + `github.com/MemTensor/MemOS/tree/main/apps/memos-local-openclaw`（**本地档实锤**：SQLite `~/.openclaw/memos-local/memos.db`、FTS5+vector、Xenova in-process 嵌入、规则化兜底摘要、零强制云、Node≥18+better-sqlite3、owner 隔离、before_agent_start/agent_end hook）
- ✅ `memos-docs.openmem.net/cn/openclaw/guide`（cloud 插件 recall/capture 自动拦截「不依赖模型主动记录」、agentOverrides 隔离）
- ✅ `github.com/MemTensor/MemOS-Cloud-OpenClaw-Plugin`（cloud 插件：recall before / save after）
- �amber `testingcatalog.com/memos-2-0-brings-open-source-memory-os-to-ai-agents/`（MemOS 2.0 Stardust：长期记忆/多模态/知识库，省 token 基线未给）
- ✅ arXiv 2507.03724（MemOS 论文）· arXiv 2604.07877（MemReader 主动抽取 0.6B/4B）
- �amber 省 72%（cloud OpenClaw 口径）/ 35.24%（repo 通用口径）token —— **基线均未公开，当方向印证不当精确引用**
- 内部：P-C2 spec（`docs/superpowers/specs/2026-06-13-P-C2-JSONL操作层+token优化-design.md` §2/§3/§5）· 记忆底座合稿 v1.0（`docs/framework/01-design/2026-06-10-05-...` §3/§4 两层切分）· Q-009 §9.5 隐私 / Q-019 / Q-020
