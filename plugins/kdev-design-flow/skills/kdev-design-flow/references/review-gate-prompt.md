# 评审闸门通用 Prompt（Claude 自评 / 用户参考共用）

## 用途

每个 Stage 产出后，评审闸门用这个 prompt 评估产物。Claude 在 `--review=ai` 或 `--review=both` 模式下扮演评审者；在 `--review=human` 模式下，这个 prompt 的"成功标准"段也用作给用户的判断依据。

## 评审者要做的事

你正在评审 **{{stage_name}}** 阶段的产出。

**这是 iter {{iter}} of max 3。**

### {{stage_name}} 的成功标准（**逐条对照，禁止自由发挥**）

{{stage_specific_criteria}}

### 产物原文

<<<ARTIFACT
{{artifact_content}}
ARTIFACT>>>

### 必填输出（严格格式）

```
VERDICT: PASS | FAIL

UNCHECKED_CRITERIA: <comma-separated list of criteria IDs that the artifact does not satisfy; empty if PASS>

ISSUES (only if FAIL, max 5, priority order):
1. <one-line issue description>
2. ...

REVISIONS (only if FAIL):
1. <concrete revision instruction the next iter can apply directly>
2. ...
```

**禁止**：补充表扬话、扩展评论、解释为什么 PASS。只填这些字段。

## Stage 特定的成功标准

### Stage 1 (SR 文档)

- C-1.1: 包含 3-7 个 SR 条目
- C-1.2: 每个 SR 有验收标准 + 约束 + 依赖（三段都不空）
- C-1.3: 至少 3 个开放问题（OPEN-Q-NN）
- C-1.4: 显式列出"不做的事"
- C-1.5: 没有把原型/API/代码细节写进来（应在后续阶段）

### Stage 3 (AR + 原型 联合评审 — 这是 Gate 2)

- C-2.1: AR 用户故事覆盖了 Stage 1 所有 SR（每个 SR 至少对应 1 个 user story）
- C-2.2: 原型 HTML 可在浏览器打开且无 JS 报错
- C-2.3: 原型涵盖 AR 中的核心交互路径
- C-2.4: 原型未包含真实凭证 / 内部 URL / 敏感数据
- C-2.5: 原型样式与产品语境匹配（不是默认浏览器灰色按钮）
- **C-2.6: 项目宪法 UI 约束遵从**（若 `.specify/memory/constitution.md` 存在）：
  - 原型 MUST 使用宪法中显式声明的具体数值（字号 / 行高 / 栅格 / 间距 / 画板宽度等）
  - 原型 MUST 使用 token 化的颜色（CSS 变量或宪法明列的色板），未授权的裸 `#hex` 不允许
  - 原型 MUST 满足宪法声明的对比度阈值（如 AAA ≥ 7:1）
  - 若宪法显式声明"前端实现唯一权威来源"目录（如 `references/04-ued6.0/`），原型 MUST 与之一致（命名 / 组件层级 / 视觉 token）
  - 若 frontend-design 产出的 `self-check.md` 缺失或自检失败项 ≥ 2 → 本条 FAIL
  - 宪法不存在 → 本条标记 `N/A`，不影响 PASS 判定

### Stage 4 (设计方案 — 这是 Gate 3)

- C-3.1: 包含概要设计（架构图 / 模块划分 / 数据流）
- C-3.2: 包含详细设计（关键接口 + 数据模型）
- C-3.3: 覆盖了 Stage 1 SR 的所有约束（性能/安全/合规）
- C-3.4: 列出至少 3 项已识别的实现风险 + 缓解
- C-3.5: 与 Stage 3 原型的交互一致（没有原型上有但设计里漏掉的功能）
