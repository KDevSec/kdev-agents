# kdev-secure-coding 文档

`kdev-secure-coding` plugin 的设计 / 实施文档归档。

## 目录

| 文档 | 状态 | 内容 |
|------|------|------|
| [2026-04-28-01-python-security-coding-skill-design.md](2026-04-28-01-python-security-coding-skill-design.md) | ✅ v0.1.0 | Python 安全编码规范 skill 的设计 spec：触发模型 (A+C) / 双层工作模式 / 自举逻辑 / 项目检测规则 / 8 类 reference 文件统一结构 |
| [2026-04-28-01-python-security-coding-skill-plan.md](2026-04-28-01-python-security-coding-skill-plan.md) | ✅ v0.1.0 | 实施计划：12 个任务，从骨架 + 验证脚本 → docx 提取 → 8 个 reference 撰写 → 最终 SKILL.md → 真实项目冒烟测试 |
| [sources/Python安全编码规范.docx](sources/) | 📎 source | 公司内部 Python 安全编码规范（输入物，本次将其转化为 skill）|

## 设计要点速查

`python-security-coding` skill 是 `kdev-secure-coding` plugin 的首个语言 skill，奠定了三件事：

1. **目录结构**：每语言 skill 用 `skills/<lang>-security-coding/SKILL.md + references/`，统一约定
2. **触发模型 A+C**：description 触发为主路径 + CLAUDE.md 锚点兜底（首次激活自举写入）；不依赖 hook
3. **双层工作模式**：
   - Layer 1（编码期）：关键词 → reference 章节映射表，按需 Read
   - Layer 2（完成前）：8 类清单逐条自检，命中即 Read 验证

后续 java-security-coding / c-security-coding 复用此模板，只需要替换 description / 项目检测关键词 / Layer 1 表 / reference 内容。

## Reference 文件规则模板

每个 reference 子项采用 4 段式：

```markdown
## 3.X.Y <子项名>

### 规则
<逐条照录原文 "应/禁/推荐" 规则>

### 反例
\`\`\`python
<错误代码>
\`\`\`

### 正例
\`\`\`python
<正确代码>
\`\`\`

### 适用场景
<何时该想到本规则，model 自查用。这是对原 docx 的唯一新增内容>
```

## 后续语言 skill 路线图

| skill | 触发关键词 | 规则源 | 状态 |
|-------|------------|--------|------|
| python-security-coding | flask / django / fastapi / sqlalchemy / cursor.execute / hashlib / pickle / ... | Python 安全编码规范.docx | ✅ v0.1.0 |
| java-security-coding | maven / gradle / spring / servlet / hibernate / PreparedStatement / MessageDigest / ObjectInputStream / ... | （待提供）Java 安全编码规范 | 🚧 规划 |
| c-security-coding | CMake / Makefile / glibc / strcpy / sprintf / malloc / memcpy / system / ... | （待提供）C 安全编码规范 | 🚧 规划 |

新增语言时：

1. 在 `plugins/kdev-secure-coding/skills/<lang>-security-coding/` 复制 Python skill 目录结构
2. 改 `SKILL.md`：description 关键词 / 项目检测规则 / Layer 1 映射表 / Layer 2 清单（如果 8 类不变就保留，需调整就改）
3. 重写 `references/01-08*.md`：内容用语言原生 API、关键字、典型框架
4. 在 `tests/verify-skill.py` 的 `SKILLS` 列表加一条配置（指定该语言 reference 的子项数）
5. 跑 verifier，全 OK 后更新 plugin README + CHANGELOG，bump plugin version
