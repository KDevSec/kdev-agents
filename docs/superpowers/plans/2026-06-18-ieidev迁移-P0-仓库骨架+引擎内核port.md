# ieidev-team 迁移 P0 — 仓库骨架 + 引擎内核(ieidev_core) port 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development（推荐）or superpowers:executing-plans 逐任务实施。步骤用 checkbox（`- [ ]`）跟踪。

**Goal:** 在新仓库 `ieidev-team` 建好骨架，并把编排引擎 `kdev_core` 以「行为不变 + 全测试绿」的方式 port 成 `ieidev_core`，验证「copy→rename→tests green」迁移范式。

**Architecture:** clean-room 抽取——源仓 `/home/lyadmin/Projects/kdev-agents` 全程**只读不改**；目标在新本地仓 `/home/lyadmin/Projects/ieidev-team`（git init，后续 push 到 `KDevSec/ieidev-team`，push 前问用户）。python 包统一放 `pyieidev/` 根，前缀 `kdev_*`→`ieidev_*`、运行时目录 `.kdev/`→`.ieidev/`。

**Tech Stack:** Python 3.12 + pytest（无 pyproject，靠 PYTHONPATH）；Claude Code plugin（plugin.json + marketplace.json）。

## Global Constraints（每个任务隐含）

- **源仓 kdev-agents 零改动**——`plugins/**` 与 `.kdev/**` 只读参考，绝不写。
- **前缀映射（全程一致）**：python 包 `kdev_core`→`ieidev_core`；运行时目录 `.kdev/`→`.ieidev/`；CLI prog `kdev_core`→`ieidev_core`。
- **行为不变**：port 是保行为变换，验收 = 源仓那 22 个测试在新仓**原数量全绿**，不删测试、不改断言语义。
- **TDD 适配**：本阶段是「行为保持 port」，验收由**既有测试套**承担（非红绿新写）；真·红绿 TDD 留给后续 phase 的新建件（ieidev-spec / ieidev-qa）。
- **commit 用 AI 身份**：`git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit ...`（`-c` 值不加引号）。

---

## 迁移 roadmap（后续各 phase 各自成 plan，逐个写细+执行）

- **P0（本 plan）**：仓库骨架 + 引擎内核 `ieidev_core` port。
- P1：port 记忆底座 memory（含 76 hook + step-recorder agent，`.kdev/`→`.ieidev/`）+ ieidev_team / ieidev_hud / ieidev_ingestor 三 python 包。
- P2：port 能力 skill（secure-coding 含 KDevSec 规则原样、test-points/cases/ui/api/uicase/env-recon、code-graph 含 UA 依赖）+ 28 agent + node-table，namespace `kdev-team:*`→`ieidev-team:*`。
- P3：去第三方——新建 `ieidev-spec`（替 spec-kit，TDD）/ `ieidev-qa`（替 gstack-qa，TDD，playwright MCP）；fork `ieidev-frontend-design`（Apache2.0）；rewire req/dev/test agent 脱第三方；搬入 design-flow 5 模板（246 行）+ 删 9 处蓝本引用。
- P4：bootstrap CLI `npx ieidev-team` + `/ieidev-setup`（statusLine / PYTHONPATH / playwright MCP / UA 级联）。
- P5（事项2，迁移后）：CQO 监督员（另起 plan，依 CQO spec D-1~D-5 先决）。

---

## File Structure（本 plan 产出/触及）

新仓 `/home/lyadmin/Projects/ieidev-team/`：
- `.claude-plugin/plugin.json` — 单插件清单（name=ieidev-team）。
- `.claude-plugin/marketplace.json` — ieidev marketplace（单条目）。
- `.gitignore` — 含 `.ieidev/`、`__pycache__/`、`.pytest_cache/`。
- `README.md` — 一句话说明 + 来源溯源。
- `pyieidev/ieidev_core/` — 8 模块（cli/events/flow_state/gate/migrate/node_machine/__init__/__main__）port 自 `kdev_core`。
- `pyieidev/tests/` — 22 测试 port 自 `kdev-core/tests`（含 conftest/__init__）。

---

### Task 1: 新仓骨架（scaffold）

