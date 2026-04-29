# python-security-coding skill 评测实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 design spec 跑完 A/B/C/D 四段评测，产出 fixture 入仓 + 一次性评测报告，给出按严重度排序的改进建议。

**Architecture:** 测试矩阵分四段：A/B 派 fresh subagent 跑（11 次），C/D 主 session inline 跑。所有 fixture 按 8 类企业安全规范分类编号，落到 `plugins/kdev-secure-coding/evals/fixtures/{A-trigger,B-recall,D-adversarial}/`。报告聚合所有数据后落到 `docs/skills/kdev-secure-coding/eval-2026-04-29.md`。

**Tech Stack:** Python 3 (fixtures 不实际执行，仅作为代码样本)、Claude Code Agent 工具（subagent 派发）、Markdown（报告）

**Spec 引用:** `docs/skills/kdev-secure-coding/2026-04-29-01-python-security-coding-skill-eval-design.md`

---

## File Structure

**新增（评测产物）：**

```
plugins/kdev-secure-coding/evals/
├── README.md                            # 重跑说明 + fixture 索引
└── fixtures/
    ├── A-trigger/
    │   ├── a01-vulnerable.py            # SQL 拼接 + eval()
    │   ├── a02-clean.py                 # 干净 CRUD
    │   └── a03-borderline.py            # subprocess shell=False + yaml.safe_load
    ├── B-recall/
    │   ├── b01-input.py                 # 3.1 SQL + os.system
    │   ├── b02-security.py              # 3.2 md5 密码 + random token
    │   ├── b03-encapsulation.py         # 3.3 CORS * + 缺 CSP + 弱 cookie
    │   ├── b04-api-misuse.py            # 3.4 路径未校验 + 0o777
    │   ├── b05-time-state.py            # 3.5 mktemp + race
    │   ├── b06-error.py                 # 3.6 暴露 traceback
    │   ├── b07-quality.py               # 3.7 硬编码路径分隔符
    │   └── b08-environment.py           # 3.8 DEBUG=True + 旧 Django
    └── D-adversarial/
        ├── d01-subprocess-safe.py       # shell=False + allowlist
        ├── d02-yaml-safe-load.py        # yaml.safe_load
        ├── d03-random-non-crypto.py     # random.choice 非密码场景
        └── d04-md5-checksum.py          # md5 完整性校验

docs/skills/kdev-secure-coding/
└── eval-2026-04-29.md                   # 一次性报告（最后产出）
```

**职责边界：**
- `evals/fixtures/` 永久落仓，未来重跑 / 回归用
- `evals/README.md` 说明每段如何手动重跑
- `eval-2026-04-29.md` 仅为本次报告，不进 fixtures
- 不修改 skill 本身（`plugins/kdev-secure-coding/skills/python-security-coding/`）

---

## Task 0: 建立 evals 目录骨架 + README

**Files:**
- Create: `plugins/kdev-secure-coding/evals/README.md`
- Create directories: `plugins/kdev-secure-coding/evals/fixtures/{A-trigger,B-recall,D-adversarial}/`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p plugins/kdev-secure-coding/evals/fixtures/A-trigger
mkdir -p plugins/kdev-secure-coding/evals/fixtures/B-recall
mkdir -p plugins/kdev-secure-coding/evals/fixtures/D-adversarial
```

Expected: 三个空目录创建成功

- [ ] **Step 2: 写 evals/README.md**

```markdown
# python-security-coding skill — Evaluation Fixtures

本目录存放评测 fixture，配套 design spec 见
`docs/skills/kdev-secure-coding/2026-04-29-01-python-security-coding-skill-eval-design.md`。

## 重跑步骤（手动）

### A 段（触发可靠性，3 用例）
派 3 个 fresh subagent，每个 prompt：
```
Please review this Python file. Report any concerns or improvements you'd
suggest. Code follows below:

<贴 fixtures/A-trigger/a0X-*.py 的全文>
```
判定：subagent 是否自动 invoke `python-security-coding` skill；invoke 后 Read 的 reference 是否对应实际问题。

### B 段（漏洞召回率，8 用例）
派 8 个 fresh subagent，每个 prompt：
```
Use the python-security-coding skill (available in your environment) to
review the following file. List every security issue you find with the
category number (3.1 / 3.2 / ... / 3.8) and the recommended fix.

<贴 fixtures/B-recall/b0X-*.py 的全文>
```
评分：每文件头注释列出预埋漏洞清单，对照 subagent 输出统计命中 / 漏报 / 误报 / 召回率。

### D 段（对抗 / 误报，4 用例）
人工评估：按 SKILL.md 关键词映射表查每个 fixture 的关键词命中，模拟对应 reference 的判定，看是否会误报。

### C 段（完成清单实战）
无 fixture。在主会话内对 4 个真实业务场景按"朴素实现 → 走 8 项 gate → 评估"三步法演练。

## Fixture 索引

见同级 `fixtures/` 子目录，文件名编号与 design spec 第 3 节表格一一对应。
```

- [ ] **Step 3: 验证文件就位**

```bash
ls plugins/kdev-secure-coding/evals/
ls plugins/kdev-secure-coding/evals/fixtures/
```

Expected: `README.md` + 3 个子目录

- [ ] **Step 4: 提交**

```bash
git add plugins/kdev-secure-coding/evals/
git -c user.name="<localname>-AI" -c user.email="<localemail>" commit -m "$(cat <<'EOF'
chore(kdev-secure-coding): scaffold evals/ directory for skill evaluation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

