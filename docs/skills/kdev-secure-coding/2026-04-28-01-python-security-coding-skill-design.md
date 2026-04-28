# Python 安全编码规范 Skill — 设计文档

- 日期：2026-04-28
- 输入物：`/home/sec/skills/Python安全编码规范.docx`（公司内部规范，8 大类、50+ 条规则、含正反例代码）
- 目标：把规范落成一个用户级 skill，让 Claude 在 Python 后端项目的设计 / 编码 / 测试 / 审查环节自动遵循。

## 1. 目标与非目标

### 目标
- 在用户进入 Python 后端项目工作时，规范以 skill 形式自动可用，无需用户每次手动提示。
- 规范的规则原文和代码示例完整保留，model 在写到对应代码点时能查到具体写法。
- 任务完成前有"清单核对"环节，关键漏检能被兜住。
- skill 自包含、零外部依赖、跨环境（Claude Code / SDK）通用。

### 非目标
- 不在本期内打包发布为 plugin（保留为后续选项）。
- 不修改内置 `init` skill；不依赖 hook（不动 settings.json）。
- 不替代代码评审或 SAST 工具——skill 是"提醒 + 引导"，不是"扫描器"。

## 2. 触发模型

采用 **A + C 组合**：

- **A · description 触发**（主路径）：SKILL.md 的 description 写明触发场景（Python 后端框架在场，或代码涉及 SQL/加密/eval 等敏感面），由 Claude 自行判断是否调用。
- **C · CLAUDE.md 锚点**（兜底）：项目 CLAUDE.md 中写入"本项目所有 Python 代码改动 MUST 调用 python-security-coding skill"。CLAUDE.md 每轮自动注入 context，给 model 一根永久引线。
- **不采用 B（hook）**：避免改 settings.json、避免 prompt 噪音、避免绑定单机/单用户。

CLAUDE.md 锚点不通过修改内置 init skill 实现，而是 skill **自举**写入（见 §4）。

## 3. 目录与位置

**位置**：`~/.claude/skills/python-security-coding/`（用户级，跨项目通用）

**目录布局**：
```
python-security-coding/
├── SKILL.md                         # 索引 + 工作模式 + 自举逻辑 + 完成清单
└── references/
    ├── 01-input-validation.md       # 3.1 输入验证与表示
    ├── 02-security-features.md      # 3.2 安全特性（密码/密钥/加密/哈希/随机数/Cookie/传输/Flask/Django/隐私）
    ├── 03-encapsulation.md          # 3.3 封装（输出/网络/边界/CSP/CORS）
    ├── 04-api-misuse.md             # 3.4 API 滥用（文件/权限）
    ├── 05-time-and-state.md         # 3.5 时间与状态（临时文件）
    ├── 06-error-handling.md         # 3.6 错误处理
    ├── 07-code-quality.md           # 3.7 代码质量
    └── 08-environment.md            # 3.8 环境（响应/部署/版本）
```

原 docx 文件保留在 `/home/sec/skills/Python安全编码规范.docx`，不进 skill 目录（避免 model 误读 binary）。

## 4. 自举（首次激活写 CLAUDE.md）

SKILL.md 顶部包含一段固定流程，每次 skill 被调用时执行：

1. 读取当前项目根的 `CLAUDE.md`（不存在则跳到 4b）。
2. 若 CLAUDE.md 已包含 `python-security-coding` 字样 → 跳过自举。
3. 若否，且当前项目命中"Python 后端项目检测规则"（§7），向用户提议追加：
   ```markdown
   ## 安全编码规范
   本项目所有 Python 代码改动（设计/编码/测试/审查）MUST 调用 `python-security-coding` skill。
   ```
4. 用户同意后写入；否则记录决策、本会话不再询问。
   - 4b. CLAUDE.md 不存在时：提议先创建一个最小 CLAUDE.md，再写入上述段落（或建议用户先跑 `/init`）。

自举确保只要 skill 被触发过一次，CLAUDE.md 就成为永久锚点。

## 5. 工作模式（双层）

### Layer 1 · 编码期按需查阅（reactive）
SKILL.md 提供"关键词 → reference 文件"映射表，例：

| 当前任务/代码出现 | Read |
|---|---|
| `cursor.execute` / SQL 字符串拼接 | `01-input-validation.md` SQL 段 |
| `os.system` / `subprocess` / `shell=True` / `eval` / `exec` | `01-input-validation.md` 命令/动态评估段 |
| `pickle` / `marshal` / `yaml.load` | `01-input-validation.md` 反序列化段 |
| `lxml` / `xml.etree` / `XPath` | `01-input-validation.md` XML 段 |
| `hashlib` / `Crypto` / `cryptography` / `hmac` / `pbkdf2` | `02-security-features.md` 加密/哈希段 |
| `random` / `secrets` / `uuid` | `02-security-features.md` 随机数段 |
| Flask `Response` / `set_cookie` / Django `HttpResponse` | `02-security-features.md` Cookie/Flask/Django 段 |
| `open(` / `tempfile` / `os.chmod` / `Path.open` | `04-api-misuse.md` + `05-time-and-state.md` |
| `try/except` / 错误响应 | `06-error-handling.md` |
| `os.sep` / 路径拼接 | `07-code-quality.md` |
| 部署 / 版本依赖 / 响应头 | `08-environment.md` |

