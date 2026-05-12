# kdev-agents

KDev 系列 Claude Code 插件集合 —— 工程记忆、流程辅助、代码提交等。

## 已有插件

| 插件 | 说明 |
|-----|------|
| [kdev-memory](plugins/kdev-memory) | 工程记忆制度：实时落盘决策/踩坑/执行/评分，七层 hook 兜会话续航 + 按月/按季度归档 |
| [kdev-commit](plugins/kdev-commit) | AI commit + push 一体化：AI 用 `<name>-AI` 身份提交，push 前弹 IDE 权限框让用户确认 |
| [kdev-secure-coding](plugins/kdev-secure-coding) | 公司安全编码规范 skill 集合：description 触发 + CLAUDE.md 锚点兜底 + 编码期按需查阅 + 完成前 8 类清单核对。当前含 python-security-coding，规划 Java / C |
| [kdev-code-graph](plugins/kdev-code-graph) | 语义级代码图谱：需求追溯、变更爆炸半径分析、文档-代码同步检查，支持 Markdown 和图片解析 |
| [kdev-design-flow](plugins/kdev-design-flow) | 需求-原型-设计流程编排：串联 spec-kit + frontend-design，加 3 个评审闸门（Claude 自评/人工/混合三档可选），把"原始需求 → SR 文档 → AR 用户故事 → 高保真原型 → 概要+详细设计"链路固化为一个可复跑 skill。**v0.1 实验版**：boot sequence 已验证，主循环依赖 spec-kit 安装环境验收 |
| [kdev-env-recon](plugins/kdev-env-recon) | 测试环境实测前置 skill：登录测试环境 → 实测抓取左菜单全树 / Tab / 按钮 / 字段 / 弹窗 → 持久化为 `recon/menu_list.md` + 4 类 JSON + 截图，作为后续测试用例 .md 与 PageObject 的 UI 文案权威源；可选反向 diff 已有用例并 propose 修正补丁。从 `kdev-ui-autotest` 的 STEP 0 抽离独立，下游 UI 自动化插件直接消费产物 |
| [kdev-ui-autotest](plugins/kdev-ui-autotest) | Playwright + pytest + Element-Plus UI 自动化测试规范固化 skill：把 6 大类规范（STEP 0 环境/菜单/弹窗实测前置、登录复用、资源清理、四件产物归档、Element-Plus 三大坑、用例命名、失败诊断）作为下游项目（KDevSec / Gen9 / 可信评估 / vfadmin 等）的强制实践。第零原则：测试脚本目的是发现 BUG，不是刷通过率 |
| [kdev-test-points-v1](plugins/kdev-test-points-v1) | 测试点 / 测试设计文档生成 skill：基于 ISO/IEC/IEEE 29119-4（EP / BVA / 决策表 / 状态迁移 / pairwise / MC/DC / error guessing）+ GB/T 25000.51 ≡ ISO/IEC 25051（三域覆盖 + 8×31 质量子特性 + 符合/部分符合/不符合 verdict）双标准，从 spec / PRD / API 契约 / RUSP / COTS 源生成可审计测试点。四种模式：feature-spec / feature-spec-lite / api-contract / full-conformity |
| [kdev-test-cases-v1](plugins/kdev-test-cases-v1) | 测试用例渲染 skill：把上游 测试点 .md 1:1 渲染成 Playwright 友好 fielded 用例代码块（用例编号 / 名称 / 步骤 / 预期结果 等字段 + UI/API 自动化直通字段）。严格 byte-equality + arithmetic-equality 契约：用例名称逐字符相同、用例编号确定性 `TC-AR<8 位>-<3 位>`、预期结果同序保留。仅 测试步骤 / 前置条件 / 测试数据 生成式推断。`kdev-test-points-v1` + `kdev-test-cases-v1` 组合取代旧 kdev-test-case |

## 安装方式

