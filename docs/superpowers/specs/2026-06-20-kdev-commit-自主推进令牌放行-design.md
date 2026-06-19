# 2026-06-20 · kdev-commit「自主推进」令牌放行 · 设计 spec

> 状态：**design 已锁定（用户已口头通过，TDD 实施中）**
> 起源：用户对话——"kdev-commit 修改逻辑为对话授权后就不再卡 hook，弹窗就自动确认 push 了"
> 目标版本：kdev-commit v0.4.0
> 关联文件：`plugins/kdev-commit/hooks/confirm-push.js`、`plugins/kdev-commit/skills/kdev-commit/SKILL.md`、`plugins/kdev-commit/README.md`、`plugins/kdev-commit/.claude-plugin/plugin.json`
> 前序 spec：[2026-05-18-push-confirm-config-design.md](../../skills/kdev-commit/specs/2026-05-18-push-confirm-config-design.md)（本 spec 在「自主推进态」对其「每次重新问 / 不接受永久授权」结论开例外，见 §8）

## 1. 一句话

对话里授予「自主推进」后，AI 给每条 `git push` 命令盖一个 `# 自主推进` 令牌章；`confirm-push.js` hook 认章即跳过 IDE 弹窗——把"对话 yes + IDE 点击"两道确认收成一道。手动模式（无令牌）照常弹窗兜底；裸 `--force` 即便带令牌也仍弹窗。

## 2. 背景与动机

v0.3.0 的 push 弹窗是"全有/全无"的三档（`ask`/`warn-force`/`off`），缺一条"**因为我已经在对话里授权了所以这次别弹**"的中间路径。成熟用户在自主/无人值守流程里，每次 push 都要：① AI 在对话里问、② IDE 弹框再点一次——对一次授权做了两次确认。本 spec 补上这条中间路径。

**核心权衡（必须明示）**：IDE 弹窗的全部价值在于它**不信任 AI**——它是人类硬停。任何"对话授权后自动放行"都把信任移交给"AI 声称授权发生过"。本设计接受这一权衡，但通过**令牌**把它做得**比 `off` 更安全**：没盖令牌的 push（手动模式 / AI 漏问擅自推）仍会弹窗兜底。

## 3. 范围

### 包含
- `confirm-push.js` 增加单一令牌 `# 自主推进` 检测，命中则放行普通 push
- `SKILL.md` 新增「自主推进模式」小节：触发集 / 撤销集 / 令牌盖章规则 / `--force` 例外 / 歧义回落
- `README.md` 新增令牌行为说明
- `plugin.json` version `0.3.0 → 0.4.0`，新增 `CHANGELOG.md`
- 回归测试续写 T10–T17
- 旧 spec 加 R-009 重定向锚

### 不包含（明确排除 / YAGNI）
- ❌ hook 解析 `transcript_path` 判断授权（脆、依赖措辞/语言、易误判——已在 brainstorm 否决）
- ❌ 英文触发词 `autopilot/autonomous/auto-advance`（用户未选）
- ❌ 从 `/loop`、`ralph-loop`、subagent-driven 等运行态**隐式**授予自主推进（仍需用户显式说触发词；将来可作扩展）
- ❌ hook 端识别多个令牌变体（hook 只认单一规范令牌，AI 负责翻译）
- ❌ 改动 `block-unattributed-commit.js`（身份校验是独立关注点，零改动）

## 4. 两层职责（关键架构）

不要混淆"用户说的话"和"AI 盖的章"：

| 层 | 在哪 | 谁产生 | 内容 |
|---|---|---|---|
| **对话触发层** | `SKILL.md` | 用户说 | 一组触发词（同义集） |
| **命令令牌层** | push 命令字符串 | AI 盖 | **单一**规范令牌 `# 自主推进` |

AI 把"用户说了触发集里任一词"翻译成"给 push 盖 `# 自主推进`"。hook 只做确定性的令牌匹配，不做自然语言判断。