model 写到对应代码时按表 Read 对应章节，无关章节不加载——节省 token。

### Layer 2 · 完成前清单核对（completion gate）
SKILL.md 末尾定义清单核对步骤：在声明任务完成 / 提交 commit / 创建 PR **之前**，MUST 按 8 大类逐条自检本次改动是否触发其中规则：

- [ ] 3.1 输入验证：本次是否引入/修改了外部输入处理路径？
- [ ] 3.2 安全特性：本次是否涉及密码、密钥、加密、随机数、Cookie、传输配置？
- [ ] 3.3 封装：本次是否涉及响应头、CORS、CSP、边界？
- [ ] 3.4 API 滥用：本次是否涉及文件/权限操作？
- [ ] 3.5 时间与状态：本次是否使用临时文件 / 共享状态？
- [ ] 3.6 错误处理：本次是否新增异常路径或错误响应？
- [ ] 3.7 代码质量：本次是否硬编码了路径分隔符？
- [ ] 3.8 环境：本次是否影响响应安全 / 部署配置 / 依赖版本？

每项命中即对应 Read references 验证规则；未命中跳过。

与 `superpowers:verification-before-completion` 协作：当该 skill 触发时，把上述清单作为 Python 项目的子清单插入。

可选辅助：项目级 `/python-security-check` slash command，用于显式触发 Layer 2，但不强制走它。（slash command 的具体实现留到 plan 阶段决定。）

## 6. Reference 文件统一结构

每个 `references/0X-*.md` 按下列模板组织：

```markdown
# 3.X <类别中文名>

> 概述：一句话说明本类别防什么风险（基于原 docx 概述精炼）。

## 3.X.Y <子项中文名>

### 规则
- 应/禁/推荐 ...（逐条照录原文）

### 反例
\`\`\`python
# 原 docx 中的错误代码块
\`\`\`

### 正例
\`\`\`python
# 原 docx 中的正确代码块
\`\`\`

### 适用场景
何时应想到这条规则（model 自查用，docx 没有，本次新增）。
```

**取舍原则**：
- 保留：所有 "应 / 禁 / 推荐" 规则原文 + 全部代码示例（正反例）
- 新增：每条规则末尾 "适用场景" 一行，让 model 知道何时该想到它
- 沿用：规则编号 3.X.Y 体系，便于规范升级时对账

## 7. Python 后端项目检测规则

自举判定与 description 触发判定共用：

**强信号（任一命中即视为 Python 后端项目）**：
- `pyproject.toml` / `requirements.txt` / `Pipfile` / `setup.py` 中出现以下任一依赖：
  - Web 框架：`flask`, `django`, `fastapi`, `tornado`, `aiohttp`, `sanic`, `bottle`, `falcon`, `starlette`, `quart`
  - 数据 / 异步栈：`sqlalchemy`, `pymysql`, `psycopg2`, `asyncpg`, `redis`, `celery`, `kombu`, `pika`

**弱信号**：
- 项目内有 `*.py` 文件 + 上述任一 framework 的 `import` 语句
- 存在 `manage.py` / `wsgi.py` / `asgi.py` / `app.py`

**纯脚本项目**：
- 不主动自举（避免对一次性脚本造成打扰）。
- 但 description 仍可在代码涉及 SQL / 加密 / 反序列化 / 网络 / 文件操作时触发——大部分规则对纯脚本同样适用。

## 8. docx → markdown 转换

一次性把规范文档拆成 8 个 reference 文件，转换约束：

- 规则原文（"应/禁/推荐"开头的那一行）逐字照录。
- 代码块照录（保留 `import`、`from ... import ...`、错误注释等所有上下文）。
- 中文叙述部分允许做轻度编辑（去除 docx 排版冗余，保留语义）。
- 不做规则增删；不做规则改写；不"翻译"规则措辞。
- "适用场景" 一行由实施者补充，作为 skill 自查辅助，不视为规范的一部分。

转换工具留到 plan 阶段定（unzip + XML 解析 / pandoc / python-docx 任一即可，不影响产出物）。

## 9. 维护策略

- 规范升级：只动对应 reference 文件 + SKILL.md 的关键词映射表；规则编号 3.X.Y 不变即向后兼容。
- 错漏修复：直接编辑 reference 文件。
- 打包 plugin（未来可选）：将整个目录包成 superpowers 风格 plugin 发布给团队，本期不做。

## 10. 风险与未决项

| 风险/未决项 | 处理 |
|---|---|
| description 触发漏判 | 由 CLAUDE.md 锚点兜底（A+C 组合的设计初衷） |
| 自举首次未触发即写代码 | CLAUDE.md 锚点会在下次会话补上；可接受 |
| 规范本身有歧义/过时条款 | 在 reference 中保持原文，但允许在"适用场景"中加注；不在 skill 中改写规则 |
| 纯脚本项目用户体验 | 不自举但仍可被触发，避免一次性脚本被打扰 |
| 与 `verification-before-completion` 协作细节 | 留到 plan 阶段细化（清单如何嵌入、是否互引） |

## 11. 后续

本设计经用户确认后进入 writing-plans 阶段，产出实施计划：
- docx → markdown 转换的具体步骤
- SKILL.md 完整内容草稿
- 自举逻辑的 prompt 表述
- 关键词映射表的最终词条
- 完成清单的措辞
- 可选 slash command 的去留与形式
