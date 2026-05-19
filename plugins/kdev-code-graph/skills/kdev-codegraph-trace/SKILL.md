---
name: kdev-codegraph-trace
description: 双向追溯安全规范与代码——给定一条 kdev-secure-coding 规则，找出代码里哪些函数/类实现/违反它；或给定一段代码，找出关联的安全规范条目。基于 .understand-anything/knowledge-graph.json + kdev:security_rule tag 节点。触发时机：用户说"这条规范在哪实现 / 这段代码涉及哪些安全规范 / 安全规范追溯 / 规范覆盖检查"，或对一段代码做安全审查需要查规范来源时。
---

# /kdev-codegraph-trace

> 节点 ID / tag 命名约定：详见 [conventions.md](../../references/conventions.md)

在 kdev 知识图谱（`.understand-anything/knowledge-graph.json`，由 `/kdev-codegraph-build` 构建）上做规范↔代码双向追溯。

图谱节点 ID 约定（速查表，完整定义见 [conventions.md](../../references/conventions.md)）：

| Kind | ID |
|---|---|
| 文件 | `file:<relative_path>` |
| 函数 | `function:<relative_path>:<name>` |
| 类 | `class:<relative_path>:<name>` |
| kdev 安全规则 | `kdev-sec:rule:<rule_id>` |
| kdev 漏洞 | `kdev-sec:vuln:<slug>` |

## 前置条件

`.understand-anything/knowledge-graph.json` 必须存在。如果不存在，先调 [`/kdev-codegraph-build`](../kdev-codegraph-build/SKILL.md)。

## 模式 1：规范 → 代码

**输入**：规则 ID（如 `3.1.1`）或规则名称片段（如「命令注入」）。

**步骤**：

1. 用 grep 在 `knowledge-graph.json` 中找带 `"kdev:rule_id:<id>"` 或 name 含关键词的节点，得到 rule node ID `kdev-sec:rule:<id>`。
2. 找所有 source 或 target 是该 rule node 的边：
   - `documents` 边 → 直接关联代码
   - `tested_by` 边 → 测试覆盖
3. 跨 1 跳邻居取 file/function/class 节点。
4. 输出 markdown 报告：

```markdown
# 安全规范 3.1.1「命令操作安全」追溯报告

> 摘要：<rule.summary>

## 直接关联的代码（N 处）

| 文件 | 函数/类 | 关系 | 信心 |
|---|---|---|---|
| app/web/api.py | execute_command | 实现 | weight=0.9 |

## 测试覆盖（M 处）

| 测试文件 | 测试函数 |
|---|---|
| tests/test_api.py | test_command_injection |

## 未覆盖警告

无关联代码——可能项目里没人实现这条规范，建议人工核对。
```

## 模式 2：代码 → 规范

**输入**：文件路径或函数节点 ID。

**步骤**：

1. 找 `file:<path>` 或 `function:<path>:<name>` 节点。
2. 找邻边：source 端是 `concept` 节点 + `kdev:security_rule` tag → 关联的规范。
3. 输出：

```markdown
# 代码 `app/web/api.py::execute_command` 关联的安全规范

| 规则 ID | 规则名 | 分类 | 来源 |
|---|---|---|---|
| 3.1.1 | 命令操作安全 | input_validation | kdev-secure-coding |

## 建议

如果该函数处理用户输入但未关联任何 input_validation 规范——建议人工补充。
```

## 失败处理

| 现象 | 应对 |
|---|---|
| 规则 ID 不存在 | 列出现有所有 `kdev:rule_id:*` 让用户选 |
| 没有任何关联边 | 不是错误——明确告诉用户「这条规范暂未在代码中关联」 |
| 图谱过期 | 提示用户跑 `/kdev-codegraph-build` 重建 |

## 不要做

- ❌ 不要凭空猜代码与规范的关联——只输出图谱里有的边
- ❌ 不要直接读源码做判断——这是 LLM 关联器的职责，kdev-codegraph-trace 只查图谱
