# demo-api 项目指南

长期演进的 FastAPI 项目，单人开发。

## 开发惯例

- Python 3.12 + FastAPI 0.110
- 测试用 pytest + pytest-asyncio
- 提交前必须跑 `pytest -q`

## 智能体自动记录规则

走项目流程时，必须实时维护 `.kdev/memory/` 下的记录文件。不需要征求用户许可即可写入这些文件。

（此处规则段对齐 kdev-memory skill 的 references/初始化-claude-md-模板.md，此处省略。）