### 4.1 触发集（用户说 = 授予自主推进 standing 态）
- Tier1 核心：`自主推进` / `自动推进` / `自主执行` / `自动执行` / `无人值守` / `全自动`
- Tier2 口语：`自动跑` / `自己跑完` / `一路到底`
- 直白表达：`不用问我` / `不用每次确认`（含 `不用确认`）

### 4.2 撤销集（用户说 = 退出自主推进态，立刻回到每次弹窗）
`停` / `暂停` / `手动` / `我来确认` / `退出自主` / `接管`

### 4.3 歧义回落
AI 拿不准是否仍在自主推进态 → **保守按"弹窗 + 问"处理**，不盖令牌。

## 5. 行为矩阵（`ask` 默认档）

| 场景 | 弹窗？ |
|---|---|
| 普通 push，**无**令牌（手动模式） | **弹** ✓ 兜底不变 |
| 普通 push，**带** `# 自主推进` 令牌 | **不弹** ✓ |
| 裸 `--force`（带/不带令牌） | **弹** ✓ 不可逆操作永远留一道关 |
| `--force-with-lease`，带令牌 | 不弹 |
| `off` 档（任意 push） | 不弹（令牌无关，行为不变） |
| `warn-force` 档，普通 push | 不弹（行为不变） |
| `warn-force` 档，裸 `--force` | 弹（行为不变） |

令牌只在 `ask` 档对普通 push 起作用；`off`/`warn-force` 行为零改动，向后兼容 v0.3.0。

## 6. 令牌定义与防误触

**规范令牌**：push 命令中出现 `#` 注释前缀后紧跟（仅空白）`自主推进`。

**匹配正则**：`/#\s*自主推进/`

**为什么必须有 `#`**：防止 branch 名 / commit message 里的"自主推进"字样误触：
- `git push origin feat-自主推进`（branch 名，无 `#`）→ **不匹配** → 弹窗 ✓
- `git commit -m "feat: 自主推进模式" && git push`（链式命令，"自主推进"前是 `: ` 不是 `# `）→ **不匹配** → 弹窗 ✓
- `git push # 自主推进` / `git push #自主推进`（`\s*` 容忍 0~N 空白）→ **匹配** → 放行 ✓

bash 语义：`git push # 自主推进` 里 `#` 起注释，bash 忽略其后内容，`git push` 正常执行；hook 读的是 `tool_input.command` 原始字符串（含注释），故能检测。

## 7. confirm-push.js 实现（增量）

在 `mode === 'off'` 之后、`warn-force` 判断之前插入令牌放行分支：

```js
const mode = readMode();
const hasBareForce = /(^|\s)(--force(?!-)(\s|$)|-f(\s|$))/.test(cmd);
const hasAutoToken = /#\s*自主推进/.test(cmd);   // 新增

if (mode === 'off') return;
if (hasAutoToken && !hasBareForce) return;        // 新增：令牌放行普通 push（--force 仍走兜底弹窗）
if (mode === 'warn-force' && !hasBareForce) return;

// 其余走原 'ask' 弹窗路径（含：ask 档无令牌普通 push、任意档裸 --force）
```

放置顺序保证：
- `off` 仍最高优先（完全静默，令牌无意义）
- 令牌只放行**非** `--force` 的普通 push（`--force` 落到后面的弹窗路径）
- `warn-force` / `ask` 原逻辑不被令牌干扰

## 8. SKILL.md 改动

