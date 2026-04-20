#!/usr/bin/env bash
# kdev-memory evals 轻量自验证
# 跑 evals.json 里的 10 个 prompt，每个直接喂给 UserPromptSubmit hook，
# 验证召回机制正确（should-trigger 命中，should-not-trigger 静默）。
#
# 这是机制层的确定性测试——比 skill-creator 完整 eval 快得多，够用于 CI
# 或开发自验证。skill-creator 完整 eval 的价值是测 Claude 的语义行为
# （召回后是否用好），是另外的事。
#
# 用法：bash plugins/kdev-memory/evals/run-hook-selftest.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
FIXTURE_DIR="$SCRIPT_DIR/fixtures/project-state"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 not found" >&2
  exit 1
fi

cd "$FIXTURE_DIR"

# 清一下可能的历史 state（避免 session 去重影响本次）
rm -rf .kdev/memory/state

PLUGIN="$PLUGIN_DIR" python3 <<'PYEOF'
import json, subprocess, pathlib, os, re

evals = json.loads(pathlib.Path(os.environ["PLUGIN"], "evals", "evals.json").read_text())["evals"]
plugin = os.environ["PLUGIN"]

pass_count = 0
fail_count = 0
for ev in evals:
    payload = json.dumps({"prompt": ev["prompt"], "session_id": f"eval-{ev['id']}"})
    result = subprocess.run(
        ["bash", f"{plugin}/hooks/user-prompt-trigger.sh"],
        input=payload, capture_output=True, text=True, timeout=15,
    )
    try:
        out = json.loads(result.stdout)
    except json.JSONDecodeError:
        out = {}
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    triggered = bool(ctx)
    expected = ev["category"] == "should-trigger"
    ok = (triggered == expected)
    if ok:
        pass_count += 1
        marker = "[PASS]"
    else:
        fail_count += 1
        marker = "[FAIL]"
    tag = ""
    if triggered and ctx:
        hits = re.findall(r"\*\*([^*]+)\*\*", ctx)
        if hits:
            tag = f" -> {', '.join(hits)}"
    print(f"{marker} [{ev['id']:2d}] {ev['name']:<38s} exp={expected}, act={triggered}{tag}")

print(f"\n{pass_count}/{len(evals)} pass, {fail_count} fail")
import sys
sys.exit(0 if fail_count == 0 else 1)
PYEOF
