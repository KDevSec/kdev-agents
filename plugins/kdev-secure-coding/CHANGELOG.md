# Changelog

本插件遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。每次发版请同步更新 `.claude-plugin/plugin.json` 的 `version` 字段。

## 版本 bump 规则

| 变化 | bump | 例子 |
|------|------|------|
| **MINOR** `0.X.0` | 新增语言 skill / 新增规则类别 | + Java skill = v0.2.0 |
| **PATCH** `0.x.Y` | 规则措辞修正 / 代码示例改进 / Layer 1 关键词补充 | Python typo fix = v0.1.1 |
| **MAJOR** `X.0.0` | skill 触发逻辑改变 / reference 组织改变 / 3.X.Y 编号体系改变 | 罕见 |

---

## v0.1.0 — 2026-04-28

### python-security-coding skill 首版

**新增**：
- `skills/python-security-coding/SKILL.md`：description 触发 + 首次激活自举 CLAUDE.md 锚点 + 项目检测规则 + Layer 1 关键词→reference 映射表（23 行）+ Layer 2 8 类完成前清单 + Reference 索引
- `skills/python-security-coding/references/`：8 个 reference 文件，覆盖公司规范 §3.1–§3.8
  - `01-input-validation.md`：3.1 输入验证与表示（10 子项：命令/动态评估/网络/数据库/SQL/XML/邮件/日志/资源/表达式）
  - `02-security-features.md`：3.2 安全特性（11 子项：访问控制/密码/密钥/加密/哈希/随机数/Cookie/传输/Flask/Django/隐私）
  - `03-encapsulation.md`：3.3 封装（5 子项：输出/网络/边界/CSP/CORS）
  - `04-api-misuse.md`：3.4 API 滥用（2 子项：文件/权限）
  - `05-time-and-state.md`：3.5 时间与状态（临时文件）
  - `06-error-handling.md`：3.6 错误处理（4 条规则）
  - `07-code-quality.md`：3.7 代码质量（路径分隔符）
  - `08-environment.md`：3.8 环境（响应/部署/版本）
- 每个 reference 子项采用统一 `### 规则 / ### 反例 / ### 正例 / ### 适用场景` 模板，正反例代码取自规范原文（含 Django settings / `pbkdf2_hmac` / `bleach.clean` 等关键示例）
- `tests/verify-skill.py`：结构验证器（frontmatter / 必备小节 / 8 个 reference 的 heading 数 + 规则三元组完整性）
- 设计 spec / 实施 plan / 源规范 docx 入档 `docs/skills/kdev-secure-coding/`

**触发覆盖**：
- 强信号自举触发：`pyproject.toml` / `requirements.txt` / `Pipfile` / `setup.py` 命中 flask / django / fastapi / tornado / aiohttp / sanic / bottle / falcon / starlette / quart / sqlalchemy / pymysql / psycopg2 / asyncpg / redis / celery / kombu / pika 任一依赖
- 弱信号（不主动自举但仍可被 description 触发）：`*.py` + 上述框架 import；`manage.py` / `wsgi.py` / `asgi.py` / `app.py` 存在
