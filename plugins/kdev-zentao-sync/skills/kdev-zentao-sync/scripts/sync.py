# scripts/sync.py
"""kdev-zentao-sync 编排：query-bugs / regress-bugs / import-cases / submit-bugs。

写操作（submit-bugs / import-cases）默认 dry-run，须 --execute 真写。
query-bugs / regress-bugs 是**只读**（不改禅道）：query 列 bug、regress 对照 junit 出回归报告。
"""
from __future__ import annotations

import argparse, csv, html, json, re, sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from zentao_client import ZentaoClient, load_credentials
from case_md_parser import parse_cases
from mapper import (bug_row_to_payload, case_to_testcase_payload, testtask_payload,
                    base_ar, build_case_title)
import bug_ops

_TC_RE = re.compile(r"\[(TC-[A-Za-z0-9-]+)\]")
_STORY_AR_RE = re.compile(r"(AR-[A-Za-z0-9.\-]+)")


def story_ar_map(client: ZentaoClient, product: int) -> dict[str, int]:
    """需求库 story 标题里的 AR 主键 → story id（用于回填用例『对应需求』）。"""
    out: dict[str, int] = {}
    for s in client.paginate(f"/api.php/v1/products/{product}/stories", "stories"):
        m = _STORY_AR_RE.search(s.get("title", ""))
        if m:
            out[m.group(1)] = s.get("id")
    return out


def story_module_map(client: ZentaoClient, product: int) -> dict[str, int]:
    """需求库 story 标题里的 AR 主键 → 该 story 所在模块 id（story.module）。

    禅道 v1 无模块 GET API，但 story 记录带 `module` 字段，且用例库与 story 共用同一棵
    模块树 → 用例可据此自动归到「与其对应需求同一模块」，绕开 §4 的 /browse 查 module id。
    仅收录 module 非 0/非空的 story（module=0 视为未归类、不参与自动回退）。"""
    out: dict[str, int] = {}
    for s in client.paginate(f"/api.php/v1/products/{product}/stories", "stories"):
        m = _STORY_AR_RE.search(s.get("title", ""))
        mod = s.get("module")
        if m and mod:
            out[m.group(1)] = mod
    return out


def parse_module_map(s: str) -> dict[str, int]:
    """'产品管理中心=10,系统管理=11' → {模块名: id}。本实例无模块 GET API，故手工给。"""
    out: dict[str, int] = {}
    for pair in (s or "").split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise RuntimeError(f"--module-map 项格式应为 名=id：{pair!r}")
        name, _id = pair.split("=", 1)
        out[name.strip()] = int(_id.strip())
    return out


def _reports_dir() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    d = Path("reports") / ts
    d.mkdir(parents=True, exist_ok=True)
    return d


def _client(args) -> ZentaoClient:
    base, user, pwd = load_credentials(args.cred)
    c = ZentaoClient(base); c.login(user, pwd)
    return c


def existing_tc_ids(client: ZentaoClient, product: int) -> set[str]:
    out: set[str] = set()
    for bug in client.paginate(f"/api.php/v1/products/{product}/bugs", "bugs"):
        m = _TC_RE.search(bug.get("title", ""))
        if m:
            out.add(m.group(1))
    return out


# F-002：defects CSV 双 schema 兼容 —— Schema A（submit-bugs 原生）↔ Schema B
# （playwrighttest / apitest canonical）。列名别名把 Schema B 列归一到内部认的 Schema A 列名
# （原列保留，目标列缺失才补）。判定『真实缺陷』口径不变（原因分类/原因分析 以『真实-』开头），
# 不臆测自动分类——未分诊（占位）/ 列名漂移 一律 Fail Loud（见 cmd_submit_bugs 守卫）。
_CSV_COL_ALIASES = {
    "用例ID": ("用例ID", "用例"),
    "原因分类": ("原因分类", "原因分析"),
    "失败摘要": ("失败摘要", "错误信息"),
    "截图": ("截图", "失败截图"),
}


def _normalize_defect_row(row: dict) -> dict:
    out = dict(row)
    for canon, aliases in _CSV_COL_ALIASES.items():
        if out.get(canon):
            continue
        for a in aliases:
            if row.get(a):
                out[canon] = row[a]
                break
    return out


def _is_real_defect(cause: str) -> bool:
    """真缺陷判定，兼容两套分诊前缀：playwrighttest 人工『真实-』 / apitest 自动『real-defect』
    （apitest conftest `_classify_root_cause` 实证）。占位『（待人工分析…）』含 real-defect 子串
    但不以其开头 → 不误判为真缺陷（仍走 Fail Loud）。"""
    c = (cause or "").strip()
    return c.startswith("真实-") or c.startswith("real-defect")


