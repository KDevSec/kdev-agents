# 知识图谱集成方案 — Memory Level 1 借用 kdev-code-graph

> 日期：2026-05-30
> 状态：**提案草稿**，未拍板
> 关联：[2026-05-30-03-KDev记忆架构对齐分析与双轨提案.md](2026-05-30-03-KDev记忆架构对齐分析与双轨提案.md) §4.2 Memory Level 1

---

## 一、问题

Memory Level 1 知识图谱（来自 `01-design/2026-04-08-03-KDev融合架构设计.md §6.3`）的设计：

```json
{
  "id": "fact-20260408143022",
  "fact": "Use JWT + Refresh Token for authentication",
  "timestamp": "2026-04-08",
  "status": "active",
  "confidence": 0.95,
  "source": "user-confirmed"
}
```

这是 **project-fact-domain 知识图谱**——节点是项目决策、架构事实、用户偏好。

KDev 项目里已经有一个活跃的 KG plugin：**`plugins/kdev-code-graph/`**（Tasks 0-12 完成）。问题：能不能借用它实现 Memory Level 1？

---

## 二、kdev-code-graph 现状

| 维度 | 现状 |
|---|---|
| 底层引擎 | **Understand-Anything (UA)** —— Lum1104/Understand-Anything (13k star) |
| 上游胶水 | `plugins/kdev-code-graph/ingestor/` 调 UA build graph |
| 节点类型 | `file` / `function` / `class` / **`kdev:security_rule`** / **`document`** |
| 边类型 | 调用关系 + spec-link（doc ↔ code）+ security_rule ↔ code |
| 4 个 slash command | `/kdev-codegraph-build` / `trace` / `impact` / `doc-sync` |
| 核心定位 | **code-domain KG**：以代码实体为主节点，外挂 spec/security rule |

引用文档：

- [docs/skills/kdev-code-graph/README.md](../../skills/kdev-code-graph/README.md)
- [docs/skills/kdev-code-graph/2026-05-22-spec-link设计.md](../../skills/kdev-code-graph/2026-05-22-spec-link设计.md)

---

## 三、Memory Level 1 vs kdev-code-graph：重叠与分歧

| 维度 | 重叠 | 分歧 |
|---|---|---|
| 数据形态 | ✅ 都是 KG（节点 + 边）| - |
| 查询接口 | ✅ by-topic / by-relation | - |
| 存储引擎 | ✅ 都可用 UA 作底层 | - |
| **节点 schema** | - | ❌ code 节点（function / class）vs 决策节点（fact + lifecycle） |
| **生命周期** | - | ❌ code 节点 = 跟代码同步（删函数节点消失）/ 决策节点 = active / superseded |
| **是否绑定代码** | - | ❌ code 节点必须 / 决策节点可"自由漂浮"（"我们每周一开会"跟代码无关）|
| **生成方式** | - | ❌ code 节点 UA 自动抽取 / 决策节点用户/AI 显式写入 + 蒸馏 |

**结论**：场景不同，但底座技术可共用。

---

## 四、三方案对比

### 方案 A：完全独立

kdev-memory Level 1 自己写 KG 实现，跟 kdev-code-graph 完全平行。

| 维度 | 评估 |
|---|---|
| 优点 | 无耦合，节奏自主 |
| 缺点 | 重复造 UA 集成；失去 spec ↔ code 跨图追溯 |
| 工作量 | 中（重新写 UA bridge） |

### 方案 B：共用 UA 引擎，schema 独立（**短期推荐**）

两个 plugin 都用 UA 当 graph engine，各自定义 domain 节点和边：

```
              ┌──────────────────────────────┐
              │  Understand-Anything 引擎     │  ← 共用底座
              │  （graph build / query / viz）│
              └──────────────────────────────┘
                       ↑           ↑
        ┌──────────────┘           └──────────────┐
        │                                          │
┌───────────────────┐                  ┌────────────────────────┐
│ kdev-code-graph   │                  │ kdev-memory L1         │
│ - file/function   │                  │ - decision/fact         │
│ - class/import    │                  │ - constraint/preference │
│ - security_rule   │                  │ - active/superseded     │
└───────────────────┘                  └────────────────────────┘
```

### 方案 C：跨图链接（**长期目标**）

在方案 B 基础上，让两个图能互引：

```
memory:fact-20260408 "Use JWT for auth"
   │
   │ (kdev:implements 边)
   ▼
code:function "auth.verify_jwt"
```

kdev-code-graph 的 **spec-link 机制已经做了一半**——它把 `kdev:security_rule` 节点链到代码节点。把这个能力**泛化到所有 decision/fact 类型**，就是方案 C。

---

## 五、推荐路径

**短期（v0.x）：方案 B**

理由：

- kdev-code-graph 已在 Tasks 0-12 活跃，不要现在动它
- kdev-memory Level 1 还没建，正是 greenfield 设计时机
- 抽 ua-bridge 共用 lib 是小工作（~1-2 天），收益是两个 plugin 都不用各自重写 UA 集成

**长期（v1.x+）：方案 C**

升级触发信号：

- Memory Level 1 积累 50+ 决策，**且**用户开始问"这条 fact 在代码里有体现吗"
- 在此之前方案 B 完全够用

---

## 六、方案 B 实施步骤

### 6.1 抽取共用 lib

