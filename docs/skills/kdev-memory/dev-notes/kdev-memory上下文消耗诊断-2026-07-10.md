# kdev-memory 会话上下文消耗诊断报告

- **日期**：2026-07-10 01：23
- **项目**：ClaudeCodeTest（`/home/sec/project/ClaudeCodeTest`）
- **诊断对象**：kdev-memory 插件（SessionStart brief 注入）+ `.kdev/memory/当前状态.md`
- **会话**：`1422832c-b94e-400e-86b6-10b6fdbae54b`（Opus 4.8 1M，Claude Code）

---

## TL;DR（一句话结论）

会话"消耗很快"的**头号可控元凶**是 `.kdev/memory/当前状态.md` 的 **`current_step` 单个 frontmatter 字段膨胀到 10 万字符**，里面把 **5 段里程碑叙事**（当前 1 段 + `【上一里程碑】` × 4 段）全部串联堆积、从未归档；而 kdev-memory 的 SessionStart brief **每次会话都把这个字段全量注入上下文**。按中英混排 ~3–4 字符/token 估算，**单这一个字段就约 25–33k tokens，占开局上下文（实测 ~62k tokens）的 40%–54%**。

这是**无界增长（unbounded growth）**：里程碑越攒越多，字段只增不减，每个新会话的固定开销随之线性上涨。

---

## 1. 现象

用户反馈"Current session 消耗非常快"。实测发现：**第 1 轮对话（用户尚未输入任何实质任务）时，上下文已达 ~62k tokens**——即固定注入成本已占满大半，与本会话实际干的活（起 SSH 隧道、读几个文件、记一条备忘）无关。

## 2. 测量方法与数据来源（可复现）

1. **逐轮 token 用量**：解析会话 transcript JSONL（`~/.claude/projects/<project>/<session-id>.jsonl`）中每个 assistant 消息的 `message.usage` 字段（`input_tokens` / `cache_read_input_tokens` / `cache_creation_input_tokens` / `output_tokens`）。→ 得到"开局上下文 ~62k tokens、当前 ~110k tokens"这两个**地面真值（ground truth）**。
2. **固定注入源文件字符数**：直接 `wc -m` / Python `len()` 量 `CLAUDE.md`、`MEMORY.md`、`当前状态.md` 及其 `current_step` 字段。→ 得到各项**精确字符数（硬事实）**。
3. **token 估算**：字符数 ÷ 3～4（中英混排经验系数）。**注意：token 数为估算，字符数与 token 总量（62k/110k）为实测。**

## 3. 上下文构成排名（当前 ~110k tokens）

| 消耗项 | 估算 tokens | 性质 | 硬事实 |
|---|---:|---|---|
| 🔴 **`当前状态.md` 的 `current_step` 字段** | **~25–33k** | 每会话 SessionStart 全量注入 | **100,151 字符**，5 段里程碑，占该文件 97% |
| 技能目录（system prompt 内 100+ skills 描述） | ~18–20k | 每轮固定 | gstack / genskills--* / speckit-* / kdev-* / superpowers 等 |
| kdev-memory Skill 正文（本会话调用 `/kdev-memory` 时载入） | ~10–13k | 单次 | 单条消息 19,989 字符（本会话最大单条） |
| `MEMORY.md`（Claude 自动记忆索引） | ~4.5k | 每轮固定 | 13,569 字符（设计应"一行一条"，实际每条整段） |
| 两个 `CLAUDE.md`（工作区 + 项目） | ~3.4k | 每轮固定 | 3,367 + 6,694 字符 |
| base system prompt + MCP 指令 + deferred 工具 schema | ~10k+ | 每轮固定 | 环境/harness/30+ 延迟工具 |
| 本会话实际产出（干活） | ~16–20k | 累积 | 占比很小 |

> **注**：技能目录、base system prompt、MCP 指令等属 harness / 插件生态层面，非本项目 `.kdev/` 可直接控制；`current_step` / `MEMORY.md` 是**项目可控**且**可立即优化**的部分。

## 4. 根因：`current_step` 字段无界增长

### 4.1 设计意图 vs 实际

kdev-memory 文档中 `当前状态.md` 的 frontmatter `current_step` 定位为**"工作状态的单一真相源 / 短指针"**（"每次完成 Step 都要顺手改 `current_step` + `last_updated`"）。历史里程碑本应留在 `每日汇总/YYYY-MM-DD.md` 归档。

**实际**：写入路径每到一个新里程碑，就把上一段完整叙事用 `| 【上一里程碑】…` 前缀拼接进同一个 `current_step` 字段，**只增不减、从不归档**，导致该字段退化为一份"全量里程碑流水账"。

### 4.2 放大器：SessionStart brief 全量注入

kdev-memory 的 SessionStart hook 生成 `<kdev-memory-brief>` 时，**把 `current_step` 字段原样整段注入**（本会话 brief 中可见完整的 `🟢 2026-07-09… | 【上一里程碑】🟢 2026-06-30… | …2026-06-26… | …2026-06-24…`）。字段有多大，每个新会话的固定开销就多大——**无截断、无摘要、无上限**。

### 4.3 证据（硬数字）

```
当前状态.md 全文字符数        : 102,831
current_step 单字段字符数     : 100,151   （= 全文的 97%）
current_step 里程碑段数       : 5         （当前 1 段 + 【上一里程碑】×4）
transcript 实测开局上下文     : ~61,672 tokens   （用户尚未输入任务）
transcript 实测当前上下文     : ~110,213 tokens
```

