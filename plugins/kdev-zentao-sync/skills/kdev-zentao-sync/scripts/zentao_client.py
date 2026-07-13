"""禅道 REST API v1 传输层。仅标准库。port 自 zentao_submit.py（已验证可建 bug）。"""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterator

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE


def load_credentials(cred_path: Path) -> tuple[str, str, str]:
    text = Path(cred_path).read_text(encoding="utf-8")
    m_ip = re.search(r"ip\s*[:：]\s*(\S+)", text)
    if m_ip is None:
        raise RuntimeError(f"凭据文件缺少 ip 行: {cred_path}")
    ip = m_ip.group(1).rstrip("/")
    m_user = re.search(r"user\s*[:：]\s*(\S+)", text)
    if m_user is None:
        raise RuntimeError(f"凭据文件缺少 user 行: {cred_path}")
    user = m_user.group(1)
    m_pwd = re.search(r"password\s*[:：]\s*(.+?)\s*$", text, re.MULTILINE)
    if m_pwd is None:
        raise RuntimeError(f"凭据文件缺少 password 行: {cred_path}")
    pwd = m_pwd.group(1)
    base = ip if ip.startswith("http") else f"https://{ip}"
    return base, user, pwd


class ZentaoClient:
    def __init__(self, base: str, token: str | None = None,
                 max_retries: int = 2, retry_backoff: float = 0.8):
        self.base = base.rstrip("/")
        self.token = token
        # F-003：传输层网络抖动（TLS 握手超时 / SSLEOF / 连接重置）有限重试 + 指数退避。
        # 只重试**连接/传输层**异常；业务级 HTTP 4xx/5xx（已收到响应）绝不重试——
        # 避免对已落库的写操作（如建 bug）重复提交。
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def _request(self, method, path, *, body=None, raw=None, headers=None):
        url = path if path.startswith("http") else f"{self.base}{path}"
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Token"] = self.token
        if headers:
            h.update(headers)
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, context=_SSL, timeout=30) as resp:
                    txt = resp.read().decode("utf-8", "replace")
                    try:
                        return resp.status, json.loads(txt)
                    except json.JSONDecodeError:
                        return resp.status, txt
            except urllib.error.HTTPError as e:
                # 业务级响应（收到了 4xx/5xx）：按原逻辑返回，**不重试**（避免重复写）。
                txt = e.read().decode("utf-8", "replace")
                try:
                    return e.code, json.loads(txt)
                except json.JSONDecodeError:
                    return e.code, txt
            except (urllib.error.URLError, ssl.SSLError, TimeoutError, OSError) as e:
                # 传输层网络错误（超时 / SSLEOF / 连接重置）：有限重试 + 指数退避，
                # 仍失败则收成简洁 loud（不糊裸 traceback）。与第零原则「环境失败先重试吸收抖动」一致。
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff * (2 ** attempt))
                    continue
                raise RuntimeError(
                    f"禅道连接失败（{type(e).__name__}: {e}），已重试 {self.max_retries} 次；"
                    f"请检查网络 / 实例状态 / IP 白名单。url={url}"
                ) from e

    def get_json(self, path):
        return self._request("GET", path)

    def post_json(self, path, body):
        return self._request("POST", path, body=body)

    def login(self, user, pwd) -> str:
        code, body = self.post_json("/api.php/v1/tokens", {"account": user, "password": pwd})
        if code not in (200, 201) or not isinstance(body, dict) or "token" not in body:
            raise RuntimeError(f"登录失败 status={code} body={body!r}")
        self.token = body["token"]
        return self.token

    def paginate(self, path, key, limit=200) -> Iterator[dict]:
        page = 1
        sep = "&" if "?" in path else "?"
        while True:
            code, body = self.get_json(f"{path}{sep}limit={limit}&page={page}")
            if code != 200 or not isinstance(body, dict):
                raise RuntimeError(f"分页拉取失败 status={code} path={path}")
            items = body.get(key, [])
            for it in items:
                yield it
            if not items or len(items) < limit:
                break
            page += 1

    # 注：本实例 ZenTao 15.7.1 v1 REST **无文件上传端点**（/api.php/v1/files 及
    # /bugs/{id}/files 均 404，内嵌 base64 data-URI 图也被服务端 HTML 净化器剥除，
    # 2026-06-20 实测）。故不提供 upload_file —— 截图按路径写入 bug 描述（见 mapper），
    # 真附件须走 /browse UI。别再加注定 404 的上传方法（Fail Loud：不留假装能用的死代码）。
