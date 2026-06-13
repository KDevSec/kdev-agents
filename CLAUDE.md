# kdev-agents 项目 Claude Code 指引

<!-- BEGIN kdev-memory:智能体自动记录规则 (managed · 勿手改正文，升级会覆盖) -->
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
- **v0.17+ 记录 ID 时间戳化（Q-020）**：新建 Step + Q/G/R/F 用 `<Type> <YYYYMMDD-HHMMSS>-<who>` 格式（who=git email 前缀，无 git 则省略后缀不写 None；同秒同写手 `.N` 兜底），通过 `step_id.mint_record_id()` 算。现存顺序 ID（`Step main-N`/`Q-NNN`）冻结、解析双认。slug/counter 退役（修 G-011 worktree 撞号）。详见 [P-C2 spec §11](docs/superpowers/specs/2026-06-13-P-C2-JSONL操作层+token优化-design.md) / Q-020。

---

**详细 schema、格式、流程、边缘处理**：都在 skill 里，用户召唤后读即可。本规则段故意不复述，以避免跟 skill 演进漂移。
<!-- END kdev-memory:智能体自动记录规则 -->