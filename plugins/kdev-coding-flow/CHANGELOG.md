# Changelog

## v0.2.0 — 2026-05-12

### Changed

- plugin / skill 同步重命名为 `kdev-coding-flow`（原 `kdev-coding-sop` / skill `coding-sop`），与 `kdev-design-flow` 等同系命名对齐

### Added

- `commands/kdev-coding-flow.md` — 显式斜杠命令 `/kdev-coding-flow <specs-dir> [--auto] [--bundle-strategy=...]`，把参数透传给 skill

## v0.1.0 — 2026-05-09

初始版本。从 `SOP_test-rerun` 项目仓库迁出，沉淀为独立 plugin。

### Added

- `skills/kdev-coding-flow/SKILL.md` — 13 节点 SOP 主体（节点 0 含项目背景对齐 / 蒸馏起源 / 可选 LSP 检测；节点 8 含 4 步验证；3 个人工判断 Gate；Bundle 策略 + 量化阈值；Auto Mode 适配）
- `skills/kdev-coding-flow/references/implementer-prompt-template.md` — 通用派单 prompt 骨架（必填段 + 固定段拆分；约束 3 兜底链不读相邻文件）
- `skills/kdev-coding-flow/references/examples/project-rules-example.md` — 项目级 `<repo>/docs/rules.md` 格式示例
- `evals/iteration-baseline/` — 2 轮 cross-stack eval（Node / Go / Rust 各 1 prompt × 2 版本对比）

### 设计要点

- **技术栈无关的方法论层**：栈通用约定（PEP8 / gofmt / 路由顺序等）依赖模型自带，skill 不内置
- **项目特定规则外置**：项目命名 / 框架 fork bug / 版本错配等走 `<repo>/docs/rules.md`，由项目维护
- **蒸馏经验出 skill**：决策判据 / 质量纪律速查作为项目 docs 落档，不放 skill 内
- **Eval 验证**：iter-2 极简版（删除 env-by-stack + example-quirks 内置文件）vs iter-1 通用化版，3 个 cross-stack eval 均 100% pass，证明栈通用知识无需 skill 内置

### Source 项目

迁出自 `https://<...>/SOP_test-rerun` 项目，初始 commit 为该仓库的 `b9185bb feat(skill): 提炼 coding-phase-sop-12nodes skill`。迁入时 skill 由 `coding-phase-sop-12nodes` 改名为 `coding-sop`（去掉来自原项目的「12nodes」后缀，与当时的 plugin 名 `kdev-coding-sop` 对齐）。后续 plugin 与 skill 同步重命名为 `kdev-coding-flow`（与 kdev-design-flow 等同系命名）。
