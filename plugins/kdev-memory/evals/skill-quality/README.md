# skill-quality evals（skill-creator 风格的完整 eval）

## 这条 eval 线的定位

测 **SKILL.md + references/** 的**行为质量**：

> 当 Claude 被召唤来执行 skill 任务时（初始化、写汇总、切档、规则升级、跨会话续航、处理 WARN 等），它读了 SKILL.md 和对的 reference 后，产出的文件/动作是否符合预期？新老版本的差异在哪？

不同于 [`../evals.json`](../evals.json) 那条线（测 `hooks/trigger-match.py` 的召回准确性），这里测的是**语义层的 skill 行为**——Claude 真正在 sandbox 里执行后的结果。

## 什么时候跑

| 触发 | 建议 |
|---|---|
| 重写 SKILL.md 核心章节 | 跑 |
| 新增 / 删除 reference 文件 | 跑 |
| 改 description 的触发场景 | 跑 |
| 改 hook 脚本（trigger-match / sanitize 等） | **不用跑这条线**，用 `../evals.json` 那条 |
| 改 .kdev/memory/ 文件格式 | 跑（会影响 Claude 写入的产物） |

## 当前场景覆盖（8 个）

| # | 名字 | 场景类型 | 覆盖的 skill description 触发词 |
|---|---|---|---|
| 0 | init | core-flow | "建立工程记忆 / 加 .kdev / 搞记忆机制" |
| 1 | daily-summary | core-flow | "写今天总结 / 生成每日汇总 / 交接给明天" |
| 2 | rule-upgrade | core-flow | "这条以后都要遵守 / 加到项目规则 / 升级成铁规" |
| 3 | archive | core-flow | "切档 / 归档一下 / 整理主文件" |
| 4 | merge-conflict | edge-case | CLAUDE.md 已有同名章节的合并策略 |
| 5 | missing-data | edge-case | 当天 .kdev/memory/ 无条目时的坦白报告 |
| 6 | cross-session-resume | core-flow | "昨天做到哪了 / 继续上次的工作 / 恢复上下文" |
| 7 | warn-file | hook-interaction | 处理 SessionEnd hook 留下的 WARN-未记录-*.md |

**未覆盖**（skill description 里提到但暂不测的）：
- `<kdev-memory-recall>` / `<kdev-memory-brief>` 注入的处理 —— 需要模拟 hook 注入的上下文，subagent harness 做不到
- `checkpoints/压缩前-*.md` 的回溯读取 —— 低频场景，优先级低

## 目录结构

```
skill-quality/
├── README.md                  # 本文件
├── .gitignore                 # outputs / snapshots / review.html 不入库
├── evals.json                 # 【单一真相源】8 个场景的 prompt + fixture + assertions
└── iterations/                # 每次完整跑一次 eval 就新建一个子目录
    ├── 20260422-01-baseline-3-scenarios/   # 首轮 3 场景 + 基础 assertions
    └── 20260422-02-expanded-6-scenarios/   # 第二轮 6 场景 + 升级 assertions（当前权威基线）
        ├── benchmark.json
        ├── benchmark.md
        ├── notes.md                        # 本轮人工观察 + 过程指标
        └── eval-<name>/
            ├── eval_metadata.json          # 【冻结快照】本轮跑测时的 assertions（可能和 evals.json 不一样）
            ├── with_skill/run-1/
            │   ├── grading.json            # 本次 run 评分
            │   └── timing.json             # tokens + duration
            └── old_skill/run-1/
                ├── grading.json
                └── timing.json
```

### assertions 单一真相源 vs 冻结快照

- **`evals.json`** 是**当前权威**定义：assertions 会随着 skill 演进而升级（比如发现某条太宽松时改严格）
- **`iterations/*/eval-*/eval_metadata.json`** 是**冻结快照**：记录那一轮跑测时用的是什么 assertions，便于追溯
- 新增 iteration 时从 `evals.json` 拷贝 assertions 到 `eval_metadata.json`，之后两者分开演进

**运行时产生、不入库的**：
- `iterations/*/eval-*/<config>/run-*/outputs/` — subagent 生成的 sandbox（每份几百 KB）
- `workspace-*/` 目录 — 跑 eval 时的临时工作区（整个 skill-snapshot + outputs 都在这里）
- `review.html` — 随时可 regenerate

## 怎么跑一次完整 eval（人工步骤）

### 前置条件

```bash
# 已安装 skill-creator plugin
ls ~/.claude/plugins/cache/claude-plugins-official/skill-creator/ 2>/dev/null

# SKILL.md 和 references/ 处于你想测的状态
wc -l plugins/kdev-memory/skills/kdev-memory/SKILL.md
```

### Step 1：为本次 iteration 开一个工作区

```bash
# 命名约定：workspace-YYYYMMDD-<purpose>
WS=plugins/kdev-memory/evals/skill-quality/workspace-$(date +%Y%m%d)-<purpose>
mkdir -p $WS/skill-snapshot/skills/kdev-memory

# baseline skill（旧版）→ 从 git HEAD 或某个 tag 取
git show HEAD:plugins/kdev-memory/skills/kdev-memory/SKILL.md \
  > $WS/skill-snapshot/skills/kdev-memory/SKILL.md
```

### Step 2：为每个 eval 起 with_skill + old_skill 两个 subagent（并行）

在主 Claude Code 会话里用 Agent 工具。每个 subagent 要被告知：
- skill 路径（新版 = 当前 repo；老版 = snapshot 里的）
- fixture 路径（从 `../fixtures/skill-quality/eval-<N>-<name>/target-project/`）
- 要 `cp -r` 到自己的 sandbox 后再操作
- 写 `REPORT.md` 汇报

### Step 3：grade + aggregate + viewer

```bash
# 起 grader subagent 读 evals.json 的 assertions + 每个 run 的 sandbox/REPORT.md
# 每个 run 生成 run-1/grading.json

