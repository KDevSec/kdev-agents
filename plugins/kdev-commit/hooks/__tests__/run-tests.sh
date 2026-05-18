#!/usr/bin/env bash
# kdev-commit hook 测试入口（Node 内置 node:test，零外部依赖）
set -euo pipefail
cd "$(dirname "$0")/.."
exec node --test __tests__/*.test.js
