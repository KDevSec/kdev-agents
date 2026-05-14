# zentao-integration

禅道（ZenTao）bug 拉取 + 状态回写 reference。**0 依赖**——仅靠 curl + jq，不写 Python wrapper。

## 适配的禅道版本

| 维度 | 推荐 | 备注 |
|------|------|------|
| 版本 | **开源版 22.x / 旗舰版 / 企业版 22.x+** | REST API v1 在 18.x 引入，22.x 稳定 |
| 已实测 | 开源版 22.1（IP 部署）| 本 reference 主要面向该组合 |
| 部署方式 | IP / 域名均支持 | IP 部署常装到 `/zentao/` 子路径 |
| 协议 | HTTP（IP 部署常见） / HTTPS（域名部署推荐）| **HTTP 部署有 token 在传输中暴露风险**，详见 §6 |

## 认证方式

REST API v1 支持两种认证。**开源版 22.1 实测：UI 入口经常找不到 PAT 选项**，所以本 reference 把 **session-auth 作为主路径**，PAT 作为可选优化：

| 认证 | 工作方式 | 何时用 |
|------|----------|--------|
| **session-auth**（主路径） | 用账号密码调 `/api.php/v1/tokens` 换 session token，**24h 自动失效**，过期重换 | 开源版 22.1 默认走这条；UI 找不到 PAT 时强制走这条 |
| **PAT**（可选优化） | 用户在禅道 UI 生成长期 token，PUT `Token: <PAT>` 头 | 找得到 PAT 入口、对长期 token 没顾虑 |

### 主路径 · session-auth 配置

```bash
# .kdev/zentao.env

# 禅道部署 URL（不含尾斜杠）
# ⚠️ 开源版 22.1 IP/域名部署实测：外部访问 nginx rewrite 后**不带 /zentao 后缀**
#    即便管理员告诉你"禅道装在 /zentao 路径"，nginx 转发后从外部看就是根路径
#    踩坑现象：带 /zentao 时端点 302 重定向到登录页（path 不存在被 framework 兜底）
ZENTAO_API_URL=https://your-zentao-host    # 例：https://101.35.217.78（不要写 /zentao）

# 自签证书 → curl 跳过验证（HTTPS 内网 / 公网部署常见）
# 如果是有效 CA 签发的证书，删掉此行或设为 false
ZENTAO_INSECURE_TLS=true

# 认证模式
ZENTAO_AUTH_MODE=session

# 账号密码（用于换 session token）
ZENTAO_ACCOUNT=your-account
ZENTAO_PASSWORD=your-password

# session token 缓存路径（skill 第一次跑后写入，24h 内复用，过期自动重换）
ZENTAO_SESSION_CACHE=.kdev/.zentao-session
ZENTAO_DEFAULT_BUILD=trunk
```

**换 session token 的 curl**（skill 自动跑，开发者不用记）：

```bash
# curl_opts 按 ZENTAO_INSECURE_TLS 自动决定加不加 -k
CURL_OPTS=""
[[ "$ZENTAO_INSECURE_TLS" == "true" ]] && CURL_OPTS="-k"

curl -sS $CURL_OPTS -X POST \
  -H "Content-Type: application/json" \
  -d "{\"account\":\"$ZENTAO_ACCOUNT\",\"password\":\"$ZENTAO_PASSWORD\"}" \
  "$ZENTAO_API_URL/api.php/v1/tokens"

# 返回 HTTP 201（Created）+ JSON：
# {
#   "token": "32 字符 hex 字符串"
# }
# ⚠️ 开源版 22.1 实测：返回 token 但**不**返回 expire 字段（与某些 Pro 版文档不同）
# skill 用 mtime + 23h 作为缓存有效期判据，过期遇 401 自动重换
```

skill 把 `.token` 写到 `ZENTAO_SESSION_CACHE`，后续 24h 内复用：

```bash
# 用 session token 调其他端点（与 PAT 用法相同）
curl -s -H "Token: $(cat $ZENTAO_SESSION_CACHE)" \
  "$ZENTAO_API_URL/api.php/v1/bugs/<bug-id>"

# token 过期会返回 401，skill 自动重新换 session token 并重试一次
```

### 可选路径 · PAT 配置

如果你在禅道 UI 找到了 PAT 入口（位置见 SKILL.md 触发文档），切换为：

```bash
# .kdev/zentao.env
ZENTAO_API_URL=http://192.168.x.x/zentao
ZENTAO_AUTH_MODE=pat
ZENTAO_API_TOKEN=your-long-lived-pat
ZENTAO_DEFAULT_BUILD=trunk
```

