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
