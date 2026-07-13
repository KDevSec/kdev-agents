"""Phase-0 能力探测：只读探测禅道 v1 端点覆盖，输出能力矩阵 JSON。

针对换实例 / 换 product 时重新核实「哪些操作能纯 API、哪个要 /browse」。
只发 GET（外加一次 login）；不写任何业务数据。

端点路径已据 2026-06-20 实测校正：
  - 测试单在**顶层** /api.php/v1/testtasks（非 /products/{id}/testtasks）；
  - 但顶层 testtasks 仅 GET 可用，POST 不创建（200 空 body）→ 建测试单须 /browse；
  - 无 v1 模块端点（产品详情 modules=null）→ 建用例 module 默认 0 或 --module 手传。
详见 .superpowers/sdd/capability-findings.md（设计期实测记录）。

用法：
  /usr/bin/python3 capability_probe.py --cred 禅道.md --product 1
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from zentao_client import ZentaoClient, load_credentials


def _get(client: ZentaoClient, path: str) -> dict:
    code, body = client.get_json(path)
    return {"path": path, "status": code, "ok": code == 200}


def probe(client: ZentaoClient, product: int) -> dict:
    """只读探测。返回 {能力名: {path,status,ok}}。"""
    return {
        "list_bugs": _get(client, f"/api.php/v1/products/{product}/bugs?limit=1&page=1"),
        "list_testcases": _get(client, f"/api.php/v1/products/{product}/testcases?limit=1&page=1"),
        "product_detail": _get(client, f"/api.php/v1/products/{product}"),
        "list_testtasks_toplevel": _get(client, "/api.php/v1/testtasks?limit=1&page=1"),
        "list_testtasks_underproduct": _get(client, f"/api.php/v1/products/{product}/testtasks?limit=1&page=1"),
        "list_projects": _get(client, "/api.php/v1/projects?limit=1&page=1"),
    }


def summarize(caps: dict) -> list[str]:
    """据探测结果给出操作可行性判断（确定性，不靠 LLM）。"""
    out = []
    out.append("提bug(API): " + ("可用" if caps["list_bugs"]["ok"] else "不可用"))
    out.append("导用例(API): " + ("可用" if caps["list_testcases"]["ok"] else "不可用"))
    # 测试单：GET 顶层可用不代表 POST 能建（实测该实例 POST 不创建）→ 永远提示 /browse 兜底核实
    tt = caps["list_testtasks_toplevel"]["ok"]
    out.append("测试单(列表 API): " + ("顶层 /testtasks 可用" if tt else "不可用"))
    out.append("测试单(创建): 须实测 POST /testtasks 是否真创建；本设计实例为 200 空 body 不建 → 走 /browse")
    out.append("用例模块: 无 v1 模块端点 → import-cases 用 --module（默认 0=根）")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cred", type=Path, required=True, help="禅道.md 凭据路径")
    ap.add_argument("--product", type=int, required=True)
    args = ap.parse_args()

    base, user, pwd = load_credentials(args.cred)
    client = ZentaoClient(base)
    client.login(user, pwd)
    caps = probe(client, args.product)
    verdict = summarize(caps)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("reports") / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"capability_{ts}.json"
    out.write_text(json.dumps({"caps": caps, "verdict": verdict}, ensure_ascii=False, indent=2),
                   encoding="utf-8")

    print(json.dumps(caps, ensure_ascii=False, indent=2))
    print("\n=== 判断 ===")
    for line in verdict:
        print("  -", line)
    print(f"\n[INFO] 能力矩阵: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