**Files:**
- Create: `/home/lyadmin/Projects/ieidev-team/.claude-plugin/plugin.json`
- Create: `/home/lyadmin/Projects/ieidev-team/.claude-plugin/marketplace.json`
- Create: `/home/lyadmin/Projects/ieidev-team/.gitignore`
- Create: `/home/lyadmin/Projects/ieidev-team/README.md`

**Interfaces:**
- Produces: 一个已 `git init` 的空插件仓，供后续 task 往 `pyieidev/` 灌 python 包。

- [ ] **Step 1: 建目录 + git init**

```bash
mkdir -p /home/lyadmin/Projects/ieidev-team/.claude-plugin /home/lyadmin/Projects/ieidev-team/pyieidev
cd /home/lyadmin/Projects/ieidev-team && git init
```

- [ ] **Step 2: 写 plugin.json**

```json
{
  "name": "ieidev-team",
  "description": "ieidev 数字员工集群（自包含单插件）：编排引擎 + 记忆底座 + 业务员工 + 能力 skill。从 KDevSec/kdev-agents clean-room 抽取通用化。",
  "version": "0.1.0",
  "author": { "name": "ly" },
  "license": "MIT",
  "keywords": ["digital-employee", "agent", "orchestration", "ieidev"]
}
```

- [ ] **Step 3: 写 marketplace.json**

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "ieidev",
  "description": "ieidev 数字员工集群 marketplace",
  "owner": { "name": "ly" },
  "plugins": [
    { "name": "ieidev-team", "description": "ieidev 数字员工集群（自包含单插件）", "category": "development", "source": "./" }
  ]
}
```

- [ ] **Step 4: 写 .gitignore**

```
.ieidev/
__pycache__/
*.pyc
.pytest_cache/
.venv/
```

- [ ] **Step 5: 写 README.md**

```markdown
# ieidev-team

ieidev 数字员工集群——自包含单插件（编排引擎 + 记忆底座 + 业务员工 + 能力 skill）。

