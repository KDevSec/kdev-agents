# HUD box 模板（CLI ASCII）

```
┌───────────────────────────────────────────────────────────┐
│ KDev cluster-x3 — {feature_slug}                          │
│ started: {feature_started_at}   active: {current_active_group} │
├───────────────────────────────────────────────────────────┤
│ reqs   {reqs.icon}   step:{reqs.current_step:<10} │ {reqs.last_progress:<24} │
│ dev    {dev.icon}    step:{dev.current_step:<10}  │ {dev.last_progress:<24}  │
│ test   {test.icon}   step:{test.current_step:<10} │ {test.last_progress:<24} │
│ review {review.icon} step:{review.current_step:<10} │ {review.last_progress:<24} │
├───────────────────────────────────────────────────────────┤
│ 最近事件:                                                  │
│ {events[0]}                                                │
│ {events[1]}                                                │
│ {events[2]}                                                │
└───────────────────────────────────────────────────────────┘
```
