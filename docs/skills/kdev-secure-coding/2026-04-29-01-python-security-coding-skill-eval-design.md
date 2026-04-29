# python-security-coding skill 评测方案设计

- 文档类型：评测方案设计（eval design spec）
- 评测对象：`plugins/kdev-secure-coding/skills/python-security-coding/`（v0.1.0 首版）
- 评测日期：2026-04-29
- 报告产出：`docs/skills/kdev-secure-coding/eval-2026-04-29.md`（一次性，不进 CI）
- Fixture 落仓：`plugins/kdev-secure-coding/evals/fixtures/`（B/D 段，长期保留）

## 1. 目标 / Non-goals

**目标**：在 skill 首版上线后，定性 + 定量评估它在四个维度上的可用性，并产出可执行的改进清单。

四个维度：
1. **触发可靠性**（A）—— description 是否能在 0 上下文激活；激活后是否选对 reference
2. **漏洞召回率**（B）—— 已知调用 skill 时，对预埋漏洞的命中率
3. **完成清单实战**（C）—— Layer 2 的 8 项 gate 在真实业务代码工作流里能否真正拦住违规
4. **对抗 / 误报**（D）—— skill 是否会把安全代码误判为风险

**Non-goals**：
- 不评估 skill 的 token 成本 / 性能
- 不评估对非 Python 项目的健壮性（首版只支持 Python）
- 不搭建 CI 自动化 eval harness（kdev-memory 那种 `run-hook-selftest.sh` 形式）。fixture 入仓便于未来手动重跑，但本次不写驱动脚本。
- 不修改 skill 本身。本次只产出报告 + 改进建议清单；具体修改交后续迭代。

## 2. 测试矩阵总览

| 段 | 评估维度 | 执行方式 | 用例数 | Fixture 落仓 |
|---|---|---|---|---|
| A | 触发可靠性 | fresh subagent × 3（无 skill 提示） | 3 | 是 |
| B | 漏洞召回率 | fresh subagent × 8（明示用 skill） | 8 | 是 |
| C | 完成清单实战 | 主 session inline | 4 个业务场景 | 否 |
| D | 对抗 / 误报 | 主 session inline 自评 | 4 | 是 |

## 3. Fixture 设计

### 3.1 A 段 fixtures（`evals/fixtures/A-trigger/`）

每个 `.py` 文件不写注释提示是测试样本，模拟普通用户上传。

| 文件 | 类型 | 内容描述 | 期望 subagent 行为 |
|---|---|---|---|
| `a01-vulnerable.py` | 含明显漏洞 | Flask 接口 + `cursor.execute("... " + uid)` SQL 拼接 + `eval(user_input)` | **应**自动 invoke skill；应 Read `01-input-validation.md` |
| `a02-clean.py` | 干净代码 | 同等长度的纯业务 CRUD（参数化查询 + 类型校验） | 可不 invoke；若 invoke 也合理（保险） |
| `a03-borderline.py` | 边界 | `subprocess.run([...], shell=False)` + `yaml.safe_load(f)` | 关键边界；不应误判 invoke 后报警 |

### 3.2 B 段 fixtures（`evals/fixtures/B-recall/`）

每个文件头注释列出**预埋漏洞清单**（数量 + 类型），便于评分对照。文件命名按 8 个分类编号：

| 文件 | 主类别 | 预埋漏洞（每文件 1 个核心漏洞 + 可选 1-2 个相关） |
|---|---|---|
| `b01-input.py` | 3.1 输入验证 | `cursor.execute("SELECT * FROM u WHERE id=" + uid)` + `os.system("rm " + path)` |
| `b02-security.py` | 3.2 安全特性 | `hashlib.md5(password).hexdigest()` 存密码 + `random.random()` 生成 token |
| `b03-encapsulation.py` | 3.3 封装 | Flask `Access-Control-Allow-Origin: *` + 缺 CSP + `Set-Cookie` 无 Secure/HttpOnly |
| `b04-api-misuse.py` | 3.4 API 滥用 | `open(request.args["path"])` 路径未校验 + `os.chmod(f, 0o777)` |
| `b05-time-state.py` | 3.5 时间与状态 | `tempfile.mktemp()` + 多线程共享可变 dict 无锁 |
| `b06-error.py` | 3.6 错误处理 | `except Exception as e: return jsonify({"err": str(e)})` 暴露内部错误 |
| `b07-quality.py` | 3.7 代码质量 | `path.split('\\')` + 硬编码 `C:\\Users\\` 路径前缀 |
| `b08-environment.py` | 3.8 环境 | `app.run(debug=True)` + `ALLOWED_HOSTS = ["*"]` + `requirements.txt` 钉死 `Django==1.11` |

每个文件 30-60 行，足够形成完整可读的"伪业务代码"上下文，避免 subagent 因为代码片段太短而过度警觉。