# aggregate
SC=~/.claude/plugins/cache/claude-plugins-official/skill-creator/unknown/skills/skill-creator
cd $SC && python3 -m scripts.aggregate_benchmark $WS --skill-name kdev-memory

# viewer（static 模式）
python3 $SC/eval-viewer/generate_review.py $WS \
  --skill-name "kdev-memory" \
  --benchmark $WS/benchmark.json \
  --static $WS/review.html
```

### Step 4：把可留存产物搬到 iterations/

```bash
ITER=plugins/kdev-memory/evals/skill-quality/iterations/$(date +%Y%m%d)-NN-<purpose>
mkdir -p $ITER
cp $WS/benchmark.{json,md} $ITER/
for eval_dir in $WS/eval-*; do
  name=$(basename $eval_dir)
  mkdir -p $ITER/$name
  cp $eval_dir/eval_metadata.json $ITER/$name/        # 冻结本轮 assertions 快照
  for config in with_skill old_skill; do
    mkdir -p $ITER/$name/$config/run-1
    cp $eval_dir/$config/run-1/grading.json $ITER/$name/$config/run-1/
    cp $eval_dir/$config/run-1/timing.json $ITER/$name/$config/run-1/
  done
done

# workspace 用完可以 rm -rf（outputs 太大 + gitignored）
rm -rf $WS
```

### 关键约定

- **baseline = 旧版本 skill**（不是"无 skill"）——这是"改进既有 skill"场景
- **每次 iteration 一个目录**，命名 `YYYYMMDD-NN-<purpose>` —— NN 递增标明同一天多轮
- **outputs/ / workspace-* / review.html 不入库**（已被 .gitignore）
- **benchmark / grading / timing / eval_metadata (snapshot) 入库** —— 作为 regression 基线 + 历史留痕

## 当前基线

[`iterations/20260422-04-claude-md-lint/`](iterations/20260422-04-claude-md-lint/) 是**当前对照权威基线**（版本 vs 版本对比）；
[`iterations/20260422-05-eval6-coverage/`](iterations/20260422-05-eval6-coverage/) 补齐了跨会话续航场景覆盖（单配置）。



- 对比：iter-3 解耦但无 lint ↔ 新增 `claude_md_lint.py` + SessionStart 集成 + "修漂移"召唤流程
- eval-8 drift-fix 场景 × 2 configs = 2 runs
- 关键结论：
  - 新版 100% pass vs baseline 75% pass —— lint 工具带来自动化闭环
  - 多花 ~20% tokens（跑 lint + Edit + 复验），换"发现 → 诊断 → patch → 验证"一次完成
  - Baseline 已识别漂移并给建议（证明 iter-3 架构的 self-documenting），但需用户多轮裁决；新版省去这个

完整说明见该 iteration 目录下的 `notes.md`。

## 演进历史（按时间倒序）

| iteration | 测什么 | 结论 |
|---|---|---|
| **[20260423-07-p0-1-discriminating](iterations/20260423-07-p0-1-discriminating/)** ← 最新 | P0-1 Step 完成闸门是否必要？discriminating eval | **结论：不必加**——baseline 已有等效语义，加闸门只省 21% tokens 不改变行为 |
| [20260423-06-step-completeness-lint](iterations/20260423-06-step-completeness-lint/) | Step 完整度 lint（P1-5 brief 告警 + P1-6 Stop 阻塞）| 8/8 pass，skill"坦诚反思"路线补齐半残 Step |
| [20260422-05-eval6-coverage](iterations/20260422-05-eval6-coverage/) | 补跑 eval-6 跨会话续航（场景覆盖）| 8/8 pass，skill 严格只读回读，语义理解到位 |
| [20260422-04-claude-md-lint](iterations/20260422-04-claude-md-lint/) ← 对照基线 | lint 工具 + 修漂移自动化流程 | 审计 P1-7 正式落地；自动化闭环 vs 手工裁决 |
| [20260422-03-decoupled-claude-md](iterations/20260422-03-decoupled-claude-md/) | 解耦改造：CLAUDE.md 规则段只放接口 | 解耦成功 + 边缘场景 0 regression |
| [20260422-02-expanded-6-scenarios](iterations/20260422-02-expanded-6-scenarios/) | Phase 1 重构的 6 场景全面验证 | 行为等价 + tokens -19.6% |
| [20260422-01-baseline-3-scenarios](iterations/20260422-01-baseline-3-scenarios/) | Phase 1 重构的首轮 3 场景探索 | 演进记录保留 |

## 和 skill-creator 的关系

本 eval 线是 **skill-creator 方法论的落地实例**：

| skill-creator 概念 | 本目录对应 |
|---|---|
| workspace | `workspace-<date>-<purpose>/`（运行时，跑完搬到 iterations/） |
| baseline | skill-snapshot/（git show 取旧版） |
| with_skill | 当前 `plugins/kdev-memory/skills/kdev-memory/` |
| evals.json | `evals.json`（含 prompt + fixture + assertions，单一真相源） |
| fixtures | `../fixtures/skill-quality/eval-<N>-<name>/target-project/` |
| benchmark | `iterations/<name>/benchmark.json` |
| viewer | 静态 review.html（不入库，随时 regenerate） |

skill-creator 脚本位置：`~/.claude/plugins/cache/claude-plugins-official/skill-creator/unknown/skills/skill-creator/`