```
plugins/
├── kdev-shared/                  ← 新建
│   └── ua-bridge/
│       ├── client.py             ← UA REST client
│       ├── graph_builder.py      ← build / update / delete 节点
│       ├── graph_query.py        ← by-topic / by-id / by-relation
│       └── schema.py             ← 通用 Node / Edge 抽象
│
├── kdev-code-graph/              ← 现有
│   └── ingestor/
│       └── (改造：import kdev-shared.ua-bridge 替换内部胶水)
│
└── kdev-memory/                  ← 现有
    └── knowledge-graph/          ← 新增子模块
        ├── schema.py             ← 定义 decision / fact / constraint 节点
        ├── lifecycle.py          ← active / superseded / superseded_by 逻辑
        └── (依赖 kdev-shared.ua-bridge)
```

### 6.2 namespace 隔离

两 plugin 写入不同 namespace：

| Plugin | namespace 前缀 | 节点类型 |
|---|---|---|
| kdev-code-graph | `code:*` / `kdev:security_rule` / `kdev:document` | 代码实体 + spec |
| kdev-memory L1 | `memory:fact` / `memory:decision` / `memory:constraint` / `memory:preference` | 决策类事实 |

查询时各自隔离，互不污染。

### 6.3 命令模式复用（直接抄）

kdev-code-graph 的 4 个 slash command 模式很成熟，照抄改 domain：

| code-graph 命令 | memory L1 对应 | 含义 |
|---|---|---|
| `/kdev-codegraph-build` | `/kdev-memory-kg-build` | 从既有 markdown 抽决策成图 |
| `/kdev-codegraph-trace` | `/kdev-memory-kg-trace` | 按 topic / fact id 查 |
| `/kdev-codegraph-impact` | `/kdev-memory-kg-impact` | 这条 fact 被哪些决策依赖 / 影响哪些其他决策 |
| `/kdev-codegraph-doc-sync` | `/kdev-memory-kg-drift` | active fact 是否被新 fact 隐式 supersede |

### 6.4 数据来源（fact 怎么进入图）

| 来源 | 触发 | 实现 |
|---|---|---|
| **从决策日志.md 抽取** | `/kdev-memory-kg-build` 命令 | 解析 Q-NNN frontmatter + body，提取"决定 X = Y"句式 |
| **从踩坑日志.md 抽取** | 同上 | G-NNN 反向 fact：`fact: "不要用 X 因为 Y"` |
| **从用户对话直接落** | UserPromptSubmit hook 识别 fact 句式 + 一句话确认 | hook 自动起草 + 用户 yes/no |
| **从 staff-memory 评审 R-NNN 抽取** | 跨 plugin 查询 | 评审能力维度漏检升级成 fact（罕见，但有意义）|

---

## 七、方案 C 的升级路径（长期）

### 7.1 fact ID 稳定性约束

跨图链接的前提是 **fact ID 不变**。需要：

- fact ID 用时间戳 + 哈希（不复用，废弃用 status=deprecated 标记）
- code 节点 ID 用文件路径 + 函数 fully-qualified name（refactor 时通过 git history 追踪 ID 漂移）

### 7.2 跨图边定义

| 边类型 | 含义 | 例 |
|---|---|---|
| `kdev:implements` | fact 由 code 实现 | `memory:fact-jwt-auth` → `code:auth.verify_jwt()` |
| `kdev:contradicts` | code 跟 fact 不符（漂移检测）| `memory:fact-no-eval` → `code:utils.dangerous_exec` |
| `kdev:references` | code 提到 fact | `code:README.md` → `memory:fact-deploy-aws` |

### 7.3 查询能力

- "这条 fact 在代码里有体现吗" → 跟随 `kdev:implements` 边
- "这段代码违反了哪些 fact" → 跟随 `kdev:contradicts` 边
- "去年定的 fact 现在还有效吗" → 联合 active fact + code 实现的存在性

---

## 八、与 Memory Level 1 设计的对齐校验

5 层架构的 Memory Level 1 schema（`2026-04-08-03 §6.3`）vs 本方案：

| Level 1 字段 | 本方案对应 | 说明 |
|---|---|---|
| `id` | `memory:fact-<timestamp>` | namespace 前缀 |
| `fact` | 节点 attribute `value` | 决策内容 |
| `timestamp` | 节点 attribute `created_at` | 创建时间 |
| `status` | 节点 attribute `status` | active / superseded |
| `confidence` | 节点 attribute `confidence` | 0.0-1.0 |
| `source` | 节点 attribute `source` | user-confirmed / ai-extracted / staff-review |
| `superseded_by` | 边类型 `memory:superseded_by` | 跟另一条 fact 节点的边 |
| `superseded_at` | 边 attribute `at` | - |
| topic 分类 | 节点 label / topic tag | 对应 `topics/<topic>/` 目录组织 |

完全对齐。

---

## 九、未决问题

1. **kdev-shared/ 这个 monorepo 子模块怎么发布**？是 npm/PyPI 单独包还是 inline pull？
2. **UA 引擎是否就绪**？kdev-code-graph 已经在用，但 spec-link 设计文档显示 UA 有"节点元数据扩展"限制（详见 `docs/skills/kdev-code-graph/2026-05-22-spec-link设计.md`），fact 节点带 lifecycle 字段会不会撞到
3. **fact 抽取 prompt 怎么设计**？避免 hallucinate 出不存在的"决策"
4. **kdev-memory L1 跟现有 Q-NNN 决策日志的关系**？是 Q-NNN 升华成 fact，还是平行？
5. **如果只装 kdev-memory 不装 kdev-code-graph**，Level 1 还能不能用？（独立可装的约束）
   - 选项 A：依赖 kdev-shared，必装
   - 选项 B：kdev-memory 内置一个最简 UA client，没装 kdev-code-graph 也能跑

---

## 十、变更记录

| 日期 | 改动 |
|---|---|
| 2026-05-30 | v0.1 提案 |
