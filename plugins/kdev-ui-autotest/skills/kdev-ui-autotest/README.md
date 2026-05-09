# kdev-ui-autotest (Claude Code Skill)

一个 Claude Code user-level skill，固化 Playwright + pytest + Element-Plus 自动化测试的 6 大类规范（登录复用、资源清理、四件产物归档、Element-Plus 三大坑、用例命名、失败诊断），服务基于 `playwrightmode` 模板搭建的下游项目。

skill 详情见 [`SKILL.md`](./SKILL.md)。

---

## 在新机器上安装

把仓库克隆到 Claude Code 的 user skills 目录，目录名必须保持 `kdev-ui-autotest`：

**Windows (PowerShell)：**
```powershell
git clone <this-repo-url> "$env:USERPROFILE\.claude\skills\kdev-ui-autotest"
```

**macOS / Linux：**
```bash
git clone <this-repo-url> ~/.claude/skills/kdev-ui-autotest
```

最终目录结构应是：
```
~/.claude/skills/kdev-ui-autotest/
├── SKILL.md
├── assets/test_arNN_skeleton.py
├── evals/evals.json
└── references/*.md
```

---

## 验证安装

1. 重启 Claude Code 会话（已有 session 不会刷新 skill 列表）
2. 触发关键词测试，例如对 Claude 说："给我写一条 test_arNN 用例 skeleton"
3. Claude 应主动 `Skill` 调用本 skill 而非凭直觉作答

---

## 注意事项

- `SKILL.md` 中提到的 `D:\ClaudeCode\KDevSec\playwrightmode` 是**模板原型的参考路径**。下游机器上若无此目录不影响 skill 加载——它只在 Claude 需要回溯模板时被读。
- `assets/test_arNN_skeleton.py` 和 `references/*.md` 是 skill 的关键支撑物，不要单独删。
- 如果你在下游项目里发现新坑 / 新规范，回这台仓库 PR / push 即可，所有 clone 过的机器 `git pull` 同步。

---

## 维护

本仓库源自 `D:\ClaudeCode\KDevSec\playwrightmode` 模板的实战沉淀。改动建议遵循：
- 改 `SKILL.md` 主流程 → 同步检查 `references/*.md` 是否需要新增/作废条目
- 加新 reference → 在 `SKILL.md` 的"何时该读哪个 reference"表格补一行
- evals.json 跟着重要规范一起补，便于回归
