# prompts/

bugfix skill 派 subagent 时用的 prompt 模板。

## 文件清单

| 文件 | 用途 | 何时调用 |
|------|------|----------|
| [multi-agent-review.md](multi-agent-review.md) | 步骤 6.2 `--review-mode=multi` 独立评审 prompt | 评审强制升级或用户显式传 `--review-mode=multi/both` |

## 使用规范

主 Claude 派 subagent 前**必须**：

1. **Read** 对应 prompt 模板文件
2. 按文件顶部"用法"段的占位符表替换变量（如 `<BUG_ID>` / `<MODE>`）
3. 把替换后的 prompt 传给 `Agent({prompt: ...})`

**不要**：
- 把模板内容 inline 在 SKILL.md 或主 Claude 自己的对话里（这就是模板抽取的意义）
- 透传敏感配置（如 `ZENTAO_API_TOKEN` / `ZENTAO_PASSWORD`）给 subagent
- 在 prompt 里假设 subagent 能看到主 Claude 的对话历史

## 为什么单独成目录

prompt 模板有几个特性需要专门管理：

1. **完整文本要原样传给 LLM** —— 任何编辑都可能影响评审质量，需要专门关注
2. **占位符替换有固定规则** —— 文件顶部"用法"段定义，不能 ad-hoc 改
3. **可独立 eval** —— 未来加 evals/ 时，prompt 模板可以单独做回归测试
4. **可独立 review** —— code review 时 prompt 改动应当被 reviewer 重点看（影响 subagent 行为）

## 增加新 prompt 模板的规范

如果未来 skill 需要新的 subagent prompt（如 `human-review-summary.md` 或 `pre-commit-audit.md`）：

1. 文件命名：`<动作>-<场景>.md`，kebab-case
2. 文件顶部必须有"用法"段说明占位符表 + 派单代码示例
3. prompt 主体用 `---` 与说明段分隔，便于 subagent 收到的内容跟说明分离
4. 更新本 README 的"文件清单"表
