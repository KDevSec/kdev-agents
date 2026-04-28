# Python Security Coding Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a user-level `python-security-coding` skill that auto-engages on Python backend projects, providing 8-category security rules from the company standard with completion-gate self-check.

**Architecture:** Skill installed at `~/.claude/skills/python-security-coding/`. SKILL.md acts as index with description-driven trigger (mode A), self-bootstrap that writes a CLAUDE.md anchor on first activation in a Python project (mode C), Layer-1 keyword→reference map for reactive lookup, and Layer-2 completion checklist for pre-finish gate. Eight reference files, one per docx category (3.1–3.8), each preserving rule text + canonical code examples verbatim.

**Tech Stack:** Markdown (skill format); Python 3 with `unzip` + `xml.etree.ElementTree` for docx text extraction; no runtime dependencies beyond standard library.

**Spec:** [/home/sec/skills/docs/superpowers/specs/2026-04-28-python-security-coding-skill-design.md](../specs/2026-04-28-python-security-coding-skill-design.md)

---

## Context the Engineer Needs

- **Source document**: `/home/sec/skills/Python安全编码规范.docx` — Chinese-language company regulation, 8 main categories numbered 3.1 to 3.8, each containing subsections numbered 3.X.Y.
- **Skill format**: Standard Claude Code skill — directory containing `SKILL.md` (required, with YAML frontmatter `name` and `description`) and optional `references/` subdir. SKILL.md is loaded fully when the skill is invoked; `references/` files are loaded on-demand via Read.
- **No git repo**: Working directory `/home/sec/skills/` is not a git repository. Per user's choice (option 1), commits are deferred — replace `git commit` steps with **"Save & verify"** checkpoints that confirm files exist and verifier passes. The user will move artifacts to a real repo later.
- **No worktree**: This plan is being executed directly in `/home/sec/skills/` (not in a separate worktree).

## File Structure

**Source (read-only, do not modify):**
- `/home/sec/skills/Python安全编码规范.docx`

**Intermediate artifact (temporary, can be deleted after Task 10):**
- `/tmp/python-security-rules-raw.md` — flat extraction of docx, preserving headings + code-block hints

**Skill artifacts (deliverables under `~/.claude/skills/python-security-coding/`):**
- `SKILL.md` — index, frontmatter, self-bootstrap, project detection, Layer-1 map, Layer-2 gate
- `references/01-input-validation.md` — §3.1 (10 subsections: 命令/动态评估/网络/数据库/SQL/XML/邮件/日志/资源/表达式)
- `references/02-security-features.md` — §3.2 (11 subsections: 访问控制/密码/密钥/加密/哈希/随机数/Cookie/传输/Flask/Django/隐私)
- `references/03-encapsulation.md` — §3.3 (5 subsections: 输出/网络/边界/CSP/CORS)
- `references/04-api-misuse.md` — §3.4 (2 subsections: 文件/权限)
- `references/05-time-and-state.md` — §3.5 (1 subsection: 临时文件)
- `references/06-error-handling.md` — §3.6 (4 inline rules, no numbered subsections)
- `references/07-code-quality.md` — §3.7 (1 subsection: 路径分隔符)
- `references/08-environment.md` — §3.8 (3 subsections: 响应/部署/版本)

**Verification artifacts (under `/home/sec/skills/`):**
- `scripts/verify-skill.py` — structural verifier (checks frontmatter, required sections, reference file presence, heading counts per category)
- `/tmp/test-py-backend-fixture/` — minimal Flask project for manual smoke test

---

## Task 1: Skill Scaffolding + Structural Verifier

**Files:**
- Create: `~/.claude/skills/python-security-coding/SKILL.md` (placeholder)
- Create: `~/.claude/skills/python-security-coding/references/.keep` (empty marker file)
- Create: `/home/sec/skills/scripts/verify-skill.py`

- [ ] **Step 1: Write the verifier script first**

```python
# /home/sec/skills/scripts/verify-skill.py
"""Structural verifier for python-security-coding skill.
Asserts: frontmatter present, required SKILL.md sections present,
each reference exists with expected category heading and at least one
'### 规则' / '### 反例' / '### 正例' triplet (except 06-error-handling
which has no numbered subsections — just rule lines).
"""
import re
import sys
from pathlib import Path

SKILL_DIR = Path.home() / ".claude/skills/python-security-coding"
SKILL_MD = SKILL_DIR / "SKILL.md"
REFS_DIR = SKILL_DIR / "references"

REQUIRED_SKILL_SECTIONS = [
    "首次激活",
    "项目检测",
    "Layer 1",
    "Layer 2",
    "Reference 索引",
]

# (filename, category-number, expected-subsection-count)
REQUIRED_REFS = [
    ("01-input-validation.md", "3.1", 10),
    ("02-security-features.md", "3.2", 11),
    ("03-encapsulation.md", "3.3", 5),
    ("04-api-misuse.md", "3.4", 2),
    ("05-time-and-state.md", "3.5", 1),
    ("06-error-handling.md", "3.6", 0),  # 0 means no numbered subsections expected
    ("07-code-quality.md", "3.7", 1),
    ("08-environment.md", "3.8", 3),
]

errors = []

def check_skill_md():
    if not SKILL_MD.exists():
        errors.append(f"missing: {SKILL_MD}")
        return
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append("SKILL.md: missing YAML frontmatter")
    if "name: python-security-coding" not in text:
        errors.append("SKILL.md: frontmatter missing 'name: python-security-coding'")
    if "description:" not in text:
        errors.append("SKILL.md: frontmatter missing 'description:'")
    for section in REQUIRED_SKILL_SECTIONS:
        if section not in text:
            errors.append(f"SKILL.md: missing required section '{section}'")

def check_reference(filename, category, expected_subs):
    path = REFS_DIR / filename
    if not path.exists():
        errors.append(f"missing reference: {path}")
        return
    text = path.read_text(encoding="utf-8")
    if not re.search(rf"^# {re.escape(category)} ", text, re.MULTILINE):
        errors.append(f"{filename}: missing top heading '# {category} ...'")
    if expected_subs > 0:
        sub_pattern = rf"^## {re.escape(category)}\.\d+ "
        found = len(re.findall(sub_pattern, text, re.MULTILINE))
        if found != expected_subs:
            errors.append(
                f"{filename}: expected {expected_subs} subsections matching "
                f"'## {category}.X', found {found}"
            )

def main():
    check_skill_md()
    for fn, cat, n in REQUIRED_REFS:
        check_reference(fn, cat, n)
    if errors:
        print("VERIFY FAILED")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("VERIFY OK")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run verifier — expect FAIL (skill not yet present)**

```bash
python3 /home/sec/skills/scripts/verify-skill.py
```

Expected output starts with `VERIFY FAILED` and lists missing SKILL.md + 8 missing references.

- [ ] **Step 3: Create skill directory + placeholder SKILL.md**

```bash
mkdir -p ~/.claude/skills/python-security-coding/references
touch ~/.claude/skills/python-security-coding/references/.keep
```

Create `~/.claude/skills/python-security-coding/SKILL.md` with placeholder content:

```markdown
---
name: python-security-coding
description: PLACEHOLDER — full description authored in Task 11.
---

