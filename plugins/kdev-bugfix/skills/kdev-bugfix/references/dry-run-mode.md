# dry-run-mode

`--dry-run` flag 让 8 步流程**完整跑一遍**但**不修改任何持久状态**——不写产物、不动 src/、不动 git、不动禅道。

## 定位

dry-run 是**演练 / 教学 / 评估 plan 质量**用的，不是缩水版 bugfix：

- ✅ 适合：第一次跑 skill 摸熟流程 / wet-test 验证流程对真实 bug 是否合理 / 评估修复方案前要不要真做
- ❌ 不适合：真实 bug 修复（缺了实际 commit）/ 性能测试 / 验证回归测试有效性（需要真实 RED）

输出形式：每一步会"打印它将要做什么"（含完整 artifact 内容预览、diff 预览、curl 命令预览），但**不**真做。

## 启动方式

```bash
/kdev-bugfix --from-zentao 12345 --dry-run
/kdev-bugfix login-button-error --dry-run --review-mode=multi
/kdev-bugfix issue-123 --dry-run --p0
```

`--dry-run` 可以**叠加**任何其他 flag。叠加规则：

| 叠加 flag | 行为 |
|----------|------|
| `--from-zentao <id>` | 真拉禅道 bug（GET 只读，不污染）；但**不**回写状态 |
| `--review-mode=<x>` | 评审照常走，但评的是 plan（design.md 修复方案 + tasks.md 完整性），不是 diff |
| `--p0` | 严重度判 P0，触发评审强制升级到 multi |
| `--auto` | 仍生效（所有自动判定 + 自动升档照旧），但"做"的动作都被 dry-run 拦截 |
| `--no-zentao-update` | redundant（dry-run 本来就不动禅道）但不冲突 |
| `--archive` | redundant（dry-run 没创建 change 也就无从 archive）但不冲突 |

## 输出前缀约定

dry-run 模式下，所有"本应执行但被拦截"的动作前**统一打 `🔵 DRY-RUN |`** 前缀，便于用户 grep / 视觉区分。

```
🔵 DRY-RUN | step 2: 将创建 openspec/changes/zentao-12345/proposal.md（不实际写）
🔵 DRY-RUN | step 5: 将修改 src/foo.py:42（不实际改）
🔵 DRY-RUN | step 7: 将 commit message:
              fix: 订单金额计算错 (#zentao-12345)
              ...
🔵 DRY-RUN | step 8: 将 PUT /api.php/v1/bugs/12345/resolve with body {...}
```

## 8 步行为对照表

| 步骤 | 真跑（无 `--dry-run`） | dry-run |
|------|-------------------|---------|
| **1. Intake** | 拉禅道 / 生成 bug-id / 判模式 / 判严重度 | 全部照常做（只读，不污染） |
| **2. Proposal** | `openspec new change` 真创建目录 + 写 proposal.md | **不创建目录、不写文件**；打印 `🔵 DRY-RUN | step 2: 将创建 openspec/changes/<bug-id>/`、proposal.md 内容用 ```markdown 代码块 inline 显示 |
| **3. 复现 + 根因** | 跑复现脚本（curl / pytest / 等）+ systematic-debugging | 复现脚本**照常跑**（只读，不污染源码）；根因投资照常 |
| **4. Design + RED** | 写 design.md + 写回归测试文件 + **实测失败** | design.md 不写，inline 显示；**回归测试不写文件，不实测**——而是 print "将写测试 `tests/test_xxx.py`，内容：```python ...```，预期失败原因：`<XXX>`" |
| **5. Tasks + GREEN + 闸门** | 写 tasks.md + 改 src/ + 跑 type-check / lint / 测试 | tasks.md inline 显示；src/ 改动**用 `unified diff` 格式 print**，**不真改**；type-check / lint / 测试**跳过**（因没改文件，跑了无意义）；输出 `🔵 DRY-RUN | step 5.3: 跳过验证闸门（无实际改动）` |
| **6. 评审** | reviewer 看 design.md / fix.md + diff | reviewer 看 plan（design.md 修复方案 + tasks.md 完整性），**不看 diff（无 diff）**；评审 prompt 改为 plan-review 而非 code-review |
| **7. Validate + Commit** | `openspec validate` + `kdev-commit` 真 commit | `openspec validate` **跳过**（无 change 容器）；commit message 用 ```bash 代码块 print，**不真 commit** |
| **8. 后置动作** | 禅道 API PUT resolve | **不调 API**；print 完整 curl 命令（含 body 但 redact token）+ 期望响应 |
| **8.2 终态报告** | 所有项标 ✅ / ❌ | 所有项加 `(DRY-RUN, 未实际执行)` 后缀 |