### 3.3 D 段 fixtures（`evals/fixtures/D-adversarial/`）

每个文件头注释**明确写出 3 项**：(a) 这段代码是安全的；(b) 为什么是安全的（具体到上下文约束）；(c) skill 若把它判为风险即为误报。

| 文件 | 测试点 | "安全"理由（写入文件头） | 期望结果 |
|---|---|---|---|
| `d01-subprocess-safe.py` | `subprocess.run(["ls", path], shell=False)` 且 path 来自服务器内部白名单 dict | 参数列表形式 + shell=False + 输入来自硬编码 allowlist 而非用户输入 | 不应报警；至多提醒"若 path 改为用户输入则需重审" |
| `d02-yaml-safe-load.py` | `yaml.safe_load(f)` | `safe_load` 仅解析基础类型，不会执行任意构造器，是 yaml 库官方推荐的安全 API | 不应报警 |
| `d03-random-non-crypto.py` | `random.choice(["cat","dog","bird"])` 用于游戏角色 NPC 随机分配 | 用途为娱乐展示，非身份验证 / 非 token 生成 / 非加密种子；可预测性不构成安全问题 | 不应报警；至多提醒"确认非密码学场景" |
| `d04-md5-checksum.py` | `hashlib.md5(file_content).hexdigest()` 用于检测文件传输是否完整 | 用途为完整性校验（detect accidental corruption），非密码存储 / 非签名 / 非抗碰撞攻防场景 | 不应报警；至多提醒"确认非密码学场景" |

### 3.4 C 段场景（无 fixture，inline 演练）

| # | 场景 | 主 session 写哪段代码 | 触发 8 类中的哪些 |
|---|---|---|---|
| C1 | Flask 密码重置接口 | 收邮箱 → 生成 token → 发邮件 → 校验 token 重置 | 3.1 / 3.2 / 3.6 |
| C2 | 文件上传 + 缩略图 | `request.files['avatar']` → 校验 → 保存 → PIL 缩略图 | 3.1 / 3.4 / 3.5 |
| C3 | 第三方 webhook 接收 | `/webhook/payment` → HMAC 校验 → 记录 → 触发任务 | 3.1 / 3.2 / 3.3 / 3.6 |
| C4 | Django 上线前 settings + 部署 review | `settings.py` + `gunicorn.conf` + `requirements.txt` | 3.2 / 3.7 / 3.8 |

**8 类覆盖确认**：3.1✓✓✓ / 3.2✓✓✓ / 3.3✓ / 3.4✓ / 3.5✓ / 3.6✓✓ / 3.7✓ / 3.8✓ —— 全到。

## 4. 评测协议（按段）

### 4.1 A 段 — 触发可靠性

每个 fixture 派一个 fresh subagent（用 Agent 工具 `subagent_type: "general-purpose"`）：

```
Prompt 模板（不提 skill / 不提安全）:
"Please review this Python file. Report any concerns or improvements you'd
suggest. Code follows below:

<贴 fixture 全文>"
```

**判定**：
- 是否自动 invoke 了 `python-security-coding`？（看 subagent 输出里有无 skill 调用迹象）
- 若 invoke：Read 的 reference 文件是否对应 fixture 实际问题类型？
- 若未 invoke：subagent 自己用通用知识发现漏洞了吗？反衬 description 触发是否冗余还是必要。

### 4.2 B 段 — 漏洞召回率

每个 fixture 派 fresh subagent，**明示**调用 skill：

```
Prompt 模板:
"Use the python-security-coding skill (available in your environment) to
review the following file. List every security issue you find with the
category number (3.1 / 3.2 / ... / 3.8) and the recommended fix.

<贴 fixture 全文>"
```

**评分（每文件）**：
- 命中数 = 预埋漏洞清单中被报告出来的条数
- 漏报数 = 预埋 - 命中
- 误报数 = 报告了但 fixture 注释里未预埋的"问题"（需人工判断是否真为问题）
- 召回率 = 命中 / 预埋

**汇总**：8 类各一行，最后给一个加权平均召回率。

### 4.3 C 段 — 完成清单实战

每个场景由主 session inline 完成，输出 3 段进报告：
1. **Step 1 — 朴素实现**：模拟普通开发者写代码，不刻意防御，不主动想安全
2. **Step 2 — 走 Layer 2 完成前清单**：逐项核对 8 类 gate；命中即 Read 对应 reference 修正
3. **Step 3 — 评估**：(a) 清单是否真挡住了 Step 1 的违规？(b) 走完清单后还有什么漏？(c) gate 是否误挡了正确代码？

**判定**：每场景给一段 200 字以内的"工作流真实有效性"评语，标"通过 / 部分通过 / 未通过"。

### 4.4 D 段 — 对抗 / 误报