```bash
# 1. 注册 marketplace（一次性）
claude plugin marketplace add KDevSec/kdev-agents

# 2. 按需安装插件
claude plugin install kdev-memory@kdev-agents
claude plugin install kdev-commit@kdev-agents
claude plugin install kdev-secure-coding@kdev-agents
claude plugin install kdev-code-graph@kdev-agents
claude plugin install kdev-design-flow@kdev-agents   # v0.1 实验版，需先装 spec-kit
claude plugin install kdev-env-recon@kdev-agents
claude plugin install kdev-ui-autotest@kdev-agents
claude plugin install kdev-test-points-v1@kdev-agents
claude plugin install kdev-test-cases-v1@kdev-agents
```

## 更新

### 关键事实：第三方 marketplace 默认**不**自动更新

Claude Code 对官方 Anthropic marketplace 默认启用 auto-update，但对第三方（包括 kdev-agents）**默认禁用**。这意味着：**即便我们发布了新版本，你也不会自动收到**——除非你主动拉更新或开启 auto-update。

升级检查机制是看每个插件 `plugin.json` 的 `version` 字段做语义版本比较，不看 git tag。我们每次发布都会 bump `version` 并更新对应插件的 `CHANGELOG.md`，[推到 main 分支](https://github.com/KDevSec/kdev-agents) 即生效。

### 方式 A：手动更新（默认方式）

```bash
# 先刷新 marketplace 本地缓存（否则 Claude Code 不知道有新版本）
/plugin marketplace update kdev-agents

# 再升级具体插件
/plugin update kdev-memory@kdev-agents
/plugin update kdev-commit@kdev-agents
/plugin update kdev-secure-coding@kdev-agents
/plugin update kdev-code-graph@kdev-agents
/plugin update kdev-design-flow@kdev-agents
/plugin update kdev-env-recon@kdev-agents
/plugin update kdev-ui-autotest@kdev-agents
/plugin update kdev-test-points-v1@kdev-agents
/plugin update kdev-test-cases-v1@kdev-agents
```

两步都要跑——`marketplace update` 只刷新元数据，`plugin update` 才真正升级。

### 方式 B：开启 auto-update（一次性配置，之后每次启动自动拉新）

**UI 方式（推荐）**：

```
/plugin → Marketplaces 标签 → 选中 kdev-agents → 打开 Auto-update 开关
```

**settings.json 方式**（在项目或全局 `.claude/settings.json`）：

```json
{
  "extraKnownMarketplaces": {
    "kdev-agents": {
      "source": { "source": "github", "repo": "KDevSec/kdev-agents" },
      "autoUpdate": true
    }
  }
}
```

配置后 Claude Code 每次启动会自动 `/plugin marketplace update kdev-agents`，发现新版本立即升级。

### 如何知道有新版本

- **CHANGELOG**：每个插件目录下的 `CHANGELOG.md` 记录了每个版本的改动（如 [plugins/kdev-memory/CHANGELOG.md](plugins/kdev-memory/CHANGELOG.md)）
- **GitHub watch**：在 [KDevSec/kdev-agents](https://github.com/KDevSec/kdev-agents) 点 Watch → Custom → Releases，有新 release 时收邮件通知
- **当前版本自查**：`/plugin` → Marketplaces → 看 installed version vs latest version

### 环境变量全局开关

如果你想全局禁用所有 plugin 自动更新（包括官方 marketplace）：

```bash
export DISABLE_AUTOUPDATER=1
```

如果只想禁 Claude Code 本体更新但保留 plugin 更新：

```bash
export DISABLE_AUTOUPDATER=1
export FORCE_AUTOUPDATE_PLUGINS=1
```

## 开发

本地目录结构：

```
kdev-agents/
├── .claude-plugin/marketplace.json       # marketplace 清单
└── plugins/
    ├── kdev-memory/                      # 工程记忆插件
    │   ├── .claude-plugin/plugin.json
    │   ├── skills/kdev-memory/SKILL.md
    │   ├── hooks/                        # 七层 hook（SessionStart/UserPromptSubmit/Stop/PostToolUse/PreCompact/SessionEnd/Strict）
    │   │   ├── hooks.json
    │   │   ├── lib/                      # trigger-match.py / archive-hint.sh / frontmatter.sh / ...
    │   │   └── *.sh
    │   ├── tests/                        # stdlib unittest（trigger-match.py 单元测试）
    │   ├── evals/                        # skill-creator 式 eval（端到端 hook 召回验证）
    │   ├── CHANGELOG.md
    │   └── README.md
    ├── kdev-commit/                      # AI commit + push 插件
    │   ├── .claude-plugin/plugin.json
    │   ├── skills/kdev-commit/SKILL.md
    │   ├── hooks/                        # 纯 Node，零外部依赖
    │   │   ├── hooks.json
    │   │   ├── block-unattributed-commit.js
    │   │   └── confirm-push.js
    │   └── README.md
    ├── kdev-secure-coding/               # 公司安全编码规范 skill 集合
    │   ├── .claude-plugin/plugin.json
    │   ├── skills/python-security-coding/   # 8 大类、50+ 条规则
    │   │   ├── SKILL.md
    │   │   └── references/01-08*.md
    │   ├── tests/verify-skill.py         # 结构验证器（heading + 三元组）
    │   ├── CHANGELOG.md
    │   └── README.md
    ├── kdev-code-graph/                  # 语义级代码图谱插件
    │   ├── .claude-plugin/plugin.json
    │   ├── skills/kdev-code-graph/SKILL.md
    │   └── README.md
    ├── kdev-design-flow/                 # 需求-原型-设计流程编排插件 (v0.1 实验)
    │   ├── .claude-plugin/plugin.json
    │   ├── commands/kdev-design-flow.md  # /kdev-design-flow 斜杠命令
    │   ├── skills/kdev-design-flow/
    │   │   ├── SKILL.md                  # 5 阶段 + 3 评审闸门 + retry 主循环
    │   │   └── references/               # SR prompt + 模板 + review 通用 prompt + 合并规则
    │   ├── lib/                          # slug.py（slug 化）+ flow_state.py（原子状态 IO）
    │   ├── tests/                        # pytest（slug 11 + flow_state 8 + skill_md_lint 9 = 28）
    │   ├── CHANGELOG.md
    │   └── README.md
    ├── kdev-env-recon/                   # 测试环境实测前置插件（菜单/Tab/按钮/弹窗/字段 UI 文案权威源）
    │   ├── .claude-plugin/plugin.json
    │   └── skills/kdev-env-recon/
    │       ├── SKILL.md                  # 登录 → probe → menu_list.md + 4 类 JSON + 截图；可选反向 diff 用例
    │       ├── references/               # recon-workflow / menu-list-template / case-diff-patch
    │       └── assets/recon_env_bootstrap.py
    ├── kdev-ui-autotest/                 # Playwright + pytest + Element-Plus 自动化测试规范插件
    │   ├── .claude-plugin/plugin.json
    │   └── skills/kdev-ui-autotest/
    │       ├── SKILL.md                  # 6 大类规范 + STEP 0 实测前置 + 第零原则
    │       ├── references/               # env-recon-bootstrap / element-plus-pitfalls / case-skeleton / infra-standards / failure-diagnosis
    │       ├── assets/                   # recon_env_bootstrap.py + test_arNN_skeleton.py + 用例 .md 头模板
    │       └── evals/evals.json
    ├── kdev-test-points-v1/              # 测试点 / 测试设计文档生成插件（29119-4 + 25051 双标准）
    │   ├── .claude-plugin/plugin.json
    │   └── skills/kdev-test-points-v1/
    │       ├── SKILL.md                  # 四模式：feature-spec / feature-spec-lite / api-contract / full-conformity
    │       ├── references/               # quality-characteristics / output-templates / template-override / example-walkthrough
    │       └── evals/evals.json
    └── kdev-test-cases-v1/               # 测试用例渲染插件（测试点 .md → Playwright fielded 用例代码块）
        ├── .claude-plugin/plugin.json
        └── skills/kdev-test-cases-v1/
            ├── SKILL.md                  # byte-equality + arithmetic-equality 渲染契约
            ├── references/               # output-skeleton / playwright-handoff
            └── evals/evals.json
```

新增插件：在 `plugins/` 下新建目录 + 在 `marketplace.json` 的 `plugins` 数组里追加条目。

## License

MIT