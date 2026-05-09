import json
from pathlib import Path
from collections import defaultdict
import re

def analyze_session(jsonl_path, max_lines=None):
    """深度分析单个会话"""
    events = []
    user_requests = []
    tool_calls = []
    thinking_samples = []
    errors = []
    success_markers = []

    line_count = 0
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_count += 1
            if max_lines and line_count > max_lines:
                break
            try:
                record = json.loads(line)
                ts = record.get("timestamp", "")
                rtype = record.get("type")

                # 用户请求
                if rtype == "user":
                    msg = record.get("message", {})
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        texts = []
                        for c in content:
                            if c.get("type") == "text":
                                text = c.get("text", "")
                                # 过滤元消息
                                if not any(x in text for x in ["<local-command", "<ide_opened", "tool_result", "<ide_selection"]):
                                    texts.append(text)
                        content = "\n".join(texts)
                    if content and len(content) > 10:
                        user_requests.append({
                            "line": line_count,
                            "timestamp": ts,
                            "content": content[:300],
                            "content_full": content
                        })

                # AI响应
                elif rtype == "assistant":
                    msg = record.get("message", {})
                    for c in msg.get("content", []):
                        if c.get("type") == "thinking":
                            thinking = c.get("thinking", "")
                            if thinking:
                                thinking_samples.append({
                                    "line": line_count,
                                    "timestamp": ts,
                                    "thinking": thinking[:200]
                                })
                        elif c.get("type") == "tool_use":
                            tool_name = c.get("name", "")
                            tool_calls.append({
                                "line": line_count,
                                "timestamp": ts,
                                "tool": tool_name
                            })

                # 工具结果
                if "toolUseResult" in record:
                    result = record["toolUseResult"]
                    duration = result.get("durationMs", 0)
                    filenames = result.get("filenames", [])
                    if duration > 5000:  # 超过5秒的慢调用
                        events.append({
                            "type": "slow_tool",
                            "line": line_count,
                            "duration": duration,
                            "files": len(filenames)
                        })
                    # 检查错误
                    stdout = result.get("stdout", "")
                    stderr = result.get("stderr", "")
                    if stderr or "error" in stdout.lower() or "failed" in stdout.lower():
                        errors.append({
                            "line": line_count,
                            "stderr": stderr[:200],
                            "stdout": stdout[:200]
                        })

            except Exception as e:
                pass

    return {
        "total_lines": line_count,
        "user_requests": user_requests,
        "tool_calls": tool_calls,
        "thinking_samples": thinking_samples,
        "errors": errors,
        "events": events
    }

def classify_request_quality(content):
    """评估用户请求质量"""
    score = 1
    reasons = []

    # 检查是否有具体文件路径
    if re.search(r'[a-zA-Z0-9_\-]+\.[a-zA-Z]{1,4}', content) or \
       re.search(r'(src|lib|app|plugins|docs)/', content):
        score += 1
        reasons.append("有文件路径")

    # 检查是否有具体功能描述
    if re.search(r'(添加|实现|修复|重构|删除|更新|创建)', content):
        score += 1
        reasons.append("有明确动作")

    # 检查是否有验收标准
    if re.search(r'(测试|通过|验证|检查|确保)', content):
        score += 1
        reasons.append("有验收标准")

    # 检查是否过于模糊
    if re.search(r'(帮我看看|优化一下|检查一下|分析一下)', content) and len(content) < 50:
        score = 1
        reasons.append("过于模糊")

    return min(score, 5), reasons

def analyze_tool_efficiency(tool_calls):
    """分析工具调用效率"""
    tool_counts = defaultdict(int)
    for tc in tool_calls:
        tool_counts[tc["tool"]] += 1

    # 识别过度调用
    abuse_patterns = []
    for tool, count in tool_counts.items():
        if count > 10 and tool in ["Glob", "Grep", "Read"]:
            abuse_patterns.append({"tool": tool, "count": count})

    return tool_counts, abuse_patterns

# 分析几个代表性会话
sessions_dir = Path("C:/Users/liyong/.claude/projects")

target_sessions = [
    # 大型会话 - kdev-agent (3月底到4月初)
    ("d--Works-kdev-agent", "144b8393-bafb-429f-a316-5c9efa286519.jsonl", "大型"),
    # 中型会话 - kdev-agents 4月底
    ("D--Works-SecDev-kdev-agents", "5eb6df47-f6a5-4345-a018-25761cea6299.jsonl", "中型"),
    # 小型会话
    ("D--Works-SecDev-kdev-agents", "ba1fe12f-a18f-4faa-9ac9-e9dd7d89bd7b.jsonl", "小型"),
]

print("=" * 80)
print("代表性会话深度分析")
print("=" * 80)

for proj, session_file, size_type in target_sessions:
    jsonl_path = sessions_dir / proj / session_file
    if not jsonl_path.exists():
        continue

    file_size_kb = jsonl_path.stat().st_size / 1024
    print(f"\n{'='*80}")
    print(f"会话: {proj}/{session_file}")
    print(f"类型: {size_type} | 文件大小: {file_size_kb:.1f} KB")
    print("="*80)

    # 分析（限制大型会话的行数以加快处理）
    max_lines = 2000 if size_type == "大型" else None
    result = analyze_session(jsonl_path, max_lines)

    print(f"\n基本统计:")
    print(f"  分析行数: {result['total_lines']}")
    print(f"  用户请求: {len(result['user_requests'])}")
    print(f"  工具调用: {len(result['tool_calls'])}")
    print(f"  思考片段: {len(result['thinking_samples'])}")
    print(f"  错误事件: {len(result['errors'])}")

    # 用户请求质量分析
    print(f"\n用户请求质量分析:")
    quality_scores = []
    for req in result['user_requests'][:10]:  # 分析前10个请求
        score, reasons = classify_request_quality(req['content_full'])
        quality_scores.append(score)
        print(f"  [{score}分] {req['content'][:80]}...")
        if reasons:
            print(f"         原因: {', '.join(reasons)}")

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    print(f"  平均质量评分: {avg_quality:.2f}/5")

    # 工具调用效率
    tool_counts, abuse_patterns = analyze_tool_efficiency(result['tool_calls'])
    print(f"\n工具调用分布:")
    for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {tool}: {count}")

    if abuse_patterns:
        print(f"\n潜在过度调用:")
        for abuse in abuse_patterns:
            print(f"  {abuse['tool']}: {abuse['count']}次 (可能过多)")

    # 错误分析
    if result['errors']:
        print(f"\n错误事件 ({len(result['errors'])}个):")
        for err in result['errors'][:5]:
            print(f"  行{err['line']}: {err['stderr'][:100] or err['stdout'][:100]}")

    # 思考样本分析
    if result['thinking_samples']:
        print(f"\nAI思考样本 (前3个):")
        for think in result['thinking_samples'][:3]:
            print(f"  [{think['timestamp'][:10]}] {think['thinking'][:100]}...")

print("\n" + "="*80)
print("分析完成")