## 步骤 4 RED 的特殊处理

实测的 RED（写测试 → 跑 → 看 fail）是 TDD 纪律的核心。dry-run 跳过实测意味着**失去"watch it fail"保证**。

dry-run 输出要明确告诉用户这一点：

```
🔵 DRY-RUN | step 4.4 RED: 跳过回归测试实测
   将写测试 tests/test_order_amount.py::test_zero_price_rejected
   测试内容预览：
       def test_zero_price_rejected():
           ...
   预期失败原因（基于根因预测）：AssertionError on line 5: ...
   
   ⚠️ dry-run 不实测"watch it fail"——真跑时这一步可能暴露：
       (a) 测试自身有 bug（如 import 错）
       (b) 测试不卡根因（其他错误先跑到）
       (c) 测试在没 fix 时居然通过（说明根因诊断错）
   实测前不要把 dry-run 结论当成"此方案可行"的最终证据
```

## 步骤 5 GREEN 的 diff 预览格式

用标准 unified diff 格式打印将要做的改动，前缀加 `🔵 DRY-RUN | step 5.2:`：

````
🔵 DRY-RUN | step 5.2 GREEN: 将改动 src/module_admin/service/order_service.py

```diff
--- a/src/module_admin/service/order_service.py
+++ b/src/module_admin/service/order_service.py
@@ -42,7 +42,11 @@ async def create_order(price: Decimal, ...):
-    if not price:
-        raise InvalidPrice("price required")
+    if price is None or price <= 0:
+        raise InvalidPrice(
+            f"price must be > 0, got {price!r} "
+            f"(0 / 负数 / None 都拒绝)"
+        )
```

预计影响：1 个文件，4 行删除，5 行新增
````

让用户能拷贝 diff 到 patch 工具或 IDE 预览，但 skill 自身**不**调 `git apply`。

## 步骤 6 评审的 plan-review 变体

dry-run 模式下没有真实 diff，评审改为 plan-review。`prompts/multi-agent-review.md` 模板里 `<MODE>` 占位符会被替换为 `OpenSpec (dry-run)` 或 `纯 (dry-run)`，subagent 据此调整评审维度：

- 跳过维度 2（"实际跑 git stash + pytest 验证 RED"）—— dry-run 没真测试可跑
- 跳过维度 4 中的"diff 是否引入新回归点"具体维度——改评"修复方案是否会引入新风险"
- 跳过维度 5（"diff 净度"）——dry-run 无 diff
- 强化维度 1（根因对准）+ 维度 3（验证闸门覆盖度）+ 维度 6（Spec_Impact 判定）

主 Claude 派 subagent 时把 prompt 末尾**额外加一段**：

```
⚠️ 本次是 dry-run plan review，**不是 code review**。请评 design.md 修复方案 + tasks.md 完整性 + Root_Cause 是否真的对准 Symptom，**不**评 diff（没有 diff）。维度 2 / 4 后半 / 5 跳过。
```

## 步骤 7 Commit 预览

