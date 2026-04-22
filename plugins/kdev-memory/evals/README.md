# kdev-memory evals

本目录下有**两条并列的 eval 线**，测不同层面：

| eval 线 | 测什么 | 跑一次成本 | 什么时候跑 |
|---|---|---|---|
| [`evals.json`](evals.json) + [`run-hook-selftest.sh`](run-hook-selftest.sh) | `hooks/trigger-match.py` 的召回准确性（sanitize / triggers 解析 / 子串匹配 / 去重） | 秒级（纯 shell） | 每次改 trigger-match.py / sanitize 规则 / triggers 字段扫描 |
| [`skill-quality/`](skill-quality/) | **SKILL.md + references/** 的行为质量（Claude 执行 skill 任务后产出是否合格） | 分钟级 × 每个 eval 2 subagent | 每次重写 SKILL.md / 新增 / 删除 reference / 改核心原则 |

两条线互相独立——hook 改动只触发第一条，SKILL.md 文档改动只触发第二条。若同时改了就两条都跑。

---

## trigger-match 召回 eval（本文件以下章节）

skill-creator 式的质量验证集：比对 0.2.0（无 triggers）vs 0.3.0（有 triggers）在相同 prompt 下的行为差异。

## 测试集（10 条）

见 [`evals.json`](evals.json)。分两大类：

- **should-trigger**（5 条）：验证踩坑/Step/铁规/spec 在相关 prompt 下能命中并召回
- **should-NOT-trigger**（5 条）：验证 sanitize 机制（代码块 / URL / 文件路径里的字面量不触发） + 无关话题不干扰

## 测试 fixture

[`fixtures/project-state/`](fixtures/project-state/) 是一个完整的测试项目状态，包含：

- `.kdev/memory/踩坑日志.md` —— G-012（pnpm）+ G-014（aiohttp）
- `.kdev/memory/执行日志.md` —— Step 23（今日）+ Step 24（昨日）
- `.kdev/memory/方法论铁规.md` —— commit 粒度 + API 设计
- `.kdev/memory/当前状态.md` —— 带 YAML frontmatter
- `.kdev/memory/决策日志.md` —— Q-001 / Q-008
- `constitution.md` —— 项目宪章（带 frontmatter triggers）

所有条目都标了 triggers，用于 0.3.0 的召回测试。

## 怎么跑

skill-creator 的完整 eval flow（每个 test prompt 跑 baseline + with-skill 两个 subagent）比较重，建议按需跑。

### 纯单元测试（不过 hook shell）

`plugins/kdev-memory/tests/test_trigger_match.py` 用 stdlib `unittest` 覆盖
`trigger-match.py` 的内部函数（sanitize / triggers 解析 / match / TTL / glob
扫描含归档子目录），零外部依赖、几十毫秒跑完：

```bash
cd plugins/kdev-memory
python3 -m unittest discover tests -v
```

44 个测试覆盖 7 类：SanitizePrompt / ParseTriggersValue / ParseMultilineTriggers
/ MatchEntries / DedupFilter / TTLPrune / GlobScan（主文件 + 归档目录）。

### 轻量端到端验证（走 hook shell）

直接复用 fixture 跑 trigger-match.py 的端到端 hook 调用，验证整条召回链路：

```bash
cd plugins/kdev-memory/evals/fixtures/project-state

# 10 个 prompt 逐个喂给 hook，看是否正确召回/不召回
for i in $(seq 1 10); do
  name=$(python3 -c "import json; e=json.load(open('../../evals.json'))['evals']; print(e[$i-1]['name'])")
  prompt=$(python3 -c "import json; e=json.load(open('../../evals.json'))['evals']; print(e[$i-1]['prompt'])")
  echo "=== Test $i: $name ==="
  echo "{\"prompt\":$(python3 -c "import json; print(json.dumps('$prompt'))"),\"session_id\":\"eval-$i\"}" \
    | bash ../../../hooks/user-prompt-trigger.sh \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); ctx=d.get("hookSpecificOutput",{}).get("additionalContext",""); print(ctx if ctx else "<suppress>")'
  echo
done
```

### 完整 skill-creator eval（需要人工 review）

当想做深度验证（验证 Claude 在召回后的实际行为变化）时：

```
1. 安装 0.2.0 到一个 worktree（checkout v0.2.0 tag）
2. 安装 0.3.0 到另一个 worktree
3. 对每个 eval prompt，分别在两个 worktree 跑 Claude 子 session
4. 对比输出质量（Claude 是否 Read G-012 / Step 23 / 宪章等）
5. 生成 benchmark.json + 用 skill-creator 的 generate_review.py 出 HTML 报告
```

详见 skill-creator 的 [运行指南](https://github.com/anthropics/skills)。

## 已完成的手工验证

Phase 2 提交时已做了 19 个手工测试（见 commit 77f83c9 的消息），覆盖：

- 5 个 should-trigger（G/Step/铁规/spec）
- 5 个 should-NOT-trigger（代码块/URL/路径/完全无关/字面搜索）
- Session 去重（同 session 不重复 + 跨 session 独立）
- Step 日期过滤（老 Step 不召回）
- MAX_INJECT=3 限额
- 边缘（空 prompt / malformed JSON / 无 session_id / 无 .kdev）

**机制侧已 deterministic 验证通过。剩下的是语义侧的"Claude 在召回后是否用好"——这是 skill-creator 完整 eval 的价值**，按需跑。
