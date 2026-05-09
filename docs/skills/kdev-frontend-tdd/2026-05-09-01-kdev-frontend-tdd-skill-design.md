# 前端 TDD Skill — 设计方案（kdev-frontend-tdd）

- 日期：2026-05-09
- 输入物：当前 SOP_test 项目后端已强制 TDD（`superpowers:test-driven-development` + `.claude/hooks/enforce-tdd-on-task.sh`），前端缺纪律。本 skill 用于补齐前端层。
- 参考：`superpowers:test-driven-development`（红绿循环原典）、`kdev-secure-coding`（同款 A+C 触发 + 自举模板）、`kdev-ui-autotest`（已有 Playwright+pytest E2E 规范，本 skill 是其上游补位）。
- **范围说明**：本 skill 只管**代码层 TDD 纪律**（写测试 + 红绿循环），不做浏览器/页面层的"功能验收"——后者属于**研发自测环节**，由独立 skill 或流程节点承担（见 §4）。

---

## 1. 目标与非目标

### 目标

- 让 Claude 在改动前端代码（Vue/React/TS/JS/CSS/组件）时自动套用"**分层 TDD**"纪律，不再凭直觉写实现 → 直接 commit。
- 把"前端哪些层套红绿循环、哪些层不套"这套判断**固化成可执行规则**，不再让 Agent 每次自己揣摩。
- 通过 L1-L3 的红绿循环让前端逻辑层回归被及时拦截，避免"AI 改一改就坏"。
- 在 commit 前确保代码层纪律已过关，把"功能层是否真能跑"明确交接给**研发自测环节**——本 skill 不越界。
- 与已有 `kdev-ui-autotest`（E2E + 测试用例归档）形成上下游：本 skill 管"开发期单元/组件测试"，`kdev-ui-autotest` 管"E2E 测试用例的写法和归档"。

### 非目标

- **不替代** `superpowers:test-driven-development`，本 skill 在它之上加前端特有的分层判断。
- **不强制 100% 覆盖率**，分层决策的本意就是"该测的层严格测、不该测的层不浪费"。
- **不做浏览器/页面层的功能验收**——这是研发自测环节的职责（见 §4），不进本 skill 的完成清单。
- **不做视觉回归**（截图对比）——同样属于自测/QA 范畴。
- 不绑定具体框架（Vue 3 / React 18 都适用），但 reference 默认按 Vue 3 + Vite + Vitest 给样例（与本项目栈一致）；其他栈在 references 中各自一份样例文件。

---

## 2. 核心论点：前端 TDD ≠ 后端 TDD 的复制

后端有清晰的 I/O 契约（请求进、响应出），断言能精准描述"做完"的标准——红绿循环天然合身。

前端不一样：

| 维度 | 后端 | 前端 |
|------|------|------|
| 输入输出 | 请求/响应，结构化 | 用户交互、DOM 渲染、视觉效果，半结构化 |
| "做完"的判定 | 断言通过 = 做完 | 断言通过 ≠ 用户体验正确（页面可能白屏却测试全绿） |
| 改动频率 | 中-低（接口稳定） | 高（UI 频繁迭代） |
| 测试维护成本 | 低-中 | 中-高（DOM 易变） |

照搬"全量红绿循环"会出现两种失败模式：
- **激进派**：所有 UI 都强行 TDD → 测试脆弱、维护拖慢迭代、ROI 差。
- **保守派**：前端只做事后 E2E → 逻辑回归无法及时拦截、AI 改动一改就坏。

本 skill 的核心动作：**按层分治**——L1/L2/L3 严格红绿循环，L4 不写测试、留给研发自测环节兜。

---

## 3. 分层决策树（本 skill 的核心规则）

Claude 改动前端代码时，第一动作是**判断改的是哪一层**，按下表决定纪律：