# Python 安全编码规范 Skill (placeholder)

## 首次激活
TBD

## 项目检测
TBD

## Layer 1
TBD

## Layer 2
TBD

## Reference 索引
TBD
```

- [ ] **Step 4: Run verifier — expect partial pass**

```bash
python3 /home/sec/skills/scripts/verify-skill.py
```

Expected: still `VERIFY FAILED` but only complaining about missing references (8 errors). SKILL.md structural checks should now pass.

- [ ] **Step 5: Save & verify checkpoint**

Confirm:
```bash
ls -la ~/.claude/skills/python-security-coding/
ls -la ~/.claude/skills/python-security-coding/references/
ls -la /home/sec/skills/scripts/verify-skill.py
```

Expected: SKILL.md exists, references/ exists with .keep, verifier script is executable-readable.

---

## Task 2: Extract docx Content to Intermediate Markdown

**Files:**
- Create: `/home/sec/skills/scripts/extract-docx.py`
- Output: `/tmp/python-security-rules-raw.md`

- [ ] **Step 1: Write extraction script**

```python
# /home/sec/skills/scripts/extract-docx.py
"""Extract paragraphs from the company Python security regulation docx
into a flat markdown file, preserving heading levels by Word style name.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

DOCX = Path("/home/sec/skills/Python安全编码规范.docx")
OUT = Path("/tmp/python-security-rules-raw.md")
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def style_to_md(style):
    if not style:
        return None
    if "Heading1" in style or "Title" in style:
        return "# "
    if "Heading2" in style:
        return "## "
    if "Heading3" in style:
        return "### "
    if "Heading4" in style:
        return "#### "
    return None

def main():
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["unzip", "-q", str(DOCX), "-d", tmp], check=True)
        tree = ET.parse(Path(tmp) / "word/document.xml")
        root = tree.getroot()
        lines = []
        for p in root.iter(f"{{{NS_W}}}p"):
            style_el = p.find(f"{{{NS_W}}}pPr/{{{NS_W}}}pStyle")
            style = style_el.get(f"{{{NS_W}}}val") if style_el is not None else ""
            text = "".join(t.text or "" for t in p.iter(f"{{{NS_W}}}t"))
            if not text.strip():
                continue
            prefix = style_to_md(style)
            if prefix:
                lines.append(f"{prefix}{text}")
            else:
                lines.append(text)
        OUT.write_text("\n\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(lines)} paragraphs)")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run extraction**

```bash
python3 /home/sec/skills/scripts/extract-docx.py
```

Expected output: `wrote /tmp/python-security-rules-raw.md (XXXXX bytes, 200+ paragraphs)`.

- [ ] **Step 3: Spot-check the extract**

```bash
head -80 /tmp/python-security-rules-raw.md
grep -c '^### ' /tmp/python-security-rules-raw.md
```

Expected: top of file shows the document title and TOC paragraphs; grep returns a count of subsections (~30+).

- [ ] **Step 4: Save & verify checkpoint**

Confirm `/tmp/python-security-rules-raw.md` exists and contains Chinese rule text. This file is the source of truth for tasks 3–10.

---

## Task 3: Author `references/01-input-validation.md` (Canonical Reference)

This task establishes the **uniform reference template** that tasks 4–10 will reuse. Read this task in full before starting any other reference task.

**Files:**
- Create: `~/.claude/skills/python-security-coding/references/01-input-validation.md`
- Read: `/tmp/python-security-rules-raw.md` (paragraphs covering §3.1 — locate by searching for "输入验证与表示")

**Subsections to author (10 total, 3.1.1 – 3.1.10):**
1. 3.1.1 命令操作安全
2. 3.1.2 代码动态评估操作安全
3. 3.1.3 网络操作安全
4. 3.1.4 数据库操作安全
5. 3.1.5 SQL 操作安全
6. 3.1.6 XML 操作安全
7. 3.1.7 邮件操作安全
8. 3.1.8 日志操作安全
9. 3.1.9 资源操作安全
10. 3.1.10 表达式操作安全

- [ ] **Step 1: Read the §3.1 portion of the raw extract**

```bash
sed -n '/^## 输入验证与表示/,/^## 安全特性/p' /tmp/python-security-rules-raw.md
```

(If the heading levels in the extract differ — e.g. `### 输入验证与表示` — adjust the sed range. The point is to isolate the §3.1 content for transcription.)

- [ ] **Step 2: Write the file using this template**

```markdown
# 3.1 输入验证与表示

> 概述：输入验证和表示问题通常由元字符、交替编码和数字表示引起，必须对所有输入进行合法性校验。

## 3.1.1 命令操作安全

### 规则
- 避免直接调用系统命令（如 `os.system`、`os.popen`、`eval` 等），推荐使用系统 API 操作。
- 应避免拼接外部数据，并对执行的命令进行白名单限制。
- 应避免外部控制系统设置（系统设置由外部控制可能导致服务中断或意外的应用程序行为）。
- 应避免通过不可信的输入调用 memcached 操作。

### 反例
\`\`\`python
import os
os.system("ping " + user_input)  # 命令注入
\`\`\`

### 正例
\`\`\`python
import sys
import shlex
domain = sys.argv[1]
badchars = "\n&;|'\"$()`-"
for char in badchars:
    domain = domain.replace(char, " ")
# 进一步：白名单 + 参数化的 subprocess 调用
\`\`\`

### 适用场景
代码中出现 `os.system` / `subprocess` / `popen` / `commands.getoutput` / 调用外部进程时；接收 CLI 参数 / HTTP 参数 / 环境变量后将其传入 shell 时。

---

## 3.1.2 代码动态评估操作安全

### 规则
- 应避免动态解析源码指令（任何时候都应尽可能避免对代码进行动态解析）。
- 应避免直接执行和解析未验证的用户输入。
- 应避免对用户控制的数据进行反序列化（会让攻击者执行任意代码）。

### 反例
（基于规范原文：在程序运行时解析用户控制的指令、对用户数据反序列化均会导致 RCE。）
\`\`\`python
import pickle
obj = pickle.loads(request.body)  # 任意代码执行
eval(user_input)                   # 动态解析
\`\`\`

### 正例
\`\`\`python
import json
obj = json.loads(request.body)     # 用 JSON 替代 pickle
# 对真正需要表达式求值的场景，使用 ast.literal_eval（仅字面量）
import ast
val = ast.literal_eval(user_input)
\`\`\`

### 适用场景
代码中出现 `eval` / `exec` / `compile` / `pickle.loads` / `marshal.loads` / `yaml.load(..., Loader=yaml.Loader)` / `dill` / `cloudpickle`；任何接收外部字节流并反序列化的位置。

---

## 3.1.3 网络操作安全

### 规则
- 应避免向 Web 浏览器发送未经验证的数据。
- 应避免在响应头文件中包含未验证的数据。
- 应避免在 Cookie 中包含未验证的数据。
- 应启用 X-XSS-Protection 标头。
- 禁止未验证的输入控制重定向机制所使用的 URL。

### 反例
\`\`\`python
# 未启用 XSS 保护
SECURE_BROWSER_XSS_FILTER = False
\`\`\`

### 正例
\`\`\`python
# Django settings
MIDDLEWARE_CLASSES = (
    ...
    'django.middleware.security.SecurityMiddleware',
    ...
)
SECURE_BROWSER_XSS_FILTER = True
\`\`\`

### 适用场景
写入响应头 / Set-Cookie / `HttpResponseRedirect` / `flask.redirect` 时；接收外部 URL 作为重定向目标时。

---

## 3.1.4 数据库操作安全

### 规则
- 禁止在数据库连接中加入未经验证的输入。
- 避免动态构造数据库查询语句。

### 反例
\`\`\`python
mysql.connector.connect(host=request.GET['host'], ...)  # 连接参数外部可控
\`\`\`

### 正例
\`\`\`python
# 连接参数从受信任的配置读取
mysql.connector.connect(host=settings.DB_HOST, ...)
\`\`\`

### 适用场景
建立数据库连接、构造 DSN、动态拼接表名/列名时。

---

## 3.1.5 SQL 操作安全

### 规则
- 应使用参数化查询语句（强制区分数据和命令，避免 SQL 注入）。
- 推荐使用组件操作数据库（Django ORM、SQLAlchemy 等）。
- 应对接收到的外部参数进行过滤（动态拼接 SQL 时必须过滤）。

### 反例
\`\`\`python
cur.execute("SELECT id FROM auth_user WHERE id=" + str(userid))  # SQL 注入
\`\`\`

### 正例
\`\`\`python
import mysql.connector
mydb = mysql.connector.connect(...)
cur = mydb.cursor()
userid = get_id_from_user()
cur.execute(
    "SELECT `id`, `password` FROM `auth_user` WHERE `id`=%s",
    (userid,),
)
result = cur.fetchall()

# 当必须动态拼接时，先过滤
def sql_filter(sql, max_length=20):
    dirty_stuff = ["\"", "\\", "/", "*", "'", "=", "-", "#", ";",
                   "<", ">", "+", "&", "$", "(", ")", "%", "@", ","]
    for stuff in dirty_stuff:
        sql = sql.replace(stuff, "x")
    return sql[:max_length]
\`\`\`

### 适用场景
任何 `cursor.execute` / `cursor.executemany` / `db.session.execute` / raw SQL 字符串；对外部参数做表名/列名/排序方向拼接时。

---

## 3.1.6 XML 操作安全

### 规则
- 禁止使用外部实体方法。
- 禁止在 XML 文档中写入未验证的数据。
- 禁止动态构建 XPath 查询语句。
- 禁止使用未经验证的 XSL 样式表。

### 反例
\`\`\`python
from lxml import etree
etree.parse(xmlSource)  # 默认可能解析外部实体（XXE）
\`\`\`

### 正例
\`\`\`python
from lxml import etree
xmlData = etree.parse(xmlSource, etree.XMLParser(resolve_entities=False))
\`\`\`

### 适用场景
任何 XML 解析（`lxml.etree`、`xml.etree.ElementTree`、`xml.dom.minidom`）；构造 XPath 表达式；XSLT 转换。

---

## 3.1.7 邮件操作安全

### 规则
- 应避免在 SMTP 头中包含未验证的用户输入。
- 应避免直接执行未验证的 SMTP 命令。

### 反例
\`\`\`python
smtp.docmd("MAIL FROM:<" + user_input + ">")  # SMTP 命令注入
\`\`\`

### 正例
\`\`\`python
# 使用高层接口，传入经过验证的字段
import smtplib
from email.message import EmailMessage
msg = EmailMessage()
msg["From"] = validated_sender
smtp.send_message(msg)
\`\`\`

### 适用场景
使用 `smtplib` / `email` 模块；构造邮件头（From/To/Subject）拼入外部数据时。

---

## 3.1.8 日志操作安全

### 规则
- 禁止将未经验证的用户输入写入日志文件（攻击者可伪造日志条目或注入恶意信息）。

### 反例
\`\`\`python
logging.info("user login: " + user_input)  # 日志注入（CRLF / 伪造）
\`\`\`

### 正例
\`\`\`python
# 过滤换行符 + 使用结构化字段
clean = user_input.replace("\n", "").replace("\r", "")
logging.info("user login", extra={"user": clean})
\`\`\`

### 适用场景
所有 `logging.*(...)` / `logger.*(...)` / `print` 写日志的位置，形参中含外部数据时。

---

## 3.1.9 资源操作安全

### 规则
- 应避免用户输入控制资源标识符（防止访问/修改其他受保护的系统资源）。
- 应避免让用户提供目标引擎的模板（防止模板注入 / 服务器端代码执行）。

### 反例
\`\`\`python
template_str = request.GET["template"]
Template(template_str).render(...)  # SSTI
\`\`\`

### 正例
\`\`\`python
# 模板从受信任来源加载，外部输入只作为变量
env.get_template("user_view.html").render(user=user_data)
\`\`\`

### 适用场景
Jinja2 / Mako / Django Template 加载；文件路径 / S3 key / 资源 ID 接受外部输入时。

---

## 3.1.10 表达式操作安全

### 规则
- 应避免不受信任的数据被传递至应用程序并作为正则表达式使用（ReDoS / 注入）。

### 反例
\`\`\`python
re.match(user_pattern, target)  # 用户控制正则 → ReDoS
\`\`\`

### 正例
\`\`\`python
# 白名单或预编译固定正则；如必须用户提供，限制长度并设置超时
ALLOWED = {"alpha": r"[A-Za-z]+", "digits": r"\d+"}
re.match(ALLOWED[user_choice], target)
\`\`\`

### 适用场景
`re.match` / `re.search` / `re.compile` / `regex` 库；模式来自外部输入时。
```

- [ ] **Step 3: Cross-check against raw extract**

For each of the 10 subsections, confirm:
- All "应/禁/推荐" rules from the docx text appear in the corresponding "### 规则" block (verbatim or close paraphrase).
- Every code block from the docx (recognizable by `import` / `def` / `... = ...` keywords) has been transferred to either "### 反例" or "### 正例".

Use `grep` to spot any rule keywords from the docx that didn't make it:

```bash
grep -E '^(应|禁止|推荐|避免)' /tmp/python-security-rules-raw.md | head -100
```

- [ ] **Step 4: Run verifier**

```bash
python3 /home/sec/skills/scripts/verify-skill.py 2>&1 | grep '01-input-validation'
```

Expected: no error mentioning `01-input-validation.md`.

- [ ] **Step 5: Save & verify checkpoint**

Confirm: file exists, has exactly 10 `## 3.1.X` subsections, contains 字符串 "适用场景" exactly 10 times.

```bash
grep -c '^## 3.1\.' ~/.claude/skills/python-security-coding/references/01-input-validation.md
grep -c '^### 适用场景' ~/.claude/skills/python-security-coding/references/01-input-validation.md
```

Expected: both commands print `10`.

---

## Task 4: Author `references/02-security-features.md`

Apply the same template as Task 3, sourcing content from §3.2 of `/tmp/python-security-rules-raw.md`.

**Files:**
- Create: `~/.claude/skills/python-security-coding/references/02-security-features.md`

**Subsections (11 total, 3.2.1 – 3.2.11):**
1. 3.2.1 访问控制安全 (数据库访问控制 / 文件权限)
2. 3.2.2 密码管理安全 (空密码 / 硬编码 / NULL / 明文 / 注释 / 弱算法 / 单独哈希 — 7 条规则)
3. 3.2.3 密钥管理安全 (空密钥 / 硬编码 / HMAC / PBE 密码 / NULL / 明文私钥 — 8 条规则)
4. 3.2.4 加密算法安全 (弱算法 DES / RSA 填充 / IV / 操作模式 / 密钥长度 / 流密码 / 用户控制密钥大小 — 7 条规则)
5. 3.2.5 加密哈希算法安全 (弱算法 / PBE Salt / 用户控制 Salt / 迭代次数 / 可预测 Salt — 9 条规则)
6. 3.2.6 随机数安全 (推荐 CSPRNG / 硬编码 Seed / 用户控制 Seed / 弱熵源)
7. 3.2.7 Cookie 安全 (Secure/HttpOnly / Django CSRF/SESSION 属性 / 域路径 / 永久 cookie 敏感数据)
8. 3.2.8 传输安全 (SSL 重定向 / HSTS / 邮件未加密 / 弱 SSL / 服务器身份认证)
9. 3.2.9 Flask 使用安全 (引用官方文档)
10. 3.2.10 Django 使用安全 (SECRET_KEY / Host 标头 / JSON 序列化 / 自带安全特性)
11. 3.2.11 隐私安全 (敏感数据加密存储 / 不展示存储 / 加密传输 / 不可信不控制)

- [ ] **Step 1: Read §3.2 portion of raw extract**

```bash
sed -n '/^## 安全特性/,/^## 封装/p' /tmp/python-security-rules-raw.md
```

- [ ] **Step 2: Author file using same template as Task 3 — `# 3.2 ...` heading, then 11 `## 3.2.X` subsections, each with 规则 / 反例 / 正例 / 适用场景**

For each subsection, transcribe **all** "应/禁/推荐" rules from the raw extract into "### 规则", and place every code block under "### 反例" or "### 正例" based on context (the docx usually labels via "正确示例如下" / "错误示例如下").

Critical code blocks to preserve (from raw extract):
- 3.2.3 PBE 密码空示例: `from hashlib import pbkdf2_hmac ... dk = pbkdf2_hmac('sha256', '', salt, 100000)` (反例)
- 3.2.7 Cookie Django 示例: `res.set_cookie("emailCookie", email, secure=True, httponly=True)` (正例)
- 3.2.7 Django settings: `CSRF_COOKIE_SECURE = True / SESSION_COOKIE_SECURE = True / SESSION_COOKIE_HTTPONLY = True`
- 3.2.7 域路径示例: `res.set_cookie("sessionid", value, path="/MyForum", domain="...", secure=True, httponly=True)`
- 3.2.8 SECURE_SSL_REDIRECT, HSTS_SECONDS, HSTS_INCLUDE_SUBDOMAINS

For each subsection, write a meaningful "### 适用场景" line based on the rule keywords (this is the only added content).

- [ ] **Step 3: Run verifier**

```bash
python3 /home/sec/skills/scripts/verify-skill.py 2>&1 | grep '02-security-features'
```

Expected: no errors.

- [ ] **Step 4: Save & verify checkpoint**

```bash
grep -c '^## 3.2\.' ~/.claude/skills/python-security-coding/references/02-security-features.md
grep -c '^### 适用场景' ~/.claude/skills/python-security-coding/references/02-security-features.md
```

Expected: both print `11`.

---

## Task 5: Author `references/03-encapsulation.md`

**Files:**
- Create: `~/.claude/skills/python-security-coding/references/03-encapsulation.md`

**Subsections (5 total, 3.3.1 – 3.3.5):**
1. 3.3.1 输出安全 (避免 print/sys.stdout/sys.stderr，推荐 logging)
2. 3.3.2 网络安全 (Django CSRF 中间件)
3. 3.3.3 边界安全 (信任边界 / 验证逻辑)
4. 3.3.4 内容策略安全 (CSP — 避免 unsafe-inline / unsafe-eval / 通配符)
5. 3.3.5 跨资源共享策略安全 (CORS — 避免 `*`)

- [ ] **Step 1: Read §3.3 portion of raw extract**

```bash
sed -n '/^## 封装/,/^## API滥用/p' /tmp/python-security-rules-raw.md
```

- [ ] **Step 2: Author file using template — `# 3.3 封装` + 5 subsections**

Critical code to preserve:
- 3.3.1 logging vs print 对比示例
- 3.3.2 CsrfViewMiddleware 配置片段

- [ ] **Step 3: Run verifier**

```bash
python3 /home/sec/skills/scripts/verify-skill.py 2>&1 | grep '03-encapsulation'
```

Expected: no errors.

- [ ] **Step 4: Save & verify checkpoint**

```bash
grep -c '^## 3.3\.' ~/.claude/skills/python-security-coding/references/03-encapsulation.md
```

Expected: `5`.

---

## Task 6: Author `references/04-api-misuse.md`

**Files:**
- Create: `~/.claude/skills/python-security-coding/references/04-api-misuse.md`

**Subsections (2 total, 3.4.1 – 3.4.2):**
1. 3.4.1 文件安全 (5 条：禁止存于可执行目录 / 类型限制 / 文件名随机化 / 避免路径拼接 / 校验)
2. 3.4.2 权限管理安全 (4 条：umask/chmod 区分 / 最小权限 / 定期清理 / 默认身份认证)

- [ ] **Step 1: Read §3.4 portion of raw extract**

```bash
sed -n '/^## API滥用/,/^## 时间与状态/p' /tmp/python-security-rules-raw.md
```

- [ ] **Step 2: Author file**

Critical code:
- 3.4.1 ALLOWED_EXTENSIONS / `os.path.splitext` 校验 (正例)
- 3.4.1 `os.path.normpath` 路径白名单校验 (正例)

- [ ] **Step 3: Run verifier**

```bash
python3 /home/sec/skills/scripts/verify-skill.py 2>&1 | grep '04-api-misuse'
```

- [ ] **Step 4: Save & verify checkpoint**

```bash
grep -c '^## 3.4\.' ~/.claude/skills/python-security-coding/references/04-api-misuse.md
```

Expected: `2`.

---

## Task 7: Author `references/05-time-and-state.md`

**Files:**
- Create: `~/.claude/skills/python-security-coding/references/05-time-and-state.md`

**Subsections (1 total):**
1. 3.5.1 避免操作不安全的临时文件 (推荐 tempfile)

- [ ] **Step 1: Read §3.5 portion of raw extract**

```bash
sed -n '/^## 时间与状态/,/^## 错误处理/p' /tmp/python-security-rules-raw.md
```

- [ ] **Step 2: Author file**

Critical code:
- 反例: `os.path.exists("/tmp/foo")` + `open("/tmp/foo", "w")` (TOCTOU)
- 正例: `tempfile.NamedTemporaryFile(delete=False)` / `tempfile.mkstemp()`

- [ ] **Step 3: Run verifier + save & verify**

```bash
python3 /home/sec/skills/scripts/verify-skill.py 2>&1 | grep '05-time-and-state'
grep -c '^## 3.5\.' ~/.claude/skills/python-security-coding/references/05-time-and-state.md
```

Expected: no error; count = 1.

---

## Task 8: Author `references/06-error-handling.md`

**Files:**
- Create: `~/.claude/skills/python-security-coding/references/06-error-handling.md`

**No numbered subsections** — §3.6 contains 4 inline rules (try/except/finally / 不忽略异常 / 记录异常 / 不抛出敏感信息).

- [ ] **Step 1: Read §3.6 portion of raw extract**

```bash
sed -n '/^## 错误处理/,/^## 代码质量/p' /tmp/python-security-rules-raw.md
```

- [ ] **Step 2: Author file with adapted template (single section)**

```markdown
# 3.6 错误处理

> 概述：错误处理不当是这类问题最常见的引入方式。

## 规则
- 应合理利用 try/except/finally，避免出错信息输出到前端。
- 禁止忽略异常，否则会导致程序无法发现意外状况。
- 应记录抛出的异常，以便稍后查询及预知影响。
- 禁止异常抛出敏感信息（堆栈、SQL、密钥、内部路径等）。

## 反例
\`\`\`python
try:
    do_thing()
except Exception:
    pass  # 静默吞异常

try:
    pay(user)
except Exception as e:
    return jsonify({"error": str(e)})  # 把堆栈/内部信息返给前端
\`\`\`

## 正例
\`\`\`python
import logging
try:
    do_thing()
except SpecificError:
    logging.exception("do_thing failed")
    return jsonify({"error": "internal error"}), 500   # 通用提示
finally:
    cleanup()
\`\`\`

## 适用场景
所有 try/except 代码块；构造 HTTP 错误响应；异常上抛到框架层时。
```

- [ ] **Step 3: Run verifier + save & verify**

```bash
python3 /home/sec/skills/scripts/verify-skill.py 2>&1 | grep '06-error-handling'
```

Expected: no errors. (Verifier expects 0 numbered subsections for this file — the verifier's `expected_subs == 0` branch.)

---

## Task 9: Author `references/07-code-quality.md`

**Files:**
- Create: `~/.claude/skills/python-security-coding/references/07-code-quality.md`

**Subsections (1 total):**
1. 3.7.1 避免使用硬编码文件分隔符 (推荐 os.path.join)

- [ ] **Step 1: Read §3.7 portion of raw extract**

```bash
sed -n '/^## 代码质量/,/^## 环境/p' /tmp/python-security-rules-raw.md
```

- [ ] **Step 2: Author file**

Critical code:
- 反例: `open(directoryName + "\\" + fileName)` 或 `open(directoryName + "/" + fileName)`
- 正例: `os.open(os.path.join(directoryName, fileName))` 或 `pathlib.Path(directoryName) / fileName`

- [ ] **Step 3: Run verifier + save & verify**

```bash
python3 /home/sec/skills/scripts/verify-skill.py 2>&1 | grep '07-code-quality'
grep -c '^## 3.7\.' ~/.claude/skills/python-security-coding/references/07-code-quality.md
```

Expected: no error; count = 1.

---

## Task 10: Author `references/08-environment.md`

**Files:**
- Create: `~/.claude/skills/python-security-coding/references/08-environment.md`

**Subsections (3 total, 3.8.1 – 3.8.3):**
1. 3.8.1 响应安全 (X-Content-Type-Options / X-Frame-Options / Content-Type bleach)
2. 3.8.2 部署安全 (DEBUG off / 不安全组件 / 调试代码 / 环境隔离 / 不可预测资源名)
3. 3.8.3 版本安全 (推荐 Python 3.6+)

- [ ] **Step 1: Read §3.8 portion of raw extract**

```bash
sed -n '/^## 环境/,/^## 支持文件清单/p' /tmp/python-security-rules-raw.md
```

- [ ] **Step 2: Author file**

Critical code:
- 3.8.1 `bleach.clean('an <script>evil()</script> example')` 正例
- 3.8.2 Django admin URL 可预测/不可预测对照示例

- [ ] **Step 3: Run verifier + save & verify**

```bash
python3 /home/sec/skills/scripts/verify-skill.py 2>&1 | grep '08-environment'
grep -c '^## 3.8\.' ~/.claude/skills/python-security-coding/references/08-environment.md
```

Expected: no error; count = 3.

---

## Task 11: Author Final SKILL.md

**Files:**
- Modify: `~/.claude/skills/python-security-coding/SKILL.md` (replace placeholder authored in Task 1)

- [ ] **Step 1: Replace placeholder with full content**

```markdown
---
name: python-security-coding
description: Use when designing, writing, reviewing, or testing Python backend code (Flask/Django/FastAPI/Tornado/aiohttp/Sanic/SQLAlchemy/pymysql/psycopg2/celery), or when project contains pyproject.toml/requirements.txt/setup.py with Python web/data framework dependencies, or when code touches SQL/crypto/eval/pickle/file-IO/auth/cookies/CORS/CSP/error-handling. Enforces 8-category company security standard with completion checklist before declaring work done.
---

# Python 安全编码规范 Skill

本 skill 把公司 Python 安全编码规范落到 Claude 的工作流中：description 触发为主路径，CLAUDE.md 锚点兜底，编码期按需查阅 + 完成前清单核对。

## 首次激活：自举写入 CLAUDE.md 锚点

每次本 skill 被调用，第一步执行：

1. 读取项目根目录的 `CLAUDE.md`
2. 若已包含 `python-security-coding` 字样 → 跳过本节
3. 若否，按下方"项目检测"判断当前是否为 Python 后端项目；若是，向用户提议追加：
   ```
   ## 安全编码规范
   本项目所有 Python 代码改动（设计/编码/测试/审查）MUST 调用 `python-security-coding` skill。
   ```
4. 用户同意 → 写入 CLAUDE.md；不同意 → 本会话不再询问
5. 若 CLAUDE.md 不存在 → 提议先创建一个最小 CLAUDE.md（或建议先跑 `/init`），再写入上述段落

## 项目检测

**强信号（任一命中即视为 Python 后端项目）：**
`pyproject.toml` / `requirements.txt` / `Pipfile` / `setup.py` 中出现：
- Web 框架：flask, django, fastapi, tornado, aiohttp, sanic, bottle, falcon, starlette, quart
- 数据/异步栈：sqlalchemy, pymysql, psycopg2, asyncpg, redis, celery, kombu, pika

**弱信号（强信号缺失时不主动自举，但仍可被 description 触发）：**
- 项目内有 `*.py` + 上述任一框架的 `import`
- 存在 `manage.py` / `wsgi.py` / `asgi.py` / `app.py`

## Layer 1 · 编码期按需查阅

写到对应代码点时，Read 对应 reference 文件验证规则。**关键词映射表**：

| 当前任务/代码出现 | Read |
|---|---|
| `cursor.execute` / SQL 拼接 / `?`/`%s` 参数化 | `references/01-input-validation.md` SQL 段 |
| `os.system` / `subprocess` / `shell=True` / `popen` / `eval` / `exec` / `compile` | `references/01-input-validation.md` 命令/动态评估段 |
| `pickle` / `marshal` / `yaml.load` / `cPickle` | `references/01-input-validation.md` 反序列化段 |
| `lxml` / `xml.etree` / `xml.dom` / XPath / XSLT | `references/01-input-validation.md` XML 段 |
| `smtplib` / `email.mime` | `references/01-input-validation.md` 邮件段 |
| 日志写入用户输入 | `references/01-input-validation.md` 日志段 |
| `re.compile` / 正则用户输入 | `references/01-input-validation.md` 正则段 |
| `redirect()` / 重定向到外部 URL | `references/01-input-validation.md` 网络段 |
| `open()` 路径用户控制 / `os.chmod` / `os.umask` | `references/04-api-misuse.md` |
| `tempfile` / `mkstemp` / `mktemp` | `references/05-time-and-state.md` |
| `hashlib` / `Crypto` / `cryptography` / `hmac` / `pbkdf2_hmac` / DES / AES / RSA | `references/02-security-features.md` 加密/哈希段 |
| `random.random` / `random.choice` / `secrets` / `os.urandom` / Seed | `references/02-security-features.md` 随机数段 |
| `set_cookie` / `Set-Cookie` / `CSRF_COOKIE_SECURE` | `references/02-security-features.md` Cookie 段 |
| Flask `app = Flask(...)` / `@app.route` | `references/02-security-features.md` Flask 段 |
| Django settings.py / SECRET_KEY / ALLOWED_HOSTS / MIDDLEWARE | `references/02-security-features.md` Django 段 |
| 用户认证 / 密码处理 / 密钥管理 | `references/02-security-features.md` 密码/密钥/访问控制段 |
| 敏感数据 / PII / 加密存储 | `references/02-security-features.md` 隐私段 |
| `print()` / `sys.stdout` / `sys.stderr` | `references/03-encapsulation.md` 输出段 |
| CSRF 中间件 / X-Frame-Options / X-XSS-Protection / `Access-Control-Allow-Origin` | `references/03-encapsulation.md` + `references/08-environment.md` |
| Content-Security-Policy / CSP | `references/03-encapsulation.md` CSP 段 |
| `try/except` / 异常向用户暴露 | `references/06-error-handling.md` |
| `os.sep` / `\\` / 硬编码路径分隔符 | `references/07-code-quality.md` |
| `DEBUG=True` / 部署配置 / 依赖版本 / Python 版本 | `references/08-environment.md` |

无关键词命中的章节不要预先 Read——节省 token。

## Layer 2 · 完成前清单核对（completion gate）

声明任务完成 / 提交 commit / 创建 PR **之前** MUST 执行：

按以下 8 类逐条自检本次改动是否触发其中规则。命中即对应 Read references 验证；未命中跳过该项。

- [ ] **3.1 输入验证**：本次是否引入/修改了外部输入处理路径（HTTP 参数、请求体、文件读入、消息消费、CLI argv、环境变量）？
- [ ] **3.2 安全特性**：本次是否涉及密码、密钥、加密、哈希、随机数、Cookie、传输配置、Flask/Django settings？
- [ ] **3.3 封装**：本次是否涉及响应输出、CORS、CSP、可信/不可信边界？
- [ ] **3.4 API 滥用**：本次是否涉及文件上传/读写、权限设置（chmod/umask）？
- [ ] **3.5 时间与状态**：本次是否使用临时文件 / 共享状态 / 多线程多进程？
- [ ] **3.6 错误处理**：本次是否新增异常路径、错误响应、日志写入？
- [ ] **3.7 代码质量**：本次是否硬编码了路径分隔符或平台相关常量？
- [ ] **3.8 环境**：本次是否影响响应安全、部署配置、依赖版本、调试开关？

如与 `superpowers:verification-before-completion` skill 同时被触发，将本清单作为该 skill 的 Python 子清单提交。

## Reference 索引

- [`references/01-input-validation.md`](references/01-input-validation.md) — 3.1 输入验证与表示（10 子项：命令/动态评估/网络/数据库/SQL/XML/邮件/日志/资源/表达式）
- [`references/02-security-features.md`](references/02-security-features.md) — 3.2 安全特性（11 子项：访问控制/密码/密钥/加密/哈希/随机数/Cookie/传输/Flask/Django/隐私）
- [`references/03-encapsulation.md`](references/03-encapsulation.md) — 3.3 封装（5 子项：输出/网络/边界/CSP/CORS）
- [`references/04-api-misuse.md`](references/04-api-misuse.md) — 3.4 API 滥用（2 子项：文件/权限）
- [`references/05-time-and-state.md`](references/05-time-and-state.md) — 3.5 时间与状态（临时文件）
- [`references/06-error-handling.md`](references/06-error-handling.md) — 3.6 错误处理（4 条规则）
- [`references/07-code-quality.md`](references/07-code-quality.md) — 3.7 代码质量（路径分隔符）
- [`references/08-environment.md`](references/08-environment.md) — 3.8 环境（响应/部署/版本）
```

- [ ] **Step 2: Run verifier — expect full pass**

```bash
python3 /home/sec/skills/scripts/verify-skill.py
```

Expected output: `VERIFY OK` (exit 0).

- [ ] **Step 3: Save & verify checkpoint**

```bash
grep -E '^(name|description):' ~/.claude/skills/python-security-coding/SKILL.md
wc -l ~/.claude/skills/python-security-coding/SKILL.md
ls ~/.claude/skills/python-security-coding/references/
```

Expected: frontmatter present; SKILL.md is roughly 80–120 lines; references dir contains all 8 .md files plus `.keep`.

---

## Task 12: Manual Smoke Test in Fixture Project

This task verifies the skill behaves as intended in a realistic scenario. It cannot be fully automated (requires Claude session). Document outcomes inline.

**Files:**
- Create: `/tmp/test-py-backend-fixture/pyproject.toml`
- Create: `/tmp/test-py-backend-fixture/app.py`
- Create: `/home/sec/skills/docs/superpowers/plans/2026-04-28-smoke-test-results.md` (record outcomes)

- [ ] **Step 1: Build the fixture project**

```bash
mkdir -p /tmp/test-py-backend-fixture
```

Create `/tmp/test-py-backend-fixture/pyproject.toml`:

```toml
[project]
name = "test-py-backend"
version = "0.0.1"
dependencies = ["flask>=3.0", "sqlalchemy>=2.0"]
```

Create `/tmp/test-py-backend-fixture/app.py`:

```python
from flask import Flask, request
import sqlite3

app = Flask(__name__)

@app.route("/login")
def login():
    user = request.args.get("user")
    conn = sqlite3.connect("db.sqlite")
    cur = conn.cursor()
    # intentionally vulnerable — smoke test target
    cur.execute("SELECT id FROM users WHERE name='" + user + "'")
    return str(cur.fetchall())
```

- [ ] **Step 2: Open a fresh Claude Code session in the fixture project**

```bash
cd /tmp/test-py-backend-fixture
claude
```

Then prompt Claude (literal):

> 帮我看下 app.py 有没有安全问题，并修复

- [ ] **Step 3: Observe and record three behaviors**

Record in `/home/sec/skills/docs/superpowers/plans/2026-04-28-smoke-test-results.md`:

| Observation | Pass criteria |
|---|---|
| Did Claude invoke the `python-security-coding` skill? | Skill tool call visible in transcript |
| Did Claude propose adding the CLAUDE.md anchor? | Bootstrap message offered (since CLAUDE.md doesn't exist) |
| Did Claude Read `references/01-input-validation.md`? | Read tool call on that file (because SQL is involved) |
| Did Claude identify the SQL injection and fix with parameterized query? | Edit replaces string concat with `?` / `%s` |
| Did Claude run the Layer 2 checklist before declaring done? | 8-category checklist visible in final message |

Sample expected pass row: `Skill invoked: yes (transcript shows Skill(python-security-coding) call)`.

- [ ] **Step 4: If any observation fails, root-cause and patch SKILL.md**

Common failure modes and fixes:
- Skill not invoked → description too narrow or lacks the relevant trigger keywords; expand description.
- References not loaded → keyword map missing the trigger; add row to Layer 1 table.
- Bootstrap not offered → "首次激活" instruction unclear; tighten wording.
- Layer 2 not run → wording of "MUST 执行" insufficiently directive; reinforce.

Re-run verifier after any patch:

```bash
python3 /home/sec/skills/scripts/verify-skill.py
```

- [ ] **Step 5: Final save & verify checkpoint**

```bash
ls ~/.claude/skills/python-security-coding/
ls ~/.claude/skills/python-security-coding/references/
python3 /home/sec/skills/scripts/verify-skill.py
cat /home/sec/skills/docs/superpowers/plans/2026-04-28-smoke-test-results.md
```

Expected: skill structure complete, verifier `VERIFY OK`, smoke test results file shows all observations passing (or documents the patch loop).

---

## Decision: Skip Slash Command in v1

The spec mentioned an optional `/python-security-check` slash command for explicit Layer 2 invocation. **Decision: skip in v1.**

**Reasoning:**
- Layer 2 is already wired into the natural completion flow via SKILL.md instructions ("声明任务完成 / 提交 commit / 创建 PR 之前 MUST 执行").
- A separate slash command bifurcates the surface area: users have to remember it; new users won't know about it; it duplicates a behavior that should always happen.
- If smoke test (Task 12) shows Layer 2 is being skipped despite clear instructions, the right fix is to strengthen the SKILL.md wording, not paper over it with a manual command.

**Re-evaluate when:** post-deploy, if you observe Claude consistently skipping Layer 2 on real tasks. At that point a slash command + a hook could be added.

---

## Self-Review

Cross-check against spec sections (`docs/superpowers/specs/2026-04-28-python-security-coding-skill-design.md`):

| Spec section | Implementing task |
|---|---|
| §1 目标与非目标 | All tasks together; non-goal "不修改 init" honored (no init changes anywhere) |
| §2 触发模型 (A+C) | A: Task 11 description; C: Task 11 self-bootstrap section |
| §3 目录与位置 | Task 1 (scaffolding) + Tasks 3–11 (content) |
| §4 自举 | Task 11 SKILL.md "首次激活" section |
| §5 工作模式（双层） | Task 11 Layer 1 keyword map + Layer 2 checklist |
| §6 Reference 文件统一结构 | Task 3 establishes template; Tasks 4–10 reuse |
| §7 项目检测规则 | Task 11 SKILL.md "项目检测" section |
| §8 docx → markdown 转换 | Task 2 (extraction) + Tasks 3–10 (transcription) |
| §9 维护策略 | Self-evident from file structure; not a build-time task |
| §10 风险与未决项 | "verification-before-completion 协作" referenced in Task 11 Layer 2 |
| §11 后续 | This document |

Placeholder scan: no "TBD" / "TODO" / "implement later" outside the placeholder created in Task 1 step 3 (which is explicitly replaced in Task 11).

Type/name consistency: `python-security-coding` used uniformly across all tasks; reference filenames `0X-*.md` consistent across spec, plan, verifier, SKILL.md.
