# kdev-memory CHANGELOG

## 0.5.0 — 2026-04-22

**特性**：SKILL.md 拆分为 references/ 渐进式披露（-65% 行数，-19.6% 触发
token）+ CLAUDE.md 规则段接口 / 实现解耦（`claude_md_contract` 契约化）+
`claude_md_lint.py` 自动漂移检测 + 修漂移一键 diff patch 流程 + skill-quality
eval 线（4 轮 iteration 14 runs 数据驱动）。

### 背景

0.4.0 之后发现更深层问题：**项目 CLAUDE.md 的规则段与 skill 会漂移**。
根因审计（见 `docs/skills/kdev-memory/dev-notes/2026-04-22-skill-CLAUDEmd
模板漂移审计-token-statistics与KDevSec对照.md`）指出：

- token-statistics 项目 CLAUDE.md 是 v0.2.0 时代写的 snapshot
- skill 从 v0.2 → v0.3 → v0.4.0 升级了 6 版，每版都有新内容
- 老项目 CLAUDE.md 永远停留在首次初始化时的版本 → 规则失效 → 执行失守
- 原 SKILL.md 没有"项目升级时重写 CLAUDE.md"的路径

同时 SKILL.md 本身也膨胀到 734 行，渐进式披露没有真正落地——每次 skill
被触发都要把所有场景细节拉入上下文，浪费 context 预算。

### 新增