| 层级 | 典型文件 | 是否套红绿循环 | 测试工具 | 完成标准 |
|------|------|---------|---------|---------|
| **L1 · 业务逻辑层** | `store/*.ts`、`composables/*.ts`、`hooks/*.ts`、`utils/*.ts`、纯函数 | ✅ **严格套**（与后端 TDD 一致） | Vitest | 测试覆盖到改动行 + 红绿循环可见 |
| **L2 · 组件交互层** | `components/**/*.vue` 中的事件、表单、状态机 | ✅ **行为级套**（测"点了按钮该发生什么"，不测样式） | Vue Testing Library + Vitest | testing-library 行为断言通过 |
| **L3 · API 调用层** | `api/*.ts`、`services/*.ts`、网络请求封装 | ✅ **契约级套**（mock 接口测调用与响应处理） | Vitest + msw（或类似 mock） | 调用参数 / 错误分支 / 边界响应都被断言 |
| **L4 · 纯展示/样式** | 仅样式调整、纯渲染组件、CSS-only 改动 | ❌ **不套红绿** | —（不属本 skill） | 标记为"待研发自测"，commit 时附说明，由自测环节兜底 |

### 判定优先级（多层重叠时）

如果一次改动横跨多层（例如同时改了 store 和组件），**取最严格层的纪律**——L1 + L2 都改 → 必须同时满足两层的红绿循环。

### 边界情况

- **改的是路由配置**：归 L3（契约级），写测试断言路由表结构与守卫逻辑。
- **改的是国际化文案**：归 L4，由研发自测环节验证。
- **改的是 TypeScript 类型定义**：不算独立层，跟随它服务的层走。

---

## 4. 与研发自测的衔接

### 4.1 边界：本 skill 在哪里停手

本 skill 的产出边界是 "**L1/L2/L3 红绿循环测试通过 + commit 同时含失败测试与实现**"。一旦这一步过了，**本 skill 视为完成**——不要求 Claude 开浏览器跑页面、不要求截图、不要求验证用户路径。

理由：
- TDD 是"代码层纪律"，浏览器层是"功能验收"，本质不同；混在一起会稀释 TDD 纪律的纯粹性。
- 浏览器/页面层验证有自己的方法论（场景设计、用户路径、视觉对比、跨浏览器/响应式），不应被压缩成 TDD skill 的一个尾巴章节。
- 每次 commit 都强制开浏览器跑三件套，对高频迭代是不必要的负担。

### 4.2 commit 时如何标记"待自测"

L4 改动（纯样式、纯展示组件）或跨多层涉及用户路径的改动，commit message 中**显式标记**：

```
ui: <改动摘要>

[selftest-required] L4 纯展示改动 / 涉及用户路径变更，请走研发自测确认：
- 受影响页面：<path1>, <path2>
- 关注点：<具体要看什么，例如"列表分页边界"、"表单必填校验提示位置"等>
```

`[selftest-required]` 标记便于后续：
- 研发自测环节按 commit 历史检索"今天哪些 commit 需要走自测"。
- 后续若做 PR，CI 可基于此标记给出自测 checklist。

### 4.3 与可能的 `kdev-frontend-selftest` skill 的关系

研发自测如果未来**独立成 skill**（建议命名 `kdev-frontend-selftest`），本 skill 不依赖它存在，但提供**衔接点**：
- 本 skill 在完成清单末尾输出一句"**已完成代码层 TDD，建议进入研发自测环节**"作为引导。
- 自测 skill 反过来读取 `[selftest-required]` 标记，自动生成自测清单。
- 两者解耦：用 / 不用都不影响对方运行。

研发自测是否成 skill、长什么样，由独立设计稿决定（开放问题见 §14）。

### 4.4 与 `kdev-ui-autotest` 的边界

- `kdev-ui-autotest` 管 E2E 测试用例归档（test_arNN.py、defects_<ts>.csv、四件产物），属测试/QA 团队产物。
- 本 skill 管开发期单元/组件测试（L1/L2/L3），属开发者/AI 产物。
- 研发自测（如果独立成 skill）夹在两者之间——是开发完成与 E2E 用例库归档之间的一道闸。
- 三者**互不重叠**，按职责接力。

---

## 5. 触发模型（A + C 组合，同 kdev-secure-coding）

- **A · description 触发**（主路径）：SKILL.md 的 description 写明触发场景：
  - 当前任务涉及前端文件路径（`src/views/`、`src/components/`、`src/store/`、`src/api/`、`*.vue`、`*.tsx` 等）
  - 用户说"加一个页面 / 改组件 / 修前端 bug / 调样式 / 加表单 / 接接口"等关键词
