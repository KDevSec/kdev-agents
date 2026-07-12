# 设计：工程记忆分流规则（默认 .kdev · host 内建仅跨项目 carve-out）+ 产品级传播

- 日期：2026-07-12
- 目标仓：kdev-agents（插件包 / kdev-memory 制度）
- 类型：产品缺陷修复（记忆误路由）+ 传播机制
- 触发：agent 把**项目工程事实**误写进 host 内建 `~/.claude/**/memory/` 而非 `.kdev/memory/`。同源根因在姊妹制度 ieidev-memory 已消歧并做成产品级修复（ieidev-team commit 3569763，根因 G 20260711-180559）。本设计把同一修复**forward-port 到 kdev-memory**：经现成 契约/lint/merge/brief 机制传播到所有新旧下游安装。

## 问题

`.kdev/memory/`（kdev-memory 制度）与 host 内建记忆（Claude Code `# Memory`，写 `~/.claude/projects/<proj>/memory/`）是两套并行的「记忆」。host `# Memory` 是 system-prompt 注入的直接指令、读起来像 agent 内建能力，与项目 CLAUDE.md 的 `.kdev/` 制度**在无明确分流规则时冲突**。后果：agent 把项目工程事实（Step / 决策 / 踩坑 / 反馈）误写进 host 内建，而非项目 institutional 账，两处并存必漂移。

**这不是本仓个例**：下游项目的 CLAUDE.md 记忆段由 `skills/kdev-memory/references/初始化-claude-md-模板.md` 生成，而该模板**通篇没有分流规则**——每个 init 过 kdev-memory 的下游项目都缺这条护栏。

## 分流规则（默认制，非绝对）

> 🔴 **工程记录默认落 `.kdev/memory/`**：Step / 决策(Q) / 踩坑(G) / 改进(R) / skill 反馈(F) / 每日汇总 / 当前状态——凡是关于「**这个项目怎么干**」的，一律写 `.kdev/memory/`。
>
> **唯一例外 → host 内建 `~/.claude`（或全局 CLAUDE.md）**：用户**明示**是**跨项目 / 所有项目通用**的规则或用户身份（「以后**所有项目**都…」「你**全局**这样」「记住我是谁」）。
>
> **拿不准 → 归 `.kdev/`**。判别一句话：讲「这个项目的工程」→ `.kdev/`；讲「这个用户 / 跨项目习惯 / 环境」→ host 内建。

**为什么默认制而非绝对**：host 内建记忆有它的天职（跨项目用户身份/偏好、账号/环境级事实），不是「错误的仓」。绝对禁止会误伤这些正当用途。默认制把**常见项**（项目工程事实）钉死到 `.kdev/`，只给**明确跨项目**留窄口，既堵误路由又不牺牲鲁棒性（默认项无歧义）。

## 传播架构（复用现成机制，不新造）

`claude_md_lint.py` 已实现「契约 vs 项目 CLAUDE.md」漂移检测：模板 frontmatter 的 `claude_md_contract.cross_session_rules` 定义贯穿铁规主题，`RULE_THEME_KEYWORDS` 给每主题一组宽松关键词，SessionStart brief lint 存量项目、缺主题就提醒。v0.18 起托管段用 BEGIN/END marker + `claude_md_merge.merge_managed_section()` 幂等 insert-or-replace。

分流规则做成**第 4 条 cross_session_rule 主题**，即自动获得全套传播：

| 覆盖面 | 机制 | 效果 |
|---|---|---|
| **新装** | init 时 `claude_md_merge` 写模板正文进项目 CLAUDE.md | 落地即带分流规则 ✅ |
| **存量·有 marker（v0.18+）** | 升级走 `merge_managed_section()` 幂等推新段 | 主动补 ✅ |
| **存量·无 marker（老项目）** | lint 检出缺「记忆分流」主题 → brief 提醒手工补 | 被动提醒 ✅ |
| **每会话** | SessionStart brief always-on 一行断言 | 对抗 host `# Memory` 的高显著性加持 ✅ |

## 组件改动（产品侧 1-6 分发 / 本仓 7-8）