## 5. 建议

### 5.1 插件侧（kdev-memory 维护者，治本）

1. **SessionStart brief 对 `current_step` 截断 / 摘要**：只注入当前段 + 最近 1 段里程碑，或做长度上限（如 ≤ 2k 字符）+ "更多见 `每日汇总/`" 指针，避免字段大小直接线性传导到每会话上下文。
2. **写入路径加防膨胀**：新增里程碑时，把上一段里程碑**移出** `current_step`、落进 `每日汇总/` 归档，`current_step` 恒定只保留"当前一句话状态"。可加校验（字段超阈值时 WARN / 阻止拼接）。
3. **文档明确 `current_step` 是短指针**，禁止 `| 【上一里程碑】` 式无界拼接（当前文档只说"顺手改"，未给出大小约束，留下了漂移口子）。

### 5.2 用户侧（可立即执行，治标）

1. **瘦身 `current_step`**：把现有 5 段里程碑**原样搬进** `每日汇总/` 对应日期文件（不丢历史），`current_step` 只留最新一句状态 + 归档指针。预计**每会话省 ~25–33k tokens**。
2. **压缩 `MEMORY.md`**：恢复"一行一条 hook"，省 2–3k。
3. **少反复调 skill**：每次 `/xxx` 会把整份 SKILL.md（~10k+）载入上下文，非必要不重复触发。

## 6. 附：复现命令

```bash
# 1) 逐轮 token 用量（地面真值）
python3 - <<'PY'
import json
f="<session-id>.jsonl"   # ~/.claude/projects/<project>/ 下
for line in open(f):
    r=json.loads(line)
    u=r.get("message",{}).get("usage") if r.get("type")=="assistant" else None
    if u: print(u.get("input_tokens"),u.get("cache_read_input_tokens"),
                 u.get("cache_creation_input_tokens"),u.get("output_tokens"))
PY

# 2) current_step 字段字符数与里程碑段数（硬事实）
python3 - <<'PY'
import re
s=open(".kdev/memory/当前状态.md",encoding="utf-8").read()
cs=re.search(r'^current_step:(.*?)\n[a-z_]+:', s, re.S|re.M).group(1)
print("当前状态.md 全文:", len(s))
print("current_step 字段:", len(cs), "占比 %.1f%%"%(len(cs)/len(s)*100))
print("里程碑段数:", s.count("【上一里程碑】")+1)
PY
```

## 7. 勘误与根因修正（2026-07-10 · kdev-agents 插件侧源码复核）

> 本节由 kdev-agents 仓（kdev-memory 插件开发地）对本报告做**源码级复核**后追加。结论：报告的因果机制成立且已逐行验证，但**根因作用域偏窄，需泛化**。

### 7.1 机制已在源码确认（非推测）

当前版本 `plugins/kdev-memory/hooks/session-start-brief.py`：

- `:559-562` — `read_state_field("current_step")` / `("pending_decisions")` / `("unresolved_gotchas")` 均读**原始字段值，无截断**。
- `:483-489` — 三字段原样拼进 brief（`f"- current_step: {state_step}"` 等），**无摘要、无长度上限**。

→ 报告 §4.2「原样整段注入，无截断 / 摘要 / 上限」与代码字节级吻合。

### 7.2 修正一：根因是「任意 verbatim 无界字段」，不止 current_step

报告把矛头钉在 `current_step` 单字段；源码显示**三字段同为 verbatim 无界注入**。本仓（kdev-agents）自身 `当前状态.md` 实测：

| 字段 | 本仓字符数 | 报告目标项目 |
|---|---:|---|
| `current_step` | 31 ✅ | 100,151 🔴 |
| `pending_decisions` | 844 ⚠️（增长中） | 未量 |
| `unresolved_gotchas` | 205 | 未量 |

**同一反模式在本仓换字段复现**：本仓 current_step 干净，但 pending_decisions 正沿老路无界增长。§5.1-1「截断 current_step」若照字面实现**只堵一洞**；治本须泛化为「三字段统一长度闸」。

### 7.3 修正二：现有 `verbosity=compact` 逃生舱堵不住

插件已有 brief 精简档（`config.yaml` 设 `brief.verbosity: compact`，`:441-457`），但 `:447-448` 显示 **compact 档仍全量注入 pending_decisions**：

```python
if state_pending:
    cparts.append(f"- pending_decisions: {state_pending}")
```

它裁的是「最近条目 / 员工 scope / 项目状态」，未裁会膨胀的字段 → 报告结论反而更成立：现成减负档也救不了。

### 7.4 对 §5 建议的修订

1. **§5.1-1 泛化**：长度闸覆盖 current_step / pending_decisions / unresolved_gotchas 三字段，且 **normal 与 compact 两档都要过闸**，溢出给「更多见 X」指针。
2. **§5.1-2 闸位前移**：写入侧（recorder / step 落盘）设阈值 WARN 或拒绝拼接，比注入侧更根治；注入侧长度闸作最后兜底。
3. **§5.2 正面样板**：本仓 current_step（31 字符）即健康「短指针」态，可直接当样板。
4. **token 估算偏乐观**：纯中文段 Claude tokenizer 常比 3–4 字符/token 更密，真实占比可能高于 40–54%（锚在 62k 实测总量，方向不翻）。

---

*本报告由测试会话内实测生成；字符数与 token 总量为实测，单项 token 为按字符数估算（中英混排 ~3–4 字符/token）。*
