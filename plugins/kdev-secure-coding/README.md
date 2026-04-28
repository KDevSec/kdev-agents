# kdev-secure-coding

公司安全编码规范 skill 集合 —— 把内部安全编码规范落到 Claude 的设计/编码/测试/审查工作流里。

## 工作模式（所有语言通用）

每个语言的 skill 走相同的双层模型：

- **Layer 1 · 编码期按需查阅（reactive）**：SKILL.md 含一张「关键词 → reference 章节」映射表。Claude 写到对应代码点（SQL 拼接 / 加密 API / 反序列化 / 文件权限 / ...）时按表 Read 对应 reference，无关章节不预加载，节省 token。
- **Layer 2 · 完成前清单核对（completion gate）**：声明任务完成 / 提交 commit / 创建 PR 前 MUST 按 8 类清单逐条自检本次改动是否触发其中规则。命中即对应 Read references 验证；未命中跳过。

触发模型：
- **A · description 触发（主路径）**：SKILL.md 的 description 写明语言/框架/敏感操作关键词，Claude 自行判断是否调用
- **C · CLAUDE.md 锚点（兜底）**：首次激活时自举提议向项目 CLAUDE.md 写入硬约束「本项目所有 X 代码改动 MUST 调用 X-security-coding skill」，写入后 CLAUDE.md 永久作为 context 锚点

## 当前包含的 skill

| skill | 覆盖范围 | 状态 |
|-------|---------|------|
| [python-security-coding](skills/python-security-coding/SKILL.md) | 8 大类（输入验证 / 安全特性 / 封装 / API 滥用 / 时间状态 / 错误处理 / 代码质量 / 环境）共 50+ 条规则 + 正反例代码 | ✅ v0.1.0 |
| java-security-coding | Maven/Gradle/Spring/Servlet/Hibernate 视角 | 🚧 规划中 |
| c-security-coding | 缓冲区/指针/内存/CMake/glibc 视角 | 🚧 规划中 |

## 触发示例

打开一个含 `flask` / `django` / `sqlalchemy` 等依赖的 Python 项目时：
- Claude 会主动调用 `python-security-coding` skill
- 首次激活会提议向 CLAUDE.md 追加锚点段
- 写到 `cursor.execute` 时，Claude Read `references/01-input-validation.md` 的 SQL 段确认是否参数化
- 提交前，Claude 走 8 类清单自检本次改动

## 安装

```bash
# 1. 注册 marketplace（一次性，已注册过可跳过）
claude plugin marketplace add KDevSec/kdev-agents

# 2. 安装本插件
claude plugin install kdev-secure-coding@kdev-agents
```

## 升级

```bash
/plugin marketplace update kdev-agents
/plugin update kdev-secure-coding@kdev-agents
```

## 目录结构

```
kdev-secure-coding/
├── .claude-plugin/
│   └── plugin.json
├── README.md
├── CHANGELOG.md
├── skills/
│   └── python-security-coding/
│       ├── SKILL.md                  # 索引 + 自举 + Layer 1/2 + Reference 索引
│       └── references/
│           ├── 01-input-validation.md
│           ├── 02-security-features.md
│           ├── 03-encapsulation.md
│           ├── 04-api-misuse.md
│           ├── 05-time-and-state.md
│           ├── 06-error-handling.md
│           ├── 07-code-quality.md
│           └── 08-environment.md
└── tests/
    └── verify-skill.py               # 结构验证器（heading/triplet 完整性）
```

## 贡献新语言 skill

按 python-security-coding 的同构模板补：

1. 在 `skills/<lang>-security-coding/` 新建 `SKILL.md`，参照 Python 的 description / 自举 / 项目检测 / Layer 1 关键词映射 / Layer 2 清单 / Reference 索引 6 段结构
2. 在 `skills/<lang>-security-coding/references/` 写 8 个对应规则文件，复用 `规则 / 反例 / 正例 / 适用场景` 模板
3. 把规则编号与 reference 文件命名对齐（`01-...md` ~ `08-...md`）
4. 跑 `tests/verify-skill.py` 通过结构检查
5. 更新本 README 表格 + CHANGELOG + plugin.json `version`

## 设计文档

完整设计 / 实现计划见 [docs/skills/kdev-secure-coding/](../../docs/skills/kdev-secure-coding/)：
- 设计 spec：`2026-04-28-01-python-security-coding-skill-design.md`
- 实施 plan：`2026-04-28-01-python-security-coding-skill-plan.md`
- 源规范：`sources/Python安全编码规范.docx`
