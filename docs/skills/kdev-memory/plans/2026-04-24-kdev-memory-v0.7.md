# kdev-memory v0.7 立场反转与机制重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 发布 kdev-memory v0.7 —— 把 `.kdev/` 的定位从"git 托管的项目资产"反转为"本地过程目录"；同时引入销账语义、Brief 三层分层、沉淀（promote）机制、手动周总结（rolling 7 天）命令，并修复 Brief hook 两个长期 bug。

**Architecture:**
- **过程/产物分家**：`.kdev/` 是个人过程草稿（默认 gitignore），团队共享通过 `docs/` 等产物通道；需要沉淀的条目通过 `/kdev-memory-promote` 半自动流转
- **Brief 三层分层**：P0 硬阻塞（当前会话可能丢数据）/ P1 需核对（疑似遗漏）/ P2 仅报告（历史存量），替代当前"字面 grep 平铺"模式
- **销账语义双轨**：B（启发式 grep `褪色补录 / 保留占位 / 非原生当场采集 / ## Step M-`）+ C（frontmatter `status: open|scored|voided-faded|voided-r-nnn`），历史条目走 B 零迁移，新条目走 C 结构化
- **SessionEnd 去 git 依赖**：从 `git status --porcelain` 改为 `.last-flush` mtime 比对，反转立场后 `.kdev/` 不再被 git tracked 也能工作

