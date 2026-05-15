# Skill Feedback (F-NNN)

## F-001: kdev-memory 召回噪声大 / 同 session 重复命中无降权
日期: 2026-05-15
subject: plugin:kdev-memory
subject_inferred_by: L1-显式提及（用户原话直接说出"kdev-memory 的召回机制"）
subject_confidence: high
type: RFE
verbatim: "这破召回要是能学着不刷屏就好了，比如同一个 session 已经命中过一次就降权"
context: 用户在做异常处理重构时触发了 kdev-memory 召回，3 条不相关踩坑均被返回，用户主动要求记录此反馈
diagnosis: triggers 关键词过宽或缺少 session 内去重/降权逻辑，导致同主题在一次 session 中多次高权重召回
desired: 增加 session 内 demote 机制——同 session 内同主题已命中过一次则降权，避免重复刷屏
score: null
