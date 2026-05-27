# 代码评审员 checklist（D2 阻断）

> 评审对象：git diff（本次 D2 循环，由调用方 TDD实现员 提供 diff 范围）
> 评审结论：PASS / FAIL（FAIL 必须列具体问题）

## D2 必检项（10 条 / 1 项 FAIL = 总体 FAIL）

1. [ ] **diff 与 plan 任务对齐**：本次 diff 覆盖且仅覆盖当前 AR 任务范围，无无关改动混入。
2. [ ] **commit 粒度合理**：每个 commit 原子性（一个逻辑变更），commit message 符合项目 conventional commits 规范。
3. [ ] **spec-conformance**：实现行为与 `handoffs/reqs/sr.md` 中对应 FR / NFR 的约定一致，无静默偏差。
4. [ ] **命名规范**：变量、函数、类、文件命名语义清晰，符合语言习惯（snake_case / camelCase 等），无拼音缩写或 `tmp` / `xxx` 类占位。
5. [ ] **边界处理完整**：空值、零值、最大值、列表为空等边界分支均有对应处理，无静默忽略。
6. [ ] **测试存在且通过**：diff 涉及的每条逻辑路径均有单元测试 / 集成测试覆盖；CI 绿灯（或本地 pytest 全通过）。
7. [ ] **无注释掉的代码**：diff 中不含大段注释掉的旧实现，历史代码通过 git 保留，不堆在文件里。
8. [ ] **无硬编码常量**：配置值、URL、密钥均走配置文件 / 环境变量，diff 中无裸 string 常量充当业务配置。
9. [ ] **依赖引入合理**：若引入新依赖，需说明原因且版本已锁定（pyproject / package.json 等）。
10. [ ] **无 TODO / FIXME 新增**：diff 中不得新增 TODO / FIXME 注释（可修改已有的）。

## 输出格式

写到 `.kdev/handoffs/dev/<AR编号>-代码评审员-review.md`：

```markdown
# 代码评审员 review — <AR编号> D2

verdict: PASS | FAIL
date: <ISO-ts>
diff_range: <base>..<head>

## 检查项结果
1. ✅ diff 与 plan 任务对齐
2. ❌ 边界处理完整 — handle_upload() 未处理文件大小为 0 的情形
...

## 问题清单（FAIL 必填）
- 文件: src/upload.py 行: 42 — 缺少 size == 0 校验
```
