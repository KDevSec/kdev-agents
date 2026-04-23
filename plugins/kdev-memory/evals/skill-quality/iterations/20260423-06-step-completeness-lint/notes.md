# iter-6 notes：Step 完整度 lint 落地（P1-5/6）

**日期**：2026-04-23
**目的**：落地审计 §5.1 P1-5（SessionStart brief 加欠评 Step 告警）+ P1-6
（Stop hook check-step-completeness，含 strict 模式阻塞）
**规模**：1 eval × 1 config × 1 run

---

## 结果

- Pass rate: **8/8 (100%)**
- Tokens: 44,591 / Time: 143.3s / Tool uses: 15

### 验证 8 条 assertion 全过

关键表现超出预期：
- skill **走"坦诚反思"路线**补齐扣分项——不编造好听的，而是承认"5/5 自评偏高 + 把
  timingSafeEqual 等长 Buffer 坑写进扣分项 + 引用 G-040"（三方证据一致）
- 时分戳锁定铁规严格满足：用户评分 10:22 > 模型自评 10:15，显式标注"晚于 10:15"
- 评分差值识别：差值 -1 被正确识别为弱信号，改进建议.md 保持空（差值 < 2 阈值不升 R-NNN）
- 踩坑日志 G-040 只引用不重写；CLAUDE.md 一字未改

---

## 本轮新增能力

### 1. `hooks/lib/step_completeness.py`（203 行，纯 Python 无外部依赖）

扫 `.kdev/memory/执行日志.md` 的最近 N 条 Step，检测"半残"：
- 用户评分段时分戳为 `—` / 空 / `待补` / `污染样本` / `TBD` / `TODO`
- 用户评分段顺畅度为同上占位符
- 模型自评段「扣分项：」后面为空或占位
- 有模型自评段但完全无用户评分段（Step 未闭环）

**容错设计**：
- `lookback_days=14` 默认只扫最近 14 天（避免老 Step 刷屏）
- `_is_placeholder()` 处理多种占位形式（空 / — / 待补 / TODO / "—/5"）
- `_has_model_self_review()` 只认 section 标题，避免 Step 标题含关键词误判

### 2. `tests/test_step_completeness.py`（33 tests）

项目累计 **98 tests 全过**（44 trigger-match + 21 claude-md-lint + 33 step-completeness）

### 3. SessionStart hook 集成

brief ⚠️ 段新增一行："发现 N 条欠评 / 半残 Step（最近 M 条中）"+ 逐条 Step 标签 + issue 列表
+ 新会话动作建议（"向用户核对评分后补齐，或明确销账"）

### 4. Stop hook 集成

- **软提醒**：今日新增半残 Step → 注入文本提醒（不阻塞）
- **strict 模式**：今日半残 + `.kdev/memory/strict` 标记存在 → `exit 2` 阻塞，
  Claude 必须补齐字段后才能真正结束本轮

端到端冒烟测：
- 非 strict 模式：软提醒输出 + exit 0
- strict 模式 + 今日半残：阻塞输出 + exit 2 ✓

---

## 审计 §5.1 落地进度累计

| 审计项 | 状态 | 对应 iter |
|---|---|---|
| P0-4 Step 脱离状态机 | ✅ 已隐含 | 本 session 之前 |
| P1-5 SessionStart brief 欠评告警 | ✅ **本轮** | iter-6 |
| P1-6 Stop hook check-step-completeness | ✅ **本轮** | iter-6 |
| P1-7 CLAUDE.md 版本漂移检测 | ✅ 已落地（claude_md_contract lint） | iter-4 |
| 其他 P0/P1 | 🟡 待后续 | — |

---

## 下一 session 候选

- P0-1 Step 完成闸门 discriminating eval 设计（~1-2h）——验证"加四段必填硬规"
  是否真必要。iter-3/5/6 的数据持续暗示 skill 本体已够硬（本 iter eval-9 就是
  skill 在无硬闸门时"坦诚反思路线"补齐的例子）；做 discriminating eval 验证
  假设再决定是否加硬规
- v0.6.0 scope 决策：按 dev-note 的方案 A 加 `使用的 skill` 事实字段

---

## 文件清单

- `benchmark.json` / `benchmark.md`
- `eval-9-step-half-complete/eval_metadata.json`
- `eval-9-step-half-complete/with_skill/run-1/grading.json`
- `eval-9-step-half-complete/with_skill/run-1/timing.json`
