# Skill Feedback (F-NNN)

## F-001: brainstorming 开题引导到位
日期: 2026-05-15
subject: skill:brainstorming
subject_inferred_by: L1-显式提及（用户原话直接说出 "brainstorming skill"）
subject_confidence: high
type: 表扬
verbatim: "brainstorming skill 这次引导得很到位，开题问得很对"
context: 在 Step 12 评分时夹带反馈（评分裂解触发），Step 12 执行事实段「使用的 skill」含 brainstorming
diagnosis: 开题问题设计得当，引导了有效的思路展开
desired: null
score: null

## F-002: kdev-memory 召回无关内容噪声大
日期: 2026-05-15
subject: plugin:kdev-memory
subject_inferred_by: L1-显式提及（用户原话直接说出 "kdev-memory"）
subject_confidence: high
type: 痛点
verbatim: "kdev-memory 又召回了一堆无关的，太吵了"
context: 在 Step 12 评分时夹带反馈（评分裂解触发），Step 12 执行事实段「使用的 skill」含 kdev-memory
diagnosis: triggers 关键词覆盖面过宽，导致无关条目被召回，干扰主对话节奏
desired: 同 session 内重复命中降权 / 召回结果按相关度过滤
score: null