skill 检测到 `ZENTAO_AUTH_MODE=pat` → 直接用 `Token: $ZENTAO_API_TOKEN` 头，不调换 session 接口。

### 强制要求（两种模式都适用）

`.kdev/zentao.env` 和 `.kdev/.zentao-session` **必须**进 `.gitignore`：

```gitignore
# .gitignore
.kdev/*.env
.kdev/.zentao-session
```

skill 启动时检查：如 `.kdev/zentao.env` 或 session cache 存在但未 gitignore → 警告"敏感凭证未被忽略"并停步。

## §0 启动时探测（必跑）

第一次配完 `.kdev/zentao.env` 后，**先跑探测脚本验证 URL + 认证都对**，再进 bug 拉取流程：

```bash
# 加载配置
set -a; source .kdev/zentao.env; set +a

# 探测 1: URL 路径前缀对不对（开源版 IP 部署常见踩坑）
echo "=== 探测 API 路径前缀 ==="
PROBE_URL="$ZENTAO_API_URL/api.php/v1/version"
echo "试探：$PROBE_URL"
curl -s -o /tmp/zentao-probe.json -w "HTTP %{http_code}\n" "$PROBE_URL"
cat /tmp/zentao-probe.json | jq '.' 2>/dev/null || cat /tmp/zentao-probe.json

# 期望：HTTP 200 + JSON 含 version 字段
# 如 404：URL 路径前缀错。换 ZENTAO_API_URL 试：
#   - 去掉 /zentao → http://<IP>
#   - 加 /zentao → http://<IP>/zentao
#   - 加 /zentaopms → http://<IP>/zentaopms（老版本目录名）

# 探测 2A: session-auth 换 token（主路径）
if [[ "$ZENTAO_AUTH_MODE" == "session" ]]; then
  echo "=== 探测 session-auth 换 token ==="
  curl -s -o /tmp/zentao-token.json -w "HTTP %{http_code}\n" \
    -X POST -H "Content-Type: application/json" \
    -d "{\"account\":\"$ZENTAO_ACCOUNT\",\"password\":\"$ZENTAO_PASSWORD\"}" \
    "$ZENTAO_API_URL/api.php/v1/tokens"
  TOKEN=$(jq -r '.token' /tmp/zentao-token.json 2>/dev/null)
  EXPIRE=$(jq -r '.expire' /tmp/zentao-token.json 2>/dev/null)
  
  if [[ "$TOKEN" != "null" && -n "$TOKEN" ]]; then
    echo "✓ session token 换取成功，到期：$EXPIRE"
    echo "$TOKEN" > "$ZENTAO_SESSION_CACHE"
    chmod 600 "$ZENTAO_SESSION_CACHE"
  else
    echo "✗ 换取失败，response:"
    cat /tmp/zentao-token.json
    # 常见原因：账号密码错；账号被禁用；URL 路径前缀错
    exit 1
  fi
fi

# 探测 2B: PAT 直用（可选路径）
if [[ "$ZENTAO_AUTH_MODE" == "pat" ]]; then
  TOKEN="$ZENTAO_API_TOKEN"
fi

# 探测 3: 用 token 调一个无副作用端点验证生效
echo "=== 探测 token 是否生效 ==="
CURL_OPTS=""
[[ "$ZENTAO_INSECURE_TLS" == "true" ]] && CURL_OPTS="-k"
curl -sS $CURL_OPTS -o /tmp/zentao-me.json -w "HTTP %{http_code}\n" \
  -H "Token: $TOKEN" \
  "$ZENTAO_API_URL/api.php/v1/user"

# ⚠️ 开源版 22.1 实测：返回字段嵌套在 .profile 下，**不是顶层**
# 字段路径：.profile.account / .profile.realname / .profile.email / .profile.last
jq '.profile.account, .profile.realname' /tmp/zentao-me.json 2>/dev/null

# 期望：HTTP 200 + 返回当前 token 对应的 user account / realname
# 如 401：session 过期或 PAT 无效 → 重新换 session 或重新生成 PAT
# 如 200 但 account 不是你的 → token 串了
# 如 200 但 .profile 为 null → 检查 jq 路径，22.x 之前的版本字段在顶层
```

skill 在跑 §1 拉 bug 前**应当**先跑 §0 探测；探测失败立即停下让用户修配置，**不**假装走 direct 模式。

### session token 自动续期

skill 调任何端点前先检查 `$ZENTAO_SESSION_CACHE`：