注意：本仓的 kdev-commit hook 强制 AI commit 必须用 `-c user.name=<name>-AI` + `-c user.email=<本地 git 邮箱>`。执行前先 `git config user.name` / `git config user.email` 取本地真实值。

---

## Task 1: R5 风险探针 — 验证 subagent 是否能访问 skill

**目的：** 在写完所有 fixture 之前先确认 subagent 能否看到 `python-security-coding` skill。如果不能，B 段需要切到兜底方案（提前知道有助于设计 prompt）。

- [ ] **Step 1: 派 probe subagent**

调用 Agent 工具，参数：
- `subagent_type`: `general-purpose`
- `description`: "Probe available skills"
- `prompt`:
  ```
  List all skills currently available to you. Output exact skill names only,
  one per line. Do not invoke any skill — just list what you see.
  ```

- [ ] **Step 2: 解析 probe 输出**

判断：
- 若输出含 `python-security-coding` → 走原方案（B 段 prompt 直接 reference skill 名）
- 若不含 → 启用兜底：B 段 prompt 必须前置注入 SKILL.md + 8 个 reference 全文

- [ ] **Step 3: 把结果写入 working notes**

不入仓，仅本会话内记录。在 todo list 加一条："B 段使用方案=原方案 / 兜底方案"，作为后续任务的输入。

---

## Task 2: 编写 A 段 fixtures（3 个）

**Files:**
- Create: `plugins/kdev-secure-coding/evals/fixtures/A-trigger/a01-vulnerable.py`
- Create: `plugins/kdev-secure-coding/evals/fixtures/A-trigger/a02-clean.py`
- Create: `plugins/kdev-secure-coding/evals/fixtures/A-trigger/a03-borderline.py`

**重要：A 段 fixture 不写"这是测试样本"的提示注释**，以免子代理识别出测试上下文导致行为偏差。文件头只写正常业务模块的 docstring。

- [ ] **Step 1: 写 a01-vulnerable.py（含明显漏洞，~40 行）**

要求：Flask 单文件应用，必须包含至少：
- 一处 `cursor.execute(f"... {user_input} ...")` 字符串拼接 SQL
- 一处 `eval(...)` 或 `exec(...)` 接受外部数据
- 文件外壳要像真实业务代码：有路由、有 db 连接、有 logger，~40 行

示例骨架（编写时按此扩展到 40 行）：

```python
"""User profile microservice — internal service, port 8001."""
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "users.db"

def _conn():
    return sqlite3.connect(DB_PATH)

@app.route("/api/users/<uid>")
def get_user(uid):
    conn = _conn()
    cursor = conn.cursor()
    # 漏洞 1: SQL 拼接
    cursor.execute(f"SELECT name, email FROM users WHERE id = {uid}")
    row = cursor.fetchone()
    return jsonify({"name": row[0], "email": row[1]})

@app.route("/api/calc", methods=["POST"])
def calc():
    expr = request.json.get("expr", "")
    # 漏洞 2: eval 用户输入
    return jsonify({"result": eval(expr)})

if __name__ == "__main__":
    app.run(port=8001)
```

- [ ] **Step 2: 写 a02-clean.py（干净代码，~40 行）**

要求：同等长度的 Flask 单文件应用，但全部使用安全 API：
- 参数化查询（`?` 占位符）
- 类型校验（如 `int(uid)` 包 try/except）
- 不出现任何 8 类敏感关键词

示例骨架：

```python
"""Pet inventory service — internal service, port 8002."""
import sqlite3
from flask import Flask, request, jsonify, abort

app = Flask(__name__)
DB_PATH = "pets.db"

def _conn():
    return sqlite3.connect(DB_PATH)

@app.route("/api/pets/<int:pid>")
def get_pet(pid):
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("SELECT name, species FROM pets WHERE id = ?", (pid,))
    row = cursor.fetchone()
    if not row:
        abort(404)
    return jsonify({"name": row[0], "species": row[1]})

@app.route("/api/pets", methods=["POST"])
def create_pet():
    data = request.get_json() or {}
    name = data.get("name")
    species = data.get("species")
    if not isinstance(name, str) or not isinstance(species, str):
        abort(400)
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pets (name, species) VALUES (?, ?)", (name, species))
    conn.commit()
    return jsonify({"ok": True}), 201

if __name__ == "__main__":
    app.run(port=8002)
```

- [ ] **Step 3: 写 a03-borderline.py（边界用例，~40 行）**

要求：同等长度，**两处必须出现的边界 API**：
- `subprocess.run([...], shell=False)` — 不应被视为漏洞
- `yaml.safe_load(f)` — 不应被视为漏洞

示例骨架：

```python
"""Config loader + system info reporter — internal admin tool."""
import subprocess
import yaml
from pathlib import Path
from flask import Flask, jsonify

app = Flask(__name__)
CONFIG_PATH = Path(__file__).parent / "config.yaml"

def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

@app.route("/api/diskinfo")
def diskinfo():
    # 安全：参数列表 + shell=False
    result = subprocess.run(
        ["df", "-h", "/var/log"],
        capture_output=True, text=True, shell=False, timeout=5,
    )
    return jsonify({"output": result.stdout})

@app.route("/api/version")
def version():
    cfg = load_config()
    return jsonify({"version": cfg.get("version", "unknown")})

if __name__ == "__main__":
    app.run(port=8003)
```

