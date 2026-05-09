# References 项目指引文档

> 更新日期: 2026-05-09
> 用途: 代码知识图谱项目调研参考，后续在 Linux 上可根据此文档下载
> 路径: `docs/skills/kdev-code-graph/references/` (文档可提交，源码项目已 gitignore)

---

## 一、已下载项目

| 项目名 | GitHub URL | Stars | 简述 |
|--------|------------|-------|------|
| **Understand-Anything** | https://github.com/Lum1104/Understand-Anything | 13k | 交互式知识图谱 + 多Agent Pipeline + Dashboard |
| **graphify** | https://github.com/safishamsi/graphify | 45k | 多模态知识图谱 (代码+文档+视频+音频) |
| **code-review-graph** | https://github.com/tirth8205/code-review-graph | - | Token优化 + 爆炸半径分析 + 28 MCP tools |
| **ops-codegraph-tool** | https://github.com/optave/ops-codegraph-tool | 47 | CFG/DataFlow深度分析 + CI Gates + 30+ MCP tools |

---

## 二、下载命令

### Linux/macOS

```bash
# 创建 references 目录 (在 kdev-code-graph docs 下)
mkdir -p ~/Works/SecDev/kdev-agents/docs/skills/kdev-code-graph/references
cd ~/Works/SecDev/kdev-agents/docs/skills/kdev-code-graph/references

# 下载四个项目 (--depth 1 浅克隆，节省空间)
git clone --depth 1 https://github.com/Lum1104/Understand-Anything.git
git clone --depth 1 https://github.com/safishamsi/graphify.git
git clone --depth 1 https://github.com/tirth8205/code-review-graph.git
git clone --depth 1 https://github.com/optave/ops-codegraph-tool.git
```

### Windows (PowerShell)

```powershell
# 创建 references 目录
mkdir D:\Works\SecDev\kdev-agents\docs\skills\kdev-code-graph\references
cd D:\Works\SecDev\kdev-agents\docs\skills\kdev-code-graph\references

# 下载四个项目
git clone --depth 1 https://github.com/Lum1104/Understand-Anything.git
git clone --depth 1 https://github.com/safishamsi/graphify.git
git clone --depth 1 https://github.com/tirth8205/code-review-graph.git
git clone --depth 1 https://github.com/optave/ops-codegraph-tool.git
```

---

## 三、项目核心文件索引

### Understand-Anything (TypeScript)

| 文件 | 说明 |
|------|------|
| `README.md` | 项目概述 |
| `CLAUDE.md` | Claude Code 使用指南 |
| `understand-anything-plugin/skills/understand/SKILL.md` | 核心Skill：7阶段Agent Pipeline |
| `understand-anything-plugin/skills/doc-code-sync/SKILL.md` | 文档-代码同步检查 |
| `understand-anything-plugin/skills/semantic-trace/SKILL.md` | 需求追溯 |
| `understand-anything-plugin/skills/code-review-enhanced/SKILL.md` | 爆炸半径分析 |
| `understand-anything-plugin/packages/core/src/types.js` | Schema定义 (13节点 + 26边) |
| `docs/superpowers/specs/2026-03-14-understand-anything-design.md` | 架构设计文档 |

### graphify (Python)

| 文件 | 说明 |
|------|------|
| `README.md` | 项目概述 |
| `ARCHITECTURE.md` | Pipeline架构设计 |
| `graphify/skill.md` | Claude Code Skill定义 |
| `graphify/extract.py` | 多模态提取核心 |

### code-review-graph (Python)

| 文件 | 说明 |
|------|------|
| `README.md` | 项目概述 |
| `docs/architecture.md` | 系统架构 |
| `docs/schema.md` | 数据Schema |
| `skills/*.md` | Skills定义 |
| `CLAUDE.md` | Claude Code 配置 |

### ops-codegraph-tool (TypeScript)

| 文件 | 说明 |
|------|------|
| `README.md` | 项目概述 (前500行) |
| `src/ast-analysis/engine.ts` | AST分析引擎 |
| `src/ast-analysis/visitors/cfg-visitor.ts` | CFG构建 |
| `src/ast-analysis/visitors/dataflow-visitor.ts` | DataFlow分析 |
| `src/cli/commands/mcp.ts` | MCP Server |

---

## 四、功能对比摘要

| 功能需求 | UA | graphify | CRG | ops-codegraph |
|----------|:--:|:---------:|:---:|:--------------:|
| **需求追溯** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐ |
| **爆炸半径** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **文档同步** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐ |
| **知识蒸馏** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **MCP Server** | ❌ | ✅ | ✅ 28 tools | ✅ 30+ tools |
| **CFG/DataFlow** | ❌ | ❌ | ❌ | ✅ |
| **多模态** | 图片 | 图片+视频+音频 | ❌ | ❌ |
| **语言支持** | 10 | 25 | 23 | 34 |

**结论:** UA 功能适配度最高 (20/20)，完美覆盖四个核心需求。

---

## 五、分析报告索引

| 报告 | 文件 | 说明 |
|------|------|------|
| 综合对比分析 | `COMPARATIVE_ANALYSIS.md` | 四项目完整对比 |
| 功能适配度分析 | `FEATURE_FIT_ANALYSIS.md` | 四核心需求适配度评分 |
| **讨论议程** | `DISCUSSION_AGENDA.md` | 待讨论问题 + 调研进展 |

---

## 六、注意事项

1. **浅克隆限制** — `--depth 1` 只下载最新版本，无历史提交。如需完整历史，去掉此参数
2. **graphify 警告** — 克隆时有 case-sensitive 路径冲突警告 (sample.F90/sample.f90)，Windows 上可忽略
3. **ops-codegraph-tool 体积** — 下载较慢 (933 files)，需耐心等待
4. **UA 依赖** — TypeScript 项目，需 Node.js >= 22 + pnpm >= 10

---

## 七、后续使用建议

阅读顺序推荐：

1. **先看 README.md** — 了解项目定位
2. **再看分析报告** — `COMPARATIVE_ANALYSIS.md` + `FEATURE_FIT_ANALYSIS.md`
3. **深入 UA** — 功能适配度最高，优先研究其 Schema 和 Skill 设计
4. **参考 ops-codegraph** — 如需 CFG/DataFlow，参考其实现
5. **参考 graphify** — 如需多模态或置信度分级，参考其设计