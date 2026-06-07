# kdev-team — KDev 数字员工集群

员工集中总目录。每个员工 = `agents/<canonical>-<cap>.md`（瘦 persona，CC subagent）+ `orchestration/<canonical>.node-table.yml`（编排结构）。花名册见 `staff.yml`。

## 模型（守 spec §2.4）
- **编排 = 编排 agent 按 node-table 调度**业务 agent + 驱动 kdev-core CLI；**不是调 flow-skill 串联**。
- **业务 agent** 调能力 skill 干活。
- **flow-skill**（kdev-coding-flow / kdev-design-flow）= 方法论 + skill 调用模板**参考**，非编排器。

## 员工
| canonical id | 中文 | flow-skill 方法论 |
|---|---|---|
| dev-engineer | 开发工程师 | kdev-coding-flow |
| （req-architect 阶段2 P-A 加） | 需求架构师 | kdev-design-flow |

## ⚠️ 激活（G-004）
新插件 / 改 agent 后，CC 按 version 键控 cache：**改动须 bump `plugin.json` version** + **用户侧刷新 marketplace（`/plugin` 更新/重装）+ 重启 session** 才生效。agent 不代劳激活。
