---
name: doc-code-sync
description: 检查项目文档（PRD/设计/spec markdown）与代码的同步状态——基于 UA /understand 建出的 document 节点 + documents 边，比对 git 时间戳与图谱信心度，识别「✅同步 / ⚠️需更新 / ❌缺实现 / 🔍缺文档」四种状态。触发时机：用户说"文档代码同步检查 / 文档过期了吗 / docs 审计 / spec 漂移 / 有哪些 PRD 没实现"，或对一份 PRD 做实现状态盘点时。
---

# /doc-code-sync

按 UA 知识图谱里的 `document` 节点逐份核对，识别四种状态：

| 状态 | 含义 |
|---|---|
| ✅ 同步 | 文档时间戳 ≥ 关联代码时间戳；存在 `documents` 边；信心 ≥ 0.7 |
| ⚠️ 需更新 | 关联代码时间戳 > 文档时间戳超过 N 天 |
| ❌ 缺实现 | 文档存在但无关联代码 |
| 🔍 缺文档 | 代码有 file/function 但无 `document` 节点对其负责 |

## 前置条件

- 图谱已建好
- 当前在 git 仓库

## 流程

### Step 1：列所有 document 节点

```bash
grep -A 5 '"type": "document"' .understand-anything/knowledge-graph.json | head -50
```

### Step 2：每份 doc 拉 git mtime

```bash
git log -1 --format=%ct -- "<doc-path>"
```

### Step 3：找 document → code 的边

按 [_ua_adapter](../_ua_adapter/SKILL.md) 中 ID 命名约定，找所有 `documents` 类型且 source/target 之一是当前 doc 的边。

### Step 4：每个关联 code 节点拉 git mtime（取最大值）

### Step 5：状态判定

| 条件 | 状态 |
|---|---|
| 没有任何 `documents` 边 | ❌ 缺实现 |
| `code_mtime > doc_mtime + 30d` | ⚠️ 需更新 |
| 否则 | ✅ 同步 |

代码侧：找 `kind == "codebase"` 节点中没被任何 `documents` 边覆盖的 file/function/class → 🔍 缺文档（按文件聚合）。

### Step 6：输出报告

```markdown
# 文档-代码同步审计报告

## 摘要

| 状态 | 数量 |
|---|---|
| ✅ 同步 | 12 |
| ⚠️ 需更新 | 3 |
| ❌ 缺实现 | 2 |
| 🔍 缺文档 | 8（按文件聚合） |

## 详情

### ⚠️ 需更新（3）

| 文档 | 文档时间 | 代码最新时间 | 漂移天数 | 建议 |
|---|---|---|---|---|
| docs/auth-spec.md | 2025-12-01 | 2026-04-22 | 142 | 立即处理 |

### ❌ 缺实现（2）

| 文档 | 关联节点数 |
|---|---|
| docs/proposed-feature-x.md | 0 |

### 🔍 缺文档（按文件聚合）

| 文件 | 节点数 | 建议 |
|---|---|---|
| app/billing/refund.py | 5 | 写 refund 流程 doc |

## 推荐处理顺序

1. 立即处理（漂移 > 90 天 OR 涉及 kdev:security_rule 关联）
2. 本周处理（30-90 天）
3. 后续处理（缺文档但模块稳定）
```

## 漂移阈值

可调，默认警示 30 天 / 严重 90 天。

## 与 trace-security 协同

如果 doc 关联到带 `kdev:security_rule` tag 的节点 → 漂移阈值降为 14 天。

## 失败处理

| 现象 | 应对 |
|---|---|
| 图谱无 `document` 节点 | 用户项目可能没在 `/understand` 配置文档目录——重跑 `/understand --full` |
| git mtime 拉不到 | 文件未提交——按当前 mtime |

## 不要做

- ❌ 不要扫所有 .md——只信图谱里的 `document` 节点
- ❌ 不要按函数级别刷"缺文档"——按文件聚合
- ❌ 不要在「缺文档」误报 generated 文件（如 migrations / __pycache__）
