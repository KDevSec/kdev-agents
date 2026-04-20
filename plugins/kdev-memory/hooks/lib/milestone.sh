#!/usr/bin/env bash
# kdev-memory 里程碑路径白名单 —— 单一真相源
# 被 stop-check.sh 和 post-write-check.sh 通过 source 引用
#
# 设计原则：
#   - 命中 = "这条变更大概率对应一个工作单元 Step，值得显式落盘"
#   - 保持克制：日常源码/配置/脚本编辑不命中（避免 PostToolUse 刷屏）
#   - 只收"有约定结构"的目录/文件名，不扫 .md 泛匹配
#
# 扩展办法：在下面 case 里添加模式。优先考虑通用约定，而非单项目特殊结构。

is_milestone_path() {
  local path="$1"
  case "$path" in
    # --- Spec Kit 产物 ---
    specs/*/*.md|specs/*/contracts/*.yml|specs/*/contracts/*.yaml) return 0 ;;

    # --- 工程记忆自己的硬规 ---
    .kdev/方法论铁规.md) return 0 ;;

    # --- 迭代 / Sprint / 冲刺 ---
    docs/iterations/*.md|docs/iterations/*/*.md) return 0 ;;
    docs/sprints/*.md|docs/sprints/*/*.md) return 0 ;;
    docs/sprint-*.md) return 0 ;;
    docs/迭代-*.md|docs/迭代/*.md|docs/迭代/*/*.md) return 0 ;;

    # --- ADR（架构决策记录）---
    docs/adr/*.md|docs/adr/*/*.md) return 0 ;;
    docs/ADR/*.md|docs/ADR/*/*.md) return 0 ;;
    docs/decisions/*.md|docs/decisions/*/*.md) return 0 ;;
    adr/*.md|adrs/*.md) return 0 ;;

    # --- 架构 / 设计 / PRD / 需求 ---
    docs/architecture/*.md|docs/architecture/*/*.md) return 0 ;;
    docs/design/*.md|docs/design/*/*.md) return 0 ;;
    docs/设计-*.md|docs/设计/*.md|docs/设计/*/*.md) return 0 ;;
    docs/prd/*.md|docs/prd/*/*.md|docs/PRD-*.md|docs/PRD/*.md) return 0 ;;
    docs/requirements/*.md|docs/requirements/*/*.md) return 0 ;;
    docs/需求-*.md|docs/需求/*.md|docs/需求/*/*.md) return 0 ;;

    # --- 根目录关键文档 ---
    ARCHITECTURE.md|ROADMAP.md|MIGRATION.md|CHANGELOG.md|DECISIONS.md) return 0 ;;

    # --- 数据库 migration ---
    migrations/*.sql|migrations/*/*.sql) return 0 ;;
    db/migrate/*.sql|db/migrate/*.rb) return 0 ;;
    db/migrations/*.sql|db/migrations/*/*.sql) return 0 ;;
    prisma/migrations/*/migration.sql) return 0 ;;
    supabase/migrations/*.sql) return 0 ;;
    alembic/versions/*.py) return 0 ;;

    # --- API / 协议契约 ---
    openapi.yml|openapi.yaml|openapi.json) return 0 ;;
    api/openapi.yml|api/openapi.yaml|api/openapi.json) return 0 ;;
    api/schema.graphql|schema.graphql) return 0 ;;
    *.proto|proto/*.proto|proto/*/*.proto) return 0 ;;
  esac
  return 1
}