- **C · CLAUDE.md 锚点**（兜底）：项目 CLAUDE.md 加：
  ```
  本项目所有前端代码改动 MUST 调用 `kdev-frontend-tdd` skill。
  ```
- **不采用 B（hook 强拦截）作为主路径**：理由同 secure-coding——避免改 settings.json、避免误伤纯文档/纯配置改动；但**可选 hook**仍提供（见 §11），让用户按需启用。

CLAUDE.md 锚点通过 skill **自举**写入（同 secure-coding §4 做法）。

---

## 6. 目录与位置

**Plugin 位置**：`plugins/kdev-frontend-tdd/`（与 `kdev-secure-coding` / `kdev-ui-autotest` 同级）

**目录布局**：
```
plugins/kdev-frontend-tdd/
├── README.md
├── CHANGELOG.md
├── skills/
│   └── kdev-frontend-tdd/
│       ├── SKILL.md                          # 索引 + 分层决策树 + 自举 + 完成清单 + 自测衔接
│       └── references/
│           ├── 01-layer-decision-tree.md     # L1/L2/L3/L4 详细判定 + 多层重叠 + 边界情况
│           ├── 02-l1-logic-tdd.md            # 业务逻辑层红绿循环 + Vitest 模板 + 反模式
│           ├── 03-l2-component-tdd.md        # 组件交互层 + Vue Testing Library 模板（含 React 变体）
│           ├── 04-l3-api-tdd.md              # API 层 + msw mock 模板 + 错误分支清单
│           ├── 05-l4-handoff.md              # 纯展示层不写测试 + commit selftest-required 标记规范
│           ├── 06-anti-patterns.md           # 反模式清单（假测试、await nextTick 掩盖、过度 mock 等）
│           └── 07-frameworks/                # 框架变体
│               ├── vue3-vite-vitest.md
│               ├── react-vite-vitest.md
│               └── nuxt.md（可选）
├── evals/                                    # 待 kdev-secure-coding eval 模板成熟后再补
└── tests/                                    # skill 自身的 sanity check（可选）
```

---

## 7. 自举逻辑（CLAUDE.md 锚点）

SKILL.md 顶部固定流程，每次 skill 调用时执行：

1. 读当前项目根 `CLAUDE.md`（不存在跳 4b）。
2. 若 CLAUDE.md 已含 `kdev-frontend-tdd` 字样 → 跳过自举。
3. 若否，且当前项目命中"前端项目检测规则"（§8）→ 向用户提议追加：
   ```markdown
   ## 前端开发纪律
   本项目所有前端代码改动 MUST 调用 `kdev-frontend-tdd` skill，按分层决策树
   套用 TDD（L1/L2/L3 红绿循环），commit 同时包含失败测试与实现。L4 纯展示
   改动需在 commit message 加 `[selftest-required]` 标记，由研发自测环节兜底。
   ```
4. 用户同意写入；否则记录决策、本会话不再问。
5. 4b. CLAUDE.md 不存在 → 提议先创建最小 CLAUDE.md 或建议用户跑 `/init`。

---

## 8. 前端项目检测规则

满足以下**任一**视为前端项目（触发自举）：

- 项目根含 `package.json` 且 `dependencies` / `devDependencies` 出现：`vue` / `react` / `nuxt` / `vite` / `webpack` / `next`。
- 项目根含 `vite.config.*` / `vue.config.*` / `next.config.*` / `nuxt.config.*`。
- 当前会话改动文件路径含 `src/views/` / `src/components/` / `*.vue` / `*.tsx` / `*.jsx`。

至少 2 条命中才触发自举（避免后端项目里偶有几个 .vue 文件就被误判）。

---

## 9. 完成清单（commit 前 Claude 必须自检过）