1. 文件存在 + mtime < 23h 前 → 直接用缓存 token
2. 文件不存在或 stale → 跑探测 2A 重新换，写入缓存
3. 调端点遇 401 → 缓存被禅道侧 invalidate 了 → 跑探测 2A 重换，重试 1 次

这套逻辑 skill 自动处理，用户不需要手工管 session 寿命。

## API 版本回退（22.x 不支持的端点 fallback）

22.1 开源版的 REST API v1 覆盖了 bug CRUD 主路径，但**少数 endpoint 仍走 web 表单接口**（如部分批量操作、附件上传）。本 reference 用到的 4 个 endpoint（GET bug / POST resolve / POST comment / GET user）在 22.1 开源版**已实测**可用。

如未来命中不支持端点，**fallback 模板**（web 表单接口）：

```bash
# REST：POST /api.php/v1/bugs/<id>/resolve
# fallback：POST /bug-resolve-<id>.json（form-urlencoded）
curl -s -X POST \
  -H "Cookie: zentaosid=$ZENTAO_SESSION_ID" \
  --data-urlencode "resolution=fixed" \
  --data-urlencode "resolvedBuild=trunk" \
  --data-urlencode "comment=<comment>" \
  "$ZENTAO_API_URL/bug-resolve-<bug-id>.json"
# 注意：web 表单接口走 session 鉴权，不能用 PAT。需先调登录接口换 session ID
```

## §1 拉取 bug 详情（用于 Intake 步骤 1）

```bash
ZENTAO_BUG_ID=12345

curl -s \
  -H "Token: $(cat $ZENTAO_SESSION_CACHE 2>/dev/null || echo $ZENTAO_API_TOKEN)" \
  "$ZENTAO_API_URL/api.php/v1/bugs/$ZENTAO_BUG_ID" \
  | jq '.'
```

返回 JSON 关键字段（**开源版 22.1 实测**）：

```json
{
  "id": 12345,
  "product": 1,
  "module": 5,
  "severity": 2,                  // 1=致命, 2=严重, 3=一般, 4=轻微
  "pri": 2,                       // ⚠️ 字段名是 "pri" 不是 "priority"（22.x 内外字段命名不一致）
  "type": "codeerror",
  "status": "active",             // active, resolved, closed
  "title": "登录后点击订单按钮无反应",
  "steps": "<p>1. ...</p>",       // HTML，需清洗（见下）；22.x 实测 steps 内可含 <b> <br> 等用户自定义结构
  "openedBy": { "id": 12, "account": "qa01", "realname": "张三", "avatar": "" },
  "openedDate": "2026-05-10T14:23:11Z",   // ISO 8601 with Z（22.x 是这种格式）
  "assignedTo": { "id": ..., "account": "dev01", "realname": "李四", "avatar": "" },
  "resolution": "",
  "resolvedBy": "",
  "resolvedDate": "",
  "productName": "产品名",
  "moduleTitle": "模块路径",
  // ...更多字段：actions / branch / browser / case / caseVersion / closedBy /
  //              confirmed / deadline / found / hardware / keywords / mailto /
  //              moduleTitle / preAndNext / project / repo / story / storyTitle 等
}
```

**字段命名陷阱速查**（22.x 开源版）：

| 想拿的语义 | 错误字段名 | 正确字段名 |
|-----------|-----------|-----------|
| 优先级 | `priority` | `pri` |
| 模块名 | `moduleName` | `moduleTitle` |
| 产品名 | `productName` ✓（这个对） | — |
| 报告人 | `.openedBy`（顶层）| `.openedBy.account` 或 `.openedBy.realname` |

**HTML 清洗**（steps 字段常含 `<p>` `<br>` `<img>`）：

```bash
# steps 字段转纯文本（保留换行）
echo "$STEPS_HTML" \
  | sed -e 's|<br[^>]*>|\n|g' -e 's|</p>|\n|g' -e 's|<[^>]*>||g' \
  | sed 's/&nbsp;/ /g; s/&amp;/\&/g; s/&lt;/</g; s/&gt;/>/g; s/&quot;/"/g'
```

**字段映射到 proposal.md Bug Context**：

