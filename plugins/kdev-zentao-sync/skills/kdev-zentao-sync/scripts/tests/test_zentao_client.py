# scripts/tests/test_zentao_client.py
import io, json
import urllib.request
import urllib.error
import pytest
import zentao_client as zc

class _Resp(io.BytesIO):
    status = 201
    def __enter__(self): return self
    def __exit__(self, *a): return False

def test_post_json_sets_token_and_body(monkeypatch):
    captured = {}
    def fake_urlopen(req, *a, **k):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["token"] = req.headers.get("Token")
        captured["body"] = req.data
        return _Resp(json.dumps({"id": 9}).encode())
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    c = zc.ZentaoClient("https://h", token="T")
    code, body = c.post_json("/api.php/v1/products/1/bugs", {"title": "x"})
    assert code == 201 and body["id"] == 9
    assert captured["method"] == "POST"
    assert captured["token"] == "T"
    assert json.loads(captured["body"])["title"] == "x"


# ---------------------------------------------------------------------------
# M1: load_credentials — 含空格密码 + 缺字段 Fail Loud
# ---------------------------------------------------------------------------

def test_load_credentials_password_with_spaces(tmp_path):
    """含空格的密码应被完整解析，而不截断到第一个空格前。"""
    cred = tmp_path / "cred.txt"
    cred.write_text("ip: 192.168.1.1\nuser: admin\npassword: p@ss w0rd\n", encoding="utf-8")
    base, user, pwd = zc.load_credentials(cred)
    assert pwd == "p@ss w0rd", f"密码被截断: {pwd!r}"
    assert user == "admin"
    assert base == "https://192.168.1.1"


def test_load_credentials_missing_password_raises(tmp_path):
    """凭据文件缺 password 行时应 raise RuntimeError，而不是 AttributeError。"""
    cred = tmp_path / "cred_no_pwd.txt"
    cred.write_text("ip: 192.168.1.1\nuser: admin\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="password"):
        zc.load_credentials(cred)


def test_load_credentials_missing_ip_raises(tmp_path):
    """凭据文件缺 ip 行时应 raise RuntimeError 并说明缺哪行。"""
    cred = tmp_path / "cred_no_ip.txt"
    cred.write_text("user: admin\npassword: secret\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="ip"):
        zc.load_credentials(cred)


# ---------------------------------------------------------------------------
# M2: paginate — 中途非 200 raise + 缺 total 靠 len<limit 正确终止
# ---------------------------------------------------------------------------

class _PaginateResp(io.BytesIO):
    def __init__(self, data: bytes, status: int = 200):
        super().__init__(data)
        self.status = status
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_paginate_raises_on_non_200_mid_page(monkeypatch):
    """分页第 2 页返回 500 时应 raise RuntimeError，而不是静默 break 丢数据。"""
    call_count = [0]
    def fake_urlopen(req, *a, **k):
        call_count[0] += 1
        if call_count[0] == 1:
            # 第 1 页：正常，返回 limit 条（触发翻页）
            body = json.dumps({"items": [{"id": i} for i in range(5)], "total": 10}).encode()
            return _PaginateResp(body, status=200)
        else:
            # 第 2 页：服务端错误
            raise urllib.error.HTTPError(url="http://x", code=500, msg="err",
                                         hdrs=None, fp=io.BytesIO(b"internal error"))
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    c = zc.ZentaoClient("https://h", token="T")
    with pytest.raises(RuntimeError, match="分页拉取失败"):
        list(c.paginate("/api.php/v1/products/1/bugs", "items", limit=5))


# ---------------------------------------------------------------------------
# F-003: 传输层网络错误有限重试 + 退避；业务级 HTTPError 不重试
# ---------------------------------------------------------------------------

def test_retries_on_network_error_then_succeeds(monkeypatch):
    """传输层网络错误（URLError）应有限重试，恢复后成功返回（F-003）。"""
    calls = [0]
    def fake_urlopen(req, *a, **k):
        calls[0] += 1
        if calls[0] < 3:
            raise urllib.error.URLError("timed out")
        return _Resp(json.dumps({"id": 7}).encode())
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    c = zc.ZentaoClient("https://h", token="T", max_retries=2, retry_backoff=0)
    code, body = c.post_json("/api.php/v1/x", {"a": 1})
    assert code == 201 and body["id"] == 7
    assert calls[0] == 3   # 2 次失败 + 第 3 次成功


def test_raises_concise_after_max_retries(monkeypatch):
    """网络错误超重试上限应 raise 简洁 RuntimeError（不糊裸 traceback）（F-003）。"""
    calls = [0]
    def fake_urlopen(req, *a, **k):
        calls[0] += 1
        raise urllib.error.URLError("timed out")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    c = zc.ZentaoClient("https://h", token="T", max_retries=2, retry_backoff=0)
    with pytest.raises(RuntimeError, match="已重试 2 次|禅道连接失败"):
        c.post_json("/api.php/v1/x", {"a": 1})
    assert calls[0] == 3   # 初次 + 2 次重试


def test_http_error_not_retried(monkeypatch):
    """业务级 HTTPError(4xx/5xx) 已收到响应，应直接返回不重试（避免重复写）（F-003）。"""
    calls = [0]
    def fake_urlopen(req, *a, **k):
        calls[0] += 1
        raise urllib.error.HTTPError(url="http://x", code=400, msg="bad",
                                     hdrs=None, fp=io.BytesIO(b'{"message":"bad"}'))
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    c = zc.ZentaoClient("https://h", token="T", max_retries=2, retry_backoff=0)
    code, body = c.post_json("/api.php/v1/x", {"a": 1})
    assert code == 400
    assert calls[0] == 1   # 不重试


def test_paginate_stops_when_page_shorter_than_limit(monkeypatch):
    """当页条数 < limit 时应终止，即使服务端未返回 total 字段，也不丢数据。"""
    call_count = [0]
    def fake_urlopen(req, *a, **k):
        call_count[0] += 1
        if call_count[0] == 1:
            # 第 1 页：满 limit
            body = json.dumps({"items": [{"id": i} for i in range(3)]}).encode()  # 无 total
        else:
            # 第 2 页：不足 limit
            body = json.dumps({"items": [{"id": 100}]}).encode()  # 无 total
        return _PaginateResp(body, status=200)
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    c = zc.ZentaoClient("https://h", token="T")
    results = list(c.paginate("/api.php/v1/products/1/bugs", "items", limit=3))
    assert len(results) == 4  # 3 + 1，不多不少
    assert call_count[0] == 2  # 第 2 页不足 limit 后停止，不发第 3 页