**Tech Stack:** Bash 5+、Python 3.11+（hooks/lib/*.py）、pytest（`plugins/kdev-memory/tests/`）、Claude Code plugin slash command（新增 `commands/` 目录）。

---

## Pre-Work

### Task 0: 起独立 worktree + 创建 release 分支

**Rationale**: v0.7 涉及 8+ 个文件的跨 phase 协同改动，直接在 main 上容易误伤。主仓库 `main` 当前有 3 个未 commit 的 dev-note，先在 worktree 里隔离 v0.7 工作，main 上继续做其他。

- [ ] **Step 0.1: 从项目根起 worktree**

```bash
cd /home/lyadmin/Projects/kdev-agents
git worktree add ../kdev-agents-v0.7 -b kdev-memory-v0.7
cd ../kdev-agents-v0.7
```

Expected: `../kdev-agents-v0.7/` 创建成功，当前目录切到 worktree 根。

- [ ] **Step 0.2: 验证 worktree 正常**

```bash
git status
git log --oneline -5
```

Expected: 分支 `kdev-memory-v0.7`，基于 main 最新 commit（`35dd341` 或更新）。

---

## Phase 1: Schema 扩展（纯文档）

### Task 1: 在 SKILL.md 里加 status / promote_* schema 定义

**Files:**
- Modify: `plugins/kdev-memory/skills/kdev-memory/SKILL.md`（在"六类记录的触发时机总览"表后、"triggers 写法要点"前新增一节）

**Rationale**: Schema 先行。v0.7 的 Brief 分层、promote 机制、销账跳过都依赖这两类字段；先把字段定义写进 SKILL.md，后续 hook 代码 reference 这里。

- [ ] **Step 1.1: 打开 SKILL.md 定位插入点**

SKILL.md 第 143 行（"六类记录要点速览"段结束）之后、第 161 行（"triggers 写法要点"之前）之间，新增一整节。

- [ ] **Step 1.2: 插入新章节"条目状态与沉淀字段（v0.7+）"**

在 SKILL.md `> 每类的完整格式、字段语义、设计意图、锁定铁规细节见 **\`references/六类记录-schema.md\`**。`（第 159 行）**之后**插入：

```markdown

## 条目状态与沉淀字段（v0.7+）

Step / Q-NNN / G-NNN / R-NNN / 改进建议条目的 frontmatter 新增两组字段，服务于 **销账语义** 和 **沉淀（promote）机制**。

### status 字段（销账语义）

```yaml
---
status: open | scored | voided-faded | voided-r-nnn
---
```

| 取值 | 含义 | 适用时机 |
|---|---|---|
| `open` | 进行中 / 待评分 | 默认（未填等价于 open） |
| `scored` | 评分完整已闭环 | Step 四段填齐后填 |
| `voided-faded` | 褪色补录占位，不强求补 | iter meta 回补、跨多日才补的条目 |
| `voided-r-nnn` | 显式 R-NNN 销账 | 用户要求跳过评分、强行开下一步时 |

**Hook 行为**：Brief 的"欠评 Step"扫描优先读 `status` 字段，`voided-*` 一律跳过；读不到 `status` 字段时 fallback 启发式（grep `褪色补录` / `保留占位` / `非原生当场采集` / `## Step M-`）——历史条目（v0.6 及以前写的）零迁移成本。

### promote_* 字段（沉淀机制）

适用于改进建议.md 的 R-NNN、conventions.md §11 的 R-NNN、决策日志.md 的 Q-NNN、踩坑日志.md 的 G-NNN：

```yaml
---
promote_status: pending | done | skipped
promote_target: docs/05-报告/实战总结.md  # 结晶后填
promote_date: 2026-04-24                   # 结晶完成日期
---
```

| 取值 | 含义 |
|---|---|
| `pending` | 待沉淀（默认值，未填等价于 pending） |
| `done` | 已沉淀到 `promote_target` 指向的 docs 路径 |
| `skipped` | 明确决定不沉淀（用 `promote_target` 存放理由：如 "个人细节，无团队价值"） |

**Hook 行为**：Brief 的 P1 层扫描所有 `pending` 条目，统计数量；超过阈值（改进建议 3+ / R-NNN 2+ / G-NNN 5+，或距上次沉淀 > 7 天）时提醒用户执行 `/kdev-memory-promote`。超过 30 天未沉淀升 P0。
```

- [ ] **Step 1.3: 校验 SKILL.md 渲染正常**

```bash
cd plugins/kdev-memory/skills/kdev-memory
head -250 SKILL.md | tail -100
```

Expected: 新章节嵌入自然，"条目状态与沉淀字段"在"六类记录要点速览"之后、"triggers 写法要点"之前。

- [ ] **Step 1.4: Commit**

```bash
git add plugins/kdev-memory/skills/kdev-memory/SKILL.md
git commit -m "docs(kdev-memory): SKILL.md 加 status / promote_* schema 定义（v0.7 前置）"
```

---

### Task 2: references/六类记录-schema.md 同步 frontmatter 字段

**Files:**
- Modify: `plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md`

**Rationale**: SKILL.md 只点到为止，真正 schema 细则在 references 目录。v0.7 字段扩展必须同步 reference，否则 Claude 在初始化项目时拿不到完整字段表。

- [ ] **Step 2.1: 核查 reference 文件存在**

```bash
ls plugins/kdev-memory/skills/kdev-memory/references/
```

Expected: 看到 `六类记录-schema.md`（若不存在，本任务跳过，字段定义仅留在 SKILL.md）。

- [ ] **Step 2.2: 读文件找 Step / Q / G / R 各段的 frontmatter 示例**

```bash
grep -n "^---$\|^##\|frontmatter\|status:\|promote_" plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md | head -60
```

记录：每段 frontmatter 示例块的行号，准备在每个块里追加 `status` 和 `promote_*` 字段。

- [ ] **Step 2.3: 在每个 frontmatter 示例里追加字段**

**Step 段** 的 frontmatter 示例里追加：
```yaml
status: open  # v0.7+，填完评分后改 scored；褪色补录用 voided-faded
```

**R-NNN / Q-NNN / G-NNN 段** 的 frontmatter 示例里追加：
```yaml
status: open  # v0.7+
promote_status: pending  # v0.7+
```

**改进建议.md** 每条建议（#N）的 frontmatter 示例追加：
```yaml
promote_status: pending  # v0.7+
```

每处修改之后附一行说明：
> v0.7+ 新增。详见 SKILL.md「条目状态与沉淀字段」节。字段缺失等价于 `status: open` / `promote_status: pending`，历史条目无需手工迁移。

- [ ] **Step 2.4: Commit**

```bash
git add plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md
git commit -m "docs(kdev-memory): reference schema 同步 status / promote_* 字段（v0.7 前置）"
```

---

## Phase 2: 启发式销账跳过 + status 字段优先级（TDD）

### Task 3: 写失败测试 —— 褪色补录 Step 不被报欠评

**Files:**
- Create: `plugins/kdev-memory/tests/test_step_completeness_voided.py`

**Rationale**: note-2（`2026-04-24-brief-hook-欠评step误报...md`）的核心用例。先造失败测试：一个 M-5 褪色补录 Step，当前 `check_step` 会把它当半残报。

- [ ] **Step 3.1: 创建测试文件**

```python
"""test step_completeness 识别褪色补录销账（v0.7 新增）

背景：v0.6 及以前 step_completeness.check_step 只看字面 "完成时间：—"
就报欠评，导致 iter 5~8 的 meta 回补条目（Step M-5~M-8）被反复报"待处理"。
v0.7 要求 check_step 在"空完成时间"命中后再扫销账信号，任一命中即跳过。
"""

import sys
from pathlib import Path

HOOK_LIB = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(HOOK_LIB))

import step_completeness  # noqa: E402


def _write_log(tmp_path: Path, content: str) -> Path:
    log = tmp_path / "执行日志.md"
    log.write_text(content, encoding="utf-8")
    return log


def test_faded_backfill_step_is_not_half_complete(tmp_path):
    """褪色补录 Step（含 **褪色补录** / 保留占位 / 非原生当场采集 任一标记）应被跳过。"""
    log = _write_log(tmp_path, """## Step M-5（回补 meta）: iter-5 主控零评分兜底

日期：2026-04-15

### 执行事实
- 工具调用：—
- 使用的 skill：kdev-memory

### 模型自评
- 顺畅度：—/5
- 扣分项：—

### 用户评分
- 完成时间：—
- 顺畅度：—/5（**褪色补录**，距今 6~7 天；保留占位不强求补）
- 用户评价：—

> 🔴 回补声明：非原生当场采集

### 评分差异分析
- 无原生评分 → 不计入差值
""")
    result = step_completeness.run_check(log, "2026-04-24")
    assert result["status"] == "ok", (
        f"褪色补录 Step 应被识别为已销账，当前 half_complete: "
        f"{result['half_complete_steps']}"
    )


def test_m_prefix_step_is_not_half_complete(tmp_path):
    """Step 标题含 M- 前缀（meta 回补标识）就应跳过，哪怕没有其他销账关键词。"""
    log = _write_log(tmp_path, """## Step M-7 meta 回补

日期：2026-04-19

### 用户评分
- 完成时间：—
- 顺畅度：—/5
""")
    result = step_completeness.run_check(log, "2026-04-24")
    assert result["status"] == "ok", (
        f"M- 前缀 Step 应被识别为 meta 回补占位，当前 half_complete: "
        f"{result['half_complete_steps']}"
    )


def test_genuine_open_step_still_reported(tmp_path):
    """真正欠评的 Step（没有任何销账标记）还是要报 —— 启发式不能过度跳过。"""
    log = _write_log(tmp_path, """## Step 20: collector v1.4 重构

日期：2026-04-24

### 模型自评
- 顺畅度：4/5
- 扣分项：一次 import 路径错

### 用户评分
- 完成时间：—
- 顺畅度：—/5
- 用户评价：—
""")
    result = step_completeness.run_check(log, "2026-04-24")
    assert result["status"] == "has_half_complete", (
        f"真正欠评的 Step 应被报，当前 status: {result['status']}"
    )
    assert any(s["step_label"] == "Step 20" for s in result["half_complete_steps"])


def test_status_voided_faded_frontmatter_skipped(tmp_path):
    """Step body 里的 YAML frontmatter status: voided-faded 应直接跳过（不依赖启发式）。"""
    log = _write_log(tmp_path, """## Step M-6（回补 meta）: iter-6

---
status: voided-faded
---

日期：2026-04-17

### 用户评分
- 完成时间：—
- 顺畅度：—/5
""")
    result = step_completeness.run_check(log, "2026-04-24")
    assert result["status"] == "ok", (
        f"status=voided-faded 应被直接跳过，当前 half_complete: "
        f"{result['half_complete_steps']}"
    )


def test_status_open_with_missing_fields_still_reported(tmp_path):
    """status=open 且真的字段缺 → 仍然要报（status=open 不是免死金牌）。"""
    log = _write_log(tmp_path, """## Step 21: 真正欠评

---
status: open
---

日期：2026-04-24

### 用户评分
- 完成时间：—
- 顺畅度：—/5
""")
    result = step_completeness.run_check(log, "2026-04-24")
    assert result["status"] == "has_half_complete"
```

- [ ] **Step 3.2: 运行测试验证 4 条 FAIL、1 条 PASS**

```bash
cd plugins/kdev-memory
python3 -m pytest tests/test_step_completeness_voided.py -v
```

Expected:
- `test_faded_backfill_step_is_not_half_complete` → **FAIL**（当前没有销账识别）
- `test_m_prefix_step_is_not_half_complete` → **FAIL**
- `test_genuine_open_step_still_reported` → **PASS**（现有行为就是报）
- `test_status_voided_faded_frontmatter_skipped` → **FAIL**
- `test_status_open_with_missing_fields_still_reported` → **FAIL**（可能是 FAIL 或 PASS，取决于当前 frontmatter 是否被当作 body 扫描——两种都合理，先跑一遍看）

- [ ] **Step 3.3: Commit failing tests**

```bash
git add plugins/kdev-memory/tests/test_step_completeness_voided.py
git commit -m "test(kdev-memory): 褪色补录 / M- 前缀 / status 字段销账识别的失败测试"
```

---

### Task 4: 在 step_completeness.py 里实现启发式 + status 字段跳过

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/step_completeness.py`

**Rationale**: 让 Task 3 的失败测试通过。改动集中在 `check_step()` 入口和 `parse_steps()` 提取 `status` 字段。

- [ ] **Step 4.1: 在模块顶部加销账关键词常量**

在 `step_completeness.py` 第 54 行（`DEFAULT_LOOKBACK_DAYS = 14` 之后）之前插入：

```python
# v0.7+ 销账信号
VOIDED_HEURISTIC_PATTERNS = (
    "**褪色补录**",      # Brief 模板语（最强信号）
    "褪色补录",           # 不带 ** 的纯文字
    "保留占位不强求补",
    "保留占位",
    "非原生当场采集",
    "无原生评分",
    "不计入差值",
)

VOIDED_STATUSES = {"voided-faded", "voided-r-nnn"}
```

- [ ] **Step 4.2: 在 parse_steps 里提取每条 Step 的 frontmatter status 字段**

找到 `parse_steps` 函数（第 57~87 行），在 `steps.append({...})` 之前加 frontmatter 提取：

```python
        # v0.7+: 提取 Step body 内的 frontmatter status 字段（若有）
        status_m = re.search(
            r"^---\s*$\n(.*?)^---\s*$",
            body,
            re.MULTILINE | re.DOTALL,
        )
        entry_status = None
        if status_m:
            fm_text = status_m.group(1)
            sf = re.search(r"^\s*status\s*:\s*(\S+)", fm_text, re.MULTILINE)
            if sf:
                entry_status = sf.group(1).strip()

        steps.append({
            "label": label,
            "title": title,
            "date": entry_date,
            "body": body,
            "status": entry_status,  # 新增
        })
```

- [ ] **Step 4.3: 在 check_step 函数开头加销账早退**

找到 `check_step` 函数（第 90 行），在 `body = step["body"]` 之后插入：

```python
def check_step(step: dict[str, Any]) -> list[str]:
    """返回该 Step 的 issues 列表（空表示无半残）。"""
    body = step["body"]

    # v0.7+: status 字段优先（schema 层，C 方案）
    if step.get("status") in VOIDED_STATUSES:
        return []

    # v0.7+: 启发式销账识别（文字层，B 方案，兼容历史条目）
    # 命中任一销账文字信号 → 跳过
    for pat in VOIDED_HEURISTIC_PATTERNS:
        if pat in body:
            return []

    # v0.7+: Step 标题带 M- 前缀的 meta 回补条目，直接跳过
    # （label 形如 "Step M-5" / "Step M-7"）
    if re.match(r"^Step\s+M-", step["label"]):
        return []

    issues: list[str] = []
    # ...（保留原有检测逻辑）
```

- [ ] **Step 4.4: 运行测试验证全部 PASS**

```bash
cd plugins/kdev-memory
python3 -m pytest tests/test_step_completeness_voided.py -v
```

Expected: 5 条全部 PASS。

- [ ] **Step 4.5: 运行全部测试确认没回归**

```bash
cd plugins/kdev-memory
python3 -m pytest tests/ -v
```

Expected: 现有三个测试（`test_step_completeness.py` / `test_trigger_match.py` / `test_claude_md_lint.py`）全部仍 PASS。

- [ ] **Step 4.6: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/step_completeness.py
git commit -m "feat(kdev-memory): step_completeness 加销账识别 —— status 字段优先 + 启发式兜底"
```

---

## Phase 3: Brief 三层分层 + 两个长期 bug

### Task 5: 定位 note-2 里的"Step 编号 M- 误合成 11-12"bug

**Rationale**: note-2 §根因-2 说 brief 把 `Step M-5 ~ M-8` 识别成 "Step 11-12"。刚读过的 `step_completeness.py` 的 regex `r"^##\s+(Step\s+[\w\-\.]+)..."` 其实**支持** `Step M-7`——所以 bug 不在 `parse_steps`，而是更可能在 `session-start-brief.sh` 的显示层合并逻辑、或者 trigger-match。先定位。

- [ ] **Step 5.1: 核查 step_completeness 对 M- 编号的 parse 行为**

```bash
cd plugins/kdev-memory
python3 -c "
import sys
sys.path.insert(0, 'hooks/lib')
import step_completeness
log = '''## Step M-5（回补 meta）: foo

日期：2026-04-15

### 用户评分
- 完成时间：—
- 顺畅度：—/5

## Step M-6: bar

日期：2026-04-17
'''
from pathlib import Path
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
    f.write(log); p = Path(f.name)
result = step_completeness.run_check(p, '2026-04-24')
for s in result['half_complete_steps']:
    print(s['step_label'], '|', s['date'])
"
```

Expected: 输出 `Step M-5 | 2026-04-15` 和 `Step M-6 | 2026-04-17`（独立条目，编号无合并）。

**如果输出正确** → bug 不在 Python，在 shell（`session-start-brief.sh` 的 STEP_HINT 字符串处理），记录为 Task 6 待修。

**如果输出错误** → bug 还在 Python，在 Task 6 修 Python 即可。

- [ ] **Step 5.2: 检查 format_hint_for_brief 的输出是否正确**

```bash
cd plugins/kdev-memory
python3 -c "
import sys
sys.path.insert(0, 'hooks/lib')
import step_completeness
result = {
    'status': 'has_half_complete',
    'half_complete_steps': [
        {'step_label': 'Step M-5', 'date': '2026-04-15', 'title': 'foo', 'issues': ['用户评分段「完成时间」为 空']},
        {'step_label': 'Step M-6', 'date': '2026-04-17', 'title': 'bar', 'issues': ['用户评分段「完成时间」为 空']},
        {'step_label': 'Step M-7', 'date': '2026-04-19', 'title': 'baz', 'issues': ['用户评分段「完成时间」为 空']},
        {'step_label': 'Step M-8', 'date': '2026-04-20', 'title': 'qux', 'issues': ['用户评分段「完成时间」为 空']},
    ],
    'total_scanned': 4,
}
print(step_completeness.format_hint_for_brief(result))
"
```

Expected: 输出 4 条独立 `Step M-5` ~ `Step M-8` 各一行，**不是** `Step 11-12` 合并。

记录实际输出到 plan 备忘；若是合并，bug 在 Python format_hint；若正确，bug 在 shell（Task 6 重写 brief 时一并解决）。

- [ ] **Step 5.3: 如果 Python 层正常，用 shell 模拟 brief 输出复现 bug**

```bash
cd plugins/kdev-memory
mkdir -p /tmp/kdev-bug-repro/.kdev/memory
cat > /tmp/kdev-bug-repro/.kdev/memory/执行日志.md <<'EOF'
## Step M-5（回补 meta）: iter-5

日期：2026-04-15

### 用户评分
- 完成时间：—
- 顺畅度：—/5（**褪色补录**）

## Step M-6: iter-6

日期：2026-04-17

### 用户评分
- 完成时间：—
- 顺畅度：—/5（**褪色补录**）
EOF
cd /tmp/kdev-bug-repro
bash "$OLDPWD/hooks/session-start-brief.sh" < /dev/null
cd -
```

Expected: 注意输出里的 STEP_HINT 行。

**注意**：Phase 2 做完后，褪色补录会被跳过 → 这里应该没有欠评报告。为了验证 bug 修复，**临时** 去掉 `（**褪色补录**）` 标记重跑。

记录 bug 是否还在显示层。

- [ ] **Step 5.4: Commit 调查笔记（可选）**

如果发现 bug 在特定位置，把发现写成一个简短 comment 追加到 Task 6 里。不单独 commit。

---

### Task 6: 重构 session-start-brief.sh 为三层分层（P0/P1/P2）+ 修显示 bug

**Files:**
- Modify: `plugins/kdev-memory/hooks/session-start-brief.sh`

**Rationale**: v0.7 Brief 核心重构。当前 brief 的"⚠️ 待处理"是平铺的，把所有信号当同级。v0.7 分成 P0（硬阻塞）/ P1（需核对）/ P2（仅报告）。同时顺手重写显示层，修 note-2 的编号/日期 bug。

- [ ] **Step 6.1: 读现有 session-start-brief.sh 全文**

```bash
cat plugins/kdev-memory/hooks/session-start-brief.sh
```

确认当前结构：
- 第 56~145 行：收集数据（WARN / CHECKPOINT / MISSING_SUMMARIES / DRIFT_HINT / STEP_HINT / STATE / RECENT）
- 第 148~215 行：`build_brief` 按 source 分档拼字符串

三层分层改造在 `build_brief` 的 `startup/clear/默认` 分支里做。

- [ ] **Step 6.2: 替换 "⚠️ 待处理（优先看）" 段为三层**

找到 `# startup / clear / 默认` 分支（大约第 175~211 行），把现有：

```bash
      if [ -n "$WARN_FILES" ] || [ -n "$CHECKPOINT_FILES" ] || ...
        brief+="⚠️ **待处理（优先看）**：\n"
        ...
      fi
```

整段替换为三层结构：

```bash
      # ===== v0.7 三层分层 =====
      # P0 硬阻塞：必须立刻处理（WARN / 今日半残）
      local P0_HINTS=""
      [ -n "$WARN_FILES" ] && P0_HINTS+="$(echo "$WARN_FILES" | sed 's|^|  - |')\n"
      if [ -n "$STEP_HINT" ] && echo "$STEP_HINT" | grep -q "今日"; then
        P0_HINTS+="$STEP_HINT\n"
      fi

      # P1 需核对：跨天遗漏 / 接口漂移 / 沉淀提醒 / 历史欠评
      local P1_HINTS=""
      [ -n "$MISSING_PAST_SUMMARIES" ] && P1_HINTS+="  - 过去日期缺每日汇总：$MISSING_PAST_SUMMARIES —— Read 源文件补写，严禁翻会话\n"
      [ -n "$DRIFT_HINT" ] && P1_HINTS+="$DRIFT_HINT\n"
      if [ -n "$STEP_HINT" ] && ! echo "$STEP_HINT" | grep -q "今日"; then
        P1_HINTS+="$STEP_HINT\n"
      fi
      [ -n "$PROMOTE_HINT" ] && P1_HINTS+="$PROMOTE_HINT\n"

      # P2 仅报告：历史 checkpoint / growth backlog
      local P2_HINTS=""
      [ -n "$CHECKPOINT_FILES" ] && P2_HINTS+="$(echo "$CHECKPOINT_FILES" | sed 's|^|  - |')\n"

      if [ -n "$P0_HINTS" ]; then
        brief+="🔴 **P0 硬阻塞（立刻处理）**：\n$P0_HINTS\n"
      fi
      if [ -n "$P1_HINTS" ]; then
        brief+="🟡 **P1 需核对**：\n$P1_HINTS\n"
      fi
      if [ -n "$P2_HINTS" ]; then
        brief+="⚪ **P2 参考**：\n$P2_HINTS\n"
      fi
```

- [ ] **Step 6.3: 在 resume 分支同步加三层**

`resume` 分支当前输出 `⚠️ 待处理：`，同样重写为三层（相同模式但只显示 P0 和 P1，P2 在 resume 下忽略）：

```bash
    resume)
      brief+="项目有 .kdev/ 工程记忆。本次会话是 resume。\n"
      # ... （复用 P0_HINTS / P1_HINTS 变量）
      if [ -n "$P0_HINTS" ] || [ -n "$P1_HINTS" ]; then
        brief+="⚠️ 待处理：\n"
        [ -n "$P0_HINTS" ] && brief+="🔴 $P0_HINTS"
        [ -n "$P1_HINTS" ] && brief+="🟡 $P1_HINTS"
      fi
      ;;
```

**注**：`P0_HINTS` 等变量需要在 `case "$mode"` **之前** 的共享段落计算，否则 resume 分支取不到。重构时把分层变量的计算挪到 `build_brief` 函数开头的共享段。

- [ ] **Step 6.4: 添加 PROMOTE_HINT 占位变量（为 Task 13 预留）**

在 session-start-brief.sh 第 123 行（STEP_HINT 之后、STATE frontmatter 读取之前）插入：

```bash
# ===== 沉淀候选扫描（v0.7 新增，实际聚合在 hooks/lib/promote-scan.sh） =====
PROMOTE_HINT=""
PROMOTE_SCAN_LIB="$SCRIPT_DIR/lib/promote-scan.sh"
if [ -f "$PROMOTE_SCAN_LIB" ] && [ -d "$KDEV_DIR" ]; then
  # shellcheck source=lib/promote-scan.sh
  # shellcheck disable=SC1091
  . "$PROMOTE_SCAN_LIB"
  PROMOTE_HINT=$(scan_promote_candidates "$KDEV_DIR" "$TODAY" 2>/dev/null || true)
fi
```

注：`promote-scan.sh` 本阶段还不存在，shell 会静默跳过。Task 13 才会创建它。

- [ ] **Step 6.5: 手动跑 hook 验证输出**

```bash
# 在 token-statistics 项目（有真实 .kdev/memory/）跑一次
cd /home/lyadmin/Projects/token-statistics 2>/dev/null || cd /tmp
bash "$HOME/Projects/kdev-agents-v0.7/plugins/kdev-memory/hooks/session-start-brief.sh" < /dev/null | python3 -c 'import sys,json; print(json.loads(sys.stdin.read())["hookSpecificOutput"]["additionalContext"])' 2>/dev/null || echo "(no additionalContext)"
```

Expected: 看到 🔴 / 🟡 / ⚪ 三色分层；欠评提醒不再报 Step M-5~M-8（Phase 2 的销账识别生效）。

- [ ] **Step 6.6: 修 note-2 的显示层 bug**

基于 Task 5 的定位结果：
- 如果 bug 在 Python `format_hint_for_brief`（第 265 行附近），在那里修；
- 如果 bug 在 shell 的 STEP_HINT 字符串合并（sed/awk 误处理 `M-`），在 shell 处修。

常见 bug 模式：`sed` 或 `awk` 用 `-` 作分隔符，把 `M-5` 误切成 `M` 和 `5`。重构 Brief 时避免此类模式。

验证：造 4 个 Step M-5~M-8 fixture 跑 brief，确认输出包含 `Step M-5` ~ `Step M-8` 各一行，不合并。

- [ ] **Step 6.7: Commit**

```bash
git add plugins/kdev-memory/hooks/session-start-brief.sh
git commit -m "feat(kdev-memory): Brief 三层分层 P0/P1/P2 + 修 Step M- 编号显示 bug"
```

---

## Phase 4: SessionEnd WARN 从 git 到 mtime 重构

### Task 7: 写失败测试 —— mtime-based WARN 机制

**Files:**
- Create: `plugins/kdev-memory/tests/test_session_end_mtime.py`

**Rationale**: v0.7 立场反转后 `.kdev/` 默认 gitignore，SessionEnd 的 `git status --porcelain` 检测 `.kdev/` 变化会失效。改用 `.last-flush` mtime 比对：每次成功 append 到 `.kdev/memory/` 任一核心文件时 touch `.last-flush`，SessionEnd 检测"是否存在比 `.last-flush` 更新的 `.kdev/memory/` 文件"作为"未落盘"信号。

- [ ] **Step 7.1: 创建测试文件**

```python
"""test SessionEnd hook 的 mtime-based WARN 生成逻辑（v0.7）

v0.6: git status --porcelain 检测 .kdev/ dirty → 生成 WARN
v0.7: .last-flush mtime 比对 → 生成 WARN（立场反转后 .kdev/ 不 git tracked 也能工作）
"""

import os
import subprocess
import time
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-end-check.sh"


def _setup_kdev(tmp_path: Path) -> Path:
    """造一个最小 .kdev/memory/ 结构，返回 project root。"""
    project = tmp_path / "project"
    (project / ".kdev" / "memory").mkdir(parents=True)
    (project / ".kdev" / "memory" / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    # 初始化 git（SessionEnd 在非 git 项目下现状会 exit，但 v0.7 要改成不依赖 git）
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"], cwd=project, check=True)
    return project


def test_warn_generated_when_kdev_modified_after_last_flush(tmp_path):
    """场景：last-flush 存在，但 .kdev/memory/ 有更新的文件 → 应生成 WARN。"""
    project = _setup_kdev(tmp_path)
    flush = project / ".kdev" / "memory" / ".last-flush"
    flush.touch()
    # 让 .last-flush mtime 比 执行日志 更旧
    old_time = time.time() - 3600
    os.utime(flush, (old_time, old_time))
    # 碰一下执行日志模拟新修改
    (project / ".kdev" / "memory" / "执行日志.md").write_text(
        "# 执行日志\n\n## Step 1\n", encoding="utf-8"
    )
    # 跑 hook
    subprocess.run(["bash", str(HOOK)], cwd=project, check=True)
    # 期望 WARN 文件被生成
    from datetime import date
    warn = project / ".kdev" / "memory" / f"WARN-未记录-{date.today().isoformat()}.md"
    assert warn.exists(), "SessionEnd 应生成 WARN（mtime 机制），但 WARN 文件不存在"


def test_no_warn_when_last_flush_newer(tmp_path):
    """场景：last-flush 最新（说明落盘都是最新的）→ 不应生成 WARN。"""
    project = _setup_kdev(tmp_path)
    (project / ".kdev" / "memory" / "执行日志.md").write_text(
        "# 执行日志\n\n## Step 1\n", encoding="utf-8"
    )
    # last-flush 在执行日志之后 touch
    time.sleep(0.1)
    (project / ".kdev" / "memory" / ".last-flush").touch()
    subprocess.run(["bash", str(HOOK)], cwd=project, check=True)
    from datetime import date
    warn = project / ".kdev" / "memory" / f"WARN-未记录-{date.today().isoformat()}.md"
    assert not warn.exists(), "last-flush 比 .kdev/ 都新 → 不应有 WARN"


def test_no_warn_when_no_last_flush_and_no_changes(tmp_path):
    """场景：没有 .last-flush 且 .kdev/memory/ 为空（除 placeholder）→ 不应生成 WARN。"""
    project = _setup_kdev(tmp_path)
    subprocess.run(["bash", str(HOOK)], cwd=project, check=True)
    from datetime import date
    warn = project / ".kdev" / "memory" / f"WARN-未记录-{date.today().isoformat()}.md"
    assert not warn.exists(), "初始化空项目不应有 WARN"


def test_works_without_git_repo(tmp_path):
    """v0.7 立场反转后：非 git 项目也要能正常工作（不 crash、不误报）。"""
    project = tmp_path / "nogit"
    (project / ".kdev" / "memory").mkdir(parents=True)
    (project / ".kdev" / "memory" / "执行日志.md").write_text(
        "# 执行日志\n\n## Step 1\n", encoding="utf-8"
    )
    # 无 git init；v0.6 下 hook exit 0 什么都不做，v0.7 下应仍能生成 WARN（mtime 机制）
    result = subprocess.run(["bash", str(HOOK)], cwd=project, capture_output=True)
    assert result.returncode == 0, f"hook 异常退出: {result.stderr.decode()}"
```

- [ ] **Step 7.2: 运行测试验证 FAIL**

```bash
cd plugins/kdev-memory
python3 -m pytest tests/test_session_end_mtime.py -v
```

Expected:
- `test_warn_generated_when_kdev_modified_after_last_flush` → **FAIL**（当前仍是 git-based）
- `test_no_warn_when_last_flush_newer` → **FAIL or PASS**（边缘情形）
- `test_no_warn_when_no_last_flush_and_no_changes` → 可能 PASS（无 porcelain 变更）
- `test_works_without_git_repo` → v0.6 下无 git 直接 exit 0 不写 WARN，但测试断言"不 crash"，应 PASS

- [ ] **Step 7.3: Commit failing tests**

```bash
git add plugins/kdev-memory/tests/test_session_end_mtime.py
git commit -m "test(kdev-memory): SessionEnd mtime-based WARN 机制失败测试"
```

---

### Task 8: 实现 .last-flush 机制 + 重写 session-end-check.sh

**Files:**
- Modify: `plugins/kdev-memory/hooks/session-end-check.sh`
- Modify: `plugins/kdev-memory/hooks/post-write-check.sh`（让 Claude 写 `.kdev/memory/*.md` 时自动 `touch .last-flush`）

- [ ] **Step 8.1: 改写 session-end-check.sh 的检测逻辑**

完全重写 `session-end-check.sh`（55 行→约 70 行）：

```bash
#!/usr/bin/env bash
# kdev-memory SessionEnd hook (v0.7)
# 会话真正结束时的兜底：用 mtime 比对替代 git status
# 检测 .kdev/memory/ 下有无比 .last-flush 更新的文件 → 若有则写 WARN
# v0.7 立场反转后 .kdev/ 默认 gitignore，git status 拿不到 .kdev/ 变化，必须换机制

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/migrate.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/migrate.sh"

kdev_memory_migrate

KDEV_DIR=".kdev/memory"
TODAY=$(date +%F)
LOG_FILE="$KDEV_DIR/执行日志.md"
FLUSH_FILE="$KDEV_DIR/.last-flush"
WARN_FILE="$KDEV_DIR/WARN-未记录-$TODAY.md"

[ -d "$KDEV_DIR" ] || exit 0

# 执行日志今天已有条目 → 无需警告
if [ -f "$LOG_FILE" ] && grep -q "$TODAY" "$LOG_FILE" 2>/dev/null; then
  exit 0
fi

# 检测 .kdev/memory/ 下有无比 .last-flush 更新的文件
# （不依赖 git）
CHANGED_FILES=""
if [ -f "$FLUSH_FILE" ]; then
  CHANGED_FILES=$(find "$KDEV_DIR" -type f \
    -newer "$FLUSH_FILE" \
    ! -name ".last-flush" \
    ! -name "WARN-未记录-*" \
    ! -path "*/checkpoints/*" \
    ! -path "*/state/*" \
    2>/dev/null | head -20)
else
  # 没有 .last-flush 说明 v0.7 机制还没启用 → 回退到 v0.6 行为：
  # 只在 git 仓库下用 git status 检测
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    PORCELAIN=$(git status --porcelain -uall 2>/dev/null | grep "\.kdev/memory/" || true)
    [ -n "$PORCELAIN" ] && CHANGED_FILES="$PORCELAIN"
  fi
fi

[ -n "$CHANGED_FILES" ] || exit 0

# 写 WARN
{
  echo "# ⚠️ 未记录警告：$TODAY"
  echo ""
  echo "会话结束时检测到：**执行日志 ($LOG_FILE) 今天无任何条目**，但 \`.kdev/memory/\` 有未落盘的变更。"
  echo ""
  echo "下次进入项目时："
  echo "1. 回忆这些变更对应的工作单元（Step），追加到 $LOG_FILE"
  echo "2. 如有关键决策/踩坑/改进信号，补记到对应的 Q/G/R 日志"
  echo "3. 补记完成后 \`touch $FLUSH_FILE\` 重置并 \`rm $WARN_FILE\`"
  echo ""
  echo "## 比 .last-flush 更新的文件"
  echo ""
  echo '```'
  echo "$CHANGED_FILES"
  echo '```'
  echo ""
  echo "_本文件由 kdev-memory SessionEnd hook (v0.7) 自动生成。_"
} > "$WARN_FILE"

exit 0
```

- [ ] **Step 8.2: 让 post-write-check.sh 在 Claude 写 .kdev/memory/*.md 时 touch .last-flush**

打开 `plugins/kdev-memory/hooks/post-write-check.sh`，在检测到目标文件在 `.kdev/memory/` 下时追加：

```bash
# v0.7: 刷新 .last-flush 时间戳（SessionEnd hook 用 mtime 比对）
if [[ "$TARGET_FILE" == *".kdev/memory/"* ]]; then
  touch "$KDEV_DIR/.last-flush" 2>/dev/null || true
fi
```

具体插入位置：找到 `TARGET_FILE` 解析完成后、原有里程碑判断之前。如果 `post-write-check.sh` 目前没解析 `TARGET_FILE`，在文件末尾加兜底版：

```bash
# 从 stdin 取 tool_input.file_path
if command -v python3 >/dev/null 2>&1 && [ ! -t 0 ]; then
  FP=$(timeout 1 python3 -c 'import sys,json
try:
    d=json.load(sys.stdin)
    print((d.get("tool_input") or {}).get("file_path",""))
except: pass' 2>/dev/null)
  if [[ "$FP" == *".kdev/memory/"* ]]; then
    touch ".kdev/memory/.last-flush" 2>/dev/null || true
  fi
fi
```

**注**：具体集成方式以现有 `post-write-check.sh` 结构为准，Step 8.2 在真实执行时调整。

- [ ] **Step 8.3: 运行测试全部 PASS**

```bash
cd plugins/kdev-memory
python3 -m pytest tests/test_session_end_mtime.py -v tests/ -v
```

Expected: 4 条新测试全部 PASS + 现有全部测试 PASS（无回归）。

- [ ] **Step 8.4: 跑 evals hook selftest**

```bash
cd plugins/kdev-memory
bash evals/run-hook-selftest.sh
```

Expected: selftest 全部通过。

- [ ] **Step 8.5: Commit**

```bash
git add plugins/kdev-memory/hooks/session-end-check.sh plugins/kdev-memory/hooks/post-write-check.sh
git commit -m "feat(kdev-memory): SessionEnd WARN 从 git-status 改为 .last-flush mtime 比对"
```

---

## Phase 5: 立场反转 + init 行为 + 废弃物标注

### Task 9: 写失败测试 —— init 自动 append .kdev/ 到 .gitignore

**Files:**
- Create: `plugins/kdev-memory/tests/test_init_gitignore.py`

**Rationale**: v0.7 的"立场反转"核心表现之一：用户说"给这个项目建立工程记忆"时，插件初始化逻辑应自动 append `.kdev/` 到项目 `.gitignore`。init 逻辑目前是 skill 文档引导（不是代码）——v0.7 需要提供一个 shell helper：`hooks/lib/init-gitignore.sh`，供 Claude 初始化时通过 Bash 工具调用。

- [ ] **Step 9.1: 创建测试文件**

```python
"""test init-gitignore.sh: 自动 append .kdev/ 到 .gitignore（v0.7 立场反转）"""

import subprocess
from pathlib import Path

HELPER = Path(__file__).parent.parent / "hooks" / "lib" / "init-gitignore.sh"


def _run(project: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(HELPER)], cwd=project, capture_output=True, text=True)


def test_append_when_no_gitignore(tmp_path):
    """没有 .gitignore → 创建新文件，写入 .kdev/ 一行。"""
    _run(tmp_path)
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".kdev/" in content


def test_append_when_gitignore_missing_kdev(tmp_path):
    """.gitignore 存在但无 .kdev/ → 追加。"""
    (tmp_path / ".gitignore").write_text("node_modules/\n*.log\n", encoding="utf-8")
    _run(tmp_path)
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".kdev/" in content
    assert "node_modules/" in content  # 原有不丢


def test_idempotent_when_kdev_already_ignored(tmp_path):
    """.gitignore 已有 .kdev/ → 不重复追加。"""
    (tmp_path / ".gitignore").write_text(".kdev/\nnode_modules/\n", encoding="utf-8")
    _run(tmp_path)
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert content.count(".kdev/") == 1


def test_respects_kdev_track_env(tmp_path, monkeypatch):
    """KDEV_GIT_TRACK=1 → 不写入 .gitignore（单人用户 opt-in 托管）。"""
    (tmp_path / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    monkeypatch.setenv("KDEV_GIT_TRACK", "1")
    _run(tmp_path)
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".kdev/" not in content
```

- [ ] **Step 9.2: 运行测试验证 FAIL**

```bash
cd plugins/kdev-memory
python3 -m pytest tests/test_init_gitignore.py -v
```

Expected: 全部 FAIL（`init-gitignore.sh` 不存在）。

- [ ] **Step 9.3: Commit**

```bash
git add plugins/kdev-memory/tests/test_init_gitignore.py
git commit -m "test(kdev-memory): init 自动 append .gitignore 的失败测试"
```

---

### Task 10: 实现 hooks/lib/init-gitignore.sh

**Files:**
- Create: `plugins/kdev-memory/hooks/lib/init-gitignore.sh`

- [ ] **Step 10.1: 创建脚本**

```bash
#!/usr/bin/env bash
# init-gitignore.sh —— kdev-memory v0.7
# 立场反转：.kdev/ 默认本地过程目录；init 时自动 append .kdev/ 到项目 .gitignore
# 环境变量 KDEV_GIT_TRACK=1 → 跳过（单人项目可选托管模式）

set -eu

if [ "${KDEV_GIT_TRACK:-0}" = "1" ]; then
  echo "[kdev-memory] KDEV_GIT_TRACK=1，跳过 .gitignore 修改（单人托管模式）"
  exit 0
fi

GITIGNORE=".gitignore"
MARK_LINE=".kdev/"
MARK_COMMENT="# kdev-memory v0.7: 本地过程目录，不 git 托管（产物请沉淀到 docs/）"

if [ ! -f "$GITIGNORE" ]; then
  {
    echo "$MARK_COMMENT"
    echo "$MARK_LINE"
  } > "$GITIGNORE"
  echo "[kdev-memory] 新建 .gitignore 并加入 $MARK_LINE"
  exit 0
fi

# 已有 .gitignore：只在缺 .kdev/ 行时追加（幂等）
if grep -qxF "$MARK_LINE" "$GITIGNORE"; then
  echo "[kdev-memory] .gitignore 已有 $MARK_LINE，跳过"
  exit 0
fi

{
  echo ""
  echo "$MARK_COMMENT"
  echo "$MARK_LINE"
} >> "$GITIGNORE"
echo "[kdev-memory] 追加 $MARK_LINE 到 .gitignore"
exit 0
```

设置可执行：

```bash
chmod +x plugins/kdev-memory/hooks/lib/init-gitignore.sh
```

- [ ] **Step 10.2: 运行测试验证 PASS**

```bash
cd plugins/kdev-memory
python3 -m pytest tests/test_init_gitignore.py -v
```

Expected: 4 条全部 PASS。

- [ ] **Step 10.3: 在 SKILL.md 的"初始化"章节里 reference 这个 helper**

打开 `plugins/kdev-memory/skills/kdev-memory/SKILL.md`，找到第 98~130 行"初始化"章节，在"关键授权"段之后、"六类记录的触发时机总览"之前插入：

```markdown

### v0.7+：自动加 .kdev/ 到 .gitignore

初始化时 Claude 应自动执行：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/init-gitignore.sh"
```

这会把 `.kdev/` 加入项目 `.gitignore`，符合 v0.7 立场："`.kdev/` 是**本地过程目录**，团队共享的产物（规则、决策、实战总结）应**显式沉淀**到 `docs/`，通过 `/kdev-memory-promote` 命令半自动流转（见本 SKILL 相关章节）。

**单人项目可选托管**：如果确实希望 `.kdev/` 也进 git，设置环境变量 `KDEV_GIT_TRACK=1` 再执行 init-gitignore.sh，或手动 `rm` 掉 .gitignore 里的 `.kdev/` 行。但**强烈不推荐**用于多会话 / 多成员场景（会触发 merge 冲突、Step 编号竞态、基线分叉，详见开发历程 v0.7 章节）。
```

- [ ] **Step 10.4: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/init-gitignore.sh plugins/kdev-memory/skills/kdev-memory/SKILL.md
git commit -m "feat(kdev-memory): init-gitignore.sh helper —— 初始化时自动 append .kdev/ 到 .gitignore"
```

---

### Task 11: 重写 README 立场章节（对比表 + 差异化设计点）

**Files:**
- Modify: `plugins/kdev-memory/README.md`

**Rationale**: note-1 §4.1 的核心改动。README 第 11~17 行对比表最后一列 + 第 19 行差异化设计点第 3 条，共两处需要明确从"**跟代码 commit**"改为"**本地过程目录**"。

- [ ] **Step 11.1: 改对比表第三行最后一列**

找到 README 第 11~13 行的对比表，第三行（"工程过程档案（本插件）"）最后一列当前是 `\`.kdev/memory/\`（**跟代码 commit**）`。替换为：

```markdown
| **工程过程档案**（本插件） | kdev-memory | 结构化决策/踩坑/Step/评分/改进信号 | `.kdev/memory/`（**本地过程目录，默认 gitignore**；产物沉淀到 `docs/`） |
```

- [ ] **Step 11.2: 改差异化设计点第 3 条**

找到 README 第 15~21 行的"kdev-memory 的差异化设计点"列表。第 3 条（第 19 行附近）：

当前：
```markdown
- **可跟代码一起 commit**：项目内的工程决策/踩坑属于**项目资产**，应该进 git（不是只存在于个人机器）
```

替换为：
```markdown
- **过程 / 产物分家**（v0.7 立场反转）：`.kdev/` 是**本地过程目录**（默认 gitignore）。过程是流动的、带个人视角的草稿；产物（团队规则、决策结论、实战总结）通过 `/kdev-memory-promote` 命令半自动沉淀到 `docs/` 等团队通道。为什么不直接 git 托管 `.kdev/`？——多会话/多成员会产生 merge 冲突、Step 编号竞态、基线分叉；而且个人现场一旦被"共享包袱"约束，评分质量会被污染。详见开发历程 v0.7 章节
```

- [ ] **Step 11.3: 在"命名空间约定"章节加一段"为什么默认 gitignore"**

找到 README"命名空间约定"段（第 47~57 行），在段末（第 57 行"本插件只管 \`.kdev/memory/\`，不碰同级其他目录。"之后）追加：

```markdown

### 为什么 `.kdev/` 默认 gitignore（v0.7+）

`.kdev/` 记录**个人如何走到了答案**（过程），`docs/` 记录**答案本身**（产物）。过程对作者有价值，产物对团队有价值——两者不应混在一起：

- 过程质量要求"**原始、当下、带张力**"——共享压力会让评分不敢写真话、踩坑不敢写糗事
- 产物质量要求"**结晶、去语境、面向团队**"——过程条目直接暴露给团队会混乱

因此：`.kdev/` 作为本地过程草稿（默认 gitignore）；需要团队共享的通过 `/kdev-memory-promote` 显式沉淀到 `docs/` 等产物通道。详见**开发历程 v0.7 立场反转**章节。

**单人项目可选托管**：`export KDEV_GIT_TRACK=1` 后初始化，跳过 .gitignore 写入。但不推荐（踩坑见上）。
```

- [ ] **Step 11.4: Commit**

```bash
git add plugins/kdev-memory/README.md
git commit -m "docs(kdev-memory): README 立场反转 —— .kdev/ 从项目资产改为本地过程目录"
```

---

### Task 12: 废弃物标注（R-014/R-015/建议 8/9 加 blockquote）

**Files:**
- Modify（如存在）: `docs/skills/kdev-memory/开发历程.md`（blockquote 标注现有章节 R-014/R-015）
- **无需在 plugin 仓内标注** —— R-014/R-015/建议 8/9 是 token-statistics **项目内**的 `.kdev/memory/` 条目，不在 kdev-agents 仓库范围。仓外标注属于下游 consumer 责任（见 note-1 §4.4 列表），本 plan 仅负责 kdev-agents 仓内文档的废弃标注。

- [ ] **Step 12.1: 核查 kdev-agents 仓内是否有 R-014/R-015/建议 8/9 的 reference**

```bash
grep -rn "R-014\|R-015\|建议 8\|建议 9" /home/lyadmin/Projects/kdev-agents/ --include="*.md" | grep -v "^Binary\|\.git/\|plans/2026-04-24-kdev-memory-v0.7.md"
```

预期：命中 `docs/skills/kdev-memory/dev-notes/2026-04-24-kdev-memory-git托管立场反转-过程vs产物分家.md`（本 plan 参考的 note-1）+ 可能的开发历程.md。

- [ ] **Step 12.2: 在每个命中 R-014/R-015/建议 8/9 的上下文前加 blockquote 标注**

对每个命中文件，在涉及 R-014/R-015/建议 8/9 的段落前插入：

```markdown
> **⚠️ 已被 v0.7 立场反转替代（2026-04-24）**：本条规则/建议原本用于解决"`.kdev/` git 托管下的多会话/多成员协作问题"。v0.7 把 `.kdev/` 改为本地过程目录（默认 gitignore），这类问题从根因消解，本条保留作为推理路径归档。详见 [开发历程 v0.7 立场反转](../开发历程.md#v07-立场反转) 或 [dev-note](../dev-notes/2026-04-24-kdev-memory-git托管立场反转-过程vs产物分家.md)。
```

具体改动位置根据 Step 12.1 的 grep 结果决定。

- [ ] **Step 12.3: Commit**

```bash
git add docs/
git commit -m "docs(kdev-memory): R-014/R-015/建议8/9 加 v0.7 立场反转替代 blockquote"
```

---

## Phase 6: Promote 机制（命令 + 扫描）

### Task 13: 写失败测试 —— promote 候选扫描

**Files:**
- Create: `plugins/kdev-memory/tests/test_promote_scan.py`

**Rationale**: promote-scan 的 bash 函数要返回"有多少条 pending"+"最近一次 promote 距今多少天"给 Brief P1 层。

- [ ] **Step 13.1: 创建测试**

```python
"""test promote-scan.sh: 扫描 .kdev/memory/ 的沉淀候选"""

import os
import subprocess
import time
from pathlib import Path

LIB = Path(__file__).parent.parent / "hooks" / "lib" / "promote-scan.sh"


def _call(project: Path) -> str:
    """source 进来再调 scan_promote_candidates"""
    script = f'''
source {LIB}
scan_promote_candidates "{project}/.kdev/memory" "2026-04-24"
'''
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    return r.stdout


def _mkkdev(tmp_path: Path) -> Path:
    p = tmp_path / ".kdev" / "memory"
    p.mkdir(parents=True)
    return p


def test_empty_project_no_hint(tmp_path):
    """空项目（无任何条目）→ scan 返回空。"""
    _mkkdev(tmp_path)
    out = _call(tmp_path)
    assert out.strip() == ""


def test_time_trigger_over_7_days(tmp_path):
    """.last-promote 超过 7 天 + 有 R-NNN → 应输出沉淀提醒。"""
    k = _mkkdev(tmp_path)
    # 造 8 天前的 .last-promote
    flush = k / ".last-promote"
    flush.touch()
    old = time.time() - 8 * 86400
    os.utime(flush, (old, old))
    # 造一条改进建议
    (k / "改进建议.md").write_text("""# 改进建议

## R-014: 建议

triggers: [a]
""", encoding="utf-8")
    out = _call(tmp_path)
    assert "沉淀" in out or "promote" in out.lower()


def test_count_trigger_improvements_threshold(tmp_path):
    """改进建议 >= 3 条 pending（无 promote_status: done）→ 应输出。"""
    k = _mkkdev(tmp_path)
    (k / "改进建议.md").write_text("""# 改进建议

## R-1: a

## R-2: b

## R-3: c
""", encoding="utf-8")
    out = _call(tmp_path)
    assert "沉淀" in out


def test_skip_when_all_done(tmp_path):
    """所有 R 都有 promote_status: done → 不提醒。"""
    k = _mkkdev(tmp_path)
    (k / "改进建议.md").write_text("""# 改进建议

## R-1: a
---
promote_status: done
promote_target: docs/05-报告/实战总结.md
promote_date: 2026-04-23
---

## R-2: b
---
promote_status: done
---

## R-3: c
---
promote_status: done
---
""", encoding="utf-8")
    out = _call(tmp_path)
    # 全 done 应无提醒
    assert "沉淀" not in out


def test_escalate_to_p0_over_30_days(tmp_path):
    """.last-promote 超 30 天 + 有 pending → 输出升级到 P0（含 🔴 或 "长期未沉淀"）。"""
    k = _mkkdev(tmp_path)
    flush = k / ".last-promote"
    flush.touch()
    very_old = time.time() - 35 * 86400
    os.utime(flush, (very_old, very_old))
    (k / "改进建议.md").write_text("## R-1\n", encoding="utf-8")
    out = _call(tmp_path)
    assert "长期" in out or "P0" in out or "🔴" in out
```

- [ ] **Step 13.2: 运行 FAIL**

```bash
cd plugins/kdev-memory
python3 -m pytest tests/test_promote_scan.py -v
```

Expected: 全部 FAIL（`promote-scan.sh` 不存在）。

- [ ] **Step 13.3: Commit**

```bash
git add plugins/kdev-memory/tests/test_promote_scan.py
git commit -m "test(kdev-memory): promote-scan.sh 候选扫描失败测试"
```

---

### Task 14: 实现 hooks/lib/promote-scan.sh

**Files:**
- Create: `plugins/kdev-memory/hooks/lib/promote-scan.sh`

- [ ] **Step 14.1: 创建脚本**

```bash
#!/usr/bin/env bash
# promote-scan.sh —— kdev-memory v0.7
# 扫描 .kdev/memory/ 的沉淀候选，输出 Brief P1 hint（或 P0 当距 .last-promote > 30 天）
# 约束：
#   - 无 python3 依赖（纯 shell + grep/awk）
#   - 幂等、只读（不写任何文件）
#   - 返回文本：P1 hint（"📝 建议沉淀：..."）或空字符串

# shellcheck disable=SC2155

scan_promote_candidates() {
  local kdev_dir="$1"
  local today="$2"
  [ -d "$kdev_dir" ] || return 0

  local flush="$kdev_dir/.last-promote"
  local days_since_promote="never"
  local flush_ts=0
  local today_ts
  today_ts=$(date -d "$today" +%s 2>/dev/null || date +%s)

  if [ -f "$flush" ]; then
    flush_ts=$(stat -c %Y "$flush" 2>/dev/null || stat -f %m "$flush" 2>/dev/null)
    if [ -n "$flush_ts" ] && [ "$flush_ts" -gt 0 ]; then
      days_since_promote=$(( (today_ts - flush_ts) / 86400 ))
    fi
  fi

  # 统计 pending 条目
  # 粗口径：改进建议里的 ## R-/## 建议 N/## #N 条目数 - 已标 promote_status: done 条目数
  local improvements_md="$kdev_dir/改进建议.md"
  local rule_md="$kdev_dir/conventions.md"
  local decisions_md="$kdev_dir/决策日志.md"
  local gotchas_md="$kdev_dir/踩坑日志.md"

  local r_total=0 r_done=0 r_pending=0
  if [ -f "$improvements_md" ]; then
    r_total=$(grep -c "^## " "$improvements_md" 2>/dev/null || echo 0)
    r_done=$(grep -c "^promote_status:\s*done" "$improvements_md" 2>/dev/null || echo 0)
    r_pending=$(( r_total - r_done ))
  fi

  # conventions R-NNN（若存在）
  local rule_pending=0
  if [ -f "$rule_md" ]; then
    local rule_total rule_done
    rule_total=$(grep -c "^### R-[0-9]" "$rule_md" 2>/dev/null || echo 0)
    rule_done=$(grep -c "^promote_status:\s*done" "$rule_md" 2>/dev/null || echo 0)
    rule_pending=$(( rule_total - rule_done ))
  fi

  # G-NNN
  local g_pending=0
  if [ -f "$gotchas_md" ]; then
    local g_total g_done
    g_total=$(grep -c "^## G-" "$gotchas_md" 2>/dev/null || echo 0)
    g_done=$(grep -c "^promote_status:\s*done" "$gotchas_md" 2>/dev/null || echo 0)
    g_pending=$(( g_total - g_done ))
  fi

  # 触发条件（任一命中）
  local trigger_reason=""
  local escalate_p0="no"

  # 时间触发
  if [ "$days_since_promote" != "never" ] && [ "$days_since_promote" -gt 7 ]; then
    trigger_reason="距上次沉淀 $days_since_promote 天"
    if [ "$days_since_promote" -gt 30 ]; then
      escalate_p0="yes"
    fi
  fi

  # 增量触发
  if [ "$r_pending" -ge 3 ]; then
    trigger_reason="${trigger_reason:+$trigger_reason；}改进建议 $r_pending 条 pending"
  fi
  if [ "$rule_pending" -ge 2 ]; then
    trigger_reason="${trigger_reason:+$trigger_reason；}R-NNN 规则 $rule_pending 条 pending"
  fi
  if [ "$g_pending" -ge 5 ]; then
    trigger_reason="${trigger_reason:+$trigger_reason；}踩坑 $g_pending 条 pending"
  fi

  [ -z "$trigger_reason" ] && return 0
  [ "$r_pending" -eq 0 ] && [ "$rule_pending" -eq 0 ] && [ "$g_pending" -eq 0 ] && return 0

  # 输出 P1 hint（或 P0 升级版）
  if [ "$escalate_p0" = "yes" ]; then
    cat <<EOF
  - 🔴 长期未沉淀（$days_since_promote 天）：团队已长期未获本项目过程结晶
    · 改进建议 pending: $r_pending；R-NNN: $rule_pending；G-NNN: $g_pending
    · 执行 /kdev-memory-promote 查看沉淀候选并更新 .last-promote
EOF
  else
    cat <<EOF
  - 📝 建议沉淀（$trigger_reason）：
    · 执行 /kdev-memory-promote 查看沉淀候选并写入 docs/ 产物通道
EOF
  fi
}
```

- [ ] **Step 14.2: 运行测试**

```bash
cd plugins/kdev-memory
python3 -m pytest tests/test_promote_scan.py -v
```

Expected: 5 条全 PASS。

- [ ] **Step 14.3: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/promote-scan.sh
git commit -m "feat(kdev-memory): promote-scan.sh 沉淀候选扫描（Brief P1 集成入口）"
```

---

### Task 15: 新建 /kdev-memory-promote slash command

**Files:**
- Create: `plugins/kdev-memory/commands/kdev-memory-promote.md`
- Create: `plugins/kdev-memory/hooks/lib/promote-list.sh`（给 command 调用的 bash 聚合脚本）

- [ ] **Step 15.1: 创建 commands 目录**

```bash
mkdir -p plugins/kdev-memory/commands
```

- [ ] **Step 15.2: 创建 commands/kdev-memory-promote.md**

```markdown
---
description: 列出 .kdev/memory/ 里待沉淀（promote_status: pending）的条目，推荐去向，用户确认后写入 docs/ 产物通道
argument-hint: [无参数 | --all]
---

# /kdev-memory-promote

列出当前项目 `.kdev/memory/` 里所有"待沉淀"条目（改进建议 / R-NNN / G-NNN / Q-NNN），给出推荐沉淀去向，用户确认后把内容写入 `docs/` 并更新源条目的 `promote_status: done`。

## 候选扫描（Bash 聚合）

!`bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/promote-list.sh" "$ARGUMENTS"`

## 你的任务

根据上面 bash 脚本的输出：

1. **列出所有 pending 条目** —— 编号 + 标题 + 来源文件 + 建议去向（按下表）
2. **向用户询问**："这些条目哪些要沉淀？（全选 / 指定编号 / 全跳过）"
3. 对用户确认要沉淀的每条：
   - 读源条目原文
   - 写入 `promote_target` 指向的 `docs/` 文件（追加 或 按 section 合并）
   - 更新源条目 frontmatter：`promote_status: done` + `promote_target: <path>` + `promote_date: YYYY-MM-DD`
4. 对用户确认要跳过的：
   - 更新源条目 frontmatter：`promote_status: skipped`，`promote_target` 存理由
5. **全部处理完后**执行：

```bash
touch .kdev/memory/.last-promote
```

重置"上次沉淀时间"。

## 推荐沉淀去向

| 源条目类型 | 推荐 docs/ 去向 |
|---|---|
| 改进建议.md 定稿条目 | `docs/05-报告/实战总结-<项目名>.md` 反思章节 |
| conventions.md §11 R-NNN | `docs/08-开发规范.md` 或 skill-level CLAUDE.md |
| 踩坑日志.md G-NNN 高频类 | `docs/04-架构/踩坑索引.md` |
| 决策日志.md Q-NNN 架构级 | `docs/04-架构/ADR-NNN-<slug>.md` |
| 执行日志.md Step 4.5+ 高分经验 | `docs/05-报告/实战项目总结.md` |
| 日常 G-NNN / Step 现场 | **不沉淀**（留在本地过程即可） |

**严禁替用户拍板** —— 若用户拒绝某条，尊重并标 `skipped`；不要硬推。

## 参数

- 无参数：列出全部 pending
- `--all`：同上（保留给未来扩展批量模式）
```

- [ ] **Step 15.3: 创建 promote-list.sh 聚合脚本**

```bash
cat > plugins/kdev-memory/hooks/lib/promote-list.sh <<'BASH_EOF'
#!/usr/bin/env bash
# promote-list.sh —— 给 /kdev-memory-promote command 调用
# 列出 .kdev/memory/ 下所有 promote_status != done 的条目

set -eu

KDEV_DIR=".kdev/memory"
if [ ! -d "$KDEV_DIR" ]; then
  echo "[kdev-memory] 当前项目无 .kdev/memory/，无候选可沉淀。"
  exit 0
fi

FLUSH="$KDEV_DIR/.last-promote"
TODAY=$(date +%F)
DAYS="never"
if [ -f "$FLUSH" ]; then
  FT=$(stat -c %Y "$FLUSH" 2>/dev/null || stat -f %m "$FLUSH" 2>/dev/null || echo 0)
  [ "$FT" -gt 0 ] 2>/dev/null && DAYS=$(( ( $(date +%s) - FT ) / 86400 ))
fi

echo "# /kdev-memory-promote 候选列表"
echo ""
echo "- 扫描时间：$TODAY"
echo "- 距上次沉淀：$DAYS 天"
echo ""

# 扫各来源
for src in "改进建议.md:建议" "conventions.md:R-NNN 规则" "决策日志.md:Q-NNN" "踩坑日志.md:G-NNN" "执行日志.md:Step"; do
  f="${src%%:*}"
  label="${src##*:}"
  [ -f "$KDEV_DIR/$f" ] || continue
  echo "## $label（$KDEV_DIR/$f）"
  echo ""
  # 粗列：所有 ## 二级标题，然后标注是否有 promote_status: done
  awk '
    /^## / { title=$0; has_done=0; has_skipped=0; getline_ok=1 }
    /^promote_status:[[:space:]]*done/ { has_done=1 }
    /^promote_status:[[:space:]]*skipped/ { has_skipped=1 }
    /^## / && NR>1 && title {
      # flush previous
    }
  ' "$KDEV_DIR/$f" || true

  # 简化实现：把所有 ## 标题和对应 promote_status 用 grep 组合出来
  # python3 更好，但本脚本承诺纯 shell
  paste \
    <(grep "^## " "$KDEV_DIR/$f" | head -30) \
    <(awk '/^## /{if(ps){print ps}ps="[pending]"} /^promote_status:[[:space:]]*done/{ps="[done]"} /^promote_status:[[:space:]]*skipped/{ps="[skipped]"} END{if(ps)print ps}' "$KDEV_DIR/$f" | head -30) \
    2>/dev/null | grep -v "\[done\]\|\[skipped\]" | head -20 || true
  echo ""
done

echo "---"
echo ""
echo "## 推荐沉淀去向"
echo ""
cat <<'TABLE'
| 来源 | 推荐 docs/ 去向 |
|---|---|
| 改进建议.md | docs/05-报告/实战总结-<项目名>.md 反思章节 |
| conventions.md §11 R-NNN | docs/08-开发规范.md |
| 决策日志.md Q-NNN | docs/04-架构/ADR-NNN.md |
| 踩坑日志.md G-NNN 高频类 | docs/04-架构/踩坑索引.md |
| 执行日志.md Step 4.5+ | docs/05-报告/实战项目总结.md |
TABLE
BASH_EOF

chmod +x plugins/kdev-memory/hooks/lib/promote-list.sh
```

- [ ] **Step 15.4: 手工试跑 command**

```bash
# 在 kdev-agents 仓内没有 .kdev/ —— 换到 token-statistics 试
cd /home/lyadmin/Projects/token-statistics 2>/dev/null || { echo "skip"; exit 0; }
bash "$HOME/Projects/kdev-agents-v0.7/plugins/kdev-memory/hooks/lib/promote-list.sh"
```

Expected: 输出候选列表 + 推荐去向表（若 token-statistics 的 .kdev/memory/ 存在）。

- [ ] **Step 15.5: Commit**

```bash
git add plugins/kdev-memory/commands/ plugins/kdev-memory/hooks/lib/promote-list.sh
git commit -m "feat(kdev-memory): /kdev-memory-promote slash command + promote-list.sh 聚合"
```

---

## Phase 7: Weekly 命令（rolling 7 天）

### Task 16: 写失败测试 —— weekly 聚合逻辑

**Files:**
- Create: `plugins/kdev-memory/tests/test_weekly_aggregate.py`

**Rationale**: weekly 命令的 bash 聚合脚本 `hooks/lib/weekly.sh`，聚合指定日期范围内的 Step / Q / G / R，按模板输出 markdown。

- [ ] **Step 16.1: 创建测试**

```python
"""test weekly.sh 滚动 7 天窗口聚合逻辑"""

import subprocess
from datetime import date, timedelta
from pathlib import Path

LIB = Path(__file__).parent.parent / "hooks" / "lib" / "weekly.sh"


def _call(project: Path, date_from: str = "", date_to: str = "") -> subprocess.CompletedProcess:
    args = [str(LIB)]
    if date_from:
        args.extend(["--from", date_from])
    if date_to:
        args.extend(["--to", date_to])
    return subprocess.run(["bash"] + args, cwd=project, capture_output=True, text=True)


def _setup(tmp_path: Path) -> Path:
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    return k


def test_default_window_is_today_minus_6_to_today(tmp_path):
    """无参数 → 汇总 today-6 ~ today。"""
    k = _setup(tmp_path)
    today = date.today()
    from_d = (today - timedelta(days=6)).isoformat()
    # 造一条今日 Step
    (k / "执行日志.md").write_text(f"""## Step 10: foo

日期：{today.isoformat()}

### 模型自评
- 顺畅度：4/5
""", encoding="utf-8")
    r = _call(tmp_path)
    assert r.returncode == 0
    assert from_d in r.stdout
    assert today.isoformat() in r.stdout
    assert "Step 10" in r.stdout


def test_custom_range_via_from_to(tmp_path):
    """--from / --to 指定范围。"""
    k = _setup(tmp_path)
    (k / "执行日志.md").write_text("""## Step 5: in-range

日期：2026-04-15

## Step 6: out-of-range

日期：2026-04-22
""", encoding="utf-8")
    r = _call(tmp_path, "2026-04-14", "2026-04-18")
    assert "Step 5" in r.stdout
    assert "Step 6" not in r.stdout


def test_four_section_reporting_skeleton(tmp_path):
    """周总结必须有"汇报四段"骨架：过程资产 / 经验总结 / 问题教训 / 开发进展。"""
    k = _setup(tmp_path)
    (k / "执行日志.md").write_text("""## Step 1: ordinary

日期：2026-04-18

### 用户评分
- 顺畅度：3/5

## Step 2: brilliant

日期：2026-04-19

### 用户评分
- 顺畅度：4.5/5
""", encoding="utf-8")
    r = _call(tmp_path, "2026-04-15", "2026-04-21")
    # 四段必须全在输出里
    assert "过程资产" in r.stdout
    assert "经验总结" in r.stdout
    assert "问题教训" in r.stdout
    assert "开发进展" in r.stdout


def test_experience_section_contains_high_score_steps(tmp_path):
    """经验总结段应包含评分 4.5+ 的 Step。"""
    k = _setup(tmp_path)
    (k / "执行日志.md").write_text("""## Step 2: brilliant

日期：2026-04-19

### 用户评分
- 顺畅度：4.5/5
""", encoding="utf-8")
    r = _call(tmp_path, "2026-04-15", "2026-04-21")
    # 经验总结段出现且含 Step 2
    exp_idx = r.stdout.find("经验总结")
    nxt_idx = min(
        (r.stdout.find(h, exp_idx) for h in ("问题教训", "开发进展") if r.stdout.find(h, exp_idx) > 0),
        default=len(r.stdout),
    )
    assert exp_idx >= 0
    section = r.stdout[exp_idx:nxt_idx]
    assert "Step 2" in section, f"经验总结段应含高分 Step 2，实际段内容：\n{section}"


def test_lessons_section_contains_high_diff_steps(tmp_path):
    """问题教训段应包含评分差值 ≥ 1.5 的 Step。"""
    k = _setup(tmp_path)
    (k / "执行日志.md").write_text("""## Step 3: misaligned

日期：2026-04-19

### 模型自评
- 顺畅度：4.5/5

### 用户评分
- 顺畅度：2.5/5

### 评分差异分析
- 差值：2.0（模型自评偏高，用户感受实际受损）
""", encoding="utf-8")
    r = _call(tmp_path, "2026-04-15", "2026-04-21")
    lesson_idx = r.stdout.find("问题教训")
    assert lesson_idx >= 0
    nxt_idx = min(
        (r.stdout.find(h, lesson_idx) for h in ("开发进展",) if r.stdout.find(h, lesson_idx) > 0),
        default=len(r.stdout),
    )
    section = r.stdout[lesson_idx:nxt_idx]
    assert "Step 3" in section, f"问题教训段应含差值 2.0 的 Step 3，实际段内容：\n{section}"


def test_friendly_hint_about_custom_range(tmp_path):
    """输出顶部应有一行友好提示说明 --from/--to 可覆盖。"""
    _setup(tmp_path)
    r = _call(tmp_path)
    # 第一 3 行应含 "--from" 或 "可用"
    first_lines = "\n".join(r.stdout.splitlines()[:10])
    assert "--from" in first_lines or "指定" in first_lines


def test_no_entries_in_range_message(tmp_path):
    """范围内无条目 → 输出清晰提示而不是空 markdown。"""
    _setup(tmp_path)
    r = _call(tmp_path, "2020-01-01", "2020-01-07")
    assert "无记录" in r.stdout or "空" in r.stdout or "no entries" in r.stdout.lower()
```

- [ ] **Step 16.2: 运行 FAIL**

```bash
cd plugins/kdev-memory
python3 -m pytest tests/test_weekly_aggregate.py -v
```

Expected: 全 FAIL（`weekly.sh` 不存在）。

- [ ] **Step 16.3: Commit**

```bash
git add plugins/kdev-memory/tests/test_weekly_aggregate.py
git commit -m "test(kdev-memory): weekly.sh 滚动 7 天聚合 + 亮点段失败测试"
```

---

### Task 17: 实现 hooks/lib/weekly.sh

**Files:**
- Create: `plugins/kdev-memory/hooks/lib/weekly.sh`

- [ ] **Step 17.1: 创建脚本（因逻辑复杂，用 python3 subprocess 而非纯 bash）**

```bash
cat > plugins/kdev-memory/hooks/lib/weekly.sh <<'BASH_EOF'
#!/usr/bin/env bash
# weekly.sh —— kdev-memory v0.7
# 手动触发滚动 7 天周总结（today-6 ~ today）
# 调用：bash weekly.sh [--from YYYY-MM-DD] [--to YYYY-MM-DD]

set -eu

KDEV_DIR=".kdev/memory"
TODAY=$(date +%F)
DATE_FROM=""
DATE_TO=""

while [ $# -gt 0 ]; do
  case "$1" in
    --from) DATE_FROM="$2"; shift 2 ;;
    --to)   DATE_TO="$2"; shift 2 ;;
    *) shift ;;
  esac
done

[ -z "$DATE_TO"   ] && DATE_TO="$TODAY"
[ -z "$DATE_FROM" ] && DATE_FROM=$(date -d "$DATE_TO - 6 days" +%F 2>/dev/null || date -v-6d +%F 2>/dev/null || echo "$TODAY")

if [ ! -d "$KDEV_DIR" ]; then
  echo "[kdev-memory] 当前项目无 $KDEV_DIR，无法生成周总结"
  exit 0
fi

cat <<HEAD
（默认汇总过去 7 天 $DATE_FROM ~ $DATE_TO；可用 \`--from YYYY-MM-DD --to YYYY-MM-DD\` 指定范围）

HEAD

command -v python3 >/dev/null 2>&1 || { echo "[kdev-memory] weekly.sh 需要 python3"; exit 1; }

KDEV_DIR="$KDEV_DIR" DATE_FROM="$DATE_FROM" DATE_TO="$DATE_TO" python3 - <<'PYEOF'
import os, re
from pathlib import Path
from datetime import date

kdev = Path(os.environ["KDEV_DIR"])
d_from = date.fromisoformat(os.environ["DATE_FROM"])
d_to   = date.fromisoformat(os.environ["DATE_TO"])

def in_range(s):
    try:
        return d_from <= date.fromisoformat(s) <= d_to
    except Exception:
        return False

def parse_entries(path, head_re):
    """按 head_re 切条目，每条含 date 字段。"""
    if not path.exists():
        return []
    txt = path.read_text(encoding="utf-8")
    heads = list(re.finditer(head_re, txt, re.MULTILINE))
    items = []
    for i, m in enumerate(heads):
        start = m.start()
        end = heads[i+1].start() if i+1 < len(heads) else len(txt)
        body = txt[start:end]
        dm = re.search(r"^\s*日期[:：]\s*(\d{4}-\d{2}-\d{2})", body, re.MULTILINE)
        entry_date = dm.group(1) if dm else None
        title = m.group(0).lstrip("#").strip()
        items.append({"title": title, "date": entry_date, "body": body})
    return items

def user_score(body):
    m = re.search(r"^\s*[-*]?\s*顺畅度[:：]\s*([\d.]+)\s*/\s*5", body, re.MULTILINE)
    return float(m.group(1)) if m else None