- [ ] **Step 4: 验证 fixture 就位**

```bash
ls plugins/kdev-secure-coding/evals/fixtures/A-trigger/
wc -l plugins/kdev-secure-coding/evals/fixtures/A-trigger/*.py
```

Expected: 3 个文件，每个 30-50 行

- [ ] **Step 5: 提交**

```bash
git add plugins/kdev-secure-coding/evals/fixtures/A-trigger/
git -c user.name="<localname>-AI" -c user.email="<localemail>" commit -m "$(cat <<'EOF'
test(kdev-secure-coding): add A-trigger fixtures (3 files)

3 Flask single-file apps for evaluating description-trigger reliability:
- a01-vulnerable.py: SQL injection + eval()
- a02-clean.py: parameterized queries + type validation
- a03-borderline.py: subprocess shell=False + yaml.safe_load

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 跑 A 段评测（3 个 fresh subagent）

**目的：** 测 description trigger 是否能在 0 上下文激活；激活后是否选对 reference。

- [ ] **Step 1: 并发派 3 个 fresh subagent**

在同一条消息里调用 3 次 Agent 工具（subagent_type: `general-purpose`）。每个 subagent 的 prompt 完全相同模板：

```
Please review the following Python file. Report any concerns, bugs,
or improvements you'd suggest. Be thorough.

```python
<贴 fixtures/A-trigger/a0X-*.py 的全文>
```
```

**关键：prompt 不能提及 "security"、"skill"、"python-security-coding"** —— 否则 A 段失去意义。

- [ ] **Step 2: 收集 3 段输出**

每个 subagent 返回后，记录：
- (a) 输出全文（折叠保存到报告附录）
- (b) 是否调用了 `python-security-coding` skill？（看输出里有无 skill 调用迹象、关键词如 "Layer 1"、"reference 01-input-validation" 等）
- (c) 报告了哪些问题？

- [ ] **Step 3: 评判**

填充下表（先放进 working notes，最后并入报告）：

| Fixture | 自动 invoke skill? | Reference 命中? | 报告了真实漏洞? | 备注 |
|---|---|---|---|---|
| a01-vulnerable | Y/N | (若 Y) 命中/未命中 | (列出 SQL 拼接、eval 是否被发现) | |
| a02-clean | Y/N | N/A | 是否有误报 | |
| a03-borderline | Y/N | (若 Y) 命中/未命中 | 是否误报 subprocess/yaml | |

- [ ] **Step 4: 不提交**（A 段输出仅进报告附录，不入仓）

---

## Task 4: 编写 B 段 fixtures（8 个）

**Files:** 8 × `plugins/kdev-secure-coding/evals/fixtures/B-recall/b0N-*.py`

**重要约定：每个 B fixture 文件头必须有 docstring 列出预埋漏洞清单**，格式：

```python
"""<业务描述>

PREDEFINED VULNERABILITIES (for evaluator reference, NOT for subagent):
- 3.X.Y <漏洞描述> — line NN
- 3.X.Y <漏洞描述> — line NN
"""
```

注：subagent 拿到的 prompt 里也会包含 docstring，但 docstring 不暗示规则、只列出"作者已知会埋的漏洞"。subagent 仍需用 skill 自主发现。如担心污染评估，备选方案是把漏洞清单从 docstring 移到外部 `b01-input.expected.txt` 同名 sidecar 文件，subagent prompt 里只贴 `.py` 不贴 sidecar。

**默认采用 sidecar 方案**（更干净），即每个 fixture 配一个同名 `.expected.txt` 列出预埋漏洞，`.py` 文件本身不留任何评测元信息。

每个 fixture ≥30 行业务上下文。

- [ ] **Step 1: b01-input.py（3.1 输入验证）**

预埋（写入 `b01-input.expected.txt`）：
1. 3.1.4 SQL 注入: `cursor.execute(f"SELECT * FROM users WHERE id = {uid}")` 字符串拼接
2. 3.1.1 命令注入: `os.system(f"rm {filename}")` 拼接 shell 命令

`.py` 内容骨架（扩展到 30+ 行）：

```python
"""User admin endpoints."""
import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/api/users/<uid>")
def get_user(uid):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute(f"SELECT name, email FROM users WHERE id = {uid}")  # 漏洞
    row = cur.fetchone()
    return jsonify({"name": row[0], "email": row[1]})

@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    filename = request.json.get("filename")
    os.system(f"rm /tmp/uploads/{filename}")  # 漏洞
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run()
```

补充扩展到 30+ 行（加一个无害的辅助函数 / 一个干净的 endpoint），让代码看起来像真实模块。

- [ ] **Step 2: b02-security.py（3.2 安全特性）**

预埋（写入 sidecar）：
1. 3.2.4 弱哈希: `hashlib.md5(password.encode()).hexdigest()` 存储密码
2. 3.2.6 弱随机: `random.random()` 用于生成 reset token
3. 3.2.8 Cookie 缺 Secure: `response.set_cookie("session", token)` 未设 Secure/HttpOnly/SameSite

骨架（扩展到 30+ 行）：

```python
"""Auth service."""
import hashlib
import random
from flask import Flask, request, make_response, jsonify

app = Flask(__name__)

