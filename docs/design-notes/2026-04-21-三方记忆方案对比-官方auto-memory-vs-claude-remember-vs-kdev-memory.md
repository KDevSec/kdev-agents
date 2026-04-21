# 三方记忆方案对比：官方 auto memory vs claude-remember vs kdev-memory

> 日期：2026-04-21
> 背景：延续 [2026-04-19 跨会话记忆与压缩保护方案对比](2026-04-19-跨会话记忆与压缩保护-方案对比.md)，这次把对比收敛到当下值得对标的三家：
> 1. **Claude Code 官方 auto memory**（内置于 system prompt 的 `# auto memory` 段）
> 2. **Digital-Process-Tools/claude-remember**（GitHub 开源、1600+ 装机、Anthropic marketplace 上架）
> 3. **kdev-memory**（本仓库 0.3.0）
>
> 目的：
> - 沉淀清晰的产品定位（三者正交而非替代）
> - 识别可借鉴的机制，为 0.4.0 / 0.5.0 路线图提供决策依据

---

## 一、各自的核心信息

### 1.1 Claude Code 官方 auto memory

- **位置**：`~/.claude/projects/<project-hash>/memory/`（用户机本地，不进项目仓库）
- **结构**：`MEMORY.md` 作为索引 + 每条记忆一个独立 `.md`（带 frontmatter：name/description/type）
- **四类记忆**：
  - `user` —— 用户画像（角色、偏好、知识背景）
  - `feedback` —— 用户对协作方式的纠偏或肯定（带 Why / How to apply）
  - `project` —— 项目非代码可推导信息（决策动机、截止日、干系人）
  - `reference` —— 外部系统指针（Linear、Grafana 等）
- **触发**：Claude 在推理过程中"觉得该记"就写，用户显式要求"remember/forget"立即执行
- **注入**：`MEMORY.md` 随 system context 自动加载（前 200 行）
- **反模式明令禁止**：代码模式、路径结构、git history、调试 fix、临时任务状态——"能从现场读出来的不写"
- **生命周期**：长期跨项目、按主题组织、可淘汰但不按日期滚动

### 1.2 Digital-Process-Tools/claude-remember

- **GitHub**：https://github.com/Digital-Process-Tools/claude-remember
- **装机量**：Anthropic marketplace 1600+，自己也维护 `dpt-plugins` marketplace
- **测试**：186 tests / 99%+ 覆盖（v0.5.0）
- **位置**：`.remember/`（项目内，**自动 gitignore**，本机私有）
- **核心管道**（README 流程图）：

  ```
  tool use → save-session.sh → extract (Python)
           → summarize (Haiku) → now.md
           → hourly NDC compression → today-YYYY-MM-DD.md
           → daily consolidation → recent.md + archive.md
  ```

- **信息源**：**会话 JSONL raw exchanges**（不是 Claude 自己写的）
- **压缩者**：**Claude Haiku 子调用**（异步 pipeline）
- **注入策略**：SessionStart hook **全量注入** `identity.md + remember.md + now.md + today-*.md + recent.md + archive.md`
- **三个 hook**：
  - `SessionStart` —— 加载记忆到 context、恢复遗漏会话
  - `UserPromptSubmit` —— 注入当前时间戳
  - `PostToolUse` —— tool call delta 超阈值自动保存
- **手动 handoff**：`/remember` 斜杠命令 → 写 `remember.md`（自由文本）
- **配置面**：`config.json`（`cooldowns.save_seconds=120` / `cooldowns.ndc_seconds=3600` / `delta_lines_trigger=50` / `timezone`）
- **成本**：一天几美分 Haiku 费用
- **硬依赖**：**必须关闭 Auto-compact**（`/config`），否则 JSONL 被官方压缩吃掉

### 1.3 kdev-memory（本仓库 0.3.0）

- **位置**：`.kdev/memory/`（项目内，**期望 commit 跟代码走**）
- **结构化档案**：
  - `当前状态.md`（带 YAML frontmatter：phase/iteration/current_step/pending_decisions/unresolved_gotchas）
  - `决策日志.md`（Q-NNN）
  - `踩坑日志.md`（G-NNN，带 triggers）
  - `执行日志.md`（Step N + **双评分**）
  - `每日汇总/YYYY-MM-DD.md`
  - `改进建议.md`（R-NNN，喂给未来 skill 作者的原料库）
  - `方法论铁规.md`（可选）
- **信息源**：**Claude 推理中主动写结构化条目**（不是从 JSONL 抽取）
- **召回策略**：**triggers 字面子串匹配 + 渐进式披露**（只给编号/标题/路径，Claude 按需 Read）
- **六个 hook**：SessionStart / Stop / PostToolUse / SessionEnd / PreCompact / UserPromptSubmit
- **strict 模式**：`touch .kdev/memory/strict` 开启 → Stop hook 可 `exit 2` 阻塞 Claude 罢工
- **双评分机制**：模型自评（含强制扣分项，防讨好式满分）+ 用户评分（时间戳锁定防污染）+ 差值 ≥2 → R-NNN
- **成本**：零外部 API 调用（Claude 自己落盘）
- **硬依赖**：Claude 本身的"实时落盘"纪律