def diff_score(body):
    # 差值段："差值: +2.0" 或 "评分差值：1.5"
    m = re.search(r"差值[:：]\s*([+-]?\d+(?:\.\d+)?)", body)
    return abs(float(m.group(1))) if m else None

# 聚合各类
steps   = [s for s in parse_entries(kdev/"执行日志.md", r"^##\s+Step\s+\S+.*$") if in_range(s["date"] or "")]
ques    = [q for q in parse_entries(kdev/"决策日志.md", r"^##\s+Q-\d+.*$") if in_range(q["date"] or "")]
gotchas = [g for g in parse_entries(kdev/"踩坑日志.md", r"^##\s+G-\d+.*$") if in_range(g["date"] or "")]
rules   = [r for r in parse_entries(kdev/"改进建议.md", r"^##\s+(?:R-\d+|建议\s*#?\s*\d+).*$") if in_range(r["date"] or "")]

# 亮点
high_score = [s for s in steps if (user_score(s["body"]) or 0) >= 4.5]
high_diff  = [s for s in steps if (diff_score(s["body"]) or 0) >= 1.5]
gotcha_to_rule = [g for g in gotchas if re.search(r"R-\d+", g["body"])]

# 平均分
scored = [user_score(s["body"]) for s in steps if user_score(s["body"]) is not None]
avg_score = round(sum(scored)/len(scored), 2) if scored else None