从 [KDevSec/kdev-agents](https://github.com/KDevSec/kdev-agents) clean-room 抽取并通用化（去公司定制前缀、去第三方依赖、单插件化）。源仓保持冻结，本仓为通用产品going-forward 主线。
```

- [ ] **Step 6: 验收——结构存在**

Run: `cd /home/lyadmin/Projects/ieidev-team && git status && python3 -c "import json; json.load(open('.claude-plugin/plugin.json')); json.load(open('.claude-plugin/marketplace.json')); print('json ok')"`
Expected: git 显示 4 个 untracked 文件 + 打印 `json ok`

- [ ] **Step 7: Commit**

```bash
cd /home/lyadmin/Projects/ieidev-team && git add -A && git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "chore: ieidev-team 仓库骨架（plugin.json + marketplace + gitignore + README）"
```

---

### Task 2: port `kdev_core` → `ieidev_core`（引擎内核，行为不变）

**Files:**
- Create: `/home/lyadmin/Projects/ieidev-team/pyieidev/ieidev_core/{__init__,__main__,cli,events,flow_state,gate,migrate,node_machine}.py`（port 自源仓 `plugins/kdev-core/kdev_core/`）
- Create: `/home/lyadmin/Projects/ieidev-team/pyieidev/tests/`（port 自源仓 `plugins/kdev-core/tests/`，22 文件）

**Interfaces:**
- Consumes: Task 1 的 `pyieidev/` 目录。
- Produces: 可 `PYTHONPATH=pyieidev python -m ieidev_core ...` 调起的引擎；后续 phase 的 ieidev_team 会 `python -m ieidev_core` 驱动它。

- [ ] **Step 1: 拷贝源（只读源仓 → 新仓）**

```bash
cp -r /home/lyadmin/Projects/kdev-agents/plugins/kdev-core/kdev_core /home/lyadmin/Projects/ieidev-team/pyieidev/ieidev_core
cp -r /home/lyadmin/Projects/kdev-agents/plugins/kdev-core/tests /home/lyadmin/Projects/ieidev-team/pyieidev/tests
# 包目录名已随 cp 改为 ieidev_core；清理可能带入的缓存
find /home/lyadmin/Projects/ieidev-team/pyieidev -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; true
```

- [ ] **Step 2: 先跑一次，确认「未改名」必失败（建立 red 基线）**

Run: `cd /home/lyadmin/Projects/ieidev-team && PYTHONPATH=pyieidev python -m pytest pyieidev/tests/ -q 2>&1 | tail -15`
Expected: **FAIL**——大量 `ModuleNotFoundError: No module named 'kdev_core'`（测试与源码仍 import `kdev_core`，包已叫 `ieidev_core`）。这是改名前的预期红。

- [ ] **Step 3: 改名 import 与标识（kdev_core → ieidev_core）**

```bash
cd /home/lyadmin/Projects/ieidev-team
# 源码 + 测试里所有 kdev_core 标识 → ieidev_core（import / prog / from-import）
grep -rl "kdev_core" pyieidev/ | xargs sed -i 's/kdev_core/ieidev_core/g'
# 运行时数据目录 .kdev → .ieidev（flow_state.py 等）
grep -rl "\.kdev" pyieidev/ | xargs sed -i 's/\.kdev/.ieidev/g'
```

- [ ] **Step 4: 核对改名无残留**

Run: `cd /home/lyadmin/Projects/ieidev-team && { grep -rn "kdev_core" pyieidev/ || echo "NO kdev_core 残留"; } && { grep -rn "\.kdev/" pyieidev/ || echo "NO .kdev/ 残留"; }`
Expected: 两行都是 `NO ... 残留`（docstring 里的「kdev-core」中划线说明文字可留，不影响行为；只清 `kdev_core` 标识与 `.kdev/` 路径）

- [ ] **Step 5: 跑全测试套，确认全绿（验收核心）**

Run: `cd /home/lyadmin/Projects/ieidev-team && PYTHONPATH=pyieidev python -m pytest pyieidev/tests/ -q 2>&1 | tail -15`
Expected: **PASS**——passed 数 = 源仓 `kdev-core` 测试数（22 文件全收集、全绿，0 failed）

- [ ] **Step 6: 比对测试数量与源仓一致（port 保真）**

Run: `echo "源:" && cd /home/lyadmin/Projects/kdev-agents/plugins/kdev-core && PYTHONPATH=. python -m pytest tests/ --co -q 2>/dev/null | tail -1; echo "新:" && cd /home/lyadmin/Projects/ieidev-team && PYTHONPATH=pyieidev python -m pytest pyieidev/tests/ --co -q 2>/dev/null | tail -1`
Expected: 两行「collected N items」中的 **N 相等**（用例数一致，无遗漏）

- [ ] **Step 7: 冒烟——CLI 能起**

Run: `cd /home/lyadmin/Projects/ieidev-team && PYTHONPATH=pyieidev python -m ieidev_core --help 2>&1 | head -5`
Expected: 打印 usage，prog 名为 `ieidev_core`，无 traceback

- [ ] **Step 8: Commit**

```bash
cd /home/lyadmin/Projects/ieidev-team && git add -A && git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(ieidev_core): port kdev_core 引擎内核（rename kdev_core→ieidev_core / .kdev→.ieidev，22 测试全绿）"
```

---

## Self-Review

**1. Spec coverage（对 §0/§3/§5）**：本 plan 覆盖 §0 新仓+ieidev 改名（前缀/目录映射）、§5 打包（pyieidev 统一根、python 包改名）的**引擎内核片**；memory/能力/去第三方/bootstrap 在 roadmap P1-P4。✅ 范围自洽（产出一个可跑测试的 ieidev_core）。

**2. Placeholder scan**：无 TBD/TODO；每步有实际命令 + 预期输出。✅

**3. Type/命名一致**：全程 `kdev_core`→`ieidev_core`、`.kdev`→`.ieidev`、`pyieidev/` 根、`ly-AI` commit 身份，跨 Task 一致。✅

**4. 风险点**：① sed 改 `.kdev` 可能误伤 docstring 里非路径的 `.kdev` 文字——Step4 已核对（只要求 `.kdev/` 路径无残留，裸 `.kdev` 文字不影响行为）；② 若某测试硬编码绝对 `.kdev` 路径或依赖源仓 fixture，Step5 会暴露，按 systematic-debugging 处置（不弱化断言）。
