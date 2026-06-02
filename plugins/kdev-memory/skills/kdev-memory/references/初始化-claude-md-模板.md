---
claude_md_contract:
  purpose: "本文件定义 CLAUDE.md 规则段要暴露的'接口'——贯穿 session 的铁规 + Claude 要识别的 hook 信号。skill 内部实现细节（schema / 编号 / 评分机制 / 触发表）不放这里，由用户召唤 skill 时按需加载。"
  cross_session_rules:
    - "实时落盘：每做完一步立即落到 .kdev/memory/"
    - "文件聚合不翻会话：写汇总从 .kdev/memory/ 读当天条目拼装"
    - "优先处理 hook 产出：WARN 文件 / brief 注入 / recall 注入 / checkpoint"
  hook_injection_tags:
    - "<kdev-memory-brief>"
    - "<kdev-memory-recall>"
  hook_file_patterns:
    - ".kdev/memory/WARN-未记录-*.md"
    - ".kdev/memory/checkpoints/压缩前-*.md"
  summon_keywords:
    - "建立工程记忆 / 加 .kdev / 搞记忆机制"
    - "写今天总结 / 生成每日汇总 / 交接给明天"
    - "切档 / 归档一下 / 整理主文件"
    - "这条以后都要遵守 / 加到项目规则 / 升级成铁规"
    - "昨天做到哪了 / 继续上次的工作 / 恢复上下文"
  version_hint: "本契约若变（新增 hook tag / 改贯穿铁规 / 改 summon keywords），老项目的 CLAUDE.md 规则段需手工 patch 对应行。实现级变更（schema / 编号 / 评分机制细节）不触及本契约，CLAUDE.md 不用改。"
---

# 初始化时贴进项目 CLAUDE.md 的触发规则段

## 什么时候读本文件

- 执行 kdev-memory 初始化、需要把触发规则段写进项目 `CLAUDE.md` 时
- 老项目升级 skill 版本、需要核对触发规则段的**接口**部分是否对齐（接口指本文件 frontmatter 的 `claude_md_contract`）
- 看到 lint 提示"CLAUDE.md 缺少某个 hook 注入标签响应"时

## 我不负责什么

- **`.kdev/memory/` 各文件的字段格式** → `references/六类记录-schema.md`
- **triggers 关键词怎么选** → `references/triggers-写法.md`
- **各 hook 的内部行为细节** → `references/自动化机制-hooks.md`
- **每类记录详细的触发时机和评分机制** → 它们在 skill 里，CLAUDE.md 规则段**不复述**

---

## 设计原则：接口 vs 实现解耦

CLAUDE.md 规则段扮演的是 skill 的**对外接口**——只列出 Claude **必须时刻在场**的决策点：

- **贯穿 session 的铁规**：需要 Claude 下意识时刻检查（实时落盘 / 文件聚合 / hook 产出响应）
- **召唤 skill 的时机**：列出触发词，让 Claude 知道"什么时候要调 skill"
- **hook 注入接口**：列出 Claude 要识别的特殊标签和文件

**不放进规则段**（这些随 skill 演进会频繁变化）：
- ❌ 六类记录的详细 schema
- ❌ 评分机制的具体字段
- ❌ Q/G/R/Step 编号规则
- ❌ 各 hook 的内部行为表
- ❌ 切档 / 升级 / 归档的具体流程

这些都在 skill 本体（SKILL.md / references/）里，用户召唤 skill 时自然读到。

**好处**：skill 升级 schema / 评分 / 编号 / hook 细节时，CLAUDE.md 规则段**一字不动**——从根源避免"CLAUDE.md 漂移"。

## CLAUDE.md 合并策略

- 若项目已有 `CLAUDE.md` → **追加**章节 `## 智能体自动记录规则`，不要覆盖也不要改写已有内容
- 已有同名章节 → 暂停，向用户展示两个版本的差异，由用户裁决（不要自作主张合并）
- 若项目无 `CLAUDE.md` → 新建，只放触发规则段即可

---

## 触发规则段模板（整段贴入 CLAUDE.md）