# 每日汇总覆盖率
daily = kdev/"每日汇总"
covered = 0
total_days = (d_to - d_from).days + 1
if daily.is_dir():
    from datetime import timedelta
    cur = d_from
    while cur <= d_to:
        if (daily/f"{cur.isoformat()}.md").exists():
            covered += 1
        cur += timedelta(days=1)

# 输出周总结 markdown
print(f"---")
print(f"date_range: {d_from} to {d_to}")
print(f"step_count: {len(steps)}")
print(f"generated_at: {date.today().isoformat()}")
print(f"---\n")
print(f"# 周总结 {d_from} ~ {d_to}\n")

# ========== 汇报四段骨架（v0.7：过程资产 / 经验总结 / 问题教训 / 开发进展）==========

# --- 1. 过程资产（机械盘点：本期产生了哪些可检索的素材） ---
print("## 📦 过程资产（Process Assets）\n")
print(f"> 本期 `.kdev/memory/` 新增的可检索过程素材盘点。\n")
print(f"- **Step**：{len(steps)} 条")
print(f"- **决策 Q-NNN**：{len(ques)} 条")
print(f"- **踩坑 G-NNN**：{len(gotchas)} 条")
print(f"- **改进信号 R-NNN / 建议**：{len(rules)} 条")
print(f"- **每日汇总覆盖率**：{covered}/{total_days} 天")
print(f"- **平均用户评分**：{avg_score if avg_score else '—'}/5\n")
if steps:
    print("条目索引（最多 10 条）：")
    for s in steps[:10]:
        print(f"- {s['title']}（{s['date']}）")
    if len(steps) > 10:
        print(f"- ...还有 {len(steps)-10} 条 Step 未列出")
