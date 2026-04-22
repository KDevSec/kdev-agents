# meta/

跨 skill 的开发方法论——做**任何**新 skill 之前都应该先读的东西。

| 文档 | 性质 | 何时读 |
|------|------|--------|
| [skill-官方开发流程.md](skill-官方开发流程.md) | Anthropic 官方 skill-creator 的**逐字梳理**，带英文原文 + 中文翻译 | 第一次做 skill 时从头读一遍；写 description 前查 §3.3；跑 evals 前查 §5 |
| [skill-开发通用流程.md](skill-开发通用流程.md) | 基于 kdev-memory 实战的**补充**——官方没明说的工程经验（痛点驱动、hook 分层、严格度 opt-in 等） | 和官方文档配套读；开新 skill 前先答 §尾声 的 10 问 checklist |

## 两份文档的关系

- **官方流程** = 权威源头，写什么、怎么做的规矩
- **通用流程** = 实战补充，在真项目里踩过什么坑、为什么某些章节被强化

两份都要看。只看官方容易太学院派；只看补充会漏掉 evals / description optimization 的硬纪律。

## 案例锚点

[skills/kdev-memory/开发历程.md](../skills/kdev-memory/开发历程.md) 是这份方法论的第一个真实实例，上两份文档的大量引用都指向它。