def cmd_submit_bugs(args) -> int:
    raw_rows = list(csv.DictReader(args.csv.open(encoding="utf-8-sig")))
    rows = [_normalize_defect_row(r) for r in raw_rows]
    real = [r for r in rows if _is_real_defect(r.get("原因分类", ""))]
    print(f"[INFO] CSV {args.csv}：总 {len(rows)}，真实缺陷 {len(real)}")
    # F-002 Fail Loud：CSV 有行但 0 行命中『真实-』时区分两种情形——
    #   合法：列里有已分诊的非真实分类（框架-/脚本-）→ 0 真缺陷是正确结论，正常继续；
    #   可疑：缺『原因分类/原因分析』列（列名漂移）或值为『（待人工分析）』占位（Schema B 未分诊）
    #         → 拒绝静默提 0 条并 raise（第零原则：静默 0 会把真缺陷悄悄漏掉，比报红更隐蔽）。
    if raw_rows and not real:
        raw_cols = list(raw_rows[0].keys())
        has_cause_col = bool(set(raw_cols) & {"原因分类", "原因分析"})
        undiagnosed = sum(1 for r in rows if "待人工分析" in (r.get("原因分类", "") or ""))
        if not has_cause_col or undiagnosed:
            reason = ("缺『原因分类/原因分析』列（疑列名漂移）" if not has_cause_col
                      else f"{undiagnosed} 行为『（待人工分析）』占位（Schema B 未分诊）")
            raise RuntimeError(
                f"CSV {len(raw_rows)} 行但 0 行标记『真实-』缺陷，拒绝静默提 0 条（Fail Loud）。\n"
                f"  原因：{reason}\n  当前列名={raw_cols}\n"
                f"  请先人工分诊：把真缺陷行的『原因分析/原因分类』改为『真实-<类别>』"
                f"（或 apitest 的『real-defect…』）再提"
                f"（Schema B 的 用例/原因分析/错误信息/失败截图 列名已自动兼容，无需改列名）。"
            )
    # M3: 校验所有真实缺陷行必须有用例ID，否则 Fail Loud（空锚点重跑会重复提交）
    missing_id = [
        f"行{rows.index(r)+2}({r.get('用例名称', '')})" for r in real if not r.get("用例ID", "").strip()
    ]
    if missing_id:
        raise RuntimeError(f"真实缺陷行缺少用例ID，无法提交（空锚点重跑会重复建 bug）: {', '.join(missing_id)}")
    client = _client(args)
    existing = existing_tc_ids(client, args.product)
    todo = [r for r in real if r.get("用例ID") not in existing]
    skipped = [r for r in real if r.get("用例ID") in existing]
    print(f"[INFO] 去重后待提 {len(todo)}，跳过(已存在) {len(skipped)}")

    if not args.execute:
        for r in todo:
            # dry-run 预览 = 真实将创建的 bug title（含原因分类/失败摘要/255 截断），
            # 所见即所提：避免只打用例名导致确认环节与实际落库形态有偏差（F-001）。
            title = bug_row_to_payload(r, args.product, args.build)["title"]
            print(f"  + {title}")
        print(f"[DRY-RUN] 共 {len(todo)} 条未提交（加 --execute 真提交）")
        return 0

    rep = _reports_dir(); log = (rep / "submit_bugs.log").open("w", encoding="utf-8")
    succ = fail = 0
    for r in todo:
        try:
            payload = bug_row_to_payload(r, args.product, args.build)
            code, body = client.post_json(f"/api.php/v1/products/{args.product}/bugs", payload)
            if code not in (200, 201) or not isinstance(body, dict) or "id" not in body:
                raise RuntimeError(f"status={code} body={body!r}")
            bug_id = body["id"]; msg = f"[OK] {r.get('用例ID')} → bug#{bug_id}"
            if r.get("截图", "").strip():
                # 实测：本实例 v1 丢弃 bug 正文(steps)且无文件上传端点(404)→ 截图既不能附件、
                # 路径也存不进正文。据实标注(不静默/不假装)：截图仅留本地 defects CSV，真附图走 /browse。
                msg += "  (截图无法入 v1: 仅留本地 CSV; 附图须 /browse)"
            succ += 1
        except Exception as e:
            msg = f"[FAIL] {r.get('用例ID')}: {e}"; fail += 1
        print(msg); log.write(msg + "\n")
    log.write(f"\n# 成功 {succ} 失败 {fail} 跳过 {len(skipped)}\n"); log.close()
    print(f"[INFO] 成功 {succ} 失败 {fail} 跳过 {len(skipped)}；日志 {rep}")
    return 0 if fail == 0 else 1