print()

# --- 2. 经验总结（正向信号：什么做对了、哪些值得复用） ---
print("## 💡 经验总结（Experience）\n")
print("> 本期值得复用、沉淀、扩散的正向信号。\n")
experience_items = []
for s in high_score:
    experience_items.append(f"- 🏆 **高分 Step {user_score(s['body'])}/5**：{s['title']}（{s['date']}）—— 这条顺畅度高，值得提炼"
                           f"方法论")
for g in gotcha_to_rule:
    experience_items.append(f"- 📐 **踩坑升规则**：{g['title']} —— 已转化为 R-NNN 规则")
# 评分差值小且高分的 Step（方法论与感受一致，很扎实）
solid_steps = [s for s in steps
               if (user_score(s['body']) or 0) >= 4
               and (diff_score(s['body']) or 99) <= 0.5
               and s not in high_score]
for s in solid_steps[:3]:
    experience_items.append(f"- ✅ **稳扎稳打**：{s['title']} —— 模型自评和用户评分基本一致，执行扎实")
if not experience_items:
    print("- （本期无高分 Step / 踩坑升规则 / 稳扎稳打信号；可能是推进偏缓或评分未充分采集）")
else:
    for item in experience_items:
        print(item)
print()

# --- 3. 问题教训（负向信号：哪里栽了跟头、方法论盲区在哪） ---
print("## ⚠️ 问题教训（Lessons）\n")
print("> 本期暴露的方法论盲区、流程失守、差值信号。\n")
lesson_items = []
for s in high_diff:
    if s not in high_score:
        ds = diff_score(s['body']) or 0
        lesson_items.append(f"- 🔍 **评分差值 {ds}**：{s['title']}（{s['date']}）—— 模型自评和用户感受落差大，"
                           f"方法论盲区候选")
