---
name: kdev-codegraph-build
description: 在当前项目构建代码知识图谱（先调 UA /understand 建基础图，再用 kdev-ingestor 灌入 kdev-secure-coding 的安全规范节点）。触发时机：用户说"建图谱 / 建立代码图谱 / 跑 understand / 灌安全规范 / 准备追溯"，或第一次使用 kdev-codegraph-trace / kdev-codegraph-impact / kdev-codegraph-doc-sync 但 .understand-anything/knowledge-graph.json 不存在时。
---

# /kdev-codegraph-build

构建可供 kdev-code-graph 其他 skill 使用的代码知识图谱。

## Step 1：检查前置依赖

```bash
node --version  # 需要 >= 22
ls ~/.claude/plugins/cache/understand-anything/ 2>/dev/null && echo "UA installed" || echo "UA NOT installed"
```

UA 未装时引导用户：

```
/plugin marketplace add Lum1104/Understand-Anything
/plugin install understand-anything
```

## Step 2：调 UA 建基础图谱

按 [_ua_adapter](../_ua_adapter/SKILL.md) 调 `/understand`。透传 `--full` / 项目路径等参数。

跑完确认：

```bash
test -f .understand-anything/knowledge-graph.json && echo "graph ready"
```

## Step 3：灌入 kdev 安全规范节点

**Bash / macOS / Linux:**

```bash
KDEV_RULES_DIR="<repo>/plugins/kdev-secure-coding/skills/python-security-coding/references"
INGESTOR="${CLAUDE_PLUGIN_ROOT:-plugins/kdev-code-graph}/ingestor/run.py"
python3 "$INGESTOR" inject \
    --rules-dir "$KDEV_RULES_DIR" \
    --graph .understand-anything/knowledge-graph.json
```

**PowerShell / Windows:**

```powershell
$KdevRulesDir = "<repo>\plugins\kdev-secure-coding\skills\python-security-coding\references"
$Ingestor = if ($env:CLAUDE_PLUGIN_ROOT) { "$env:CLAUDE_PLUGIN_ROOT\ingestor\run.py" } else { "plugins\kdev-code-graph\ingestor\run.py" }
& py -3 $Ingestor inject --rules-dir $KdevRulesDir --graph .understand-anything\knowledge-graph.json
```

预期：`injected N rule node(s) into ...`，N ≥ 8。

## Step 4：核对结果

**Bash / macOS / Linux:**

```bash
python3 "$INGESTOR" list-tags --graph .understand-anything/knowledge-graph.json
```

**PowerShell / Windows:**

```powershell
& py -3 $Ingestor list-tags --graph .understand-anything\knowledge-graph.json
```

至少看到：`kdev:security_rule` / `kdev:rule_id:*` / `kdev:category:*` / `kdev:source:kdev-secure-coding`。

## Step 5：报告

向用户输出 markdown 表格：

| 指标 | 值 |
|---|---|
| 总节点数 | <N> |
| UA 节点 | <N> |
| kdev 安全规则节点 | <N> |
| 总边数 | <N> |
| 图谱文件 | `.understand-anything/knowledge-graph.json` |

并提示：
- 想看「这条规范在哪些代码里实现」→ `/kdev-codegraph-trace`
- 想看「改这段代码会影响哪些规范」→ `/kdev-codegraph-impact`
- 想看「文档代码哪些脱节」→ `/kdev-codegraph-doc-sync`

## 失败处理

| 现象 | 应对 |
|---|---|
| UA 未装 | Step 1 安装指令 |
| `/understand` 失败 | 看 UA 错误，常见 `pnpm install` 没跑 |
| ingestor 报 `dangling source` | 图谱不完整，重跑 `/understand --full` |
| ingestor `unknown node type` | UA 升级了——跑 `pytest plugins/kdev-code-graph/tests/contract -v` 定位 |

## 不要做

- ❌ 用户没说"建图"时不要主动跑——`/understand` 重建慢
- ❌ 不要直接编辑图谱 JSON——用 ingestor
- ❌ 不要假设规则目录路径——总是先确认