def existing_case_titles(client: ZentaoClient, product: int) -> set[str]:
    # 禅道存标题会 HTML 转义（<>& → &lt;/&gt;/&amp; 等）。按 md 原文去重会对含特殊字符的
    # 标题永远匹配不上 → 每跑一次就重复建一次。故反转义回原文再比（不依赖猜禅道转义了哪些字符）。
    return {html.unescape(c.get("title", "")) for c in
            client.paginate(f"/api.php/v1/products/{product}/testcases", "testcases")}


def cmd_import_cases(args) -> int:
    cases = parse_cases(args.md.read_text(encoding="utf-8"))
    print(f"[INFO] 解析 {args.md}：{len(cases)} 条用例（module 默认={args.module}）")
    client = _client(args)
    existing = existing_case_titles(client, args.product)
    # 去重锚点 = build_case_title（截断后的原文），与 existing（反转义回原文）同一坐标系
    todo = [c for c in cases if build_case_title(c) not in existing]
    skipped = [c for c in cases if build_case_title(c) in existing]
    print(f"[INFO] 去重后待建 {len(todo)}，跳过(同名已存在) {len(skipped)}")

    # 字段映射源：story 自需求库（按 AR 文本匹配）；module 优先 --module-map（按 md 模块名），
    # 次选 story.module（用例自动归到其对应需求所在模块，绕开 /browse 查 id），再兜底 --module。
    ar2story = story_ar_map(client, args.product)
    ar2module = story_module_map(client, args.product)
    name2module = parse_module_map(args.module_map)
    print(f"[INFO] 需求库 story 映射 {len(ar2story)} 项（其中带模块 {len(ar2module)} 项可供自动归类）；模块名映射 {len(name2module)} 项")

    # 模块解析优先级：--module-map(按 md 模块名) > story.module(同需求模块) > --module 兜底。
    def _mod_of(c):
        if name2module and c.module in name2module:
            return name2module[c.module]
        if ar2module and base_ar(c.ar) in ar2module:
            return ar2module[base_ar(c.ar)]
        return args.module

    # 覆盖率 Fail Loud：未命中的 AR / 模块名显式 surface，不静默默认
    miss_story = sorted({base_ar(c.ar) for c in todo if base_ar(c.ar) not in ar2story})
    if miss_story:
        print(f"[WARN] {len(miss_story)} 种 AR 在需求库无 story（这些用例『对应需求』留空）: {miss_story}")
    miss_mod = sorted({c.module for c in todo if c.module and _mod_of(c) == args.module})
    if miss_mod:
        print(f"[WARN] {len(miss_mod)} 种『所属模块』既未在 --module-map、对应需求 story 也无模块（回退 module={args.module}）: {miss_mod}")

    if not args.execute:
        for c in todo:
            sid = ar2story.get(base_ar(c.ar), 0)
            mid = _mod_of(c)
            print(f"  + {c.tc_id}  story={sid} module={mid}  {c.title[:48]}")
        print(f"[DRY-RUN] 共 {len(todo)} 条未创建")
        return 0

    rep = _reports_dir(); log = (rep / "import_cases.log").open("w", encoding="utf-8")
    result: dict[str, int] = {}
    succ = fail = 0
    for c in todo:
        try:
            payload = case_to_testcase_payload(c, args.product, args.module, ar2story, name2module, ar2module)
            code, body = client.post_json(f"/api.php/v1/products/{args.product}/testcases", payload)
            if code not in (200, 201) or not isinstance(body, dict) or "id" not in body:
                raise RuntimeError(f"status={code} body={body!r}")
            result[c.tc_id] = body["id"]; succ += 1
            # 回执增量落盘：每建一条即重写全量 JSON，进程被超时/SIGTERM 中断也不丢账、可据此精准回删孤儿。
            (rep / "imported_cases.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            msg = f"[OK] {c.tc_id} → case#{body['id']} story={payload.get('story',0)} module={payload['module']}"
        except Exception as e:
            msg = f"[FAIL] {c.tc_id}: {e}"; fail += 1
        print(msg); log.write(msg + "\n")
    (rep / "imported_cases.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log.write(f"\n# 成功 {succ} 失败 {fail} 跳过 {len(skipped)}\n"); log.close()
    print(f"[INFO] 成功 {succ} 失败 {fail}；caseID 映射 {rep/'imported_cases.json'}")
    return 0 if fail == 0 else 1


def _all_bugs(client: ZentaoClient, product: int) -> list[dict]:
    return list(client.paginate(f"/api.php/v1/products/{product}/bugs", "bugs"))


def cmd_query_bugs(args) -> int:
    """只读：拉 product 全部 bug → 按过滤条件筛 → 打印表 + 分布统计；可选落 JSON。"""
    client = _client(args)
    bugs = _all_bugs(client, args.product)
    sel = bug_ops.filter_bugs(
        bugs, status=args.status, opened_by=args.opened_by, module=args.module,
        tc_prefix=args.tc_prefix, title_contains=args.title_contains, resolution=args.resolution,
    )
    print(f"[INFO] 全部 {len(bugs)} 条，过滤后 {len(sel)} 条"
          f"（status={args.status or '*'} opened_by={args.opened_by or '*'} "
          f"module={args.module if args.module is not None else '*'} "
          f"tc_prefix={args.tc_prefix or '*'} resolution={args.resolution or '*'}"
          f"{' contains=' + args.title_contains if args.title_contains else ''}）")
    print(f"[INFO] status 分布: {dict(Counter(b.get('status') for b in sel))}")
    print(f"[INFO] resolution 分布: {dict(Counter((b.get('resolution') or '') for b in sel))}")
    print()
    for b in sorted(sel, key=lambda x: (str(x.get("status")), int(x.get("id") or 0))):
        tc = bug_ops.bug_tc_id(b.get("title", ""))
        print(f"#{b.get('id'):>3} [{b.get('status')}] res={b.get('resolution') or '-'} "
              f"by={bug_ops.account_of(b.get('openedBy'))} "
              f"resolvedBy={bug_ops.account_of(b.get('resolvedBy')) or '-'} "
              f"@{b.get('resolvedDate') or '-'} mod={b.get('module')} "
              f"sev={b.get('severity')} tc={tc or '-'}")
        print(f"     {html.unescape((b.get('title') or '').strip())}")
    if args.json:
        rep = _reports_dir()
        out = rep / f"bugs_query_{rep.name}.json"
        out.write_text(json.dumps(sel, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[INFO] 已落 {out}")
    return 0


_VERDICT_ORDER = ["PASS", "SKIP", "MISSING", "NO_TC", "FAIL"]


def cmd_regress_bugs(args) -> int:
    """只读：已修复 bug × junit 结果 → 逐条回归判定 + 报告（reports/<ts>/regression_*.md/.json）。

    不写回禅道（关单/重开人工在禅道点）。junit 由测试套件产（apitest 原生；playwrighttest
    回归时显式 --junitxml 临时产一份）。
    """
    xml_text = args.results.read_text(encoding="utf-8")
    results = bug_ops.parse_junit_text(xml_text)
    unmatched = bug_ops.junit_unmatched_count(xml_text)
    if not results:
        raise RuntimeError(
            f"junit {args.results} 未解析出任何可映射 TC 的 testcase（共 {unmatched} 条不符 "
            f"test_arNN_gN_NNN / test_tcNNN 命名）——拒绝静默出空回归报告（Fail Loud）。"
        )
    print(f"[INFO] junit {args.results}: 映射到 {len(results)} 个用例结果"
          f"{f'（另有 {unmatched} 条命名不符、未纳入）' if unmatched else ''}")

    client = _client(args)
    bugs = _all_bugs(client, args.product)
    sel = bug_ops.filter_bugs(
        bugs, status=args.status, opened_by=args.opened_by, module=args.module,
        tc_prefix=args.tc_prefix, title_contains=args.title_contains, resolution=args.resolution,
    )
    print(f"[INFO] 待回归 bug（status={args.status or '*'} tc_prefix={args.tc_prefix or '*'}）：{len(sel)} 条")

    records = bug_ops.correlate_regression(sel, results)
    by_code = Counter(r["verdict_code"] for r in records)
    print(f"[INFO] 回归判定分布: " +
          ", ".join(f"{c}={by_code.get(c, 0)}" for c in _VERDICT_ORDER if by_code.get(c)))
    print()

    # 控制台明细（按 verdict 归类）
    order = {c: i for i, c in enumerate(_VERDICT_ORDER)}
    for r in sorted(records, key=lambda x: (order.get(x["verdict_code"], 99), int(x["id"] or 0))):
        print(f"#{r['id']:>3} {r['verdict_text']}  {r['tc_id'] or '-'}")
        for p in r["per_tc"]:
            extra = f"  «{p['message'][:80]}»" if p["message"] else ""
            print(f"       {p['canon']}: {p['status']}{extra}")
        print(f"       {html.unescape(r['title'][:96])}")

    rep = _reports_dir()
    (rep / f"regression_{rep.name}.json").write_text(
        json.dumps({"junit": str(args.results), "results_count": len(results),
                    "unmatched": unmatched, "records": records},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    _write_regression_md(rep / f"regression_{rep.name}.md", records, args, len(results), unmatched)
    print(f"\n[INFO] 回归报告 → {rep}/regression_{rep.name}.md (+ .json)")
    return 0


def _write_regression_md(path: Path, records, args, results_count: int, unmatched: int) -> None:
    order = {c: i for i, c in enumerate(_VERDICT_ORDER)}
    lines = [f"# 回归判定报告 {path.parent.name}", "",
             f"- junit：`{args.results}`（映射 {results_count} 用例"
             f"{f'，另 {unmatched} 条命名不符未纳入' if unmatched else ''}）",
             f"- 过滤：status={args.status or '*'} tc_prefix={args.tc_prefix or '*'} "
             f"opened_by={args.opened_by or '*'} module={args.module if args.module is not None else '*'}",
             f"- 待回归 bug：{len(records)} 条", "",
             "| bug# | TC-ID | 回归判定 | 各用例结果 |", "|---|---|---|---|"]
    for r in sorted(records, key=lambda x: (order.get(x["verdict_code"], 99), int(x["id"] or 0))):
        per = "；".join(f"{p['canon']}={p['status']}" for p in r["per_tc"]) or "（无 TC）"
        lines.append(f"| #{r['id']} | {r['tc_id'] or '-'} | {r['verdict_text']} | {per} |")
    lines += ["", "> 只读报告，未写回禅道；关单/重开人工在禅道操作。"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cred", type=Path, required=True)
    ap.add_argument("--product", type=int, required=True)
    ap.add_argument("--build", default="trunk")
    ap.add_argument("--execute", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_bug = sub.add_parser("submit-bugs"); p_bug.add_argument("--csv", type=Path, required=True)
    p_bug.set_defaults(func=cmd_submit_bugs)

    p_imp = sub.add_parser("import-cases")
    p_imp.add_argument("--md", type=Path, required=True)
    p_imp.add_argument("--module", type=int, default=0, help="兜底模块 id（默认 0=根；模块名未命中 --module-map 时用）")
    p_imp.add_argument("--module-map", default="", help="模块名=id 逗号分隔（按 md『所属模块』名映射；本实例无模块 GET API，手工给）")
    p_imp.set_defaults(func=cmd_import_cases)

    def _add_bug_filters(p, *, default_status=""):
        p.add_argument("--status", default=default_status,
                       help="bug 状态过滤，逗号分隔（active/resolved/closed）；空=不过滤")
        p.add_argument("--opened-by", dest="opened_by", default="", help="提交人账号过滤")
        p.add_argument("--module", type=int, default=None, help="模块 id 过滤")
        p.add_argument("--tc-prefix", dest="tc_prefix", default="",
                       help="按 bug 标题 TC-ID 前缀过滤：TC-AR=UI 泳道 / TC-API=API 泳道")
        p.add_argument("--title-contains", dest="title_contains", default="", help="标题子串过滤")
        p.add_argument("--resolution", default="", help="解决方案过滤（fixed 等），逗号分隔")

    p_q = sub.add_parser("query-bugs", help="只读：按 status/提交人/模块/泳道/标题 过滤列出 bug")
    _add_bug_filters(p_q)
    p_q.add_argument("--json", action="store_true", help="额外落 reports/<ts>/bugs_query_<ts>.json")
    p_q.set_defaults(func=cmd_query_bugs)

    p_r = sub.add_parser("regress-bugs",
                         help="只读：已修复 bug × junit 结果 → 回归判定报告（不写回禅道）")
    p_r.add_argument("--results", type=Path, required=True, help="pytest junit.xml 结果文件")
    _add_bug_filters(p_r, default_status="resolved")
    p_r.set_defaults(func=cmd_regress_bugs)
    return ap


def main() -> int:
    ap = build_parser(); args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