# 未升规则的高频踩坑（G-NNN 无 R-NNN 关联）
unresolved_gotchas = [g for g in gotchas if not re.search(r"R-\d+", g["body"])]
for g in unresolved_gotchas[:3]:
    lesson_items.append(f"- 🕳️ **待升规则的踩坑**：{g['title']} —— 建议评估是否立 R-NNN")
# 低评分 Step（< 3）
low_score = [s for s in steps if (user_score(s['body']) or 99) < 3]
for s in low_score[:3]:
    lesson_items.append(f"- 🛑 **低评分**（{user_score(s['body'])}/5）：{s['title']} —— 用户体验受损，值得复盘")
if not lesson_items:
    print("- （本期无差值 ≥ 1.5 / 低评分 / 未升规则踩坑，方法论表现稳定）")
else:
    for item in lesson_items:
        print(item)
print()

# --- 4. 开发进展（实际业务推进：主线走到哪、完成/未完成、下期计划） ---
print("## 🚀 开发进展（Progress）\n")
print("> 本期实际业务推进、里程碑完成、下期计划。\n")
state = kdev/"当前状态.md"
state_body = state.read_text(encoding="utf-8") if state.exists() else ""

# 主线摘要：取当前状态.md 前几行 body（或提示用户自行补充）
if state_body:
    # 去 frontmatter
    cleaned = re.sub(r"^---.*?---\s*\n", "", state_body, flags=re.DOTALL)
    # 取前 300 字
    print("**主线状态**（摘自 当前状态.md）：\n")
    print(cleaned.strip()[:500])
    print()