```markdown
## 智能体自动记录规则

本项目启用 kdev-memory 工程记忆制度。**本段只讲何时召唤 skill 和 Claude 必须时刻在场的 3 条铁规；具体 schema / 格式 / 流程 / 边缘处理都在 skill 里**（用户召唤时自然读到，不在本段复述）。

### 3 条"必须时刻在场"的铁规（跨 session 贯穿）

这些动作是下意识的、持续的，不能依赖"被召唤"才触发。

🔴 **实时 dispatch step-recorder 落盘**：每做完一个 step-worthy 工作单元（任务 / 决策 / 踩坑 / 用户评分）→ 主会话**不要自己 Read/Write 执行日志**，而是写一段 YAML summary（schema 见 SKILL.md §用 kdev-step-recorder dispatch 落 step）+ dispatch kdev-step-recorder subagent（sonnet）。subagent 验 8 hard-gate + 写 4 段 Step 条目 + 更新当前状态.md frontmatter + 清空 pending-commits.json。dispatch 是 fire-and-forget——主会话写完 YAML、调用 Agent 后立刻继续下一棒工作，不等 subagent 返回。**Q/G/R/F-NNN 决策类条目仍由主会话直接写**——只有 Step 走 dispatch。**不需要征求用户许可**即可 dispatch + 让 subagent 写入 `.kdev/memory/`。

🔴 **文件聚合不翻会话**：用户说"写今天的总结"时，**必须**从 `.kdev/memory/` 当天条目聚合，**不要**回翻会话上下文、不要让用户复述。如果 `.kdev/memory/` 里今天条目为空 → **坦率报告**"今天实时落盘没跟上"，不要凭印象补写。

🔴 **优先处理 hook 产出**：看到下列 hook 留下的信号时，**优先处理**（不跳过去做别的）：
- `.kdev/memory/WARN-未记录-*.md` —— SessionEnd hook 兜底文件：读快照 → 向用户核对 → 补记 Step → `rm` 文件
- `<kdev-memory-brief>` 注入 —— SessionStart hook 的会话全景提示：其中 ⚠️ 条目先处理
- `<kdev-memory-recall>` 注入 —— UserPromptSubmit hook 的召回指针：判断相关性 → 按需 Read
- `.kdev/memory/checkpoints/压缩前-*.md` —— PreCompact hook 的压缩快照：按需读（用户问"上次压缩前细节"或本地 .kdev/ 缺失时）

### 召唤 kdev-memory skill 的时机

以下情形用户不用明说"召唤 skill"，Claude 应主动加载：

- **初始化**：用户说"建立工程记忆 / 加 .kdev / 搞记忆机制"
- **每日汇总**：用户说"写今天总结 / 生成每日汇总 / 交接给明天"
- **切档归档**：用户说"切档 / 归档一下 / 整理主文件"
- **规则升级**：用户说"这条以后都要遵守 / 加到项目规则 / 变成硬规矩 / 升级成铁规"
- **跨会话续航**：新会话用户问"昨天做到哪了 / 之前聊到什么 / 继续上次的工作 / 恢复上下文"
- **格式疑问**：写新 G-NNN / Step / 铁规不确定 schema 时
- **边缘情况**：CLAUDE.md 合并冲突 / 跨月归档 / 规则升级决策等——召唤 skill 读对应 reference

### 关键授权

- `.kdev/memory/` 下的记录文件**不需要逐条请示**即可写入——这是制度，不是每次询问的一次性操作
- 每完成 Step 要顺手更新 `.kdev/memory/当前状态.md` 的 frontmatter（`current_step` + `last_updated`），不要攒到每日汇总时才改
- **v0.11+ Step ID 加分支前缀**：新建 Step 用 `Step <branch-slug>-N` 格式（main 上是 `Step main-N`），通过 `step_id.mint_next_step_id()` 自动算。具体规则见 skill 里的「多 worktree 并发场景」段。

---

**详细 schema、格式、流程、边缘处理**：都在 skill 里，用户召唤后读即可。本规则段故意不复述，以避免跟 skill 演进漂移。
```

---

## 接口契约管理（给 skill 维护者）

本文件顶部的 `claude_md_contract` frontmatter 是 CLAUDE.md 规则段的"接口声明"。任何会导致老项目 CLAUDE.md 规则段要改的变更都必须反映在这里，并在 skill CHANGELOG 标注。

**接口变更的典型类型**（老项目 CLAUDE.md 规则段要手工 patch）：