主 session inline 自评。每个 fixture 走两遍：
1. 按 SKILL.md 关键词映射表查出 skill 会建议 Read 哪个 reference
2. 假设按 reference 的规则判断 → skill 是否会报警？

**判定**：每个用例给"误报 / 不误报 / 边界提醒（合理）"。如出现误报，记到改进建议。

## 5. 报告结构

落仓位置：`docs/skills/kdev-secure-coding/eval-2026-04-29.md`

```
# python-security-coding skill 评测报告 (2026-04-29)

## TL;DR
- 总体结论（1 段）
- 最严重问题 Top 3

## A 触发可靠性
| Fixture | 自动 invoke? | reference 命中? | 备注 |

## B 漏洞召回率
| Fixture | 类别 | 预埋 | 命中 | 漏报 | 误报 | 召回率 |
- 每条简短分析（≤3 行）

## C 完成清单实战
### C1 ... ### C4
- 朴素实现代码片段
- 清单走查表
- 评估结论

## D 对抗 / 误报
| Fixture | 期望 | 实际 | 是否误报 |

## 改进建议
按严重度排序：
- P0 / P1 / P2，每条对应 SKILL.md 或 reference 的具体行号

## 附录
- A/1: 重跑步骤
- A/2: subagent 原始输出（折叠）
- A/3: fixture 完整路径列表
```

## 6. 文件落点

```
plugins/kdev-secure-coding/evals/             # 新建
├── README.md                                 # 重跑说明
└── fixtures/
    ├── A-trigger/   { a01,a02,a03 }.py
    ├── B-recall/    { b01..b08 }.py
    └── D-adversarial/ { d01..d04 }.py

docs/skills/kdev-secure-coding/
└── eval-2026-04-29.md                        # 本次报告
```

## 7. 通过 / 不通过判据

本次评测**不设硬性通过门槛**（首版评测，目的是"摸底 + 找问题"），但下列任一情况触发 P0 改进项：
- A 段：含明显漏洞的 `a01-vulnerable.py` 未触发 skill invoke
- B 段：任一类别召回率 < 50%
- C 段：任一场景 gate 漏过了 Step 1 的明显违规
- D 段：任一对抗用例产生了"应当不报警"的明确误报

## 8. 时间预算

| 阶段 | 预估 |
|---|---|
| 编写 15 个 fixture（A/3 + B/8 + D/4） | 30-40 min |
| A/B subagent 跑 11 次 | 10-15 min（并发） |
| C 4 个场景 inline 演练 | 30-40 min |
| D 自评 | 10 min |
| 报告撰写 | 20-30 min |
| **合计** | ~2-2.5 小时，单会话内完成 |

## 9. 已知风险

- **R1 subagent 上下文未必干净**：Agent 工具内部对 skill 列表的可见性会影响 A 段判定。规避：A 段 prompt 显式不要求 skill；如发现 subagent 因看到 skill 列表自动 invoke，需在报告中诚实记录该混淆因素。
- **R2 fixture 太短易让 subagent 警觉**：B 段每个 fixture ≥30 行业务代码上下文，避免"一眼看出是测试样本"。
- **R3 C 段评估者偏差**：主 session 已读完 SKILL.md，"朴素实现"难以真正模拟无知开发者。规避：Step 1 只按需求功能写代码，不主动启用任何安全机制；写完才走 Step 2。
- **R4 D 段判定主观**：误报 / 边界提醒之间界限模糊。规避：报告中对每个 D 用例写明 "为什么这是误报 / 为什么这是合理边界提醒"。
- **R5 subagent 是否能访问本地 skill 不确定**：Claude Code 派发的 `general-purpose` 子代理是否继承父会话已加载的 plugin skill，存在机制不确定性。若子代理看不到 `python-security-coding` skill，B 段 8 次调用全部失效。
  - **探针策略**：正式跑 B 段前，先派 1 个 probe subagent，prompt 仅为"列出你当前可用的 skills"。若清单含 `python-security-coding` → 走原方案。若不含 → 启用兜底。
  - **兜底方案**：把 SKILL.md 全文 + 8 个 reference 文件全文拼接为单一 system 段，作为 prompt 前缀注入子代理。等价于"手工模拟 skill 加载"，结果效力略弱（无关键词触发机制，仅评估 reference 内容质量），但仍能完成召回率测量。报告中需注明走的是原方案还是兜底方案。
  - A 段不受此风险影响：A 段恰恰要测"description trigger 是否生效"，子代理看不到 skill = 直接得出"trigger 0%命中"的结论，是有效结果而非失效结果。

## 10. 不做的事

- 不修改 skill 源文件
- 不动 `tests/verify-skill.py`（结构校验，与本次 eval 关注点正交）
- 不做 token 成本测量
- 不重新设计 SKILL.md 结构（即使发现问题，仅写改进建议）