else:
    print("**主线状态**：（无 当前状态.md，请 Claude 根据 Step 条目总结叙事）\n")

# 完成的里程碑：基于 Step 标题里的"完成/交付/ship/release"关键词
milestones = [s for s in steps if re.search(r"完成|交付|ship|release|合并|上线|发布", s["title"], re.IGNORECASE)]
if milestones:
    print("**里程碑**：\n")
    for m in milestones[:5]:
        print(f"- {m['title']}（{m['date']}）")
    print()

# 下期展望
print("**下期展望**：")
nxt = re.search(r"(?:下一步|next|下周计划)[:：]?\s*\n?(.+?)(?:\n\n|\Z)", state_body, re.DOTALL | re.IGNORECASE) if state_body else None
if nxt:
    print(f"\n{nxt.group(1).strip()[:500]}\n")
else:
    print("（当前状态.md 未填"下一步"字段，请 Claude 整理 Step 推演下期重点）\n")

# --- 附：待沉淀候选（跨四段的辅助段，不计入骨架） ---
print("## 📌 附录：待沉淀候选（→ docs/）\n")
print("（执行 `/kdev-memory-promote` 查看完整候选列表与去向建议）\n")

if not (steps or ques or gotchas or rules):
    print(f"\n**本周范围内无记录**（{d_from} ~ {d_to} 在 .kdev/memory/ 里没有对应日期的条目）")
PYEOF
BASH_EOF

chmod +x plugins/kdev-memory/hooks/lib/weekly.sh
```

- [ ] **Step 17.2: 运行测试**

```bash
cd plugins/kdev-memory
python3 -m pytest tests/test_weekly_aggregate.py -v
```

Expected: 5 条全 PASS。

- [ ] **Step 17.3: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/weekly.sh
git commit -m "feat(kdev-memory): weekly.sh 滚动 7 天聚合 + 亮点段"
```

---

### Task 18: 新建 /kdev-memory-weekly slash command

**Files:**
- Create: `plugins/kdev-memory/commands/kdev-memory-weekly.md`

- [ ] **Step 18.1: 创建 command**

```markdown
---
description: 生成滚动 7 天周总结（默认 today-6 ~ today），可选 --from/--to 指定范围；亮点段突出高分 Step、差值 ≥ 1.5、踩坑升规则
argument-hint: [无参数 | --from YYYY-MM-DD --to YYYY-MM-DD]
---

# /kdev-memory-weekly

手动触发周总结。默认汇总过去 7 天（today-6 ~ today）；也可用 `--from/--to` 指定任意日期范围。

## 场景示例

- 周二下班执行 → 汇总上周三 ~ 本周二（7 天）
- `--from 2026-04-01 --to 2026-04-30` → 汇总整个 4 月

## 聚合数据

!`bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/weekly.sh" $ARGUMENTS`

## 你的任务

根据上面 bash 脚本的输出：

1. **复核聚合结果**：Step 数、G/Q/R 数量、评分均值是否合理
2. **按汇报四段骨架补叙事**：bash 脚本只做机械聚合，你需要为每段补上"为什么"：

   **📦 过程资产** —— 盘点段已机械输出，你只需做一件事：
   - 对 Step 条目做聚类（按主题而非日期），例如"collector 相关 3 条"、"鉴权相关 2 条"
   - 不评价，只归类

   **💡 经验总结** —— 正向信号段，必须解释"为什么是经验"：
   - 对每条 🏆 高分 Step：说明**这条做对了什么、能否复用**到其他场景
   - 对每条 📐 踩坑升规则：说明**原来的误区是什么、规则怎么闭环**
   - 对每条 ✅ 稳扎稳打：说明**方法论和感受一致说明了什么**（通常是"这类任务机制成熟"）

   **⚠️ 问题教训** —— 负向信号段，必须指出"盲区在哪"：
   - 对每条 🔍 差值大 Step：分析**模型自评偏高 vs 偏低**的原因（自我美化？用户期望没对齐？）
   - 对每条 🕳️ 待升规则的踩坑：建议是否立 R-NNN、触发条件、norm 化形态
   - 对每条 🛑 低评分：诊断**是技术问题还是流程/沟通问题**

   **🚀 开发进展** —— 业务视角，必须交代"走到哪、下期去哪"：
   - 整理里程碑为 2-3 段业务叙事（不是流水账）
   - 补完下期展望：如果 `当前状态.md` 的"下一步"为空，从 Step 轨迹推演
   - 明确标记阻塞项（`unresolved_gotchas` 字段 + 未升规则的重复踩坑）

3. **待沉淀候选（附录段）**：从 `/kdev-memory-promote` 视角扫描 pending 条目，给出 docs/ 去向建议
4. **补完下期展望**（若 `当前状态.md` 不全）
3. **落盘**：把最终周总结写入：

```
.kdev/memory/每周汇总/YYYY-MM-DD-到-YYYY-MM-DD.md
```

文件名用实际起止日期，便于检索。

4. **确认保存后告知用户**：输出文件路径 + 一句话摘要（几条 Step、最大亮点是什么）。

## 规则

- **严禁翻会话上下文**：只用 `.kdev/memory/` 源文件聚合，这是 kdev-memory 的铁规
- **四段骨架不可删**：过程资产 / 经验总结 / 问题教训 / 开发进展 —— 这是汇报骨架，即便某段为空也要保留标题并标"（本期无信号）"
- **经验/教训必须解释为什么**：例如不能只写 `Step 15 评分 4.5/5`，要写 `Step 15 评分 4.5/5 —— collector 双适配方案一次做通，差值 +0.5 说明方法论比预期更顺`
- **待沉淀候选要给出去向建议**：参考 `/kdev-memory-promote` 的推荐表
- **不做 data 修改**：周总结是只读聚合，不改源条目 frontmatter
```

- [ ] **Step 18.2: 手工试跑**

```bash
cd /home/lyadmin/Projects/token-statistics 2>/dev/null || { echo "skip"; exit 0; }
bash "$HOME/Projects/kdev-agents-v0.7/plugins/kdev-memory/hooks/lib/weekly.sh" --from 2026-04-18 --to 2026-04-24
```

Expected: 输出合法 markdown（含亮点段、数据层、下周展望）。

- [ ] **Step 18.3: Commit**

```bash
git add plugins/kdev-memory/commands/kdev-memory-weekly.md
git commit -m "feat(kdev-memory): /kdev-memory-weekly slash command（滚动 7 天）"
```

---

## Phase 8: 迁移 playbook + release 文档

### Task 19: 迁移脚本（供老项目使用）

**Files:**
- Create: `plugins/kdev-memory/hooks/lib/migrate-v0.7.sh`

**Rationale**: 已装 v0.6 且 `.kdev/` 已被 git tracked 的项目（如 token-statistics），升 v0.7 后需要"软迁移"：append gitignore + `git rm --cached`，不清历史 commit（保留 dog-fooding 证据）。

- [ ] **Step 19.1: 创建脚本**

```bash
cat > plugins/kdev-memory/hooks/lib/migrate-v0.7.sh <<'BASH_EOF'
#!/usr/bin/env bash
# migrate-v0.7.sh —— kdev-memory v0.7 软迁移
# 把已经被 git tracked 的 .kdev/ 转成本地过程目录
# - .gitignore append .kdev/（由 init-gitignore.sh 负责）
# - git rm --cached -r .kdev/（移出 index，保留历史 commit）
# - 用户手动 commit 这次改动

set -eu

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[kdev-memory] 当前不在 git 仓库，无需迁移"
  exit 0
fi

if [ ! -d ".kdev" ]; then
  echo "[kdev-memory] 当前无 .kdev/ 目录，跳过"
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. append .gitignore
bash "$SCRIPT_DIR/init-gitignore.sh"

# 2. 查 .kdev/ 是否被 tracked
if git ls-files --error-unmatch .kdev/ >/dev/null 2>&1; then
  echo "[kdev-memory] .kdev/ 当前被 git tracked，移出 index（保留历史 commit）..."
  git rm -r --cached .kdev/ > /dev/null 2>&1
  echo "[kdev-memory] 完成。请 git diff --cached 核对，再 commit："
  echo ""
  echo "  git commit -m 'chore: .kdev/ 转为本地过程目录（kdev-memory v0.7 立场反转）'"
  echo ""
else
  echo "[kdev-memory] .kdev/ 未被 git tracked，无需迁移"
fi

echo ""
echo "[kdev-memory] v0.7 软迁移完成。docs/ 下的团队级产物保持不变。"
echo "后续沉淀过程→产物用 /kdev-memory-promote；周总结用 /kdev-memory-weekly。"
BASH_EOF

chmod +x plugins/kdev-memory/hooks/lib/migrate-v0.7.sh
```

- [ ] **Step 19.2: README 加一段"从 v0.6 升级到 v0.7"**

在 README.md 末尾追加：

```markdown

## 从 v0.6 升级到 v0.7

v0.7 把 `.kdev/` 从"跟代码 commit"改为"**本地过程目录默认 gitignore**"（立场反转）。已有项目升级步骤：

```bash
# 在项目根目录执行
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/migrate-v0.7.sh"

# 核对后 commit
git diff --cached
git commit -m "chore: .kdev/ 转为本地过程目录（kdev-memory v0.7 立场反转）"
```

历史 commit 保留（`.kdev/` 过往版本仍在 git log 里，便于追溯 dog-fooding 证据）；未来 `.kdev/` 变更不再进 git。

**不想迁移**：`export KDEV_GIT_TRACK=1`，跳过 .gitignore 修改（单人项目可用，多会话/多成员强烈不推荐，会撞 merge 冲突）。

详细立场反转推理见 [dev-note 2026-04-24](../../docs/skills/kdev-memory/dev-notes/2026-04-24-kdev-memory-git托管立场反转-过程vs产物分家.md) 和**开发历程 v0.7 章节**。
```

- [ ] **Step 19.3: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/migrate-v0.7.sh plugins/kdev-memory/README.md
git commit -m "feat(kdev-memory): migrate-v0.7.sh 软迁移脚本 + README 升级章节"
```

---

### Task 20: 开发历程.md 补 v0.7 章节

**Files:**
- Modify: `docs/skills/kdev-memory/开发历程.md`（若不存在则先核查）

**Rationale**: note-1 §4.3 已提供完整草稿，本 task 把草稿落盘。

- [ ] **Step 20.1: 核查文件存在**

```bash
ls docs/skills/kdev-memory/开发历程.md 2>&1 || ls docs/skills/kdev-memory/*.md
```

Expected: 找到文件或其等价物（如 `kdev-memory 开发历程.md` / `开发历程.md`）。

- [ ] **Step 20.2: 追加 v0.7 章节**

把下面内容追加到文件末尾（如无最后空行先加空行）：

```markdown

## v0.7 立场反转：`.kdev/` 不再主张 git 托管

**背景**：kdev-memory v0.1~v0.6 的 README 主张"`.kdev/memory/` 跟代码 commit —— 工程决策/踩坑属于项目资产，应该进 git"。2026-04-24 在 token-statistics 项目的实战中，这个主张被证伪。

**证伪链条**：
1. **G-028**：多会话并发时 Step 编号撞车（2026-04-22）
2. **R-014**：代码 worktree 隔离（补丁 1）
3. **R-015 + 建议 9**：记忆 worktree 模型（补丁 2，退化为同 worktree 分 commit）
4. **merge 冲突**（2026-04-24）：iter-9 合 master 时 `.kdev/` 4 个文件同时冲突 —— 建议 9 预测的"基线分叉"真实发生
5. **用户反思**："如果 .kdev 不 git 托管，是不是就不需要考虑这些问题了"
6. **团队场景追问**："不同成员的记忆文件会混乱"
7. **结晶原则**：**"`.kdev/` 是过程记录，不是最终产物；团队共享的是产物，不是过程"**

**反转内容**：
- 旧定位：`.kdev/` 是项目资产 → 应 git 托管
- 新定位：`.kdev/` 是个人过程草稿 → 默认 gitignore；产物抽到 `docs/` 等处共享

**连带设计**：
- **Brief 三层分层（P0/P1/P2）**：替代字面 grep 平铺，P0 硬阻塞 / P1 需核对 / P2 仅报告
- **销账语义 B+C 混合**：历史条目走启发式 grep（`褪色补录` / `保留占位` / `非原生当场采集` / `## Step M-`），新条目走 `status: voided-faded` frontmatter
- **沉淀机制 `/kdev-memory-promote`**：明确"过程→产物"的流转通道，防止立场反转后团队两眼一抹黑
- **周总结 `/kdev-memory-weekly`**：滚动 7 天窗口（不是 ISO 周），手动触发，输出按**汇报四段骨架**组织（过程资产 / 经验总结 / 问题教训 / 开发进展）—— 直接可贴汇报文档
- **SessionEnd WARN**：从 `git status --porcelain` 改为 `.last-flush` mtime 比对（不依赖 git）
- **顺手修 bug**：note-2 里的 Step M- 编号合并显示 bug / 日期字段脱钩

