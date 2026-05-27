# 安全评审员 checklist（D2 阻断）

> 评审对象：`.kdev/handoffs/dev/security.md` + 代码（git diff，本次 D2 循环）
> 评审结论：PASS / FAIL（FAIL 必须列具体问题）

## D2 必检项（10 条 / 1 项 FAIL = 总体 FAIL）

1. [ ] **SAST 高危全处理**：security.md 中列出的所有 SAST 高危（Critical / High）问题已有对应修复说明或关闭依据；无未处理高危。
2. [ ] **secrets 零暴露**：diff 中无 API key、密码、token、证书私钥等敏感字符串明文出现（包括注释、测试代码）。
3. [ ] **鉴权检查完整**：所有受保护端点 / 函数均有鉴权守卫（authentication），未登录用户无法访问需权限资源。
4. [ ] **授权检查完整**：业务对象级授权（authorization）正确——用户只能操作自己拥有或被授权的资源，无 IDOR 漏洞。
5. [ ] **输入校验严格**：所有外部输入（HTTP 请求参数、文件名、用户提供字符串）在入口做类型 + 长度 + 格式校验；SQL / 命令注入防护到位。
6. [ ] **OWASP Top 10 已排查**：security.md 中对 OWASP Top 10 各项有明确「适用/不适用/已缓解」状态说明；不得空白。
7. [ ] **日志不打 PII**：diff 中日志语句不含用户姓名、手机号、邮箱、身份证等 PII 字段（脱敏处理须有证据）。
8. [ ] **依赖漏洞已处理**：依赖扫描（pip-audit / npm audit 等）输出中无 High / Critical 级别漏洞，或有明确降级 / 豁免记录。
9. [ ] **加密算法合规**：使用的哈希、加密算法为当前行业推荐（SHA-256+、AES-256、bcrypt/argon2 等），无 MD5 / SHA-1 用于安全目的。
10. [ ] **跨域策略合理**：CORS 配置白名单明确，不使用 `*`；CSRF 防护在修改操作端点上已启用。

## 输出格式

写到 `.kdev/handoffs/dev/<AR编号>-安全评审员-review.md`：

```markdown
# 安全评审员 review — <AR编号> D2

verdict: PASS | FAIL
date: <ISO-ts>

## 检查项结果
1. ✅ SAST 高危全处理
2. ❌ secrets 零暴露 — src/config.py:12 存在明文 AWS_SECRET_KEY
...

## 问题清单（FAIL 必填）
- 文件: src/config.py 行: 12 — 明文 secret，需迁移到环境变量
```