@app.route("/api/register", methods=["POST"])
def register():
    pw = request.json["password"]
    pw_hash = hashlib.md5(pw.encode()).hexdigest()  # 漏洞 1
    # ... 假装存 db
    return jsonify({"ok": True})

@app.route("/api/reset/start", methods=["POST"])
def reset_start():
    token = str(random.random())  # 漏洞 2
    return jsonify({"token": token})

@app.route("/api/login", methods=["POST"])
def login():
    pw_hash = hashlib.md5(request.json["password"].encode()).hexdigest()
    # ... 比对，假设通过
    resp = make_response(jsonify({"ok": True}))
    resp.set_cookie("session", "abc123")  # 漏洞 3
    return resp

if __name__ == "__main__":
    app.run()
```

- [ ] **Step 3: b03-encapsulation.py（3.3 封装）**

预埋：
1. 3.3.5 CORS 全开: `Access-Control-Allow-Origin: *` + `Allow-Credentials: true`
2. 3.3.4 缺 CSP: 响应未设 `Content-Security-Policy`
3. 3.3.1/3.2.8 X-Frame-Options + X-XSS-Protection 缺失

骨架（≥30 行 Flask after_request）：

```python
"""Public API."""
from flask import Flask, jsonify

app = Flask(__name__)

@app.after_request
def add_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"   # 漏洞 1
    resp.headers["Access-Control-Allow-Credentials"] = "true"  # 漏洞 1 加重
    # 漏洞 2/3: 故意不设 CSP / X-Frame / X-XSS
    return resp

@app.route("/api/data")
def data():
    return jsonify({"items": [1, 2, 3]})

# ... 补充几个 endpoint 凑到 30 行
```

- [ ] **Step 4: b04-api-misuse.py（3.4 API 滥用）**

预埋：
1. 3.4.1 路径未校验: `open(request.args["path"])` 直接打开用户路径
2. 3.4.2 权限过宽: `os.chmod(filepath, 0o777)`

骨架：

```python
"""File serving microservice."""
import os
from flask import Flask, request, send_file

app = Flask(__name__)

@app.route("/api/file")
def serve_file():
    path = request.args["path"]
    return send_file(open(path, "rb"))  # 漏洞 1

@app.route("/api/file/upload", methods=["POST"])
def upload():
    f = request.files["file"]
    target = f"/tmp/{f.filename}"
    f.save(target)
    os.chmod(target, 0o777)  # 漏洞 2
    return {"ok": True}

# ... 凑到 30 行
```

- [ ] **Step 5: b05-time-state.py（3.5 时间与状态）**

预埋：
1. 3.5.1 不安全临时文件: `tempfile.mktemp()` race condition
2. 3.5.2 共享可变状态无锁: 全局 dict 多 worker 写

骨架：

```python
"""Background processor."""
import tempfile
from flask import Flask, request

app = Flask(__name__)
JOBS = {}  # 全局 dict，多 worker 写无锁 — 漏洞 2

@app.route("/api/job", methods=["POST"])
def submit_job():
    job_id = request.json["id"]
    tmp_path = tempfile.mktemp(suffix=".tmp")  # 漏洞 1
    with open(tmp_path, "w") as f:
        f.write(request.json["data"])
    JOBS[job_id] = tmp_path
    return {"ok": True}

# ... 凑到 30 行
```

- [ ] **Step 6: b06-error.py（3.6 错误处理）**

预埋：
1. 3.6.1 异常暴露: `except Exception as e: return jsonify({"err": str(e)})` 把 traceback / 内部信息回传给客户端
2. 3.6.2 日志缺失: 关键操作无日志

骨架：

```python
"""Account API."""
import sqlite3
import traceback
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/api/account/<aid>")
def get_account(aid):
    try:
        conn = sqlite3.connect("accounts.db")
        cur = conn.cursor()
        cur.execute("SELECT name FROM accounts WHERE id = ?", (aid,))
        return jsonify({"name": cur.fetchone()[0]})
    except Exception as e:
        return jsonify({
            "err": str(e),
            "traceback": traceback.format_exc(),  # 漏洞 1
        }), 500

# ... 凑到 30 行（加一个删除接口，"成功" / "失败" 分支均无日志，构成漏洞 2）
```

- [ ] **Step 7: b07-quality.py（3.7 代码质量）**

预埋：
1. 3.7.1 硬编码路径分隔符: `path.split('\\')`
2. 3.7.1 硬编码 Windows 路径前缀: `C:\\Users\\app\\data`

骨架：

```python
"""Log analyzer (originally written on Windows)."""
from flask import Flask, jsonify

app = Flask(__name__)

LOG_BASE = "C:\\Users\\app\\data\\logs"  # 漏洞 2

def parse_path(p):
    parts = p.split("\\")  # 漏洞 1
    return parts[-1]

@app.route("/api/logs/<name>")
def show_log(name):
    full = LOG_BASE + "\\" + name  # 漏洞 1 强化
    return jsonify({"path": parse_path(full)})

# ... 凑到 30 行
```

- [ ] **Step 8: b08-environment.py（3.8 环境）**

预埋（多文件）：
1. 3.8.1 调试模式: `app.run(debug=True)`
2. 3.8.2 部署: `ALLOWED_HOSTS = ["*"]`（Django settings 风格）
3. 3.8.3 旧依赖: 同目录 `requirements.txt` 钉死 `Django==1.11`

实际仍单文件（注释里写 requirements.txt 内容；或附 sidecar `b08-environment.requirements.txt`）：

骨架：

```python
"""Production server entry point.

Deployment hint: see sidecar b08-environment.requirements.txt
"""
from flask import Flask