| 变更 | 影响 CLAUDE.md 规则段哪一段 | 建议动作 |
|---|---|---|
| 加一条贯穿 session 铁规 | 「3 条铁规」段 | 用户手工加一条 |
| 加一个 Claude 必须识别的 hook 注入标签 | 「优先处理 hook 产出」段 | 用户手工加一行 |
| 改 hook 注入标签的字符串 | 同上 | 用户手工 rename |
| 废弃一个 hook 标签 | 同上 | 用户可选（旧项目继续识别旧标签也不报错）|
| 加一个新的 summon keyword | 「召唤 kdev-memory skill 的时机」段 | 用户可选（skill description 里的触发词足够兜底）|

**不是接口变更**（CLAUDE.md 规则段一字不动）：

- 改六类记录的 schema 字段
- 改评分机制（自评 / 用户评分 / 差值阈值）
- 改 Q/G/R/Step 编号规则
- 改切档 / 升级 / 初始化的内部步骤
- 改 references/ 文件的组织方式
- 重命名 references/ 的文件
- 新增 references/ 文件

**append-only 原则**：接口变更尽量只加不改——新增 hook 标签 OK，改名或废弃要走 deprecation 周期。这样老项目的 CLAUDE.md 永远不会被现有 skill 破坏。

---

## 修 CLAUDE.md 漂移流程（用户召唤时读）

### 触发时机

用户说：
- "修 CLAUDE.md 漂移 / 接口漂移 / CLAUDE.md 升级 / claude.md 对齐 skill"
- SessionStart hook 的 `<kdev-memory-brief>` 里出现 ⚠️ "CLAUDE.md 接口漂移：..." 提示，用户让处理

### 动作路径

1. **读本文件顶部 `claude_md_contract` frontmatter**
   取得当前 skill 版本的 3 个字段：`cross_session_rules` / `hook_injection_tags` / `hook_file_patterns`

2. **读项目 CLAUDE.md**
   抽出 `## 智能体自动记录规则` 章节（其他章节完全不动）

3. **逐项比对 → 生成精确 diff patch**
   - `hook_injection_tags` 里的每一项：CLAUDE.md 规则段里是否字面包含？没有 → 加到"优先处理 hook 产出"段的列表
   - `hook_file_patterns` 同上
   - `cross_session_rules` 的每个主题：CLAUDE.md 是否有主题关键词命中？没有 → 加一条新的 🔴 铁规（内容措辞用 contract 里的 description，保持简洁）

4. **展示 diff 给用户审**
   用 `diff -u` 或手工组织的"before/after"展示缺失行的插入位置。**不要一次性重写整段**。

5. **用户批准后执行 Edit**
   用 `Edit` tool 做最小化插入。只改 `## 智能体自动记录规则` 章节内部，**严禁**触及其他章节或用户自定义加入规则段的行。

6. **验证**
   再次调用 `hooks/lib/claude_md_lint.py`（或跑 SessionStart hook）确认 `status: ok`。

### 铁规

- **只管辖 `## 智能体自动记录规则` 章节**——其他章节（开发惯例 / 项目约束等）一字不动
- **用户手动加入规则段的自定义行不覆盖**——比如用户额外加了第 4 条贯穿铁规"commit 前必须跑 lint"，这行不在 contract 里，保留
- **展示 + 批准 + 执行是三个分离步骤**——不要 silent patch
- **失败安全**：任何歧义场景（用户大幅改写了规则段 / diff 难以精确定位）→ 降级为"我只能指出缺什么，请你手工加"，不强行 patch

### 典型 diff 样例

用户 CLAUDE.md 缺一条 hook 标签：

```diff
 🔴 **优先处理 hook 产出**：看到下列 hook 留下的信号时，**优先处理**：
 - `.kdev/memory/WARN-未记录-*.md` —— SessionEnd hook 兜底文件
 - `<kdev-memory-brief>` 注入 —— SessionStart hook 的会话全景提示
 - `<kdev-memory-recall>` 注入 —— UserPromptSubmit hook 的召回指针
+- `<kdev-memory-step-incomplete>` 注入 —— Stop hook 检测 Step 缺段 → 补齐或 R-NNN
 - `.kdev/memory/checkpoints/压缩前-*.md` —— PreCompact hook 的压缩快照
```

精确、最小化、可审计。
