# kdev-memory

工程记忆制度插件 —— 为多迭代项目建立持久的跨会话记忆。

## 核心机制

- **实时落盘**：每步完成、每次踩坑、每个决策、每次评分，立刻写进 `.kdev/` 对应文件
- **快速汇总**：说"写今天的总结"时，从 `.kdev/` 当天条目聚合拼装，不翻会话记录
- **双评分**：模型自评 + 用户评分，差值暴露方法论盲区
- **经验外溢**：积累的改进建议喂给未来 skill 作者提炼新 skill

## 安装

```bash
# 第一次使用者：注册 marketplace
claude plugin marketplace add KDevSec/kdev-agents

# 安装插件（自动带 hook）
claude plugin install kdev-memory@kdev-agents
```

安装后自动启用 Stop hook —— 每次 Claude 要停下时检查 `.kdev/` 状态，提醒 Claude 落盘：

| 场景 | 提醒 |
|-----|-----|
| 项目未启用 `.kdev/` | 静默，不干扰其他项目 |
| 今天还没生成每日汇总 | 提醒 Claude 调用 skill 从 `.kdev/` 聚合生成 |
| 汇总存在 + 源文件有后续更新 | 提醒 Claude 追加新增条目（不覆盖已有内容） |
| 执行日志里今天没条目 | 提醒 Claude 实时追加 Step 记录 |

## 更新
```bash
claude plugin update kdev-memory@kdev-agents
```

## 使用

### 初始化（新项目首次使用）
> "给这个项目建立工程记忆"

### 日常（自动，无需干预）
CLAUDE.md 触发规则段让智能体在每步完成后自动记录

### 每日汇总
> "写今天的总结" / "生成每日汇总" / "交接给明天"

## .kdev/ 目录结构

```
.kdev/
├── 当前状态.md          # 工作状态单一真相源
├── 决策日志.md          # Q-NNN
├── 踩坑日志.md          # G-NNN
├── 执行日志.md          # 每步记录 + 双评分
├── 每日汇总/            # YYYY-MM-DD.md
├── 改进建议.md          # R-NNN（喂给未来 skill 作者）
└── 方法论铁规.md        # 可选，用户明确要求才建
```