**意义**：过去所有"多会话/多成员并发记忆协作"补丁（G-028 / R-014 / R-015 / 建议 8 / 建议 9）都是在**错误前提**下的补丁 — 不托管后这些问题自动消失。dog-fooding 发现的一次设计前提错误比任何补丁都有价值。

**实战参考**：
- [token-statistics 迭代 9 期间 Step 12~15](https://github.com/KDevSec/token-statistics/tree/master/.kdev/memory)（⚠️ 立场反转后此链接会失效，但历史 commit 保留）
- [dev-note 2026-04-24-kdev-memory-git托管立场反转-过程vs产物分家.md](dev-notes/2026-04-24-kdev-memory-git托管立场反转-过程vs产物分家.md)
- [dev-note 2026-04-24-brief-hook-欠评step误报-褪色补录占位识别缺口.md](dev-notes/2026-04-24-brief-hook-欠评step误报-褪色补录占位识别缺口.md)
```

- [ ] **Step 20.3: Commit**

```bash
git add docs/skills/kdev-memory/开发历程.md
git commit -m "docs(kdev-memory): 开发历程补 v0.7 立场反转章节"
```

---

### Task 21: 技术分享 md 同步

**Files:**
- Modify: `docs/skills/kdev-memory/kdev-memory 开发历程技术分享.md`

- [ ] **Step 21.1: 读文件找结构**

```bash
grep -n "^## \|^# " "docs/skills/kdev-memory/kdev-memory 开发历程技术分享.md" | head -30
```

确认文件是否有版本章节列表。

- [ ] **Step 21.2: 追加 v0.7 章节（版本简表 + 详细）**

在文件末尾追加"## v0.7（2026-04-24）：立场反转 + 机制重构"章节，内容简版：

```markdown

## v0.7（2026-04-24）：立场反转 + 机制重构

一句话：**承认 `.kdev/` 是本地过程草稿，产物走 docs/ 沉淀通道**。

### 核心反转

v0.1~v0.6 的 README 主张"`.kdev/memory/` 跟代码 commit，工程决策/踩坑属于项目资产"。token-statistics 的实战中这个前提被证伪——多会话/多成员协作会撞 merge 冲突、Step 编号竞态、基线分叉。补丁一路打到 R-015 仍在"托管前提"下挣扎，直到用户提出"如果 .kdev 不 git 托管，是不是就不需要考虑这些问题了"——釜底抽薪。

### 连带改造

| 模块 | v0.6 | v0.7 |
|---|---|---|
| README 立场 | "应该进 git" | "本地过程目录，默认 gitignore" |
| init 行为 | 只建文件 | 自动 append `.kdev/` 到 `.gitignore`（`KDEV_GIT_TRACK=1` 跳过） |
| SessionEnd WARN | `git status --porcelain` | `.last-flush` mtime 比对（不依赖 git） |
| Brief 欠评 | 字面 grep "完成时间：—" | 销账识别（status 字段 + 启发式兜底）+ 三层分层 P0/P1/P2 |
| 过程→产物 | 无 | `/kdev-memory-promote` 命令 + promote_status schema |
| 周总结 | 无 | `/kdev-memory-weekly` 滚动 7 天 + 汇报四段骨架（过程资产 / 经验总结 / 问题教训 / 开发进展） |
| Brief 显示 bug | `Step M-5~M-8` 误合成"Step 11-12" / 日期脱钩 | 修 |

### 教训

1. **skill 的核心假设应在 README 里显式列出**（本例：".kdev/ 应 git 托管"），便于后续证伪时精准定位
2. **核心假设被证伪时，优先反转前提而不是继续打补丁**
3. **skill 作者做 dog-fooding 是最重要的 validation 路径** —— 理论上的设计再合理都不如实战一次的反转信号
4. **skill 迭代史应作为公开产物保留** —— 本章就是反转证据链的公开面

详见 [dev-note 立场反转分析](dev-notes/2026-04-24-kdev-memory-git托管立场反转-过程vs产物分家.md) + [开发历程 v0.7 章节](开发历程.md#v07-立场反转)。
```

- [ ] **Step 21.3: Commit**

```bash
git add "docs/skills/kdev-memory/kdev-memory 开发历程技术分享.md"
git commit -m "docs(kdev-memory): 技术分享补 v0.7 章节"
```

---

### Task 22: CHANGELOG 更新

**Files:**
- Modify: `plugins/kdev-memory/CHANGELOG.md`

- [ ] **Step 22.1: 在 CHANGELOG 顶部加 v0.7.0 条目**

打开 CHANGELOG.md，在第一个 `## ` 二级标题之前（文件顶部 header 之后）插入：

```markdown

## [0.7.0] — 2026-04-24

### 🔄 立场反转（breaking change in philosophy, not API）
- `.kdev/` 从"项目资产、跟代码 commit"改为"**本地过程目录，默认 gitignore**"
- init 时自动 append `.kdev/` 到项目 `.gitignore`（`KDEV_GIT_TRACK=1` 可跳过）
- 团队共享产物改走 `/kdev-memory-promote` + `docs/` 通道

### ✨ 新增
- **`/kdev-memory-promote`** 命令：列出 pending 沉淀候选 + 推荐去向，用户确认后写入 docs/ 并更新 promote_status
- **`/kdev-memory-weekly`** 命令：滚动 7 天周总结（默认 today-6 ~ today，可用 --from/--to 覆盖），输出按**汇报四段骨架**组织：
  - 📦 **过程资产**（机械盘点：Step/Q/G/R 条数、每日汇总覆盖率、条目索引）
  - 💡 **经验总结**（正向信号：4.5+ 高分 Step、踩坑升规则、稳扎稳打条目）
  - ⚠️ **问题教训**（负向信号：差值 ≥ 1.5 的 Step、低评分、未升规则的高频踩坑）
  - 🚀 **开发进展**（业务视角：主线叙事、里程碑、下期展望）
- **Schema 扩展**：Step / R / Q / G frontmatter 新增 `status: open | scored | voided-faded | voided-r-nnn`，R / Q / G / 改进建议新增 `promote_status: pending | done | skipped` + `promote_target` + `promote_date`
- **Brief 三层分层**：P0 硬阻塞（WARN / 今日欠评）/ P1 需核对（跨天汇总缺失 / 接口漂移 / 沉淀提醒）/ P2 参考（checkpoint / growth backlog）
- **销账识别**：Brief 欠评扫描优先读 `status` frontmatter，fallback 启发式 grep（`褪色补录` / `保留占位` / `非原生当场采集` / `## Step M-`）—— 解决 iter 5~8 meta 回补条目被反复报"待处理"问题
- `hooks/lib/init-gitignore.sh`：helper，初始化自动配 gitignore
- `hooks/lib/promote-scan.sh`：Brief P1 集成的沉淀候选扫描器
- `hooks/lib/promote-list.sh`：`/kdev-memory-promote` 命令聚合脚本
- `hooks/lib/weekly.sh`：`/kdev-memory-weekly` 命令聚合脚本
- `hooks/lib/migrate-v0.7.sh`：v0.6 → v0.7 软迁移（保留历史 commit）

### 🐛 修复
- Brief `Step M-5 ~ M-8` 显示时被误合成 `Step 11-12` + 日期字段脱钩的长期 bug（note-2）
- SessionEnd WARN 不再依赖 git（立场反转后 `.kdev/` 默认 gitignore，git status 拿不到变化）—— 改为 `.last-flush` mtime 比对

### 📚 文档
- README：对比表第三行最后一列、差异化设计点第 3 条全部重写
- SKILL.md：新增"条目状态与沉淀字段"章节、"v0.7+ 自动加 .kdev/ 到 .gitignore"段
- references/六类记录-schema.md：所有 frontmatter 示例同步新字段
- 开发历程.md：新增 v0.7 立场反转章节
- 技术分享.md：新增 v0.7 章节

### ⚠️ 迁移指引
已装 v0.6 且 `.kdev/` 已 git tracked 的项目：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/migrate-v0.7.sh"
git diff --cached  # 核对
git commit -m "chore: .kdev/ 转为本地过程目录（kdev-memory v0.7 立场反转）"
```

历史 commit 保留（dog-fooding 证据）；未来 `.kdev/` 变更不再进 git。
```

- [ ] **Step 22.2: Commit**

```bash
git add plugins/kdev-memory/CHANGELOG.md
git commit -m "docs(kdev-memory): CHANGELOG 加 v0.7.0 条目"
```

---

### Task 23: plugin.json 版本 bump + release commit

**Files:**
- Modify: `plugins/kdev-memory/.claude-plugin/plugin.json`

- [ ] **Step 23.1: 改版本号**

```bash
# 检查当前版本
grep version plugins/kdev-memory/.claude-plugin/plugin.json
```

Expected: `"version": "0.6.0"`

手动编辑 plugin.json，把 `"version": "0.6.0"` 改为 `"version": "0.7.0"`。如果 description 字段需要相应更新，也更新（加"立场反转 + 三层分层 + 沉淀机制 + 周总结"）。

- [ ] **Step 23.2: 全量跑测试确认 ready to release**

```bash
cd plugins/kdev-memory
python3 -m pytest tests/ -v
bash evals/run-hook-selftest.sh
```

Expected: 所有测试 PASS。

- [ ] **Step 23.3: Release commit**

```bash
git add plugins/kdev-memory/.claude-plugin/plugin.json
git commit -m "chore(kdev-memory): bump 0.6.0 → 0.7.0（立场反转 + 机制重构）"
```

- [ ] **Step 23.4: Summary 输出给用户**

```bash
git log --oneline main..HEAD
```

Expected: 看到 v0.7 全部 commit 序列（大约 15-20 个 commit）。把这些列给用户，让用户决定：
- 方案 A：直接 fast-forward 合 main
- 方案 B：压成一个大 commit 合 main
- 方案 C：开 PR 走正常 review 流（若仓库有 CI）

---

## Plan Scope Summary

**总任务数**：23 tasks（含 Pre-Work）
**预计 commit 数**：~20（每个 task 末尾一个 commit）
**TDD 覆盖**：Phase 2/4/5/6/7 共 5 个 phase 走 red-green-refactor；Phase 1/8 是纯文档/配置
**跨文件改动范围**：
- `plugins/kdev-memory/skills/kdev-memory/SKILL.md`（+2 章节）
- `plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md`（字段扩展）
- `plugins/kdev-memory/README.md`（立场重写）
- `plugins/kdev-memory/CHANGELOG.md`（v0.7 条目）
- `plugins/kdev-memory/.claude-plugin/plugin.json`（版本 bump）
- `plugins/kdev-memory/hooks/session-start-brief.sh`（三层重构）
- `plugins/kdev-memory/hooks/session-end-check.sh`（mtime 改造）
- `plugins/kdev-memory/hooks/post-write-check.sh`（.last-flush touch）
- `plugins/kdev-memory/hooks/lib/step_completeness.py`（销账识别）
- `plugins/kdev-memory/hooks/lib/init-gitignore.sh`（新增）
- `plugins/kdev-memory/hooks/lib/promote-scan.sh`（新增）
- `plugins/kdev-memory/hooks/lib/promote-list.sh`（新增）
- `plugins/kdev-memory/hooks/lib/weekly.sh`（新增）
- `plugins/kdev-memory/hooks/lib/migrate-v0.7.sh`（新增）
- `plugins/kdev-memory/commands/kdev-memory-promote.md`（新增目录 + 文件）
- `plugins/kdev-memory/commands/kdev-memory-weekly.md`（新增）
- `plugins/kdev-memory/tests/test_step_completeness_voided.py`（新增）
- `plugins/kdev-memory/tests/test_session_end_mtime.py`（新增）
- `plugins/kdev-memory/tests/test_init_gitignore.py`（新增）
- `plugins/kdev-memory/tests/test_promote_scan.py`（新增）
- `plugins/kdev-memory/tests/test_weekly_aggregate.py`（新增）
- `docs/skills/kdev-memory/开发历程.md`（+ v0.7 章节）
- `docs/skills/kdev-memory/kdev-memory 开发历程技术分享.md`（+ v0.7 章节）

---

## 执行提示（给 executor）

1. **必须按 phase 顺序执行** —— phase 间有依赖（Schema → 销账识别 → Brief 三层；mtime 机制依赖 `.last-flush` touch 集成；立场反转依赖 init-gitignore；promote 命令依赖 promote-scan；迁移脚本依赖 init-gitignore）
2. **每个 task 末尾的 commit 不要合并** —— 保持 atomic 便于 bisect
3. **TDD 严守 red-green-refactor**：Phase 2/4/5/6/7 的每个 task 都是"先写失败测试 commit → 再写实现 commit"两个独立 commit
4. **跑 evals/run-hook-selftest.sh** 作为 release 前最后的 sanity gate（Task 23.2）
5. **迁移脚本只对老项目生效** —— 在 kdev-agents 仓本身执行 `migrate-v0.7.sh` 会因为 `.kdev/` 不存在而 no-op，这是正确行为
6. **Phase 1 跳过 TDD**：Schema 定义是纯文档改动，测试由 Phase 2 的集成测试间接验证（读 frontmatter status 字段）
