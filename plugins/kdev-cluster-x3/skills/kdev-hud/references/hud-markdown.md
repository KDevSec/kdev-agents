# HUD markdown 模板

> kdev-hud 的 markdown 模式输出。占位符由 SKILL.md 在运行时填充。

```markdown
## KDev HUD — `{feature_slug}`

started: {feature_started_at} · active: `{current_active_group}`

| 组 | 状态 | 当前 step | 最后进度 |
|---|---|---|---|
| reqs | {reqs.status_icon} {reqs.status} | {reqs.current_step} | {reqs.last_progress} |
| dev  | {dev.status_icon} {dev.status}   | {dev.current_step}  | {dev.last_progress}  |
| test | {test.status_icon} {test.status} | {test.current_step} | {test.last_progress} |
| review | {review.status_icon} {review.status} | {review.current_step} | {review.last_progress} |

### 最近事件（tail 5）

- {events[0]}
- {events[1]}
- {events[2]}
- {events[3]}
- {events[4]}

### 阶段产物（COMPLETE.md 存在的组）

- reqs: {reqs.complete_link}
- dev: {dev.complete_link}
- test: {test.complete_link}
- review: {review.complete_link}
```

状态图标：complete=✅ in_progress=🟡 blocked=🔴 pending=⏳
