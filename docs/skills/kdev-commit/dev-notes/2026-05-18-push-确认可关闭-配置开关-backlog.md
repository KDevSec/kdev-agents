# 2026-05-18 · push 确认可关闭：配置开关 backlog

> 状态：**backlog（未排期）**
> 提出人：ly（用户对话原话见下文）
> 关联文件：`plugins/kdev-commit/hooks/confirm-push.js`、`plugins/kdev-commit/skills/kdev-commit/SKILL.md`

## 需求一句话

让用户能**关闭 `git push` 前的 IDE 弹窗确认**，省下一次点击；但**严禁 AI 自动 push**，AI 仍必须在对话里询问，等用户在对话中**显式说"push"**才执行。

## 用户原话（verbatim）

> kdev-commit 里能否增加配置提示，如果用户要求 push 前不询问，则不再弹窗提示框。但是不得主动 push，可以提示用户是否 push，但是必须用户在对话中显式要求（节省了点击 OK 的时间）

## 背景

- v0.2.0 的 `confirm-push.js` 在每次 `git push` 时**硬编码** `permissionDecision: 'ask'`，无 env 变量、无配置文件、无任何 opt-out 通道
- 用户长期使用中，每次都在两处确认 push：① AI 在对话里问、② IDE 弹框二次确认。两道 gate 对成熟用户是冗余
- 当前 workaround：禁用整个 kdev-commit 插件，但会一并失去 `block-unattributed-commit.js` 的 AI 身份强制（commit author 后缀 `-AI` 不再保证）—— **代价过大**
- 备选 workaround：直接改插件 cache 的 `hooks.json` —— **插件升级即被覆盖**，不可持续

## 设计要点

### 1. 配置入口（三档候选，待定）

| 方案 | 形态 | 优点 | 缺点 |
|------|------|------|------|
| A. 环境变量 | `KDEV_COMMIT_PUSH_CONFIRM=off\|warn-force\|ask` | 最轻、零文件、易记 | 不持久（每次 shell 都要设）、跨 IDE 行为可能漂移 |
| B. 用户级配置文件 | `~/.config/kdev-commit/config.json` 或 `~/.claude/plugins-config/kdev-commit.json` | 持久、独立于 settings.json | 多一个文件 / 路径约定 |
| C. 复用 Claude Code settings.json | 在 `~/.claude/settings.json` 加 `pluginConfig.kdev-commit.pushConfirm` | 用户已经熟悉这个文件 | 插件需要解析这个 schema，耦合 Claude Code 内部约定 |

**倾向**：A+B 组合 —— env 变量做临时切换、用户级 JSON 做持久化，env 优先级高于文件。env 名沿用 `KDEV_COMMIT_*` 前缀保持插件家族一致。

### 2. 取值粒度

至少三档：

- `ask`（默认，当前行为）：所有 push 都弹框
- `warn-force`：只有裸 `--force`（非 `--force-with-lease`）弹框，普通 push 静默
- `off`：完全不弹框

`warn-force` 是为了保留对真正危险操作的二道关 —— `--force` 覆盖远端历史不可逆，即使老手也建议保留确认。

### 3. SKILL.md 配套硬规

**关键**：hook 关掉 ≠ AI 可以擅自 push。

SKILL.md 现有"步骤 6：询问用户是否 push"已经写明"用自然语言问用户'要 push 到远端吗'"，但配置关闭后这变成**唯一 gate**，需要在 SKILL.md 里加粗强化以下约束：

1. **AI 永远不允许在用户未说 push / 推送 / 推 / yes 等显式肯定信号前自动 push**
2. **不允许把"提交并推送"当作一次性授权**——下一次提交时仍要重新问
3. **如果用户原话里只说"提交"没说"推"，commit 后必须停下来问，不能默认连推**
4. **`--force` 类危险操作即使在 `off` 模式下，建议在对话里额外强调一次"这是强推"再询问**

### 4. 实现草图（confirm-push.js）

```js
// 伪代码示意，正式实现需考虑 Windows 兼容、JSON 解析失败兜底
function readConfig() {
  // 1. 优先 env
  const env = process.env.KDEV_COMMIT_PUSH_CONFIRM;
  if (env === 'off' || env === 'warn-force' || env === 'ask') return env;
  // 2. 用户级文件
  try {
    const home = process.env.HOME || process.env.USERPROFILE;
    const path = `${home}/.config/kdev-commit/config.json`;
    return JSON.parse(fs.readFileSync(path, 'utf8'))?.pushConfirm || 'ask';
  } catch { return 'ask'; }
}

const mode = readConfig();
if (mode === 'off') return;  // 静默放行
if (mode === 'warn-force' && !hasBareForce) return;  // 非强推放行
// 其余继续走 'ask'
```

### 5. 文档变更

- `plugins/kdev-commit/README.md` 新增"配置项"小节
- `plugins/kdev-commit/skills/kdev-commit/SKILL.md` 步骤 6 加粗"AI 不允许擅自 push"硬规
- `CHANGELOG`（如有）记录这是 v0.3.0 增量能力，**默认值不变**（向后兼容）

### 6. 测试场景

- [ ] 默认状态：env 未设、配置文件不存在 → 行为同 v0.2.0
- [ ] `KDEV_COMMIT_PUSH_CONFIRM=off` + `git push` → 不弹框、AI 不能擅自推（靠 SKILL.md）
- [ ] `=off` + `git push --force` → 仍弹框？还是静默？取决于 `off` vs `warn-force` 边界定义
- [ ] `=warn-force` + 普通 push → 不弹框
- [ ] `=warn-force` + `git push --force` → 弹框
- [ ] `=warn-force` + `git push --force-with-lease` → 不弹框
- [ ] 文件优先级：env=ask + 文件=off → env 赢，弹框
- [ ] 配置文件 JSON 损坏 → 回落到 `ask`，不崩溃
- [ ] block-unattributed-commit.js 完全不受影响（commit 身份校验照常）

## 不做的事（明确排除）

- ❌ 不接受"一次授权永久放行" —— 必须每次对话都重新问
- ❌ 不在 SKILL.md 里隐含"用户说过一次 push 就可以连续推" —— 上下文清晰才推
- ❌ 不引入"白名单仓库"之类的复杂逻辑 —— 配置只控行为粒度，不控适用范围

## 优先级与风险

- **优先级**：P3（用户体验优化，非阻塞）
- **风险**：
  - 主要风险是 SKILL.md 约束被 AI 误解 → 关掉 hook 后真的自动推。需要回归测试覆盖
  - 次要风险是配置文件路径与未来 Claude Code 官方 plugin config 约定冲突 → 实现前先调研官方 schema
- **预估**：~半天（实现 1h + 文档 1h + 测试 2h）

## 关联记录 / 下一步

- 下次启动 v0.3.0 时把这条 backlog 提到 `plans/2026-MM-DD-kdev-commit-v0.3.md`
- 实现前需要确认：Claude Code 官方是否有标准的 plugin 配置约定（影响选项 C 是否可行）
