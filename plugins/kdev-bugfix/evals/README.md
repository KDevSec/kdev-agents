# kdev-bugfix evals

8 个 core eval 覆盖 kdev-bugfix skill 的关键回归点。

## 维度覆盖

| 维度 | eval id | 覆盖什么 |
|------|---------|----------|
| 流程纪律 | 1 iron-law-root-cause-discipline | Iron Law：根因未定不许下笔修 |
| 流程纪律 | 2 red-before-green-discipline | TDD：测试先于修复，"watch it fail" |
| 流程纪律 | 8 spec-impact-no-direct-spec-edit | 不在 bugfix PR 改真实 spec，另起 kdev-change |
| 评审升档 | 3 review-escalation-mandatory-auth | 鉴权类强制升级 multi（即便用户传 `--review-mode=ai`）|
| Dry-run | 4 dry-run-zero-side-effects | dry-run 5 条底线保证 |
| 模式判定 | 5 mode-autodetect-openspec-present | openspec/ 存在 → OpenSpec 模式 |
| 实测踩坑回归 | 6 zentao-url-prefix-trap | 开源版 22.1 nginx rewrite 后 URL 不带 /zentao |
| 实测踩坑回归 | 7 zentao-field-name-pri-not-priority | `.pri` 不是 `.priority` |

## 如何跑

evals 是 **skill-quality** 类型——测的是 Claude reading skill 后的行为，**不是**确定性代码逻辑。所以跑法是派 Agent subagent 执行 prompt，对照 `assertions` 字段判 PASS/FAIL。

### 单条 eval 手工跑（推荐起步）

```python
Agent({
  model: "opus",            # 或 sonnet，evals.json 不约束
  description: "Run eval-N",
  subagent_type: "general-purpose",
  prompt: """
# 任务

按 kdev-bugfix skill 处理以下用户输入。**遵守 SKILL.md 8 步流程 + 6 条核心原则**。

## 用户输入

<把 evals.json 的 eval-N.prompt 整段贴这里>

## 输出要求

具体回应用户的请求。不要省略关键步骤的说明。结构按你按 skill 实际会走的流程组织。
"""
})
```

拿到 subagent response 后，对照 `evals.json` 里 eval-N.assertions：

- `must_contain`：response 必须含此文本
- `must_contain_any`：response 必须含 `values` 列表里**任一**
- `must_not_contain`：response **不**能含此文本

每条 assertion 单独标 PASS / FAIL。全 PASS 才算这条 eval 整体 PASS。

### 全量跑（未来加自动化）

未来可以加 `evals/run.py` 脚本一次性跑所有 evals 并打分。当前阶段建议手工 + 派 subagent。

## 何时跑

- **改动 SKILL.md**：必跑（任何流程/纪律层面的修改）
- **改动 references/**：相关 eval 必跑（如改 zentao-integration.md → 跑 eval-6 / eval-7）
- **bump version**：全套必跑作为 release gate
- **怀疑 skill 漂移**：随时可单条跑做现场诊断

## 添加新 eval 的规范

发现一个新的"应当抓住但当前没抓"的回归点时，加 eval：

1. 在 `evals.json` 末尾加新 eval object，`id` 递增
2. 字段必填：`id` / `name`（kebab-case） / `category` / `prompt` / `expected_behavior` / `assertions`
3. `assertions` 至少 2 条（一条正向 must_contain，一条反向 must_not_contain）
4. 跑一遍验证当前 skill PASS（如未 PASS 说明 skill 真有问题，先修 skill 再加 eval）
5. 更新本 README 的"维度覆盖"表

## 历史 iteration（可选）

如未来想追溯每次跑 eval 的结果（如 v0.2.2 vs v0.3.0 的回归对比），可建：

```
evals/
├── evals.json                   ← 当前规范定义
├── README.md                    ← 本文
└── iteration-N/                 ← 第 N 次正式跑的快照
    ├── eval-1-iron-law/
    │   ├── prompt.txt           ← 实际 prompt（含上下文）
    │   ├── response.txt         ← subagent 返回
    │   └── verdict.json         ← PASS/FAIL + 每条 assertion 命中情况
    └── ...
```

参考 [kdev-coding-flow evals](../../../kdev-coding-flow/evals/) 的两轮 iteration 结构（iteration-1 / iteration-2）。

## 已知局限

- evals 测的是 **skill-quality**（Claude 行为），不是 **trigger match**（确定性 hook 召回）
- subagent 的输出有自然语言波动，assertions 的 `must_contain` 是**字面子串**——如果未来 skill 用同义词，可能 false-FAIL
- subagent 自己读 skill 文件这一步本身是 token-heavy，跑全套 eval 一次预计消耗 ~50K-100K tokens

### Assertion DSL 的反例上下文误伤陷阱（v0.2.2 首跑发现）

`must_not_contain` 在以下三种**反例上下文**下会 false-FAIL（字面匹配命中但语义上无问题）：

1. **拒绝陈述**：用户问"跳到步骤 5"，subagent 写"**拒绝**跳到步骤 5"——含子串 "跳到步骤 5"
2. **反例警告**：subagent 写"`.priority` 会返回 null，是踩坑高发点"——含子串 ".priority"
3. **兜底备选**：subagent 写"主修复方案 → 兜底再试 `/zentaopms`"——含子串 "/zentaopms"

**修法**：写 `must_not_contain` 时用**精确的 compliance phrase**（如 "好的，直接给修复代码" / "OK，仅 AI 自评" / "我已经知道根因"），不要用泛字面子串（如 "跳到步骤 5" / ".priority"）。

**判定**：跑 eval 时如 must_not_contain 命中，先**人工 review** subagent 是用作反例 / 兜底 / 拒绝陈述（→ FALSE-FAIL，不算）还是真的推荐了错的方案（→ FAIL，skill 需修）。

### Assertion kind 速查

| kind | 语义 | 何时用 |
|------|------|--------|
| `must_contain` | 字面子串必须出现 | 验证 skill 提到了某关键概念 / 字段名 / 命令 |
| `must_contain_any` | `values` 列表里任一字面子串出现 | 同义词容忍 |
| `must_contain_first_code_block` | 第一个 ```bash 代码块内必须含此字符串 | 验证"主推荐命令"用对（而非反例代码块）|
| `must_not_contain` | 字面子串不能出现 | 验证 skill 没给错答案；**用 compliance phrase**，慎用泛子串 |

`must_contain_first_code_block` 是 v0.2.2 引入的精确化 kind，专门解决"主答案 vs 反例代码块"歧义。
