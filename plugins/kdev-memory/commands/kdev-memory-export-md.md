---
description: 把 .kdev/memory/ 里的数据导出为 markdown 切片包用于知识蒸馏 / skill 自主优化（产出 3 个切片包：dataset-full / dataset-misalignment / dataset-skill-feedback-by-subject）。绝不输出 JSONL（架构终态决策）。
argument-hint: [无参数 | --out <dir> | --no-sanitize]
---

# /kdev-memory-export-md

为知识蒸馏管道产出 markdown 切片包。详见 `references/markdown-切片导出.md` 的设计决策（**markdown 主存 + markdown 切片包导出，不引入 JSONL**）。

## 探查 record_mode

!`python3 "${CLAUDE_PLUGIN_ROOT}/hooks/lib/memory_config.py"`

## 执行导出

!`python3 "${CLAUDE_PLUGIN_ROOT}/hooks/lib/export_md.py" $ARGUMENTS`

## 你的任务

根据上面两步的输出：

1. **如果 record_mode == "hybrid"** 且当前能用 `Agent`/`Task` tool：
   - **不**直接读上面 `export_md.py` 的产出结果
   - 调一个 subagent 跑 `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/lib/export_md.py" $ARGUMENTS`，让 subagent 处理产出 + 把摘要返回给你
   - subagent 返回 `{written_to, status, counts, sanitize_status}` 后再向用户汇报
   - 理由：导出涉及全量 markdown 解析 + 写 3 个文件，token 量大，剥到 subagent 节省主会话上下文

2. **如果 record_mode == "inline"** 或 Agent tool 不可用：
   - 直接读上面 `export_md.py` 的产出 markdown
   - 整理成给用户的报告

3. **向用户汇报**（两档共通）：
   - 产出文件清单 + 文件大小
   - 每类切片的条目数（full / misalignment / 各 subject 的 F 数）
   - sanitize 验证状态（`verified` / `leaks_found`）—— 如有 leaks 必须**告警**并列出
   - 提示下游消费方式：直接喂蒸馏管道（Axolotl / Unsloth / HuggingFace SFT trainer 都原生吃 markdown）

## 关键约束

- **绝无 .jsonl 文件产出**——架构终态决策，违反此条 = 违反 SKILL.md 顶部"下游"段
- 原 `.kdev/memory/*.md` **不**修改（导出是只读动作；export_md.py 已保证这一点）
- 默认开启 sanitize（脱敏 email / 内部路径 / API key / 内部 URL / 私网 IP），**严禁向用户建议加 `--no-sanitize` 后分享数据**（仅测试用）
- 三个切片包都要产出（即使某类为空，文件也要在，含说明为何为空）

## 参数

- 无参数：扫 `./.kdev/memory/`，输出到 `./.kdev/memory/dataset/`
- `--out <dir>`：自定义输出目录
- `--no-sanitize`：**仅测试用**，跳过 PII 脱敏

## 详见

- `references/markdown-切片导出.md` —— 切片包内容 / 筛选规则 / sanitize / 不引入 JSONL 论证
- `references/subagent-落盘机制.md` —— hybrid / inline 两档配置 / Agent tool fallback 逻辑