- **SKILL.md 拆分为 6 个 references/**（Phase 1 重构）：
  - `六类记录-schema.md` / `triggers-写法.md` / `初始化-claude-md-模板.md`
  - `切档与归档.md` / `规则升级流程.md` / `自动化机制-hooks.md`
  - SKILL.md 从 734 行瘦身到 260 行（-65%）；description 从 ~1400 字精简到
    ~640 字。每次触发 skill 只拉 SKILL.md 本体，场景相关细节按需 Read
    对应 reference —— iter-2 验证：tokens 平均省 -19.6%，pass rate 100%
    vs 100% 与 0.4.0 行为等价。

- **CLAUDE.md 规则段接口 / 实现解耦**：
  - `references/初始化-claude-md-模板.md` 顶部加 YAML frontmatter
    `claude_md_contract` —— 显式声明 skill 对外的稳定接口：
    - `cross_session_rules`：3 条贯穿 session 铁规（实时落盘 / 文件聚合
      不翻会话 / 优先处理 hook 产出）
    - `hook_injection_tags`：`<kdev-memory-brief>` / `<kdev-memory-recall>`
    - `hook_file_patterns`：`.kdev/memory/WARN-未记录-*.md` /
      `.kdev/memory/checkpoints/压缩前-*.md`
  - CLAUDE.md 规则段**只放接口**，删掉 17 行触发表 / 评分机制 / 编号规则 /
    hook 行为响应表——这些都是 skill 实现细节，随版本演进会变，留 SKILL.md
    本体。
  - iter-3 验证：eval-0 init 场景 CLAUDE.md 从 57 行精简到 38 行（-33%），
    边缘场景（eval-4 合并冲突 / eval-5 数据缺失 / eval-7 WARN 处理）全部
    0 regression。

- **`hooks/lib/claude_md_lint.py`** 接口漂移检测工具：
  - 读 skill 的 `claude_md_contract` + 项目 `CLAUDE.md` 规则段，字面子串
    匹配 + 关键词宽松命中，识别缺少的 hook 标签 / 文件模式 / 贯穿铁规
  - 5 种状态：`ok` / `drift` / `no-claude-md` / `no-kdev-section` /
    `contract-parse-error`
  - 纯 Python 无外部依赖，CLI + 库双用途
  - 21 个单元测试（tests/test_claude_md_lint.py），项目累计 65 tests pass

- **SessionStart hook 集成 lint**：
  - 每次新会话自动比对，漂移时在 `<kdev-memory-brief>` 的 ⚠️ 待处理段
    里列出缺什么 + 提示用户召唤 skill 说「修 CLAUDE.md 漂移」
  - 失败静默降级（contract 解析错 / lint 库缺失都不影响其他 brief 内容）

- **`references/初始化-claude-md-模板.md` 加「修漂移」流程章节**：
  - 6 步动作路径：读 contract → 读 CLAUDE.md → 逐项比对生成最小化 diff
    → 展示给用户 → 用户批准后 Edit → lint 复验 `status=ok`
  - 4 条铁规：只管辖 kdev 章节 / 用户手改保留 / 展示+批准+执行分离 /
    降级安全
  - SKILL.md description 加召唤触发词"修 CLAUDE.md 漂移 / 接口漂移 /
    claude.md 对齐 skill / claude.md 升级"

- **skill-quality eval 线**（evals/skill-quality/）：
  - skill-creator 风格的完整 eval 基础设施：8 场景 fixture（init /
    daily-summary / rule-upgrade / archive / merge-conflict / missing-data /
    cross-session-resume / warn-file）+ contract 接口变更专测
    eval-8-claude-md-drift
  - 4 轮 iteration 数据：
    - iter-1 首轮 3 场景探索（基础 assertions）
    - iter-2 扩展 6 场景（升级 assertions + 12 runs，验证 Phase 1 重构）
    - iter-3 解耦 4 场景（8 runs，CLAUDE.md 57→38 行且零 regression）
    - iter-4 lint 落地 1 场景（2 runs，with_skill 100% vs baseline 75%）

### 向后兼容

- **0.4.x 老项目 CLAUDE.md 零改动继续工作**：lint 只是 ⚠️ 提示，不阻塞
  任何动作；缺少新接口条目时 hook 不会阻断，只是用户看不到新功能的完整
  体验
- `claude_md_contract` 遵循 append-only 原则：新增 hook 标签 OK，改名或废弃
  要走 deprecation 周期
- 所有现有 hook / triggers / `.kdev/memory/` 结构 / 编号体系（Q-NNN /
  G-NNN / R-NNN / Step N）完全不变
- 项目内用户自定义加入规则段的内容（如第 4 条贯穿铁规）**受保护**，修漂移
  流程只加不删用户手写的行

### 设计决策

- **为什么是"解耦 + lint"而不是审计原方案（版本号标记 + 一键重写）**：
  - 版本号标记需要用户理解语义化版本 + 需要"迁移脚本"思路 → 每次升级都是
    风险点
  - `claude_md_contract` 让"什么是接口"成为机器可读声明 → lint 自动比对
    → diff 自动生成 → 用户只审 3 行 patch 而不是审整段合并
  - 用户手改保护天然成立：lint 只管辖 contract 里声明的字段，其他行不碰
- **为什么 SKILL.md 本体里保留 3 条贯穿铁规**：这些需要 Claude 每一步都
  下意识遵守（实时落盘 / 不翻会话 / hook 产出响应），不能依赖"被召唤"才
  触发。其他场景（初始化 / 切档 / 升级）都是用户主动发起 → 被动召唤就够
- **为什么不在 plugin 升级时自动硬改 CLAUDE.md**：硬改有三个风险——覆盖
  用户自定义、合并策略复杂、失败难恢复。改为"hook 只检测 + skill 召唤
  时执行 + 用户批准"三步分离，每一步单一职责
- **为什么 baseline 6/8 pass 也是可接受结果**：iter-4 对照显示 iter-3
  解耦架构本身就 self-documenting——baseline 通过 `claude_md_contract` +
  合并策略能正确推理出行为（识别漂移 + 暂停等用户裁决）。新版的增量是
  把多轮裁决压到单步闭环，不是"修复 baseline 的错误"

### 相关文档

- 审计文档：`docs/skills/kdev-memory/dev-notes/2026-04-22-skill-CLAUDEmd
  模板漂移审计-token-statistics与KDevSec对照.md`
- session 对账：`docs/skills/kdev-memory/dev-notes/2026-04-22-审计修订
  对账-session-end-state.md`
- iter-3 解耦 notes：`plugins/kdev-memory/evals/skill-quality/iterations/
  20260422-03-decoupled-claude-md/notes.md`
- iter-4 lint notes：`plugins/kdev-memory/evals/skill-quality/iterations/
  20260422-04-claude-md-lint/notes.md`

---

## 0.4.0 — 2026-04-21

**特性**：长项目的按期归档机制（执行日志按月、踩坑/决策按季度）+ 单元测试层
（44 个 stdlib unittest，覆盖 trigger-match.py 的 7 类核心逻辑）+ README 差异
化定位（与 Claude 官方 auto memory / claude-remember 等方案的关系说明）。

### 背景

0.3.0 引入 triggers 智能召回后，`.kdev/memory/` 主文件会随项目推进线性膨胀。
半年下来执行日志 1000+ 行、踩坑日志 几十条 G-NNN，Claude Read 效率下降、
UserPromptSubmit hook 全文扫描性能也吃力。SKILL.md 原本有"超 500 行按迭代切
档"的人工建议，但无自动化提醒、无归档约定、无配套扫描支持。

同时 Anthropic marketplace 上出现同类记忆方案（如 claude-remember），用户需要
判断"什么时候装哪个 / 会不会重复造轮子"——README 需要给出差异化定位。

### 新增

- **`.kdev/memory/归档/` 子目录约定**：
  - `执行日志.md` 按月切到 `归档/执行日志-YYYY-MM.md`
  - `踩坑日志.md` 按季度切到 `归档/踩坑日志-YYYYQN.md`
  - `决策日志.md` 按季度切到 `归档/决策日志-YYYYQN.md`
  - `改进建议.md` **不切档**——它是喂给未来 skill 作者的原料库，完整性优先
- **`hooks/lib/archive-hint.sh`**：新建共享库，日期→季度换算 + 跨期检测。
  用最早条目日期而非行数阈值判断，避免"拍脑袋定多少行"。
- **Stop hook 第 6 条软提醒**：主文件最早条目不在当月（执行日志）或当季（踩
  坑/决策日志）时注入 📦 归档提醒文本，指向 `归档/` 子目录下的目标文件名。
- **trigger-match.py 的 `_iter_memory_files()` 辅助**：所有归档扫描统一走
  "主文件 + `归档/` 子目录"两路。踩坑日志归档后**仍参与召回**（老坑也要防重
  踩），执行日志归档后被今日/昨日过滤剔除，实际等效只扫主文件。
- **`tests/test_trigger_match.py`**：44 个 stdlib unittest（零外部依赖），覆盖
  SanitizePrompt / ParseTriggersValue / ParseMultilineTriggers / MatchEntries /
  DedupFilter / TTLPrune / GlobScan。包含"归档目录隔离"测试——防止
  glob 误把同目录下其他前缀的归档文件（如 `执行日志-2026-03.md`）混入
  踩坑扫描结果。
- **SKILL.md §「文件切档与归档」**：整章新增，含切档规则一览 / 何时提醒 /
  操作步骤 / 铁规（搬家而非删除、编号保留、主文件顶部留"历史归档"索引）/
  召回逻辑变化说明。SKILL description frontmatter 加"切档 / 归档一下 / 归档
  执行日志"触发词，让 Claude 能在用户说切档时自动召唤本 skill。
- **`plugins/kdev-memory/README.md` §「这个插件和其他记忆方案的关系」**：顶
  层章节，讲清楚三类记忆工具（官方 auto memory / 会话压缩类 / 本插件）正交
  不重叠、五大差异化设计点、推荐同装。未点名任何第三方插件避免维护负担。
- **`docs/design-notes/2026-04-21-三方记忆方案对比-官方auto-memory-vs-claude-remember-vs-kdev-memory.md`**：
  三方机制对比、互补性矩阵、借鉴项决策的设计文档。

### 向后兼容

- 0.3.x 项目升级到 0.4.0 **零改动即可运行**：没有 `归档/` 子目录时，glob
  扫描退化为单主文件，行为完全一致。
- 归档是**人工触发 + Claude 提醒**，不自动执行——收到 📦 提醒后必须询问用
  户同意才能切档，避免误迁老数据。
- 现有 triggers 条目、编号体系（G-NNN / Step N / Q-NNN / R-NNN）跨档保持不
  变，切档只是"搬家"不改结构。

### 设计决策

- **为什么按月/按季度而不是统一按季度**：执行日志粒度最细（每步一条）、膨
  胀最快，按月切合理；踩坑/决策是慢积累，按月会造成过多小碎片，按季度刚好。
- **为什么改进建议不切档**：消费者不是当前项目而是未来 skill 作者——跨项目
  review 需要看全集，切档会损害聚类归纳的质量。
- **为什么不用 Haiku 做压缩归档**（借鉴了 claude-remember 但没照抄）：
  - 会违背 kdev-memory 的"零外部 API 成本"卖点
  - Haiku 压缩会丢失 R-NNN 的"用户原话 / 事实段 / 评分差值"——这些恰恰
    是下游 skill 作者最需要的原始证据
  - 切档比压缩简单、可逆、无信息损失，是更合适的工具
- **为什么归档放子目录不平铺**：几年后顶层会被几十个归档文件淹没，子目录让
  `ls .kdev/memory/` 的输出始终整洁，glob 扫描也更精确。

### 自验证

- 44 个 unit tests 全通过（`python3 -m unittest discover tests`）
- 端到端：构造主文件 + `归档/` 子目录的 fixture，UserPromptSubmit hook 正确
  从归档文件召回老 G-NNN 条目，注入路径显示 `.kdev/memory/归档/踩坑日志-2026Q1.md`
- Stop hook 跨期场景输出 📦 提醒，格式和路径（`归档/执行日志-YYYY-MM.md`）
  正确；无跨期数据时静默不误报

### 文档同步

- `plugins/kdev-memory/README.md` 顶层差异化卖点 + 目录结构加归档子目录
- `plugins/kdev-memory/skills/kdev-memory/SKILL.md` 切档章节 + 触发规则段 📦 + description 加触发词
- `plugins/kdev-memory/hooks/hooks.json` description 补归档提醒/两路扫描
- `plugins/kdev-memory/.claude-plugin/plugin.json` description 补归档切档；keywords 加 archive
- `plugins/kdev-memory/evals/README.md` 加"纯单元测试"章节指向 tests/
- `README.md`（仓库根）六层 → 七层（0.3.0 历史遗漏顺手修）+ 目录示例补 tests/ 和 evals/

### 文档后续完善（post-release，纯文档无代码变化）

- `SKILL.md` 新增「**规则升级流程**」章节：定义"R-NNN 同主题 ≥ 2 次 / 方法
  论铁规被引用 ≥ 3 次 / 用户明确表达"三类升级触发信号；规定 Claude 必须问
  用户三件事（升不升级 / 放哪 / 加不加 triggers）、严禁替用户拍板；定义升级
  搬家规则——**标记而非删除**，源 R-NNN 原文一字不改，只在末尾加
  `> 升级状态：YYYY-MM-DD 升级到 xxx` 标记，改进建议.md 作为"下游 skill
  作者的原料库"完整性不被"已升级"破坏；和「文件切档与归档」正交（切档按
  时间搬家、升级按重要性搬家）
- SKILL description frontmatter 加升级触发词（"这条以后都要遵守 / 加到项目
  规则 / 写进宪章 / 变成硬规矩 / 升级成铁规"），让 Claude 能在用户这么说时
  自动召唤 skill
- 触发规则段模板加一条 🔴 铁规 + 表格一行，把升级流程同步给每个新项目的
  CLAUDE.md
- 「方法论铁规.md」章节补一段"和项目级宪章的关系"，明确铁规.md（只给 AI 看）
  vs 项目根 `constitution.md/AGENTS.md`（对外宣称、人类也读）的分层语义

---

## 0.3.1 — 2026-04-21

**增强**：跨天会话场景的每日汇总兜底提醒。

### 背景

Claude Code 的 hook 体系是事件驱动（SessionEnd / Stop / PostToolUse / ...），
没有"日期变更"事件。晚上 23:55 干到次日 01:30 不关会话的真实场景下：
SessionEnd 不触发 → 昨天的每日汇总被静默遗漏 → 第二天新会话开局 Claude
也不知道有缺口。0.3.0 的 Stop hook "今天无汇总"规则只看今日，无法覆盖
这个 gap。

### 新增

- **`hooks/lib/missing-summaries.sh`**：共享库函数
  `list_missing_past_summaries()`。扫 `.kdev/memory/{执行日志,决策日志,
  踩坑日志,改进建议}.md` 里所有 `日期：YYYY-MM-DD` 行，返回"严格早于今日
  且 `每日汇总/<date>.md` 缺失"的日期（最近 5 个，升序）。
- **Stop hook 第 5 条软提醒**：发现过去日期缺汇总时注入提醒文本，显式说明
  "典型原因是跨天会话未关"，指引 Claude 按日聚合源文件而不是回翻会话。
- **SessionStart hook `<kdev-memory-brief>` ⚠️ 待处理段**：startup / resume /
  compact 三种模式都会把缺失的过去汇总日期列出。这样即便用户忽略了 Stop
  的提醒、新开会话时还能再看到一次。
- **SKILL.md § "三层触发方式"**：Stop hook 描述从"三条提醒"扩到"四条提
  醒"，明确说明跨天会话场景。

### 设计原则

- 软提醒、不阻塞：跨天遗漏一天不写汇总没到 strict 模式 `exit 2` 的严重
  级别。strict 仍只管"今天执行日志空 + 工作区有变更"。
- 不回翻会话：提醒文本显式禁止 Claude 凭印象补写，要求按日期从源文件聚合；
  若某日源文件信息不足，在汇总里坦白标注。
- 最近 5 条封顶：防止老项目启用 kdev-memory 时刷屏。

### 自验证

- 10/10 evals 通过（`run-hook-selftest.sh`），未破坏既有召回机制
- 端到端 fixture 测试：2 个缺失日期在 Stop 和 SessionStart 都正确浮现

---

## 0.3.0 — 2026-04-20

从 0.2.0 的"六层防线"升级到 **"七层防线 + 目录命名空间化 + 智能召回"**。
核心目标：把记忆从"档案馆"升级为"会主动浮现"的闭环系统——已经踩过
的坑不再重复，做过的决策能自然复用。

### 新增

- **UserPromptSubmit hook**（`hooks/user-prompt-trigger.sh` +
  `hooks/lib/trigger-match.py`）：用户每次发 prompt 时扫
  `.kdev/memory/` 里所有带 `triggers:` 的条目做 literal substring
  匹配，命中就注入 `<kdev-memory-recall>` 指针给 Claude。**渐进式
  披露**——只给编号+标题+路径，不塞全文，让 Claude 自己决定是否
  Read 细节。
  - 扫描 4 个数据源：G-NNN 全部 / Step 今日-昨日 / 方法论铁规 全部 /
    项目级 spec 7 个约定路径
  - Prompt sanitize：strip 代码块 / XML tag / URL / 文件路径 /
    git diff（避免字面量误触发）
  - Session 去重：`.kdev/memory/state/trigger-sessions.json`，
    60 分钟 TTL，每 session 限额 3 条（借 OMC 经验 + 避开 issue #240
    的同类坑）
  - 借 OMC (oh-my-claudecode) 的成熟做法设计：literal 子串匹配、
    toLowerCase、文件落盘去重；但放弃 OMC 直接塞全文的做法，改用
    渐进式披露
- **triggers 字段写法规范**（SKILL.md §8 新增章节）：
  明确 G-NNN / Step / 铁规 / spec 四类条目的 triggers 标注方式、
  三种合法格式（JSON 数组 / 逗号分隔 / YAML 多行）、关键词选择原则
  （3-5 个、中英文、口语词、场景+特征）
- **项目级 spec 约定路径扫描**：`constitution.md` / `spec.md` /
  `principles.md` / `AGENTS.md` / `.specify/constitution.md` /
  `docs/constitution.md` / `docs/principles.md`——存在即扫，支持
  文件级 frontmatter 或行内 `## 规则 + triggers` 两种格式

### 变更（破坏性 → 零感知迁移）

- **`.kdev/` 重构成插件命名空间容器**：所有 kdev-memory 产物从
  `.kdev/` 根目录平铺迁到 `.kdev/memory/` 子目录。未来其他 kdev
  插件（kdev-commit、kdev-triggers 等）可以建兄弟子目录互不干扰。
- **自动迁移**（`hooks/lib/migrate.sh`）：所有 hook 启动时调
  `kdev_memory_migrate`，检测 0.2.0 平铺结构自动搬家到
  `.kdev/memory/` 子目录，留 `.kdev/MIGRATED-YYYY-MM-DD.md`
  清单给用户看。**从 0.2.0 升级完全无感**——第一次打开项目
  就自动完成，用户不用手工做任何事。
- 所有 hook 脚本 `KDEV_DIR` 从 `.kdev` 改到 `.kdev/memory`；软提
  醒文本里的路径同步更新到 `.kdev/memory/*`
- `hooks/lib/milestone.sh` / `hooks/lib/frontmatter.sh` 兼容新旧
  两种路径（优先新路径，fallback 老路径）
- SKILL.md 目录结构图重绘；描述增加 triggers / 召回相关触发词
- README.md Hook 章节从"六层防线"改写为"七层防线"，加"命名
  空间约定"和"UserPromptSubmit 智能召回"两个新章节

### SKILL.md 里新增的触发规则段铁规（CLAUDE.md 贴段）

- 🔴 每写一条新 G-NNN / Step / 铁规，紧跟标题下一行加
  `triggers: [...]` 关键词列表（3-5 个用户会说的词，中英文都要）
- 🔴 看到 `<kdev-memory-recall>` 注入时先判断相关性，字面子串
  匹配有假阳性；相关再 Read，不相关忽略，不要为了"用起来"强行
  靠拢

### 兼容性

- 0.2.0 → 0.3.0 完全向后兼容（自动迁移 + 双轨 fallback）
- 没标 `triggers:` 的条目不影响现有功能，只是不会被自动召回
  （退回到 0.2.0 的"档案馆"体验）
- 缺 python3 → UserPromptSubmit 静默降级（其他 6 层 hook 继续工作）

---

## 0.2.0 — 2026-04-19

由一份用户反馈驱动的重大升级：Spec Kit 等长流程跑完后会话自然 idle，Stop hook
的 stdout 软提醒永远没有下一轮上下文可以被读到，导致 `.kdev/执行日志.md` 全天空白。
本版本从**六层防线**角度补齐这个缝隙，并引入**状态结构化（YAML frontmatter）**让脚本
和 Claude 都能结构化读写当前项目状态。

### 六层防线（按会话时序）

1. **SessionStart hook** —— 开局注入 `<kdev-memory-brief>` 摘要（WARN / checkpoint / 今日进度 / frontmatter 状态 / 最近 Step+Q+G）
2. **Stop hook** —— 软提醒（今天无汇总 / 汇总过时 / 执行日志今天空）
3. **Strict 模式（opt-in）** —— `touch .kdev/strict` 启用条件阻塞
4. **PostToolUse hook** —— 命中里程碑白名单时提醒追加 Step
5. **PreCompact hook** —— 压缩前写 `.kdev/checkpoints/压缩前-TS.md` 快照（7 天 retention）
6. **SessionEnd hook** —— 会话真正结束时写 `.kdev/WARN-未记录-*.md` 兜底警告

### 新增

- **Strict 模式（opt-in）**：项目根 `touch .kdev/strict` 后启用。执行日志今天空 +
  工作区实质变更 ≥ 2 个文件（或命中里程碑白名单）→ Stop hook `exit 2` 阻塞，
  Claude 必须先落盘才能结束会话。带 `stop_hook_active` 保护避免无限循环。
  `rm .kdev/strict` 即可关闭。
- **PostToolUse hook**（`hooks/post-write-check.sh`）：Claude 用
  `Write/Edit/MultiEdit/NotebookEdit` 命中里程碑白名单时立刻注入软提醒。
  日常源码编辑不打扰。
- **SessionEnd hook**（`hooks/session-end-check.sh`）：会话真正结束时，若执行
  日志今天空 + 工作区有变更 → 写 `.kdev/WARN-未记录-YYYY-MM-DD.md` 兜底警告
  文件，列出变更快照。下次进入项目时 CLAUDE.md 触发规则段会让 Claude 看到并
  提醒补记。
- **SessionStart hook**（`hooks/session-start-brief.sh`）：新会话启动时，通过
  `hookSpecificOutput.additionalContext` 注入 `<kdev-memory-brief>` 摘要。
  按 `source` 字段分档：`startup`/`clear` 完整摘要（待处理 WARN/checkpoint +
  今日进度 + 状态字段 + 最近条目）；`resume` 精简；`compact` 只提醒 checkpoint
  在哪。Claude 开局即知项目全景，不用等用户提"先看下昨天做到哪了"。
- **PreCompact hook**（`hooks/pre-compact-check.sh`）：会话被压缩前（auto 或
  `/compact` 手动触发）写一个 `.kdev/checkpoints/压缩前-YYYY-MM-DD-HHMMSS.md`
  快照——内含今天 `.kdev/` 核心文件原文复制 + 工作区 `git status -uall`。
  压缩后 Claude 即便丢失上下文也能 Read 此文件回读细节。7 天后自动清理
  （`hooks/lib/checkpoint.sh` 的 retention 逻辑）。
- **`.kdev/当前状态.md` YAML frontmatter schema**：状态文件引入结构化字段
  （`phase` / `iteration` / `current_step` / `last_updated` / `pending_decisions` /
  `unresolved_gotchas`），body 保留自由文本。SessionStart hook 直接读 frontmatter
  秒报项目状态给 Claude，不再靠 fuzzy 解析自由文本。实现：`hooks/lib/frontmatter.sh`
  提供 `read_state_field` / `has_state_frontmatter`（python3 优先，bash fallback）。
  兼容旧仓库：没 frontmatter 也能工作。
- **stdin hang 保护**：已有三个 hook（stop/session-end/post-write）的 stdin 读取
  加 `timeout 1` 超时，避免 Claude Code 管道未 EOF 时永久 hang（参考 OMC issue #240
  同类问题）。
- **里程碑白名单统一维护**（`hooks/lib/milestone.sh`）：单一真相源，stop-check
  与 post-write-check 共同 source。覆盖：
  - Spec Kit：`specs/**/*.md`、`specs/**/contracts/*.{yml,yaml}`
  - 迭代 / Sprint：`docs/iterations/**`、`docs/sprints/**`、`docs/sprint-*.md`、`docs/迭代*`
  - ADR / 决策：`docs/adr/**`、`docs/decisions/**`、`adr/*.md`、`adrs/*.md`
  - 架构 / 设计 / PRD / 需求：`docs/architecture/**`、`docs/design/**`、`docs/设计*`、
    `docs/prd/**`、`docs/PRD*`、`docs/requirements/**`、`docs/需求*`
  - 根目录关键文档：`ARCHITECTURE.md`、`ROADMAP.md`、`MIGRATION.md`、
    `CHANGELOG.md`、`DECISIONS.md`
  - 数据库 migration：`migrations/**`、`db/migrate/**`、`db/migrations/**`、
    `prisma/migrations/**`、`supabase/migrations/**`、`alembic/versions/*.py`
  - API / 协议契约：`openapi.{yml,yaml,json}`、`api/openapi.*`、
    `schema.graphql`、`*.proto`、`proto/**`
  - 工程记忆自己的硬规：`.kdev/方法论铁规.md`
- **SKILL.md 触发规则段**：新增"进入项目先处理 `.kdev/WARN-未记录-*.md`"条目，
  促使 Claude 不跳过上次会话留下的兜底警告。

### 变更

- Stop hook 计数逻辑：`.kdev/` 内部自维护文件（除 `方法论铁规.md`）不计入
  "实质变更"，避免 `touch .kdev/strict` 本身触发阻塞。
- README 重写 Hook 章节，分四层防线叙述（Stop 软提醒 / Strict 阻塞 /
  PostToolUse 联动 / SessionEnd 兜底），加入验证方式和新会话自检 prompt。
- SKILL.md 的 Hook 章节从"外部 `settings.json` 样板"改为"插件自带三层" 描述，
  并说明三层缺一不可的原因。

### 兼容性

- 0.1.x 行为保持不变（Stop 软提醒的四种状态检查原样保留）。
- 新增 hook 默认行为都是"静默或软提醒"，不会影响现有用户；Strict 阻塞必须
  用户主动 `touch .kdev/strict` 才启用。

---

## 0.1.1 — 2026-04-16

- Stop hook 新增 `汇总过时` 检测：每日汇总生成后若源文件（执行/决策/踩坑/改进）
  又有更新，提醒 Claude 追加到汇总而不是覆盖。
- 去掉 Stop hook 冗余的 `matcher: "*"` 字段。

## 0.1.0 — 2026-04-16

- 首次发布工程记忆制度插件：`.kdev/` 目录结构 + SKILL.md + Stop hook
  四态软提醒（无 `.kdev/` / 无汇总 / 执行日志空 / 汇总过时）。
