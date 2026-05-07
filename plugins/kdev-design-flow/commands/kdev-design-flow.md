---
description: 走完整需求-原型-设计流程：SR 需求文档 → AR 用户故事 → 高保真原型 → 概要+详细设计，3 个评审闸门
argument-hint: <feature-name> [--review=ai|both|human] [--resume]
---

# /kdev-design-flow

把"原始需求 → 工程设计文档"这一条链路固化为可复跑的 skill。

## 用法

```
/kdev-design-flow 用户登录功能
/kdev-design-flow 用户登录功能 --review=both
/kdev-design-flow --resume yong-hu-deng-lu-gong-neng
```

## 参数

- `<feature-name>`：必填（除非用 `--resume`）。中文/英文均可，会被规范化为 slug。
- `--review=ai|both|human`：评审模式，默认 `ai`（Claude 自评）。
- `--resume <slug>`：恢复中断的流程（不带 feature-name）。

## 你的任务

调用 `kdev-design-flow` skill，把 `$ARGUMENTS` 透传给它。skill 自身负责参数解析、依赖检测、状态初始化和主循环。

参数原文：`$ARGUMENTS`

按 `kdev-design-flow` skill 的 SKILL.md 步骤执行。
