---
name: kdev-codegraph-build
description: 在当前项目构建代码知识图谱（先调 UA /understand 建基础图，再用 kdev-ingestor 灌入 kdev-secure-coding 的安全规范节点）。触发时机：用户说"建图谱 / 建立代码图谱 / 跑 understand / 灌安全规范 / 准备追溯"，或第一次使用 kdev-codegraph-trace / kdev-codegraph-impact / kdev-codegraph-spec-link 但 .understand-anything/knowledge-graph.json 不存在时。
---

# /kdev-codegraph-build

> 节点 ID / tag 命名约定：详见 [conventions.md](../../references/conventions.md)

构建可供 kdev-code-graph 其他 skill 使用的代码知识图谱。

## Step 0：前置面板（人友好知情同意）

向用户展示：

```markdown
## 即将执行: /kdev-codegraph-build

### 这次会做什么
1. **UA `/understand`**：全库语义分析，产 `.understand-anything/knowledge-graph.json`（每个文件由 LLM file-analyzer agent 分析）
2. **ingestor inject**：把 kdev-secure-coding 安全规则灌成 concept 节点（本地，0 LLM）
3. **ingestor link**：模式匹配把规则连到使用了点名 API 的代码（本地，0 LLM）

### 成本提示 🔴 重要
- **UA 全库语义分析会派出几十~上百个 file-analyzer subagent**
- **强烈建议不要在按"请求次数"计费的 coding plan 上跑** —— 配额会被快速打空
- 推荐：切到 API 计费，或对增量项目用 `/understand`（UA 默认增量），别用 `--full` 除非必要
- 估算耗时：中等项目首次 build 可能数分钟到数十分钟

### 这次会产生
- `.understand-anything/knowledge-graph.json`（主图谱）
- 含 N 条安全规则节点 + M 条 related 边（模式命中）

### 跑完后你可以做的事
- `/kdev-codegraph-trace` —— 安全规则 ↔ 代码双向追溯
- `/kdev-codegraph-impact` —— 变更安全爆炸半径分析
- `/kdev-codegraph-spec-link` —— spec ↔ 代码对齐审计（也烧 LLM，按需跑）
```

用户 `n` → 退出。`y` → 进入 Step 1。

`--yes` 跳过此 prompt。

---

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

调 UA skill `/understand`（即 understand-anything 插件的 `/understand` 命令）建基础图谱。透传 `--full` / 项目路径等参数。

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

## Step 3.5：连边（安全规则 → 代码）

inject 只灌规则节点，需再跑 `link` 把规则连到使用了其点名 API 的代码节点（产 `related` 边）。

**Bash / macOS / Linux:**

```bash
python3 "$INGESTOR" link \
    --rules-dir "$KDEV_RULES_DIR" \
    --graph .understand-anything/knowledge-graph.json \
    --source-root .
```

**PowerShell / Windows:**

```powershell
& py -3 $Ingestor link --rules-dir $KdevRulesDir --graph .understand-anything\knowledge-graph.json --source-root .
```

预期：`linked N security edge(s) into ...`。N=0 不是错误（可能项目没用到规则点名的 API，或规则无 pattern）。

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
| 安全关联边(related) | <N> |
| 图谱文件 | `.understand-anything/knowledge-graph.json` |

并提示：
- 想看「这条规范在哪些代码里实现」→ `/kdev-codegraph-trace`
- 想看「改这段代码会影响哪些规范」→ `/kdev-codegraph-impact`
- 想看「spec ↔ code 对齐审计 / 哪些需求没实现」→ `/kdev-codegraph-spec-link`

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