1. **`references/初始化-claude-md-模板.md` frontmatter**：`cross_session_rules` 加第 4 条（分流规则一句话）；bump `version_hint` 注明 2026-07-12 契约新增该主题、老项目缺则 lint 提醒补、有 marker 走 merge 自动推。
2. **同文件正文模板**：铁规段实时落盘 🔴 后插 🔴 分流规则（默认 .kdev / 跨项目才 host）——这是新装项目 CLAUDE.md 的实际文本。铁规从 3 → 4，正文「3 条铁规」措辞及「接口变更表」的「3 条铁规」相应改「4 条」。
3. **`hooks/lib/claude_md_lint.py`**：`RULE_THEME_KEYWORDS` 加一条 `"记忆分流"` 主题，关键词取**分流规则独有词**：`["~/.claude", "内建记忆", "host 内建", "跨项目", "所有项目"]`。**刻意不含 `.kdev/memory`**——前 3 条铁规文本都提 `.kdev/memory`，若纳入则任何合规的老 CLAUDE.md 都会「假装」含分流规则，从而假阳性放过真正缺分流的项目（本设计最易踩的坑）。
4. **`hooks/session-start-brief.py`（`main()`）**：把 `if not brief.strip(): print(SUPPRESS)` 改成 **always-on 一行分流提醒**——即使 brief 其余为空也显示，让分流规则每会话在场，对抗 host `# Memory` 的高显著性。放在 **ieidev 让位守卫之后**（让位项目已 early-return、不受影响）、包 `<kdev-memory-brief>` **前**。文案：`📌 工程记忆默认写 .kdev/memory/；仅跨项目/所有项目通用规则或用户身份才写 host 内建 ~/.claude`。
5. **`skills/kdev-memory/SKILL.md`**：「这 3 条是贯穿 session 的铁规」→「4 条」；bullet 列表加 🔴 分流条。
6. **`tests/test_claude_md_lint.py`**（TDD）：① CLAUDE.md 缺分流独有词 → `check_drift` 的 `missing_rule_themes` 含「记忆分流」；② 含任一独有词 → 不含该主题于 missing；③ 修既有「完整合规 section」正例（`FULL_KDEV_SECTION` / check_drift 全命中正例 / marker 抽块 fixture）补分流词，否则加了新主题后它们新报漂移。
7. **本仓 `CLAUDE.md`（dogfood）**：铁规段 3 → 4，实时 dispatch 🔴 后插分流铁规，与模板正文同源同措辞——本仓自身吃自家新规、且满足新主题关键词不被 lint 报漂移。
8. **`plugins/kdev-memory/CHANGELOG.md` + `.claude-plugin/plugin.json`**：bump `0.21.0` → `0.22.0`，CHANGELOG 记第 4 条铁规。G-004：plugin 改 hook 须 bump version + 用户刷 marketplace，否则下游 cache stale、新 lint 主题传播不出去。

## 边界裁定

- **F 反馈归属**：项目会话里冒出的 skill/工具反馈 → `.kdev/` 的 F；用户明说「以后所有项目都这样」→ host 内建 / 全局 CLAUDE.md。
- **拿不准**：一律归 `.kdev/`。
- **host 内建不是错误仓**：跨项目身份/环境是它的天职，规则是「默认钉死 + 窄口 carve-out」，绝不误伤正当 host 写入。

## 测试策略

- **claude_md_lint（单元，TDD）**：新增缺分流→drift / 含独有词→不报 两用例；修既有全命中正例补分流独有词。
- **brief**：always-on 分流行——若无 brief 测试套则手跑一次 hook 目视。
- **全套回归**：现有绿基线不破（`python3 -m pytest plugins/kdev-memory/tests/`）。

## 非目标（YAGNI）

- **host 历史迁移**：每台机器一次性运维、不随插件分发、**绝不碰下游用户 host 历史**——产品只改新记录路由，不在本设计范围。
- 不硬拦 host 写入（host 内部行为，hook 拦不住）。
- 不改 kdev record schema（Step/Q/G/R/F 不动）。
- 不扫 host 记忆目录做事后误写检测（双层不做三层）。