| 禅道 JSON 字段 | proposal.md 位置 | 备注 |
|---------------|------------------|------|
| `.title` | Bug Context § Symptom | 直接拷 |
| `.steps`（清洗后） | Bug Context § Steps_to_Reproduce | HTML→纯文本，分行 |
| `.openedDate` | Bug Context § Environment 表格"报告时间"行 | ISO 8601 with Z |
| `.openedBy.realname`（fallback `.account`） | Bug Context § Environment 表格"报告人"行 | 是嵌套对象 |
| `.severity` | Gate-A 严重度初判 | 1→P0, 2→P1, 3→P1, 4→P2 |
| `.pri` | Bug Context § Environment "优先级"行 | ⚠️ 不是 `priority` |
| `.product` + `.productName` | proposal.md § Capabilities "Modified Capabilities" | |
| `.module` + `.moduleTitle` | proposal.md § Capabilities | moduleTitle 是模块路径，比 module ID 更可读 |
| `.id` | proposal.md frontmatter `zentao_bug_id` | |

## §2 禅道源 proposal.md 顶部 frontmatter

OpenSpec 模式：

```yaml
---
bug_source: zentao
zentao_bug_id: 12345
zentao_url: https://zentao.example.com/bug-view-12345.html
zentao_severity: 2
zentao_priority: 2
zentao_opened_by: qa01
zentao_opened_date: 2026-05-10
---
```

直接源：

```yaml
---
bug_source: direct
---
```

## §3 修复完成后回写禅道状态（步骤 8.1）

**Active → Resolved**（**不**直接到 Closed，让 QA 走关单）：

```bash
COMMIT_SHA=$(git log -1 --format=%H)
ARTIFACT_PATH="openspec/changes/$BUG_ID/"   # 或 docs/bugfix/$BUG_ID/

# 三段交付摘要（详细模板见 delivery-summary.md）
ROOT_CAUSE_PARA="<根因分析 1-3 句：哪行代码 + 哪个条件 + 为什么 trigger>"
IMPACT_PARA="<影响范围：受影响用户/角色 + 数据/路径/功能 + 严重度/时间窗口>"
FIX_PARA="<修复方案：改了什么文件/行号 + 为什么这么改 + 回归测试 cover 什么>"

COMMENT=$(cat <<EOF
【根因分析】
$ROOT_CAUSE_PARA

【影响范围】
$IMPACT_PARA

【修复方案】
$FIX_PARA

---
Commit: $COMMIT_SHA
产物: $ARTIFACT_PATH
EOF
)

# JSON-escape comment
COMMENT_JSON=$(jq -nR --arg c "$COMMENT" '$c')

CURL_OPTS=""
[[ "$ZENTAO_INSECURE_TLS" == "true" ]] && CURL_OPTS="-k"

curl -sS $CURL_OPTS -X POST \
  -H "Token: $(cat $ZENTAO_SESSION_CACHE 2>/dev/null || echo $ZENTAO_API_TOKEN)" \
  -H "Content-Type: application/json" \
  -d "{
    \"resolution\": \"fixed\",
    \"resolvedBuild\": \"$ZENTAO_DEFAULT_BUILD\",
    \"comment\": $COMMENT_JSON
  }" \
  "$ZENTAO_API_URL/api.php/v1/bugs/$ZENTAO_BUG_ID/resolve" \
  | tee /tmp/zentao-resolve-response.json
```

**comment 格式**：固定 **【根因分析】/【影响范围】/【修复方案】** 三段中文方括号段头 + 段间空行，末尾用 `---` 分隔追加 `Commit:` + `产物:` 元数据行。这套格式跨**禅道 comment / 会话报告 / 产物文档 / commit message** 共用，详细规范见 [delivery-summary.md](delivery-summary.md)。

**响应字段**：成功返回 `{ "id": 12345, "status": "resolved", "resolvedDate": "..." }`；失败返回 `{ "error": "...", "code": "..." }`。

**可能的失败码**：
- `401`：token 无效或过期 → 让用户重新生成 PAT
- `403`：用户无该 bug 权限（如非 assignedTo）→ 让用户在禅道内手动 reassign 或人工改
- `400 status_not_transferable`：当前状态非 active（如已 resolved / closed）→ 警告但不报错（可能已被人工处理）
- `5xx`：禅道服务端问题 → 重试 1 次，失败后输出手动指引

**resolution 字段合法值**（禅道默认）：
- `fixed` — 已修复（最常用）
- `bydesign` — 设计如此
- `duplicate` — 重复 bug
- `notrepro` — 无法重现
- `willnotfix` — 不予修复
- `postponed` — 延期处理

bugfix skill 默认用 `fixed`。其他情况手动改。

## §4 禅道源 commit message 增强

`kdev-commit` 步骤 7.2 的 commit message 在禅道源时**额外追加** `Zentao: #<id>` 行：

