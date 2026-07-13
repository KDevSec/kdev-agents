# kdev-zentao-sync

把 kdev 测试资产（字段化测试用例 `.md` + `defects_*.csv`）同步进禅道（ZenTao）实例，另含两项只读的 BUG 查询 / 回归判定能力。

## 解决什么问题

一次测试迭代的收尾，测试资产要落进禅道：用例入库、建测试单并关联、真缺陷提 BUG。手工点又慢又容易漏；而已修复的 BUG 要不要回归、哪些还没过，也缺一个确定性的对照工具。本插件把这套动作固化成一个 skill + 一组纯标准库脚本。

## 核心机制

### skill：`kdev-zentao-sync`

用户说「同步禅道 / 建测试单 / 导入用例到禅道 / 把缺陷提到禅道 / 查禅道 bug / bug 回归判定」时触发，覆盖三写 + 两读：

**写操作（默认 dry-run，须显式 `--execute` 才真写）**
- `import-cases`：把【测试用例信息】块导入禅道产品用例库（自动填 story/module、同名去重、回执 caseID）
- 建测试单并关联用例（测试单无创建 API → 走 `/browse`）
- `submit-bugs`：把 `defects_*.csv` 里「真实-*」缺陷提为禅道 BUG（escape-aware 标题截断、反转义去重）

**读操作（只读、不写回禅道）**
- `query-bugs`：按状态 / 提交人 / 模块 / 泳道（TC-AR vs TC-API）/ 标题过滤列 BUG
- `regress-bugs`：拿一次测试运行的 `junit.xml`，对照已修复 BUG 的 TC-ID，逐条判「回归通过 / 未过 / 无法回归 / 用例缺失」，出本地报告，关单 / 重开由人工在禅道点

## 约束

- **凭据**从 gitignored `禅道.md`（`--cred` 指定，含 `ip/user/password` 三行）读，绝不硬编码、绝不进仓。
- **全局参数放子命令之前**：`sync.py --cred X --product 1 --execute <子命令> ...`。
- 仅依赖 Python 标准库；写操作默认 dry-run，`query-bugs` / `regress-bugs` 恒只读。

详细用法见 [`skills/kdev-zentao-sync/SKILL.md`](skills/kdev-zentao-sync/SKILL.md)。