```markdown
## kdev-frontend-tdd 完成自检
- [ ] 已识别本次改动涉及的层级（L1/L2/L3/L4，可多层）
- [ ] 涉及 L1/L2/L3 的部分：测试先于实现的红绿循环可见（commit 同时含失败测试和实现）
- [ ] vitest（或对应运行器）通过，且覆盖到改动行
- [ ] 涉及 L4 或跨层涉及用户路径的改动：commit message 已加 `[selftest-required]` 标记，并写明受影响页面与关注点
- [ ] 本次 commit 不含反模式（见 references/06-anti-patterns.md）
- [ ] 已向用户输出"代码层 TDD 完成，建议进入研发自测环节"的引导
```

---

## 10. 反模式清单（写进 references/06-anti-patterns.md）

| 反模式 | 表现 | 为什么错 |
|------|------|---------|
| 假测试 | `expect(true).toBe(true)` 占位 | 红灯不真实，绿灯无意义 |
| 过度 mock | mock 到只剩"调用了某函数"，不验证副作用 | 测试通过但实际功能没跑 |
| `await nextTick` 掩盖时序 | 用 nextTick 兜不稳定的异步断言 | 掩盖真问题，CI 上仍会闪 |
| 跳过红灯 | 直接写实现 + 测试一起 commit | 没验证"测试本身有效"，可能从一开始就是假绿 |
| L4 改动不加 `[selftest-required]` 标记 | 纯样式或用户路径变更直接 commit 不标记 | 自测环节漏检，回归风险下沉到 QA / 用户 |
| 用 try/catch 吞异常让测试过 | 把不该处理的异常 catch 掉 | 把"评估系统"调成"安抚系统"（参考 kdev-ui-autotest 第零原则） |
| 改了 store 没改组件测试 | 多层重叠改动只跑一层测试 | 跨层契约破坏不被发现 |
| 把"功能验收"伪装成单元测试 | 在 vitest 里跑整个页面流程拿来当 E2E 用 | 单测脆弱化、运行慢、与真正的 E2E/自测重叠 |

---

## 11. 配套 hook（可选启用，不进默认）

仿 `.claude/hooks/enforce-tdd-on-task.sh`，可提供：

```bash
.claude/hooks/enforce-frontend-tdd-on-task.sh
```

PreToolUse 阶段拦截 Task 派发，检查：
- prompt 是否提及前端文件路径（启发式：`*.vue` / `src/views/` / `src/components/` 等）
- 若是，prompt 必须显式包含 `kdev-frontend-tdd` 字样

不合规直接 deny。本 hook 作为可选项放在 plugin 的 `hooks/` 子目录，由用户决定是否启用——默认走 A+C 触发即可。

---

## 12. 与现有 skill / plugin 的关系

| 现有项 | 关系 |
|------|------|
| `superpowers:test-driven-development` | **被复用**——L1/L2/L3 的红绿循环纪律直接指向它。本 skill 提供的是"何时用、用在哪一层"的判断框架。 |
| `superpowers:writing-plans` | **互补**——前端任务派发前若复杂，先用 writing-plans 出方案，本 skill 在执行期约束。 |
| `kdev-frontend-selftest`（拟议） | **下游接力**——本 skill 完成代码层 TDD 后，由该 skill 接管浏览器/页面层功能验收。是否独立成 skill 见 §14 开放问题。 |
| `kdev-ui-autotest` | **再下游**——E2E 测试用例归档，是研发自测之后、测试团队/QA 的产物。本 skill 不直接对接它。 |
| `kdev-test-case` | **正交**——kdev-test-case 是测试用例规范，本 skill 是开发纪律。两者可同时调用。 |
| `kdev-secure-coding` | **同源不同域**——同样的 A+C+自举模板，覆盖前端层（前端的 XSS / CSP / cookie 安全可在本 skill references 中加一节链回 secure-coding，避免重复）。 |

---

## 13. 实施步骤（给开发会话用）

按以下顺序产出，每步独立可验证：

1. **写 SKILL.md 主文件**（不超过 200 行，符合 description 触发要求）
   - 顶部 frontmatter：name + description（关键词清单 + 触发场景）
   - 索引：分层决策树速查表 + reference 关键词映射
   - 自举段（按 §7）
   - 工作模式（§3 + §4 摘要）
   - 完成清单（§9 原文）
2. **写 references 八件套**（按 §6 目录布局）
   - 每个 reference 自包含，含正反例代码
   - vue3-vite-vitest 框架变体先写完整版，react / nuxt 后续补