---

## 二、机制层面逐项对比

| 维度 | 官方 auto memory | claude-remember | kdev-memory |
|---|---|---|---|
| **信息源** | Claude 推理中"觉得该记" | **会话 JSONL raw**（自动采集） | Claude 推理中**主动写结构化条目** |
| **压缩者** | 无压缩（每条独立文件） | **Haiku 子调用异步压缩** | 无压缩（Claude 用规范 schema 写） |
| **额外 API 成本** | 否 | **是**（一天几美分 Haiku） | 否 |
| **注入策略** | `MEMORY.md` 索引前 200 行 | **全量注入** 6 个文件 | **按需召回**（triggers → 指针 → 按需 Read） |
| **时间 vs 类型组织** | 按类型（user/feedback/project/reference） | **按时间滚动**（now→today→recent→archive） | **按类型累积**（Q/G/Step/R 永不滚动） |
| **硬依赖** | 无 | **必须关 Auto-compact** | 无（实时落盘不依赖会话历史） |
| **存储位置** | 用户机全局 | 项目内 gitignore（本机私有） | 项目内 commit（跟代码走） |
| **hook 数量** | 0（内置） | 3（SessionStart/UserPromptSubmit/PostToolUse） | 6（加 Stop/SessionEnd/PreCompact） |
| **强制性** | 完全软性 | 完全软性 | 可开 strict（exit 2 阻塞）+ WARN 兜底 |
| **用户评分** | 无 | 无 | 有（双评分 + 时间戳锁定） |
| **跨项目共享** | 是（用户机全局） | 否（项目私有） | 否（跟项目仓库走） |
| **成熟度** | 内置稳定 | 1600+ 装机、186 tests 99% 覆盖 | 新生 0.3.0、evals 基础设施刚落地 |

---

## 三、哲学分水岭

三者解决的**不是同一个问题**——放一起看才清楚各自定位：

### 3.1 claude-remember = "会话录像机 + 自动剪辑"

- Claude 是**无意识的参与者**——它不用知道自己在被记录
- 信任 AI 压缩：Haiku 会从 JSONL 里提炼出"这次会话干了啥"
- 下游消费者：**下一次会话的 Claude 自己**（注入后能秒续）
- 典型价值场景："昨天调了半天的 bug，今天新会话一开 Claude 就知道上次栽在哪里"

### 3.2 kdev-memory = "工程日志 + 评审制度"

- Claude 是**有意识的作者**——必须显式写 Step / 标 triggers / 接用户评分
- 不信任 AI 事后压缩：**原始信号 > 摘要**（因为摘要会丢"模型觉得顺、用户觉得难受"那种张力）
- 下游消费者：**项目 + 人类审计员 + 未来的 skill 作者**
- 典型价值场景："三个月后回看项目发现 R-001/R-005/R-012 都是'字段对齐脱钩' → 提炼成新 skill"

### 3.3 官方 auto memory = "个人化画像"

- 记的是"用户是谁、偏好什么"，不是"项目发生了啥"
- 下游消费者：**Claude 在所有项目里的默认行为调整**
- 典型价值场景："不用每次告诉 Claude 别在 commit 里加 Co-Authored-By"

---

## 四、互补性矩阵（三者可以同时跑）

三者写不同目录、消费不同数据源：

```
~/.claude/projects/<hash>/memory/   ← 官方 auto memory（用户画像，跨项目）
.remember/                          ← claude-remember（会话流压缩，本机私有）
.kdev/memory/                       ← kdev-memory（工程结构化档案，跟代码 commit）
```

**典型组合使用**：

| 场景 | 官方 auto memory 记 | claude-remember 记 | kdev-memory 记 |
|---|---|---|---|
| 用户偏好 | `ly 不要 Co-Authored-By trailer` | — | — |
| 今天干的活 | — | 压缩版会话回放（今天调 pnpm 花 2 小时） | Step 7 + 执行事实 + 双评分 |
| 踩过的坑 | — | 被压缩进摘要（细节丢失） | **G-012**（带 triggers，下次命中即召回） |
| 决策取舍 | — | 可能进压缩摘要 | **Q-007**（选项、用户选择、理由完整保留） |
| 评分盲区 | — | 无评分概念 | **R-003**（用户原话 + 事实 + 评分差值） |

---

## 五、各自的脆弱点与成熟度差距

### 5.1 claude-remember 脆弱点

