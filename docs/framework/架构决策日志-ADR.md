# 架构决策日志（ADR）

> 本文由 kdev-memory /distill promote 于 2026-07-10 从 .kdev/memory/决策日志.md 首次沉淀。原始决策现场记录仍在 .kdev/memory/，本文是加工后的长效 ADR。

本文只收录**架构决策**（Q-003 及之后、含 4 条时间戳 ID）。`Q-001`（Step 编号全局递增 vs 迭代内递增）与 `Q-002`（本项目跳过用户评分采集）是项目内部偏好、不外推，已在源文件标 `promote_status: skipped` 并注明理由，不纳入本 ADR；但下文正文在必要处会引用它们作背景（如 Q-015/Q-017 的"自评→他评"演进正是从 Q-002 的处境出发）。

ADR 加工原则：保留「决策内容 + 决策理由（选了什么/否了什么）+ 现行状态」，删去当场推导对话与已过期的中间选项；决策间的取代/演进关系以 `⚠️` 显式标注。

---

## 决策总览表

| 决策号 | 一句话决策 | 状态 |
|---|---|---|
| [Q-003](#q-003) | secondary worktree 下 Step ID 加分支前缀（`Step <slug>-N`） | ⚠️ 已被 Q-020 取代 |
| [Q-020](#q-020) | Step/Q/G/R/F 全量 ID 换时间戳原语（`<YYYYMMDD-HHMMSS>-<who>`），slug 机制退役 | 待实施（机制设计定，`step_id.py` 改造随 P-C2 一并做） |
| [Q-009](#q-009) | 数字员工记忆走独立 nested repo + 自举 hook，与代码分支彻底解耦 | 现行（设计定，隐私脱敏细节待确认） |
| [Q-019](#q-019) | P-C2 定型为「只读 + 派生」操作层，不造第二本账；判定"下一个排期" | 待实施（P-C2 implementation plan 未开） |
| [Q 20260617-182852](#q-20260617-182852) | 员工记忆层 JSONL 主账化，markdown 退成日总结派生视图 | 现行（方向已被 Q 20260625-173847 具体化为落地口径） |
| [Q 20260625-173847](#q-20260625-173847) | kdev-memory 执行日志 Step 源采「永久 dual-read」(C1)，不照 ieidev 硬切 | 现行（Phase C 已落地；其"人读"措辞被 Q 20260630-193220 修正） |
| [Q 20260630-193220](#q-20260630-193220) | 修正"什么进 jsonl"判据——"人读"降级为务实落点非永久原则 | 现行（当前判据） |
| [Q-015](#q-015) | P-C1b Step 落盘机制：后台 recorder 读 transcript、模型他评替换自评（v0.4） | 待实施（spec 已回写 v0.4，spike-gate 未跑） |
| [Q-016](#q-016) | 评审专家(reviewer) 接入设计：callee 形态 + 6 能力子集 + 双 mode 他评 | ⚠️ fork-2（mode-2）已被 Q-017 摘除；mode-1 待实施 |
| [Q-017](#q-017) | 层2 深度他评归位到蒸馏管道质量闸（非评审专家 mode-2），复活 misalignment 死切片 | 待实施（audit stage 全 defer） |
| [Q 20260614-005123](#q-20260614-005123) | `status` 字段语义钉死为评分/销账态，修复态搬 body，不加 `fix_status` | 已实施 |
| [Q-004](#q-004) | 数字员工架构从「低等级」walking-skeleton 起步，不追终态一步到位 | 已实施（首个员工=开发工程师 L2，已跑通） |
| [Q-005](#q-005) | 概念模型补维度：组成六维 + 平台底座层 + 当前锚定 L2 | ⚠️ 知识库/MCP 定位已被 Q-006 取代 |
| [Q-006](#q-006) | 等级轴改量「自主度」（L1-L4），知识库/MCP 移出等级轴归「组成」 | 现行 |
| [Q-007](#q-007) | kdev-core 底座路线 = 从 flows 抽公共编排层（借 OMC 范本、不 fork） | 现行（已实施 lean 底座；L3+ 不 foreclose 重评 OMC） |
| [Q-008](#q-008) | 底座组成：状态/编排/记忆三分离 + node 是编排层产物非中心契约 | 现行 |
| [Q-010](#q-010) | 阶段1：coding-flow 接 kdev-core 底座，7 项设计拍板 | 已实施（Step main-43） |
| [Q-011](#q-011) | 阶段2：第二员工(需求架构师) + 记忆 scope 分离 + 员工集中 `kdev-team` | 已实施 |
| [Q-012](#q-012) | 编排底座存储 feature-first 重设计：`features/<slug>/` 翻转 + 台账/流水切分 | 已实施（kdev-core v0.2.0，P-Core-FF） |
| [Q-013](#q-013) | P-Core-FF（feature-first 存储 + events.jsonl）从阶段3 提前，置于 P-A 之前 | 已实施 |
| [Q-014](#q-014) | 框架分发走 CC 插件市场 + 插件依赖（非 OMC clone 式）；kdev-core 升 marketplace 插件 | 部分已实施（kdev-core 已挂载；kdev-team 依赖声明/一键装 follow-up 未做） |
| [Q-018](#q-018) | 数字员工依赖声明：CC `plugin.json dependencies` 自动传递安装，声明不 bundle | 待实施（defer 专项，可与 FF-2 合并） |
| [Q 20260617-182851](#q-20260617-182851) | 编排路由器（CEO 总编排）设计定调：纯主会话 skill + 模板路由 + 三段 plan/confirm/drive | 待实施（MVP plan 未开） |

---

## 一、Step ID 与记忆基础设施（并发写手 / git 托管）

### Q-003
**secondary worktree symlink 架构下 Step ID 加分支前缀**（2026-05-28）

⚠️ **已被 [Q-020](#q-020) 取代**——落地约束里的计数器方案（`state/step-counter-<slug>.txt`）未见实施确认即被更根本的方案替换。

- **决策**：Step ID 格式改 `Step <branch-slug>-<N>`（如 `main-9`），每分支独立计数器，historical Step 1~8 保持无前缀不动。
- **理由**：两个 worktree 共享同一份 `.kdev/memory/执行日志.md`，并发推进时各自独立读「最新 Step 编号」会撞号；对称的都带前缀（否了"只 secondary 带前缀"的方案 C）比区分 main/secondary 简单、也比什么都不做（方案 B）在并发场景更安全。
- **后来发现的根因**（催生 Q-020）：顺序整数假设「唯一串行发号权威」，但架构本就是分布式写手（多 worktree/机/协作者），branch-slug 前缀只是把撞号的粒度从「全局」缩到「同分支」，没有从根上解决。

### Q-020
**Step ID 换时间戳原语（格式 B `Step <YYYYMMDD-HHMMSS>-<who>`），slug 机制退役**（2026-06-13）

- **决策**：Step **以及 Q/G/R/F** 全部 ID 换成 `<类型> <YYYYMMDD-HHMMSS>-<who>`（`who` = git email 前缀，取不到则整体省略后缀，绝不写 `-None`）；同秒同写手加 atomic `.N` 兜底；`compute_branch_slug()` + per-branch 计数器退役；历史 `main-N` 冻结不改写，解析器双认（`main-\d+` 或时间戳形）。
- **理由**：顺序整数的根因是「假设存在唯一串行发号权威」，但记忆系统架构刻意分布式（计数器本地不进 git，Step 条目 git 同步）——「全局 1..N」在多写手场景数学上不可满足，是**结构性**撞号（G-011 实锤），Q-003 的 branch-slug 只是缩小了炸弹半径。范围从"只 Step"扩到"Step+Q/G/R/F"，因为多协作者/跨机场景下 Q/G/R/F 的撞号是同一个结构问题，一并换掉才不留半修。
- **取舍（认下的代价）**：`Q 20260613...` 比 `Q-011` 长、不好记不好引用——用"自带日期+解析器统一"抵；时钟偏移/回拨下排序≈真实序非严格单调，对人读叙事可接受。
- **状态**：设计通过 10 场景压测（含 no-git、2 人并发、跨机），`step_id.py` 改造与受影响 hook（brief/recall/distill/frontmatter）随 P-C2 实施一并做，未落地代码。

### Q-009
**数字员工记忆 git 托管 = 独立记忆仓（nested repo）+ 自举 hook，与代码分支彻底解耦**（2026-06-05）

- **决策**：代码仓保持 `.gitignore /.kdev/`（不 track、不 submodule）；记忆走独立 nested repo（自己的 remote）；代码仓只放 tracked 的 `kdev-sync.yml` 记「记忆仓地址」；SessionStart 无 `.kdev/.git` 则 clone、有则 pull，SessionEnd/rollup 时 commit+push；多 worktree symlink 指向同一 canonical `.kdev/`。
- **否决的替代方案**：① 单独 kdev-sync 分支——切到 main 记忆不在场（gitignore 不分支）；② track 进 main——记忆随代码分支割裂、未提交挡 checkout、刷历史；③ submodule——父仓钉 per-commit 指针，重新耦合分支 + 拿旧 SHA。
- **状态**：设计已定并落地为约定（见项目 `.kdev/` 现状即独立仓）；隐私脱敏（团队仓 vs 个人仓）留待确认，非阻塞项。

---

## 二、记忆存储主账化（Step 从 markdown 迁向 JSONL）

四条决策构成一条演进线：**方向提出 → 范围/时机定型 → 落地口径拍板 → 判据措辞修正**。

### Q-019
**P-C2 = 只读复用 events 的「读+派生」操作层，不造第二本账**（2026-06-13）

- **决策**：P-C2 不写任何新流水，只读复用 `kdev-core features/<slug>/events.jsonl`（按 actor 过滤员工视图）+ transcript；叙事 markdown Step 收窄到仅 CEO/shared 一根，员工层只留 events（做了啥）+ handoffs（产出啥），砍掉 per-员工叙事 rollup——N×M token 膨胀被结构消除，非事后拆分缓解。
- **理由**：守「不造第二本账」（记忆底座 §7/§8 + R-009）；他评只在 Step rollup 粒度做（层1 P-C1b + 层2 蒸馏质量闸，见下），events 本身零他评，否则把省下的 token 又烧回去。
- **时机判定**：推翻阶段2 spec 原判「token 痛才上」的 defer 分类，改判「下一个排期」——驱动力是架构已定 + 避免员工先污染 markdown 再回头建 recall 的返工，**非**「token 痛已实测」（诚实记账）。
- **状态**：设计 spec 已写（P-C2 v1.0），implementation plan 未开。

### Q 20260617-182852
**员工记忆层 JSONL 主账化（md 退日总结派生）**（2026-06-17）

- **决策**：Step（含自评/扣分项/评分/verbatim 反馈）落结构化 JSONL 记录；markdown 退成"日总结从 JSONL 派生"，不再 per-Step 物化 md。
- **理由**：核心洞察是"人实际不持续读叙事层 markdown，只看日总结"——当初选"markdown 主存"的唯一硬理由（叙事给人持续读）因此塌陷，天平倒向结构化为主。召回不因此变差：现有 `<kdev-memory-brief>`/`<kdev-memory-recall>` 是靠 `triggers:` 字段的 lexical 召回，结构化字段过滤比正则扫 md heading 更稳，顺带消除 trigger-match 双认脆弱性一类 bug。
- **对语义召回（MemOS）的定位**：定为"后置低后悔旁挂索引"（可重建派生、不进 git、不当主账），等 lexical 召回真痛 + JSONL 主账立稳后再 PoC，不现在分叉。
- **状态**：方向已被下方 Q 20260625-173847 具体化为 Phase C 的实际落地口径（dual-read C1）。

### Q 20260625-173847
**kdev-memory 执行日志 Step 源采「永久 dual-read」(C1)，故意分叉 ieidev 硬切(C2)**（2026-06-25）

- **决策**：reader 永久读 `执行日志.md`（冻结历史）∪ `执行日志.jsonl`（新增），经 `step_dualread.py` 合成器层并集；不退 md-Step-read、不迁移存量 `执行日志.md`。`migrate_jsonl` 降为可选 cleanup。
- **对照 ieidev**：核实 ieidev 是硬切（`weekly.py`/`distill.py` 只走 jsonl，存量 md 早迁走），kdev 明确不跟。
- **理由（根本场景差异）**：kdev-memory 是**单用户·跨会话召回**场景（记忆=一条连续个人时间线，读者=人+下个会话的 Claude），ieidev-team 是**多 Agent·记忆共享**场景（记忆=团队协作底座，读者=其他 agent）。单用户最珍贵的是连续可读历史，为"干净 jsonl-only"冒险迁存量库不划算；ieidev 的 delegation/recall-events/handoffs/staff-scope/CQO 全是"多 agent 共享"机制，单用户无"别的 agent"可共享。JSONL 对 kdev 是"确定性日总结+结构化召回"的**增益**而非**刚需**，故能从容选低风险的 C1。
- **边界澄清**：只有「执行日志 Step」这一源迁了 jsonl；决策(Q)/踩坑(G)/改进(R)/反馈(F)/每日汇总/当前状态 仍永久 markdown 主存，所有 reader 照常读这 4 类 md。
- **状态**：Phase C 已落地（连同 0.19.0 bump）；其"决策/踩坑/F/R 永久 markdown 因为人读"的措辞被下方 Q 20260630-193220 修正（决策本身 C1 不变，只是理由站不住脚被替换）。

### Q 20260630-193220
**修正「什么进 jsonl」判据——"人读"降级；Q/G/R/F 留 md 是务实落点非永久原则**（2026-06-30）

- **触发**：用户挑战"这些（决策/踩坑/F/改进/当前状态）实际上都可以不用人来读"——揭穿 Q 20260625-173847 里"永久 markdown（因人读）"的理由站不住：kdev 消费早已全走渲染视图（SessionStart brief / trigger-match 召回 / daily_render / 蒸馏切片），人不直接读任何原始 md，不只 Step 如此。
- **决策（新判据，三者同时满足才迁结构化）**：① 写入路径有 recorder subagent（不给主会话核心写作流加摩擦，Q/G/R/F 是主会话直接手写 prose，没有）；② 有具体确定性消费需求拉动（像 `daily_render` 当初拉动 Step；Q/G/R/F 目前没有）；③ schema 契合（决策是自由叙事，塞字段要么丢 nuance 要么 json 包一坨 prose）。
- **结论**：Q/G/R/F + 当前状态现在不迁，留 markdown 当源——但定性为"**务实落点，非永久原则**"，修正 Q 20260625-173847 的"永久 markdown（人读）"措辞。recall 升级走「可重建的派生结构化索引」（MemOS 线），覆盖在 markdown 源之上、不迁源——存储格式与召回质量正交，不要混为一谈。
- **复议触发器**：某类记录出现具体确定性消费需求时才值得结构化，走 `daily_render` 当初为 Step 挣得迁移的同一道闸。
- **状态**：现行判据。

---

## 三、Step 落盘评估机制与两层他评（评审专家 / 蒸馏质量闸）

### Q-015
**P-C1b Step 落盘机制：后台 recorder 读 transcript + 模型他评替换自评（v0.4 修正）**（2026-06-12）

> 本条经历同日 v0.3→v0.4 修正，以下直接给修正后的最终口径。

- **决策**：Step 落盘维持"每步实时·fire-and-forget 后台 dispatch"节奏（非重型 workflow-batch fan-out），但把评估维度从"主会话当场自评"换成"recorder 独立读真 transcript 出模型他评"（`### 模型自评` → `### 模型他评`）。
- **为什么是修正而非翻案**：v0.3 判"每步实时 dispatch (a)"胜"后台 workflow-batch (b)"的核心论据是"self_eval 必须主会话当场第一人称给"——这是个没拆开的耦合假设。一旦评估换成"后台 recorder 读 transcript 出他评"，(a)/(b) 即假对立：取 (a) 的每步实时 + 取 (b) 的客观后台采集，合成更优设计；主会话付出近零（无 YAML、无 self_eval），且在**记录层**直接修了"模型自评 confabulate"（MQ-2，Step main-69 曾凭空编造扣分项）。
- **诚实地板**：hook 不能自主拉起后台 worker，"主会话零动作全自动"不可达，最小成本是边界发近空 dispatch + hook 提醒。
- **诚实代价**：他评替换（非并存）丢了"self vs peer 偏差"misalignment 信号——本项目 Q-002 早已放弃该数据、用户明确选替换，代价已接受。
- **两层他评对齐**：本条是**层1**（轻量/每步实时/基线执行质量），**层2**见 Q-017（深度复评）。
- **状态**：spec 已升 v0.4，§5.6 spike-gate（PostToolUse stdin 是否有 transcript_path 等三件事）先验后建，未跑，实施未开始。

### Q-016
**评审专家(reviewer) 接入设计：callee 形态 + 6 能力子集 + dev3/req3 接 gate + 双 mode 他评**（2026-06-12）

⚠️ **fork-2（mode-2）已被 [Q-017](#q-017) 摘除**——评审专家现只保留 mode-1。

- **决策（4 forks）**：① 形态 = **callee 员工**（非 flow-owner）——是 canonical kdev-team 员工但 `dispatch_table` 取代 `node_table`、不跑自有 flow-state、被 caller 的 R3 review gate 发函调用，因为"评审是协作不是线性工序"，硬塞假 node-table 是过度机件；② 承载他评 = 同员工双 mode（mode-1 项目产物评审 gate 驱动；mode-2 记忆 Step 他评 workflow-batch——**已被 Q-017 摘除**）；③ 本期范围 = 有 caller 的 6 能力子集（SR/用户故事/原型/方案+架构/代码+质量/安全），YAGNI 掉核心10余4 与扩展6；④ 接 gate = dev 3 deferred 兑现真发函 + req 3 self 翻 reviewer-expert，机制统一为 L1 flow-config per-gate `reviewer: self|reviewer-expert|both` 可回退。
- **发函边界**：评审专家只产出评分表+分级建议，从不直接命令 caller；🔴阻断走 caller 的有界回流+escalate，🟡/⚪ 由 caller 自主判断，3 次不过升 CEO→用户拍板。
- **状态**：设计 spec 已写（callee 形态 + staff schema delta + dispatch-table + 6+1 standards），staff.yml/agent/caller 改写等实施 follow-up 未做。

### Q-017
**层2 深度他评归位 = 蒸馏管道质量闸（非评审专家 mode-2）+ 复活 misalignment 死切片**（2026-06-13）

- **背景**：核查发现蒸馏管道的 `dataset-misalignment`（模型自评 vs 用户真实评分 gap）切片，自 Q-002（本项目不采集用户评分）起就是空的死切片；Q-015 v0.4 去 self_eval 更坐实。
- **决策**：层2 深度他评的家从"Q-016 评审专家 mode-2"改归**蒸馏管道的 audit/质量闸**（归 `/kdev-memory-distill`）。
- **理由**：① **同节奏同语料**——蒸馏本就是低频/批量/跨步读全量记忆，层2 深审也是按需/批量/跨步读 transcript，一模一样的 cadence，该一趟跑；② **污染正好在蒸馏处放大**——伤害在导出成训练数据那刻兑现，质量闸就该装在 garbage-in 的入口；③ **mode-2 是别扭嫁接**——评审专家 6+1 标准是评代码/SR/方案的，不是评"记忆诚不诚实"的，记忆审计要用另一把刀（证据锚定/confab 检测/分数校准）；④ **复活死切片**——用"层1 每步基线他评 vs 层2 深度复评"的 gap 作新对齐信号，正好复活被 Q-002 打死的 misalignment 切片。
- **三层定型**：层1 = P-C1b recorder 他评（每步实时·写时质量闸）；层2 = 蒸馏 audit stage（批量/导出时·读时质量闸，跨步深读 transcript 校准/推翻层1 他评→标/剔污染样本→可写回记忆修正→产干净切片包）；评审专家（Q-016）只保留 mode-1（评项目产物）。
- **状态**：设计已回写 P-C1b spec §5.8/§6 + Q-016 摘 mode-2；audit stage 实现全 defer，blocked-on Q-015 的 transcript 溯源管道。

### Q 20260614-005123
**`status` 字段语义钉死为评分/销账态（修复态去 body，不加 `fix_status`）**（2026-06-14）

- **决策**：`status` 只表评分/销账态（`open|scored|voided-faded|voided-r-NNN`），修复态（fixed/mitigated/处置中）写在 body「解决」段，不重载进 `status`，也不新增独立 `fix_status` 字段。
- **否决的替代方案**：(A) status 重载修复态——现状漂移写法，已在 G-005/006/011 踩过坑；(B) 新增 `fix_status` 机读字段——语义干净但目前无任何消费者，YAGNI。
- **理由**：`status` 已被 `step_completeness`（欠评扫描）/`distill`（misalignment 切片）当评分态枚举消费，重载修复态会让评分态语义漂移、下游误判（G-005/006/011 已实证）。修复态是人读的 body 叙述，不需要机读枚举。
- **落地**：`六类记录-schema.md` 补 status 字段语义块；`status_schema.py` 加防御谓词（`is_known_status`/`is_voided_status`）+ 告警接入 `step_completeness`/`distill`；清理既有 G-005/006/011 的漂移写法。
- **状态**：已实施（v0.18.0 同批 bump）。

---

## 四、数字员工架构总体设计

### Q-004
**数字员工架构从「低等级」起步，不追求一步到位最完美**（2026-06-01，2026-06-06 细化定稿）

- **决策**：39/40-agent 完整终态图定位为「北极星」而非实现起点，引入能力等级阶梯，从 L1 起步逐级演进（walking-skeleton 路线：先小、可验证、可调试，避免"一步到位最完美"的塌陷风险）。
- **细化拍板（2026-06-06）**：① 排法 = walking-skeleton，底座先行（kdev-core R1/R2/R3 + git 托管），记忆 scope/JSONL 等阶段2 有并发员工再上；② 第一个员工 = **开发工程师（coding-flow）· L2 协同**（用户否了主控推荐的"需求架构师最薄骨架"，选价值密度最高 + 一口气压测三类 gate 的开发工程师）；③ X1/X3 出局，仅 X3 reference-only 不收割；④ 回填三待定：砍员工数（→1）不砍自主度（L2），5 阶段 = L2→L2完整→L3→L4 阶梯。
- **dogfood 任务已锁**：UED 6.0 改造 benchmark（两 pass：小切片验底座 / 整题拿可比竞赛分）。
- **状态**：已实施——首个员工（开发工程师）已按此路线跑通。

### Q-005
**概念模型补维度 — 组成六维 + 平台底座层 + 当前锚定 L2**（2026-06-02）

⚠️ **关于知识库/MCP 定位的部分已被 [Q-006](#q-006) 取代**。

- **决策**：① 不加更高 L，企业资产池/治理测评是平台层非更高等级——模型升为「双轴 + 平台底座」；② 组成四件套扩为六维（+知识库+连接器 MCP）；③ 当前级别锚定 L2，L3-L4 是未来规划；④ 汇报架构图要体现附图式六维+平台底座+L1-L4 分级。
- **同日修正**：知识库/连接器最初判"不分级别、L1 就有"，同日改判"L1 不含 MCP/知识库，应到 L3 加"——但这一判断本身次日又被 Q-006 进一步推翻（知识库/MCP 根本不该挂在等级轴上）。
- **状态**：六维+平台底座+分级架构图的整体框架仍现行；知识库/MCP 具体挂哪个"级"的判断已被 Q-006 取代。

### Q-006
**等级轴改量「自主度」，知识库/MCP 移出等级轴归「组成」**（2026-06-02）

- **背景**：Q-005 反复纠结知识库/MCP 该挂 L1/L3/L4，本质是把"组成"和"成熟度"压到了一根轴上。
- **决策**：等级轴 = 自主度（L1 助手 → L2 协同 → L3 自主 → L4 自治，贴行业主流分级/自动驾驶 L1-L5）；知识库+连接器(MCP) 整体移出等级轴，归入"组成"（横向，按岗位丰俭配，不挂级别）；按级长出的只剩自主/可靠/治理机制（记忆/编排(L2) → 协作/第三方评审(L3) → 元监督/自演进/跨IDE(L4)）；当前 = L2 协同。
- **理由**：行业现实是知识库+工具/MCP 是数字员工的地基（没它就是聊天机器人），不是高级件，元监督/治理才是最高级——"L4 才加知识库/MCP"与行业认知相反；根因是知识库/MCP 在组成轴（横向配置），不在自主度轴（纵向多自主）。
- **状态**：现行——概念模型 v0.3 定调，终态 = L4 自治 × 数字公司。

### Q-007
**kdev-core 底座路线 = 抽共性渐进（借 OMC 范本不 fork）**（2026-06-03）

- **背景**：整体架构 v0.1 说"自建"，另一份对比文档又"以 OMC 为底座前提"，一直悬而未决；核实发现 design-flow/coding-flow 已各自实现底座机制，是数字员工雏形，但没有共同底座——底座真正职责是 R1-R7 编排引擎（状态机/节点机/闸门/自主/派单/产物/调度）。
- **决策**：底座从现有 flows 抽 R1-R7 公共编排层（lean kdev-core，Python/markdown 原生），照 OMC mode/Team Pipeline 范本但不 fork 源码；守 Q-004 从低起步 + Python/markdown 哲学，不引入 TS 3.3MB 运行时的 fork/维护/license 负担；不 foreclose 直接采用 OMC——L3 自主/L4 自治/跨 IDE（v2.x）真要完整运行时再重评。
- **状态**：现行，已实施为 lean 底座（kdev-core）；重心从"管道"挪到 R2 节点编排/R4 自主模式。

### Q-008
**底座组成 — 状态/编排/记忆边界 + node 是编排层产物**（2026-06-04）

- **决策**（逐项拍板）：① 编排"结构进底座、执行留 flow"——node-table+gates 作可编排 config 进底座，"每节点调哪个能力"留 flow prompt；② 状态/记忆分离——底座自存 flow-state（操作态），kdev-memory 管经验态（决策/踩坑/评审反馈），两 store 互不依赖；③ 记忆复用 kdev-memory 但不依赖其运行时；④ 框架要完整——状态/编排/记忆接口/HUD/事件流/派单/产物全纳入底座框架，实现渐进；⑤ node 是编排层产物，不是中心契约——phase（coarse 10 值）普适恒在，node（fine）要编排/配置定了才有；⑥ node 三来源优先级：底座 node-table > 项目 config.yaml > 无（只 phase 兜底）。
- **关键核实**：kdev-memory 的 phase_node 元数据增强只是工作草案，插件从未实现，纠正了此前的错误假设。
- **状态**：现行，是后续所有底座/记忆边界设计（Q-009、Q-012 等）的基础约束。

### Q-010
**阶段1 coding-flow 接 kdev-core 接入设计 —— 7 拍板**（2026-06-06）

- **决策**（7 项要点）：① 接入形态 = node-table config + 薄 driver + SKILL 加接口节，不重写方法论正文、不新建 v2 壳；② Agent 模型纠正——Agent 是带技能菜单的角色（BMAD persona）≠ skill，开发工程师 = 1 编排 + 6 业务 Agent；③ Agent 实例化按切片驱动 + 轻量 persona（否了"全套完整 persona"的 over-build 和"只编排+通用 subagent"的不兑现）；④ 驱动机制 = CLI 做编排 + hook 阶段3 当强制护栏，"自动档"是 policy 属性非 mechanism；⑤ gate 评审自评 vs 第三方分离——node 8/9b/12 自评归开发工程师本人，node 4/9a/10 第三方评审阶段1 deferred；⑥ node 9 拆 9a 代码质量评审 + 9b E2E 验收；⑦ 视觉改造非 TDD，走"前端/视觉验证支路"（build+机检+视觉diff+功能冒烟）。
- **状态**：已实施（Step main-43，kdev-core 76 测试 + coding-flow 8 测试绿）。

### Q-011
**阶段2 接入设计 —— 第二员工(需求架构师) + 记忆 scope 分离 + 员工集中 kdev-team**（2026-06-07）

- **决策**（8 项要点）：① sequencing = P-0 → P-C1 → P-A → P-B，地基先行；② P-C 按真实驱动力拆——P-C1 scope 分离(2 员工就咬→建) / P-C2 JSONL 操作层(token 痛才咬→defer) / P-C3 并发写锁(并行员工才咬→defer 阶段3)；③ scope-aware = opt-in 向后兼容，kdev-agents 框架仓自身记忆保 flat 不迁；④ 员工集中 `plugins/kdev-team/`（因 agent↔flow-skill 是参考非调用绑定，无需同插件）；⑤ 编排 agent 按 node-table 调度业务 agent（非"调 flow-skill 串联"）；⑥ ASCII canonical id + 中文 display 双轨命名；⑦ 验证走轻 dogfood；⑧ P-A = kdev-design-flow 接底座（复刻阶段1）。
- **状态**：已实施；回溯纠正了阶段1 personas/ 非标结构（P-0：persona→`kdev-team/agents/` 真 CC agent）。

### Q-012
**编排底座存储 feature-first 重设计**（2026-06-10）

- **背景**：评审 R1/R2/R3 真实代码 + superpowers plans 后发现"flow 当顶层把功能切碎、history 内嵌状态文件臃肿、slug 无 mint 规约"三个结构问题。
- **决策**：① 状态机目的口径分两半——控制态（卡节点+有界升级+断点续跑，小而热）vs 流水（事实留痕，长而冷）；② feature 当顶层（弃 `flows/<flow>/<slug>/`）——`features/<slug>/` 三摊 = `flow-state.json`（台账）+ `events.jsonl`（流水）+ `handoffs/`（产物）；③ 删独立 per-flow flow-state 文件，run-1/run-2 目录是过度设计；④ 文件名保留 `flow-state.json`（零迁移成本）；⑤ 并行模型 = feature 间分目录免锁并行，feature 内单棒约束；⑥ slug 生命周期 v0.1（立项才 mint，mint 规约标"待优化"）；⑦ 执行层选"多 flow 接力"，连续视图由台账层满足；⑧ R2/R3 纯函数不动，只重构 R1 存储层；⑨ 两套终止分工——R3 blocked（gate 评审超限转人工）vs R2 terminal_fail（非 gate 机械回流）。
- **状态**：已实施（P-Core-FF，kdev-core v0.2.0，126 测试绿，R2/R3 纯函数 git diff 全空验证了拍板⑧）。落地时细化了下游契约：events.jsonl 行 schema（去归一化自包含行）、`active{}` 生命周期推导替代布尔 stale-guard、run 完≠feature 完的两级 status。

### Q-013
**P-Core-FF 提前 —— kdev-core feature-first 存储 + events.jsonl 实现置于 P-A 之前**（2026-06-11）

- **背景**：核实发现 Q-012 只是设计完成（合稿 v1.0），代码未实现；同时 kdev-hud 的整个契约（feature-first 布局+events.jsonl）没有数据源可读。
- **决策**：把 kdev-core feature-first 存储迁移 + events.jsonl 实现从阶段3提前为独立前置块（P-Core-FF），置于 P-A 之前——否决"维持原序：P-A 建旧布局、HUD 等阶段3"。
- **理由**：一次落地解锁三件——① P-A 接最终契约不返工；② kdev-hud 数据源就绪，可越过阶段3 其余（评审专家/协作/CQO）早做；③ 阶段3 框架层提前消化一部分。
- **状态**：已实施（P-Core-FF 全部落地待办完成：路径翻转+`active{}`+history→events.jsonl+stories[]+slug origin+幂等迁移脚本，真实 dogfood 迁移 23 events 成功）。

### Q-014
**框架分发形态 —— CC 插件市场（含插件依赖）而非 OMC clone 式**（2026-06-11）

- **背景**：P-Core-FF 收尾时核实 kdev-core 是 kdev-team 的运行时依赖，但不在 marketplace，靠 `find ~ -name kdev-agents` 找自己——是 OMC 式"假设你 clone 了仓库"的逃生口，与 README 记的 CC marketplace 安装模型矛盾。
- **决策**：维持 CC 插件市场，用 CC 原生「插件依赖 + 一键 setup 脚本」拿到"一起装"的友好度（否决真走 OMC clone 式）；kdev-core 升为 marketplace 插件（`plugin.json` + 写进 `marketplace.json`）。
- **理由**：① 框架已是 CC marketplace，OMC 重运行时已被 Q-007 明确拒绝；② "带几个插件一起装"CC 原生就有先例（`setup-kdev-codegraph.sh` 用 `dependencies` 自动拉依赖）；③ OMC clone 式会丢 CC 原生 skill/hook/agent 激活、逼全有或全无、`find ~` 比声明依赖更脆。
- **状态**：部分已实施——kdev-core 已建 `plugin.json`(v0.2.0) 并写入 marketplace；`kdev-team` 加 `dependencies: kdev-core` + `setup-kdev-team.sh` + flow-driver 的 PYTHONPATH 改指向 cache 安装位，仍是 follow-up 未做。

### Q-018
**数字员工依赖声明 —— CC plugin.json dependencies 自动传递安装，声明不 bundle**（2026-06-13）

- **背景**：test-engineer 接入设计会话核查发现 `kdev-team/plugin.json` 声明零依赖，但其 agent 运行时要 call 多个 sibling plugin 的 skill（superpowers/gstack/kdev-secure-coding/spec-kit/frontend-design/kdev-test-*），现在能跑只因整个 marketplace 一起装。核实官方文档确认 CC `plugin.json` 支持 `dependencies` 数组 + 自动传递安装（装 A 自动装其依赖，enable/disable 联动）。
- **决策**：机制定调为"声明同 marketplace kdev-* 依赖，不 bundle/vendor"；把"装员工连带装全部用到的 skill"写进 roadmap 单列专项，test-engineer 本期暂不放（否决 bundle/vendor 进 kdev-team 会造成重复+版本漂移+双写维护）。
- **发现的必修前置**：marketplace 条目名（`kdev-test-points-v1`）≠ `plugin.json` 名（`kdev-test-points`），依赖解析按条目名键控，不对齐会导致 auto-install 静默失败。
- **状态**：待实施——defer 专项，宜与 Q-014 的"集群一键装"follow-up 合并。

---

## 五、编排路由器（CEO 总编排）

### Q 20260617-182851
**编排路由器（CEO/团队总编排）设计定调 + 5 项设计决策**（2026-06-17）

- **背景**：当前数字员工只能人敲 `/kdev-flow-driver <员工id>` 一次驱一个员工，跨员工生命周期（需求→开发→测试）靠人脑编排；用户要"1 个总的去编排，不靠人"，但明确是"LLM 在现有编排资产上路由选择"，不是从零写脚本。
- **总体取向**：`/kdev-team <高层目标>` 是**纯主会话 skill**（守"子 agent 不能再开子 agent"硬约束——总编排只能主会话跑），三段 `plan`（LLM 分类到命名模板）→`confirm`（一屏编排结论，人改）→`drive`（顺序链式调现有 flow-driver）。骨架取 P3「flow-config L1 即真相 + LLM 填空」，嫁接模板目录 + lint 校验器；否决 P2 自由 DAG（违背"路由现有资产非自写脚本" + 主会话顺序派单下并行是假象）。
- **5 项决策**：① 模板目录+校验器（非自由 DAG）；② loop 落点 = 后台驱动 + HUD 当前台；③ 评审开关 MVP 降级 review-mode 三档；④ 跨员工链 MVP 声明不可恢复；⑤ MVP 先 full-delivery 三段（需求→开发→测试）。
- **认下的两笔诚实债**：评审开关 per-gate 自动化引擎未建（MVP 靠手改 node-table）；跨员工链级进度只活主会话内存、无断点续跑。
- **状态**：设计 spec 已写，MVP plan（一模板跑通目标→分类→确认→三段接力）未开。

---

## 附：范围外但被本文多处引用的背景决策

- **Q-001**（Step 编号全局递增 vs 迭代内递增）——个人项目偏好，`promote_status: skipped`，未纳入本 ADR。
- **Q-002**（本项目跳过 Step 用户评分采集，只走模型自评）——本项目偏好不外推，`promote_status: skipped`，未纳入本 ADR；但它是 Q-015/Q-017"自评→他评"演进链的直接起点（用户原话"后面我不再评分，你来自评即可"），也是 `dataset-misalignment` 蒸馏切片自始死亡的原因。