3. **写 README.md + CHANGELOG.md**（plugin 元数据，模仿 kdev-secure-coding 风格）
4. **联调**：在 SOP_test 项目里跑一次端到端：
   - 模拟一个改 `src/store/xxx.ts` 的 L1 任务 → 验证红绿循环被强制
   - 模拟一个改 `src/components/xxx.vue` 的 L2 任务 → 验证组件行为测试被要求
   - 模拟一个纯样式 L4 任务 → 验证不要求测试但要求 commit message 加 `[selftest-required]`
5. **可选**：实现 `enforce-frontend-tdd-on-task.sh` hook，作为 plugin 的 hooks 子目录提供
6. **可选**：补 evals（参考 kdev-secure-coding 的 eval-design），后续迭代

---

## 14. 待确认 / 开放问题（开发会话开工前先和用户对齐）

1. **框架优先级**：先 Vue 3 还是 React？本项目（SOP_test）是 Vue 3，建议先做 Vue 3 完整版，React 用变体补。
2. **是否需要默认 hook**：默认走 A+C 触发够不够，还是和后端 TDD hook 看齐做强拦截？
3. **研发自测是否独立成 skill**（关键）：
   - 选项 A：独立 skill `kdev-frontend-selftest`，承接 `[selftest-required]` 标记，提供自测 checklist + Playwright MCP 走查模板。
   - 选项 B：不成 skill，研发自测留给项目流程/CLAUDE.md 文档说明，本 skill 仅在完成清单输出引导文字。
   - 选项 C：作为 `kdev-ui-autotest` 的一个轻量子模式，复用其 Playwright 基础设施。
   - 建议优先讨论清楚再开发本 skill，避免衔接点设计返工。
4. **`[selftest-required]` 标记格式与字段**：当前草案是 commit message 添加；是否改用 commit trailer（如 `Selftest-Required: yes`）以便 git log 检索？
5. **L4 边界是否再细分**：纯文案 / 纯样式 / 纯渲染组件三种情况是否需要不同标记或不同自测要点？

---

## 附录 A · SKILL.md 顶部 frontmatter 草稿

```yaml
---
name: kdev-frontend-tdd
description: |
  **核心基座（第零原则）：前端代码的"做完"标准是按层应套的红绿循环全部通过、commit 同时包含失败测试与实现；功能层是否真能跑由研发自测环节兜底，不在本 skill 范围。所有规范、约束、流程都服务于这一条——分层纪律是产出，不是覆盖率数字。**

  写 / 改 / 接入前端代码（Vue/React/TS/JS/CSS/.vue/.tsx/.jsx 文件，src/views|components|store|api 目录，vite/nuxt/next 项目）时使用本 skill。它把"前端 TDD 不能照搬后端"这件事固化成可执行规则：按 L1 业务逻辑 / L2 组件交互 / L3 API 调用 / L4 纯展示 四层分治，L1-L3 严格套红绿循环（复用 superpowers:test-driven-development），L4 不写测试，commit message 加 `[selftest-required]` 标记后由研发自测环节接力。**关键词触发**：加页面、改组件、修前端 bug、调样式、加表单、接接口、组件测试、Vitest、Vue Testing Library、前端覆盖率、UI 单测、selftest-required。**第一动作恒为**：判定本次改动落在哪一层（L1/L2/L3/L4，可多层）→ 查决策树 → 按层套纪律。
---
```

---

## 附录 B · 与项目当前 hook（enforce-tdd-on-task.sh）的协同

当前项目 `.claude/hooks/enforce-tdd-on-task.sh` 启发式拦截"无 TDD 调用"的代码 Task。本 skill 上线后建议：

1. 现有 hook 保持不变（继续守后端 Python TDD）。
2. 新增可选 `enforce-frontend-tdd-on-task.sh`，仅对前端文件路径生效，要求 prompt 提及 `kdev-frontend-tdd`。
3. 两个 hook 互不干扰：前端 Task 同时被前端 hook 检查，后端 Task 同时被后端 hook 检查。
4. 跨栈 Task（同时改后端 + 前端）需 prompt 同时提及两个 skill 名。

---

**End of Design**
