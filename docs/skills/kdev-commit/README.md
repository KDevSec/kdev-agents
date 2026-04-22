# kdev-commit 文档

AI commit + push 一体化插件的专属文档。插件代码与当前 README 在 [plugins/kdev-commit/](../../../plugins/kdev-commit/)。

## 现状

**暂无独立设计/调研文档**。插件逻辑简单、无外部依赖，当前所有信息都在插件自身的 README 和 hook 脚本里自解释。

真要写的话，可以在此目录补充：
- 为什么要给 AI commit 单独加 `-AI` 后缀身份（起源可能是合规 / 审计溯源需求）
- 为什么 push 前要走 IDE 权限框确认（防止 AI 在用户不知情时推代码）
- hook 实现为什么选择纯 Node 无外部依赖

**何时开始补？** 按 [../../meta/skill-开发通用流程.md §二](../../meta/skill-开发通用流程.md)：等真实痛点或用户反馈催生时再补，而不是凭完备性写。
