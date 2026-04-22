# skills/

每个 skill 一个子目录，存放该 skill 专属的调研、设计、开发笔记、案例分享。

| Skill | 状态 | 插件代码 | 文档 |
|-------|------|----------|------|
| `kdev-memory` | 已实现 | [plugins/kdev-memory/](../../plugins/kdev-memory/) | [kdev-memory/](kdev-memory/) |
| `kdev-commit` | 已实现 | [plugins/kdev-commit/](../../plugins/kdev-commit/) | [kdev-commit/](kdev-commit/) |
| `kdev-change` | 规划中（未实现） | — | [kdev-change/](kdev-change/) |

## 新增 skill 的目录约定

```
skills/<skill-name>/
├── README.md       # 本 skill 的文档索引 + 关键信息速查
├── 开发历程.md       # （可选）skill 从起源到当前版本的故事——case study 型，给后续作者看
├── research/       # （可选）该 skill 特有的调研文档
├── design/         # （可选）该 skill 的架构/设计决策
└── dev-notes/      # 开发期专题笔记（调试、踩坑、方案对比等）
```

**不要**把跨 skill 的通用内容放到这里——那应该进 `../meta/`。
**不要**把 KDev 框架级的设计放到这里——那应该进 `../framework/`。
