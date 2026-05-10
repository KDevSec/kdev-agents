---
name: _ua_adapter
description: Internal adapter — describes how kdev-code-graph skills call Understand-Anything (UA) commands. Other kdev skills MUST go through this contract instead of hard-coding UA commands. Auto-trigger when another kdev-code-graph skill needs to invoke /understand /understand-diff /understand-domain /understand-knowledge or read .understand-anything/knowledge-graph.json.
---

# UA Adapter（内部协议层）

## 用途

kdev-code-graph 不重新实现代码图谱。所有图谱构建/查询都委托给 [Understand-Anything](https://github.com/Lum1104/Understand-Anything) (UA)。本 skill 是 **唯一允许直接调用 UA 命令的接口**——其他 kdev skill 必须通过本文档约定来调，不得直接 hard-code UA 命令名/参数/路径。

**Why:** UA 是上游开源项目，命令名/参数会变。把所有调用集中在 adapter，UA 升级时只改这一处。

## 调用约定

### 1. 构建图谱：`/understand [path] [--full|--review]`

- 输出物：`<path>/.understand-anything/knowledge-graph.json`
- 调本 skill 前先 `test -f` 判断是否已建图

### 2. 爆炸半径：`/understand-diff`

- 前置：图谱已存在
- 自动读 git diff，输出 markdown

### 3. 业务领域提取：`/understand-domain`

- 前置：图谱已存在
- 输出 `domain` / `flow` / `step` 节点

### 4. 知识 wiki 蒸馏：`/understand-knowledge`

- 前置：图谱已存在
- 输出 `article` / `entity` / `topic` / `claim` / `source` 节点

### 5. 直接读图谱 JSON

只读查询应当 grep / Read `.understand-anything/knowledge-graph.json`，不调命令。

**节点 ID 模式**：

| Kind | ID |
|---|---|
| 文件 | `file:<relative_path>` |
| 函数 | `function:<relative_path>:<name>` |
| 类 | `class:<relative_path>:<name>` |
| kdev 安全规则 | `kdev-sec:rule:<rule_id>` |
| kdev 漏洞 | `kdev-sec:vuln:<slug>` |

**节点必填字段**：`id` / `type` / `name` / `summary` / `tags` / `complexity`

**节点 type 白名单**（21 种）—— [graph_io.py:UA_NODE_TYPES](../../ingestor/kdev_ingestor/graph_io.py)
**边 type 白名单**（35 种）—— [graph_io.py:UA_EDGE_TYPES](../../ingestor/kdev_ingestor/graph_io.py)

## 灌入 kdev 安全节点

不要直接编辑 `knowledge-graph.json`。用 ingestor CLI：

    cd <project_root>
    python -m kdev_ingestor.cli inject \
        --rules-dir <kdev-secure-coding>/skills/python-security-coding/references \
        --graph .understand-anything/knowledge-graph.json

ingestor 保证：节点 type 用 UA `concept`、安全语义用 `kdev:*` tag、按 `id` upsert 幂等。

## tag 命名约定

详见 [tags.py](../../ingestor/kdev_ingestor/tags.py)：

| Tag | 含义 |
|---|---|
| `kdev:security_rule` | 节点是安全规范条目 |
| `kdev:vulnerability` | 节点是漏洞 |
| `kdev:compliance` | 节点是合规要求 |
| `kdev:rule_id:<id>` | 规则 ID |
| `kdev:category:<slug>` | 一级分类 |
| `kdev:severity:<level>` | high/medium/low |
| `kdev:source:<plugin>` | 数据来源 |

## 升级 UA 上游

1. 跑 `pytest plugins/kdev-code-graph/tests/contract -v` 看护栏
2. 若 contract test 失败：
   - 节点/边白名单变 → 更新 [graph_io.py](../../ingestor/kdev_ingestor/graph_io.py)
   - `passthrough()` 移除 → 紧急评估，参考 [实施计划 v2 §决策树](../../../../docs/skills/kdev-code-graph/2026-05-10-实施计划-v2.md)
3. 命令名变 → 改本文件 + 引用本文件的 skill

## 不要做

- ❌ 不要在其他 skill 里直接调 UA 命令——从本 adapter 引用
- ❌ 不要新增 UA 之外的节点/边类型（白名单严格）
- ❌ 不要直接写 `knowledge-graph.json`——用 ingestor CLI
