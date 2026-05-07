# kdev-design-flow

Claude Code 插件：把"需求 → 原型 → 设计"流程固化为一个 skill，串联 spec-kit、frontend-design 等已有 skill，并嵌入评审闸门避免方向漂移。

## 安装前置

- 必需：`spec-kit` 插件已安装（`/kdev-design-flow` 启动时会硬性检测）
- 推荐：`frontend-design` 插件（Stage 3 用）

## 快速开始

```bash
/kdev-design-flow 用户登录功能
/kdev-design-flow --resume yong-hu-deng-lu-gong-neng
/kdev-design-flow --review=human 用户登录功能
```

## 流程

1. 初步需求分析 → SR 需求文档
2. 评审闸门 #1
3. 进一步需求分析（spec-kit）→ AR 用户故事
4. 原型设计（frontend-design）→ 高保真原型
5. 评审闸门 #2
6. 实现方案设计（spec-kit）→ 概要 + 详细设计
7. 评审闸门 #3
8. 产物合并 → `docs/design-flow/<slug>/`

## 评审模式

- `--review=ai`（默认）：Claude 自评
- `--review=both`：Claude 自评 + 用户拍板
- `--review=human`：纯人工评审

详见 [设计文档](../../docs/superpowers/specs/2026-05-07-kdev-design-flow-design.md)。

## 已知限制 (v0.1)

- 中间产物落 `.kdev/design-flow/`，不自动清理（保留迭代历史作 B 方案训练数据）
- `--review=both` / `--review=human` 模式下，会话中断后必须 `--resume` 重新进入评审闸门
- 不支持自定义 stage 顺序、跳过 stage、并行多 feature
- `spec-kit:specify` / `spec-kit:plan` 是硬依赖，没装会硬中断
- 中文 feature-name 走 SHA-1 hash 兜底（v0.1 不依赖拼音库），slug 形如 `00af4da9`，不可读但稳定
- Claude 自评（`--review=ai`）有自我确认偏差风险，缓解靠评审 prompt 写死的硬性 criteria 清单；B 方案再升级真二号意见

## 测试

```bash
cd plugins/kdev-design-flow
python3 -m pytest tests/ -v
```

预期：28 passing（slug 11 + flow_state 8 + skill_md_lint 9）。