```
🔵 DRY-RUN | step 7.2 commit: 将创建 commit 在分支 fix/<bug-id>

  message:
      fix: 订单金额计算错 (#zentao-12345)

      Root cause: ...
      Regression test: tests/test_order_amount.py::test_zero_price_rejected
      Reviewers: AI (PASS), multi-agent (PASS, plan-review)

      Refs: openspec/changes/zentao-12345/
      Zentao: #12345

  files：3 个 staged
      M src/module_admin/service/order_service.py
      A tests/test_order_amount.py
      A openspec/changes/zentao-12345/proposal.md（仅 plan，本次未真写）
      A openspec/changes/zentao-12345/design.md
      A openspec/changes/zentao-12345/tasks.md
```

## 步骤 8 禅道 PUT 预览（敏感数据 redact）

```
🔵 DRY-RUN | step 8.1 禅道 resolve: 将调禅道 API

  请求：
      PUT https://101.35.217.78/api.php/v1/bugs/12345/resolve
      Header: Token: <REDACTED>
      Body:
      {
        "resolution": "fixed",
        "resolvedBuild": "trunk",
        "comment": "已修复，详见：\n- Commit: <SHA>\n- 产物: openspec/changes/zentao-12345/\n..."
      }

  预期响应（基于上次同类 PUT）：
      HTTP 200
      { "id": 12345, "status": "resolved", "resolvedDate": "..." }
```

**永远 redact** `Token: ...` 和 body 里如有 cookie / 凭证字段。

## 终态报告差异

dry-run 跑完后输出与正常模式相同结构的报告，但**每行标 `(DRY-RUN, 未实际执行)`**：

```
## Bugfix 完成（DRY-RUN）：<bug-id>

**模式**：DRY-RUN（实际状态未改变）
**来源**：zentao #12345（拉取成功，状态未回写）
**严重度**：P1（基于禅道 .severity=2）
**根因**：<Root_Cause 一句话>
**修改文件**（**未真改**）：
  - src/module_admin/service/order_service.py（预览 +5/-4）
  - tests/test_order_amount.py（预览，新增）
**验证闸门**：全部跳过（DRY-RUN 无文件改动）
**评审**：AI (PASS, plan-review), multi-agent (PASS, plan-review)
**产物**：未实际生成；inline 预览见对话历史
**Commit**：未创建（预览 message 见 step 7）
**禅道状态**：未回写（active 状态保持；预览 PUT 见 step 8）

---
要真跑：去掉 --dry-run 重新执行 `/kdev-bugfix --from-zentao 12345`
要进 wet-test：去掉 --dry-run 但加 `--no-zentao-update`（写代码/commit，但不动禅道状态）
```

## 适用场景

| 场景 | 推荐模式 |
|------|----------|
| 第一次跑 skill，没把握 8 步流程 | `--dry-run` |
| wet-test 段 2（前面文档提的 dry-wet test）| `--dry-run` 跑一遍预览 → 满意后去掉 --dry-run 真跑 |
| 评估"这个 bug 值不值得修" | `--dry-run --review-mode=human`（让评审段决定）|
| 教学新人 / Demo 演示 | `--dry-run` 全程不污染 demo 环境 |
| 真实 bug 修复 | **不要用** `--dry-run` |
| 验证回归测试有效性 | **不要用** `--dry-run`（缺"watch it fail"实测）|

## 安全性

`--dry-run` 的**底线保证**：

1. **不写任何产物文件**（`openspec/changes/<bug-id>/` 或 `docs/bugfix/<bug-id>/`）
2. **不动 src/ tests/ 任何代码文件**
3. **不创建 / 切换 / 改动任何 git 分支**
4. **不 commit / 不 push**
5. **不调禅道 PUT / POST**（GET 只读除外，且 GET 不污染禅道状态）

⚠️ **不保证**的事：

- 步骤 3 复现脚本如果是用户自己写的破坏性命令（如 `rm -rf db && create-db`）会真跑——dry-run 不分析复现脚本的副作用
- subagent 派单本身不消耗 token 上限（这是 Claude Code 平台行为，dry-run 不能阻止）
- 拉禅道 bug（GET）会在禅道的 access log 里留记录（合规要求严格场景注意）