### 8.1 新增「自主推进模式」小节（置于步骤 6 之后）
内容覆盖：
1. **触发**：用户说触发集（§4.1）任一词 → 进入自主推进 standing 态
2. **盖章**：自主推进态内，AI 给**每条** `git push` 追加 ` # 自主推进` 注释，且**不再每次问"要 push 吗"**（standing 授权，整段自主推进期间持续有效）
3. **撤销**：用户说撤销集（§4.2）任一词 → 退出，恢复每次弹窗、不再盖章
4. **`--force` 例外**：即便在自主推进态，强推仍需用户明说"强推"，且 IDE 弹窗仍会出现（双重门，不可绕）
5. **歧义回落**：拿不准 → 按弹窗 + 问处理
6. **AI 不得自授**：自主推进态只能由用户说触发词进入，AI 不得自行宣布进入

### 8.2 步骤 6/7 加例外引用
步骤 6 现有"对话层硬规"补一条：自主推进态是对"每次重新问"的**显式例外**（用户主动授予的 standing 授权）；步骤 7 在弹窗说明处注明自主推进态会跳过 IDE 弹窗（`--force` 除外）。

## 9. 测试（confirm-push.test.js 续写）

| # | 场景 | 期望 |
|---|------|------|
| T10 | `git push # 自主推进`（令牌+普通+默认 ask） | 不弹 |
| T11 | `git push --force # 自主推进`（令牌+裸 force） | 弹（force 兜底） |
| T12 | `git push --force-with-lease # 自主推进` | 不弹 |
| T13 | `git push`（无令牌+ask，回归 backstop） | 弹 |
| T14 | `git push # 自主推进` + env=off | 不弹（off 即全关，moot） |
| T15 | `git push origin feat-自主推进`（branch 名无 `#`） | 弹（防误触） |
| T16 | `git commit -m "feat: 自主推进模式" && git push`（字样在 commit msg） | 弹（防误触） |
| T17 | `git push #自主推进`（无空格，`\s*` 容错） | 不弹 |

**不破坏验证**：T1–T9 全部仍 pass；`block-unattributed-commit.js` 行为零变化。

## 10. 文档 / 版本 / 制度

- `README.md`：在「可配置 push 弹窗」小节后新增「自主推进令牌（v0.4.0+）」说明
- `plugin.json`：`version` `0.3.0 → 0.4.0`
- 新增 `plugins/kdev-commit/CHANGELOG.md`（v0.4.0 记一笔）
- **G-004**：改 hook → 必须 bump version + 用户刷一次 marketplace，否则 cache stale 不生效（实施收尾提醒用户）
- **R-009 回写**：旧 spec [2026-05-18-push-confirm-config-design.md](../../skills/kdev-commit/specs/2026-05-18-push-confirm-config-design.md) §2"明确排除"里"一次授权永久放行 / 每次重新问"两条，需加重定向锚指向本 spec §8（自主推进态对此开例外）

## 11. 边界与风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| AI 误进自主推进态或漏退（standing 态判断错） | 中（弹窗被多跳几次） | SKILL.md 明确撤销集 + 歧义回落；普通 push 误跳后果有限（push 本身仍是用户授权过的内容） |
| `--force` 在自主推进态被误放 | 高（不可逆覆盖远端） | 令牌**永不**放行裸 `--force`（T11 锁死）；SKILL.md 强推需另说"强推" |
| 令牌字样误触（branch/commit msg） | 中 | 强制 `#` 注释前缀（T15/T16 锁死） |
| 非 ASCII 令牌跨平台/编码问题 | 低 | Node 字符串 UTF-8 安全；hook 读 `tool_input.command` 原样；令牌走 `#` 注释，无引号（规避 G-001/G-002 argv 引号坑） |

## 12. 验收标准

- [ ] T1–T17 全部 pass（T1–T9 回归 + T10–T17 新增）
- [ ] `block-unattributed-commit.js` 行为完全不变
- [ ] 默认无令牌行为与 v0.3.0 完全一致（向后兼容）
- [ ] `off`/`warn-force` 档行为零改动
- [ ] SKILL.md 自主推进小节让 AI 读到后：进入态盖章、撤销/歧义回落、`--force` 仍额外确认
- [ ] 旧 spec 已加 R-009 重定向锚