```
fix: <Symptom 一句话> (#<bug-id>)

Root cause: <一句话>
Regression test: <test 文件>
Reviewers: AI (PASS), multi-agent (PASS), human (N/A)

Refs: openspec/changes/<bug-id>/
Zentao: #12345
```

禅道有 git 集成时，会根据 commit message 中的 `#12345` 自动关联，省一道手工。

## §5 失败兜底脚本

curl 失败时输出给用户的"手动改状态"指引模板：

```
⚠️ 禅道状态自动回写失败
   ─ HTTP 状态: <code>
   ─ 错误信息: <body>

请手动操作：
   1. 浏览器打开：<ZENTAO_API_URL>/bug-view-<bug-id>.html
   2. 点"解决"按钮
   3. resolution 选：fixed
   4. resolvedBuild 填：<build name，默认 trunk>
   5. 备注粘贴下面这段（保留段头【】方括号，禅道纯文本渲染会保留）：
      ─────────────────────
      【根因分析】
      <根因分析 1-3 句>

      【影响范围】
      <影响范围：用户/角色 + 数据/路径 + 严重度/时间窗口>

      【修复方案】
      <修复方案：文件/行号 + 为什么 + 回归测试 cover>

      ---
      Commit: <SHA>
      产物: <path>
      ─────────────────────
   6. 点保存
```

bugfix skill **不**因为禅道回写失败就阻塞流程——代码已经 commit，产物已经齐全，只是 bug-tracker 状态需要人工补一道。

## §6 跟禅道集成的安全提示

### 凭证管理

**所有模式通用**：

- **永远不要**把 `ZENTAO_API_TOKEN` / `ZENTAO_PASSWORD` / session token 写进 commit / 截图 / 公开 PR
- `.kdev/zentao.env` 和 `.kdev/.zentao-session` 必须在 `.gitignore`，skill 启动时校验
- subagent 评审（步骤 6.2）的 prompt 里**不要**透传任何凭证——subagent 不需要直接调禅道 API
- 多人协作仓库：每人用自己的账号，**不**共享单个 service account
- `.kdev/.zentao-session` 权限设 `chmod 600`（owner-only read）

**session-auth 特有风险**（账号密码方式）：

- `ZENTAO_ACCOUNT` + `ZENTAO_PASSWORD` 一旦泄露 = 攻击者拥有你**所有**禅道权限（不仅 API），比 PAT 更危险
- 缓解：禅道账号开启**双因素认证**后，account/password 仅能换 API token，不能登录 web UI（视禅道版本支持情况）
- 缓解：用 session-auth 时考虑用一个**只读 service account**（如 `qa-bot`），不要用个人主账号
- session token 缓存有 24h 寿命，单次泄露窗口比永久 PAT 短

**PAT 特有风险**（如果走可选路径）：

- PAT 寿命长（默认 30-90 天），泄露窗口长
- 缓解：缩短过期时间、限制 PAT 来源 IP、定期轮换

### HTTP 部署的传输安全

**禅道开源版 IP 部署（典型 v22.1 场景）通常用 HTTP，不是 HTTPS**。这意味着：

- 每次 API 调用，`Token: <你的 PAT>` 头**以明文形式**走内网
- 同子网下抓包（如恶意员工、被入侵的内网设备）能拿到 token
- token 拿到 = 攻击者拥有你的禅道全部 bug / 项目 / 个人信息访问权

**缓解方案**（按代价从低到高）：

1. **最小化**：PAT 只授必要权限（22.x 支持权限粒度），过期时间设短（30 天）
2. **限制**：禅道管理员限制 PAT 来源 IP（如仅允许办公网段）
3. **升级**：让 IT 给禅道部署 HTTPS（自签证书也比 HTTP 强；公司有 PKI 用公司 CA）
4. **隔离**：bugfix skill 仅在公司内网工作机上跑，**不**在公共网络或 VPN over WiFi 场景调

skill 启动时如检测到 `ZENTAO_API_URL` 以 `http://` 开头（不是 `https://`），**输出一行警告**并继续：

```
⚠️ ZENTAO_API_URL 为 HTTP 协议，token 在内网以明文传输。
   建议：1) 缩短 PAT 过期时间；2) 推 IT 上 HTTPS；3) 限制 PAT 来源 IP。
```

警告**不阻塞流程**——开源版 IP 部署的常见现实，让用户知情但不强制中断。

### 失败时不外传敏感信息

- curl 失败时输出错误码 + 模糊 body（**不**贴完整 response，可能含 server-side token / 内部 path）
- subagent prompt 里出现的禅道 URL **不**含 query string（query string 偶尔含 token）