1. **硬依赖 Auto-compact 关闭**——README 第 4 条 setup 专门强调，不关就丢数据（官方自动压缩会吞 JSONL）
2. **压缩质量完全靠 Haiku**——如果 Haiku 把 PRD 字段名压错了，下次会话学到错版本无法纠正
3. **全量注入随时间线性膨胀**——archive.md 会越积越大（靠 consolidate 压但始终在增长）
4. **无评分/无人类审计**——压缩摘要里用户是否抱怨过、评分几分，都没了

### 5.2 kdev-memory 脆弱点

1. **硬依赖 Claude 的落盘纪律**——如果 Claude 偷懒不写 Step，Stop hook 只能软提醒（strict 模式能阻塞但覆盖面窄）
2. **triggers 标注质量决定召回率**——Claude 标的 triggers 用词偏书面语（`workspace 依赖`），用户日常可能说"我子包装不上依赖"，匹配不上就不召回
3. **执行日志长期膨胀**——1000+ 行后性能和可读性都下降（目前靠"超 500 行分档"的人工建议）
4. **测试覆盖低**——evals 基础设施刚落地（2815b67），hook 脚本逻辑还没做单元测试

### 5.3 成熟度差距

| 维度 | claude-remember | kdev-memory |
|---|---|---|
| 版本 | v0.5.0 | v0.3.0 |
| 装机量 | 1600+ | 本地使用 |
| marketplace | 双渠道（Anthropic + 自己的 dpt-plugins） | 未上架 |
| 测试 | 186 tests / 99% 覆盖 | evals 基础设施落地，hook 脚本单测缺 |
| 文档成熟度 | README 含 Mermaid 架构图 + 配置表 + 已知 issue 引用 | SKILL.md 详细但偏内部视角 |

---

## 六、可借鉴项（为路线图铺垫）

从 claude-remember 学到两件值得抄作业的事：

### 6.1 借鉴 A：Haiku 异步压缩管道（用于季度归档）

**问题**：kdev-memory 的 `执行日志.md` 长期累积，跑半年以上就会膨胀到 1000+ 行，影响 Claude Read 效率。

**现状方案**：文档提示"超 500 行按迭代切档"，但这是**人工建议**，无自动化。

**可借鉴**：参考 claude-remember 的 `now → today → recent → archive` 分层压缩思路，加一个**季度归档 pipeline**：
- 每季度末把"半年前的 Step"用 Haiku 压成段落
- **保留 R-NNN / Q-NNN / G-NNN 的原话**（这些是下游 skill 原料，不能被 AI 摘要覆盖）
- 只压执行流水，不压结构化信号

**关键设计差异**：claude-remember 压所有东西，kdev-memory 压之前必须先**分层**——原始信号永远不压，只压过程流水。

### 6.2 借鉴 B：测试覆盖到 hook 脚本层

**问题**：kdev-memory 6 个 hook 脚本（尤其 `user-prompt-trigger.sh` 的 triggers 匹配、trigger-sessions.json TTL、代码块 sanitize 逻辑）都只靠 evals 端到端验证，中间逻辑无单元测试。

**可借鉴**：claude-remember 186 tests 99% 覆盖，把 Python pipeline 和 shell 脚本都做了细粒度测试。

**优先测的点**：
- `triggers:` 行的三种格式解析（JSON array / 逗号分隔 / YAML 多行）
- 代码块 sanitize（避免 Claude 写 G-NNN 时在正文代码块里的词误触发匹配）
- `trigger-sessions.json` 的 60 分钟 TTL 清理
- 时区边界（跨 0 点的"今天"判定）

---

## 七、产品定位建议

不追求做 claude-remember 的替代品。二者是**正交工具**，都推荐用户装。

**kdev-memory 的差异化卖点应该对外强调**：
1. **零 API 成本**（vs 一天几美分 Haiku 费用）
2. **不依赖 Auto-compact 关闭**（vs 硬依赖）
3. **可 commit 跟代码走**（vs 本机私有）
4. **triggers 按需召回 + 渐进式披露**（vs 全量注入，长项目更省 token 更精准）
5. **双评分 + R-NNN 原料库**（vs 无评分，无下游 skill 作者视角）

**kdev-memory 不擅长的事要坦诚**：
- 不做"让 Claude 回看前几次会话的对话细节"——这件事 claude-remember 更专业
- 不做"自动从会话里抽取摘要"——我们要求 Claude 主动写结构化条目

---

## 八、下一步决策项

1. **6.1 Haiku 季度归档 pipeline** 要不要做？做的话走 0.4.0 还是 0.5.0？
2. **6.2 hook 脚本单元测试** 优先补哪几个脚本？要不要新建 `tests/unit/` 和 `tests/integration/` 分层？
3. **产品定位对外表达**：要不要在 README 顶部加一段"三选一 / 三兼得"的对比表，帮用户判断什么时候装什么？

以上三项建议分别独立评估，未达成共识前不动代码。