app = Flask(__name__)

# 模拟 Django 风格 settings
ALLOWED_HOSTS = ["*"]            # 漏洞 2
DEBUG = True                     # 漏洞 1
SECRET_KEY = "hardcoded-key-1"   # 漏洞额外

@app.route("/")
def index():
    return "Hello"

if __name__ == "__main__":
    app.run(debug=True)          # 漏洞 1 强化

# ... 凑到 30 行
```

并写 sidecar `b08-environment.requirements.txt`:
```
Django==1.11
Flask==0.12
requests==2.6.0
```
（漏洞 3：钉死过时版本）

- [ ] **Step 9: 写所有 sidecar `.expected.txt`**

每个 fixture 一个同名 `.expected.txt`，列出预埋漏洞清单，格式：

```
# b01-input.py — 预埋漏洞清单
1. 3.1.4 SQL 拼接 — line NN — get_user 函数 cursor.execute f-string
2. 3.1.1 命令注入 — line NN — delete_file 函数 os.system f-string
```

8 个 sidecar 文件。

- [ ] **Step 10: 验证**

```bash
ls plugins/kdev-secure-coding/evals/fixtures/B-recall/
wc -l plugins/kdev-secure-coding/evals/fixtures/B-recall/*.py
```

Expected: 8 个 .py + 8 个 .expected.txt + 1 个 b08-*.requirements.txt = 17 个文件，每个 .py ≥30 行

- [ ] **Step 11: 提交**

```bash
git add plugins/kdev-secure-coding/evals/fixtures/B-recall/
git -c user.name="<localname>-AI" -c user.email="<localemail>" commit -m "$(cat <<'EOF'
test(kdev-secure-coding): add B-recall fixtures (8 files + sidecars)

8 vulnerable Flask fixtures, one per security category 3.1-3.8.
Each .py paired with .expected.txt sidecar listing predefined vulns
(kept out of fixture body to avoid biasing subagent evaluation).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: 跑 B 段评测（8 个 fresh subagent）

**目的：** 测在已知调用 skill 时，对预埋漏洞的命中率。

- [ ] **Step 1: 选用 prompt 模板（取决于 Task 1 探针结果）**

**原方案**（subagent 能看到 skill）：
```
Use the python-security-coding skill (available in your environment) to
review the following Python file. List every security issue you find,
with the category number (3.1 / 3.2 / ... / 3.8) and the recommended fix.

```python
<贴 fixtures/B-recall/b0N-*.py 全文>
```
```

**兜底方案**（subagent 看不到 skill）：在原 prompt 前注入：
```
You are reviewing Python code against the following 8-category security
standard. Below is the full SKILL.md and reference text:

<贴 plugins/kdev-secure-coding/skills/python-security-coding/SKILL.md 全文>

<贴 references/01-input-validation.md 全文>
... (8 个 reference 全文)

Now review the following file ...
```

- [ ] **Step 2: 并发派 8 个 fresh subagent**

同一条消息里 8 次 Agent 调用，subagent_type 均为 `general-purpose`。

- [ ] **Step 3: 收集 8 段输出**

每个 subagent 返回后：
- 把输出与 sidecar `.expected.txt` 对照
- 计算命中数 / 漏报数 / 误报数 / 召回率

填充表（暂存 working notes）：

| Fixture | 类别 | 预埋数 | 命中数 | 漏报数 | 误报数 | 召回率 |
|---|---|---|---|---|---|---|
| b01-input | 3.1 | 2 | | | | % |
| ... | ... | | | | | |
| b08-env | 3.8 | 3 | | | | % |
| **加权平均** | | | | | | **%** |

- [ ] **Step 4: 不提交**（B 段输出进报告附录）

---

## Task 6: 编写 D 段 fixtures（4 个）

**Files:** 4 × `plugins/kdev-secure-coding/evals/fixtures/D-adversarial/d0N-*.py`

每个 fixture **文件头 docstring 必须明确写出 3 项**：(a) 这段代码安全；(b) 为什么安全；(c) skill 若报警即为误报。

- [ ] **Step 1: d01-subprocess-safe.py**

```python
"""Internal disk usage reporter — admin only.

SAFETY ASSERTION:
(a) This code is safe.
(b) Reasons:
    - subprocess.run uses argument list (not shell string)
    - shell=False is explicit
    - Path argument is selected from a hardcoded server-side allowlist dict,
      NOT from user input. The HTTP query string only chooses a key.
(c) If python-security-coding skill flags this as a command injection or
    shell-injection risk, that is a false positive.
"""
import subprocess
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

ALLOWED_PATHS = {
    "logs": "/var/log",
    "tmp": "/var/tmp",
    "data": "/var/lib/myapp",
}

@app.route("/admin/diskusage")
def diskusage():
    key = request.args.get("path", "logs")
    path = ALLOWED_PATHS.get(key)
    if path is None:
        abort(400)
    result = subprocess.run(
        ["du", "-sh", path],
        capture_output=True, text=True, shell=False, timeout=5,
    )
    return jsonify({"output": result.stdout.strip()})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9001)
```

- [ ] **Step 2: d02-yaml-safe-load.py**

```python
"""App config loader.

SAFETY ASSERTION:
(a) This code is safe.
(b) Reasons:
    - Uses yaml.safe_load, NOT yaml.load.
    - safe_load only constructs basic Python types (dict, list, str, int,
      float, bool, None). It cannot instantiate arbitrary Python objects
      via !!python/object tags. This is the official recommended API.
(c) If python-security-coding skill flags this as unsafe deserialization,
    that is a false positive.
"""
import yaml
from pathlib import Path
from flask import Flask, jsonify

app = Flask(__name__)
CONFIG_FILE = Path(__file__).parent / "config.yaml"

def load_config():
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)

@app.route("/api/config")
def get_config():
    return jsonify(load_config())

if __name__ == "__main__":
    app.run()
```

- [ ] **Step 3: d03-random-non-crypto.py**

```python
"""NPC randomizer for game backend — non-security feature.

SAFETY ASSERTION:
(a) This code is safe.
(b) Reasons:
    - random.choice is used purely to select a cosmetic NPC species.
    - Not used for: authentication tokens, session ids, password salts,
      OTP codes, encryption seeds, or any security-relevant decision.
    - Predictability of the choice has zero security impact (worst case:
      a player observes a pattern in NPCs they meet).
(c) If python-security-coding skill flags this as weak random / PRNG
    misuse, that is a false positive in this context.
"""
import random
from flask import Flask, jsonify

app = Flask(__name__)

NPC_SPECIES = ["cat", "dog", "bird", "fish", "rabbit"]

@app.route("/api/game/spawn-npc")
def spawn_npc():
    species = random.choice(NPC_SPECIES)
    return jsonify({"species": species})

if __name__ == "__main__":
    app.run()
```

- [ ] **Step 4: d04-md5-checksum.py**

```python
"""File integrity checker — detects accidental corruption during transfer.

SAFETY ASSERTION:
(a) This code is safe.
(b) Reasons:
    - hashlib.md5 is used as a checksum to detect ACCIDENTAL corruption
      (network/disk errors), NOT for:
        * password storage,
        * digital signatures,
        * adversarial collision resistance,
        * any cryptographic guarantee.
    - MD5 is sufficient for accidental-error detection. This usage matches
      common practice (e.g., Linux package manager checksums).
(c) If python-security-coding skill flags this as weak hash, that is a
    false positive in this context. (A legitimate edge-case nudge to
    "consider sha256 if context might evolve" is acceptable, not flagged.)
"""
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/api/file/checksum", methods=["POST"])
def checksum():
    f = request.files["file"]
    content = f.read()
    md5 = hashlib.md5(content).hexdigest()
    return jsonify({"md5": md5, "size": len(content)})

if __name__ == "__main__":
    app.run()
```

- [ ] **Step 5: 验证**

```bash
ls plugins/kdev-secure-coding/evals/fixtures/D-adversarial/
```

Expected: 4 个 .py 文件

- [ ] **Step 6: 提交**

```bash
git add plugins/kdev-secure-coding/evals/fixtures/D-adversarial/
git -c user.name="<localname>-AI" -c user.email="<localemail>" commit -m "$(cat <<'EOF'
test(kdev-secure-coding): add D-adversarial fixtures (4 files)

4 safe-by-design Python files testing for false positives:
- d01: subprocess shell=False with allowlist
- d02: yaml.safe_load
- d03: random.choice for non-security NPC selection
- d04: md5 for accidental-corruption checksum

Each file's docstring asserts safety with specific contextual reasoning.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: D 段 inline 自评

**目的：** 主 session 按 SKILL.md 关键词映射表查每个 fixture，模拟对应 reference 的判定，看是否会误报。

- [ ] **Step 1: 对每个 D fixture 走两遍**

对每个 d01–d04，记录：
1. **触发的 SKILL.md 关键词**：查 SKILL.md 第 37–63 行的关键词映射表，列出该 fixture 会让 skill 建议 Read 哪些 reference
2. **按 reference 规则判断**：Read 对应的 `references/0X-*.md`，看其规则是否会把这段代码判为风险
3. **结论**：误报 / 不误报 / 边界提醒（合理）

- [ ] **Step 2: 填表（暂存 working notes，最后并入报告）**

| Fixture | 触发关键词 | Read 的 reference | 实际判定 | 结论 |
|---|---|---|---|---|
| d01-subprocess-safe | `subprocess` `shell=` | references/01-input-validation.md 命令段 | (按规则该段是否报警) | 误报/不误报 |
| d02-yaml-safe-load | `yaml.load` | references/01-input-validation.md 反序列化段 | | |
| d03-random-non-crypto | `random.choice` | references/02-security-features.md 随机数段 | | |
| d04-md5-checksum | `hashlib` `md5` | references/02-security-features.md 加密/哈希段 | | |

- [ ] **Step 3: 不提交**（D 段评估结果进报告）

---

## Task 8: C1 — Flask 密码重置接口实战

**目的：** 主 session 模拟普通开发者写代码 → 走 8 项 gate → 评估 gate 实效。

- [ ] **Step 1: 朴素实现（Step 1 of 三步法）**

主 session 不打开 SKILL.md、不主动想安全。按需求"实现一个密码重置接口"直接写：
- POST `/auth/reset/start` 接收邮箱 → 生成 token → 发邮件
- POST `/auth/reset/confirm` 接收 token + 新密码 → 验证 → 更新

不要：参数化查询（除非默认习惯就是）/ 不要：bcrypt（除非默认习惯就是）/ 不要：Secret token / 不要：错误处理细化。

把这段代码记到报告里 "C1 Step 1 朴素实现"。

- [ ] **Step 2: 走 Layer 2 完成前清单（Step 2 of 三步法）**

打开 SKILL.md 第 73–80 行 8 项 gate，逐项核对 Step 1 代码：
- 3.1 输入验证 ✓/✗ → 命中则 Read `references/01-*.md` 修
- 3.2 安全特性 ✓/✗
- ...
- 3.8 环境 ✓/✗

记录每项 gate：是否命中本次改动；命中后改了哪些代码；最终状态。

把"修正后代码 + 走查表"写入报告 "C1 Step 2 完成清单"。

- [ ] **Step 3: 评估（Step 3 of 三步法）**

写一段 ≤200 字的"工作流真实有效性"评语，回答：
- (a) 清单是否真挡住了 Step 1 的违规？哪些挡住了，哪些没挡住？
- (b) 走完清单后还有什么漏？（你作为安全工程师的判断）
- (c) gate 是否误挡了正确代码？
- 标"通过 / 部分通过 / 未通过"

写入报告 "C1 评估"。

- [ ] **Step 4: 不提交**（C 段过程性产物，不入仓）

---

## Task 9: C2 — 文件上传 + 缩略图生成实战

同 Task 8 三步法，场景换为：
- POST `/api/avatar` 接收 `request.files["avatar"]` → 校验 → 保存 → PIL 生成缩略图

- [ ] **Step 1: 朴素实现** — 写代码进报告 "C2 Step 1"
- [ ] **Step 2: 走 8 项 gate** — 修正 + 走查表进报告 "C2 Step 2"
- [ ] **Step 3: 评估** — 评语进报告 "C2 评估"

---

## Task 10: C3 — 第三方 webhook 接收实战

同 Task 8 三步法，场景换为：
- POST `/webhook/payment` → HMAC 校验 → 记录入库 → 触发 celery 任务

- [ ] **Step 1: 朴素实现** — 写代码进报告 "C3 Step 1"
- [ ] **Step 2: 走 8 项 gate** — 修正 + 走查表进报告 "C3 Step 2"
- [ ] **Step 3: 评估** — 评语进报告 "C3 评估"

---

## Task 11: C4 — Django 上线前 settings + 部署 review

同 Task 8 三步法，场景换为：
- 你在 review 一个即将上生产的 Django 项目的 `settings.py` + `gunicorn.conf` + `requirements.txt`

- [ ] **Step 1: 朴素 review** — 直接看代码，列出你眼里的问题，进报告 "C4 Step 1"
- [ ] **Step 2: 走 8 项 gate** — 系统化复查 + 走查表进报告 "C4 Step 2"
- [ ] **Step 3: 评估** — 评语进报告 "C4 评估"

---

## Task 12: 编写最终报告

**Files:** Create `docs/skills/kdev-secure-coding/eval-2026-04-29.md`

**注意：A/B/C/D 各段的原始数据已在 Task 3/5/7/8-11 暂存为 working notes，本任务只做汇总 + TL;DR + 改进建议清单。**

- [ ] **Step 1: 写报告骨架**

按 design spec 第 5 节模板：

```markdown
# python-security-coding skill 评测报告 (2026-04-29)

## TL;DR

总体结论（≤150 字）：……

最严重问题 Top 3：
1. ……（P0）
2. ……（P1）
3. ……

## A 触发可靠性

| Fixture | 自动 invoke skill? | Reference 命中? | 报告了真实漏洞? | 备注 |
| ... |

简短分析（≤100 字 / fixture）：……

## B 漏洞召回率

| Fixture | 类别 | 预埋数 | 命中数 | 漏报数 | 误报数 | 召回率 |
| ... |
| **加权平均** | | | | | | **%** |

简短分析（漏报集中在哪类？误报模式？）：……

## C 完成清单实战

### C1 Flask 密码重置接口
- Step 1 朴素实现：（代码块）
- Step 2 走查后修正：（代码块 + 走查表）
- 评估：通过/部分/未通过 + ≤200 字评语

### C2 / C3 / C4 同结构

## D 对抗 / 误报

| Fixture | 触发关键词 | Read 的 reference | 实际判定 | 结论 |
| ... |

## 改进建议

按严重度排序：

### P0（首版即必须修复）
- [描述问题] → 改 SKILL.md 第 NN 行 / references/0X-*.md 第 NN 行：……

### P1
- ……

### P2
- ……

## 附录

### A.1 重跑步骤
见 `plugins/kdev-secure-coding/evals/README.md`

### A.2 Subagent 原始输出（折叠）

<details><summary>A 段 3 个 subagent 输出</summary>

#### A1 fixture: a01-vulnerable.py
```
<原始输出>
```

#### A2 / A3 ...

</details>

<details><summary>B 段 8 个 subagent 输出</summary>

#### B1 fixture: b01-input.py
```
<原始输出>
```

...

</details>

### A.3 Fixture 完整路径列表

- A 段：`plugins/kdev-secure-coding/evals/fixtures/A-trigger/{a01,a02,a03}-*.py`
- B 段：`plugins/kdev-secure-coding/evals/fixtures/B-recall/{b01-b08}-*.py` + sidecar `.expected.txt`
- D 段：`plugins/kdev-secure-coding/evals/fixtures/D-adversarial/{d01-d04}-*.py`
```

- [ ] **Step 2: 把 working notes 数据填入对应章节**

A 段表格 + 简短分析，B 段表格 + 简短分析，C 段 4 个场景 × 3 步，D 段表格。

- [ ] **Step 3: 写 TL;DR**

总体结论：定性 1-2 句 + Top 3 问题。Top 3 问题按 design spec 第 7 节"P0 触发条件"判断。

- [ ] **Step 4: 写改进建议清单**

按严重度排序，每条对应到具体文件 + 行号。例如：
- P0：B 段 3.X 类召回率 < 50% → SKILL.md 第 NN 行关键词映射表缺 `XXX` 关键词；建议加入。
- P1：D 段 d0X 误报 → references/0X-*.md 第 NN 行规则过严，建议补充"非密码学场景例外"。

- [ ] **Step 5: 把 subagent 原始输出贴入附录 A.2**

折叠 `<details>`，A 段 3 个 + B 段 8 个，原文不删。

- [ ] **Step 6: 提交**

```bash
git add docs/skills/kdev-secure-coding/eval-2026-04-29.md
git -c user.name="<localname>-AI" -c user.email="<localemail>" commit -m "$(cat <<'EOF'
docs(kdev-secure-coding): add v0.1.0 skill evaluation report

Evaluates python-security-coding v0.1.0 across 4 dimensions:
- A: trigger reliability (3 fresh subagents)
- B: vulnerability recall (8 fresh subagents)
- C: completion gate effectiveness (4 inline scenarios)
- D: false-positive resistance (4 adversarial fixtures)

Findings include prioritized improvement backlog. Spec:
docs/skills/kdev-secure-coding/2026-04-29-01-python-security-coding-skill-eval-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: 收尾确认

- [ ] **Step 1: 检查所有产物就位**

```bash
ls plugins/kdev-secure-coding/evals/
ls plugins/kdev-secure-coding/evals/fixtures/A-trigger/
ls plugins/kdev-secure-coding/evals/fixtures/B-recall/
ls plugins/kdev-secure-coding/evals/fixtures/D-adversarial/
ls docs/skills/kdev-secure-coding/eval-2026-04-29.md
```

Expected:
- `evals/README.md` 存在
- A-trigger: 3 个 .py
- B-recall: 8 个 .py + 8 个 .expected.txt + 1 个 .requirements.txt
- D-adversarial: 4 个 .py
- `eval-2026-04-29.md` 存在

- [ ] **Step 2: 检查 git log**

```bash
git log --oneline -10
```

Expected: 至少 4 个 commit（Task 0 / Task 2 / Task 4 / Task 6 / Task 12 各一）；每条 commit 作者形如 `<localname>-AI`。

- [ ] **Step 3: 向用户汇报**

按下述模板：
```
评测完成。

- Fixture: 15 个文件已落 `plugins/kdev-secure-coding/evals/fixtures/`
- 报告: `docs/skills/kdev-secure-coding/eval-2026-04-29.md`
- 主要发现 (Top 3):
  1. ……
  2. ……
  3. ……
- 改进建议: P0 N 条 / P1 N 条 / P2 N 条 (见报告"改进建议"章节)

是否需要：(a) 把改进建议转成下一轮 skill 修订计划 / (b) 推到远端 / (c) 其他?
```

不要主动 push（kdev-commit 的 confirm-push hook 也会拦）。

---

## Self-Review

完成后我自检：

**1. Spec 覆盖**：
- ✓ A 段（spec §2 + §3.1 + §4.1）→ Task 2/3
- ✓ B 段（spec §3.2 + §4.2）→ Task 4/5
- ✓ C 段（spec §3.4 + §4.3）→ Task 8-11
- ✓ D 段（spec §3.3 + §4.4）→ Task 6/7
- ✓ R5 探针（spec §9）→ Task 1
- ✓ 报告结构（spec §5）→ Task 12
- ✓ 文件落点（spec §6）→ File Structure 段
- ✓ 通过判据（spec §7）→ Task 12 Step 4 P0 判断
- ✓ Non-goals（spec §1）：未触碰 skill 源、未改 verify-skill.py、未做 token 测量、未重构 SKILL.md → 全部不在任何 Task 内

**2. Placeholder 扫描**：
- 未见 "TBD / TODO / 后续填" 类
- Task 8-11 (C 段) 三步法没复写完整代码 —— 因为这是"主 session 实时按场景写"的 inline 任务，预先写死代码反而扭曲评估。已说明三步法每步要做什么、产出贴到报告哪一节。
- Task 4 fixture 给了示例骨架（≥30 行的具体起点）+ 沙袋扩展提示，避免编写者卡壳。

**3. 类型 / 命名一致性**：
- "fixture / .expected.txt sidecar" 命名贯穿全文一致
- "C 段 / 完成前清单 / Layer 2 gate" 三个等价表达均用，但每次出现都附 spec § 引用
- subagent 调用：A/B 段均强调 `general-purpose` + fresh subagent + 并发派发（同消息多次 Agent 调用）
- 提交 author 字段：每个 commit 块都用占位 `<localname>-AI` / `<localemail>` 提示读者执行前 `git config` 取真实值（CLAUDE.md 强制要求）

发现并修：无（所有项 review 后通过）。
