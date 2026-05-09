import json
from pathlib import Path
from collections import defaultdict
import re

# 模式定义
SUCCESS_PATTERNS = {
    "完成确认": ["完成", "成功", "已实现", "merged", "passed", "完美", "很好", "感谢", "谢谢"],
    "测试通过": ["test passed", "tests passing", "all tests pass"],
    "代码提交": ["commit", "committed", "pushed"],
}

FAILURE_PATTERNS = {
    "错误": ["error", "failed", "失败", "报错", "异常", "抱歉", "无法"],
    "中断": ["interrupted", "cancelled", "aborted"],
    "超时": ["timeout", "timed out"],
}

EFFICIENT_TOOL_PATTERNS = {
    "并行调用": "多工具在同一条消息中",
    "快速定位": "单次 Glob/Grep 找到目标",
}

INEFFICIENT_TOOL_PATTERNS = {
    "重复搜索": "同类型工具调用 >10次",
    "盲目探索": "连续 Glob 无明确目标",
}

def scan_all_sessions_for_patterns():
    """扫描所有会话识别模式"""
    sessions_dir = Path("C:/Users/liyong/.claude/projects")

    results = {
        "success_events": [],
        "failure_events": [],
        "tool_efficiency": {"efficient": [], "inefficient": []},
        "user_request_quality": [],
        "session_stats": []
    }

    works_projects = []
    for project_dir in sessions_dir.iterdir():
        if "Works" in project_dir.name:
            works_projects.append(project_dir.name)
            for jsonl_file in project_dir.glob("*.jsonl"):
                if "subagents" in str(jsonl_file):
                    continue

                session_stats = analyze_session_patterns(jsonl_file)
                results["session_stats"].append({
                    "project": project_dir.name,
                    "session": jsonl_file.name,
                    **session_stats
                })

    return results

def analyze_session_patterns(jsonl_path):
    """分析会话中的模式"""
    stats = {
        "total_lines": 0,
        "success_count": 0,
        "failure_count": 0,
        "tool_calls_by_type": defaultdict(int),
        "slow_tools": 0,
        "user_requests_count": 0,
        "avg_request_length": 0,
        "request_lengths": [],
        "thinking_count": 0,
        "skill_invocations": 0,
        "error_events": [],
        "success_markers": [],
    }

    prev_tool_calls = []
    consecutive_same_tool = 0

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            stats["total_lines"] += 1
            try:
                record = json.loads(line)
                ts = record.get("timestamp", "")
                rtype = record.get("type")

                if rtype == "user":
                    msg = record.get("message", {})
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                        content = " ".join(texts)
                    # 过滤元消息
                    if content and not any(x in content for x in ["<local-command", "<ide_", "tool_result", "tool_use_id"]):
                        stats["user_requests_count"] += 1
                        stats["request_lengths"].append(len(content))

                        # 检查成功/失败模式
                        for pattern_name, keywords in SUCCESS_PATTERNS.items():
                            if any(k in content for k in keywords):
                                stats["success_markers"].append({
                                    "type": pattern_name,
                                    "content": content[:100]
                                })
                                stats["success_count"] += 1

                        for pattern_name, keywords in FAILURE_PATTERNS.items():
                            if any(k.lower() in content.lower() for k in keywords):
                                stats["error_events"].append({
                                    "type": pattern_name,
                                    "content": content[:100]
                                })
                                stats["failure_count"] += 1

                elif rtype == "assistant":
                    msg = record.get("message", {})
                    current_tools = []
                    for c in msg.get("content", []):
                        if c.get("type") == "thinking":
                            stats["thinking_count"] += 1
                        elif c.get("type") == "tool_use":
                            tool_name = c.get("name", "")
                            stats["tool_calls_by_type"][tool_name] += 1
                            current_tools.append(tool_name)

                            if tool_name == "Skill":
                                stats["skill_invocations"] += 1

                    # 检查并行调用
                    if len(current_tools) > 1:
                        stats["efficient_pattern_parallel"] = stats.get("efficient_pattern_parallel", 0) + 1

                    # 检查重复调用
                    if current_tools and prev_tool_calls:
                        overlap = set(current_tools) & set(prev_tool_calls)
                        if overlap:
                            consecutive_same_tool += 1

                    prev_tool_calls = current_tools

                # 工具结果分析
                if "toolUseResult" in record:
                    result = record["toolUseResult"]
                    duration = result.get("durationMs", 0)
                    if duration > 10000:  # 超过10秒
                        stats["slow_tools"] += 1

                    stderr = result.get("stderr", "")
                    if stderr and "error" in stderr.lower():
                        stats["failure_count"] += 1
                        stats["error_events"].append({
                            "type": "tool_error",
                            "content": stderr[:100]
                        })

            except:
                pass

    if stats["request_lengths"]:
        stats["avg_request_length"] = sum(stats["request_lengths"]) / len(stats["request_lengths"])

    # 识别低效模式
    for tool, count in stats["tool_calls_by_type"].items():
        if count > 15 and tool in ["Glob", "Grep", "Read"]:
            stats["inefficient_excessive_" + tool] = count

    return stats

def generate_report(results):
    """生成分析报告"""
    report_lines = []

    # 概览统计
    total_sessions = len(results["session_stats"])
    total_lines = sum(s["total_lines"] for s in results["session_stats"])
    total_user_requests = sum(s["user_requests_count"] for s in results["session_stats"])
    total_success = sum(s["success_count"] for s in results["session_stats"])
    total_failure = sum(s["failure_count"] for s in results["session_stats"])
    total_skill_calls = sum(s["skill_invocations"] for s in results["session_stats"])

    report_lines.append("# Claude Code 开发经验分析报告")
    report_lines.append("")
    report_lines.append("## 概览")
    report_lines.append(f"- 分析会话数: {total_sessions}")
    report_lines.append(f"- 总行数: {total_lines}")
    report_lines.append(f"- 用户请求总数: {total_user_requests}")
    report_lines.append(f"- 成功事件: {total_success}")
    report_lines.append(f"- 失败事件: {total_failure}")
    report_lines.append(f"- Skill调用: {total_skill_calls}")
    report_lines.append(f"- 时间范围: 2026-03-01 ~ 2026-05-08")
    report_lines.append("")

    # 汇总工具调用
    all_tool_calls = defaultdict(int)
    inefficient_tools = defaultdict(int)
    for s in results["session_stats"]:
        for tool, count in s["tool_calls_by_type"].items():
            all_tool_calls[tool] += count
        for key, value in s.items():
            if key.startswith("inefficient_excessive_"):
                tool = key.replace("inefficient_excessive_", "")
                inefficient_tools[tool] += value

    report_lines.append("## 一、工具使用分析")
    report_lines.append("")
    report_lines.append("### 1.1 工具调用分布 (TOP10)")
    report_lines.append("| 工具 | 调用次数 | 占比 |")
    report_lines.append("|------|----------|------|")
    total_calls = sum(all_tool_calls.values())
    for tool, count in sorted(all_tool_calls.items(), key=lambda x: x[1], reverse=True)[:10]:
        pct = f"{count/total_calls*100:.1f}%"
        report_lines.append(f"| {tool} | {count} | {pct} |")
    report_lines.append("")

    report_lines.append("### 1.2 低效调用识别")
    report_lines.append("| 工具 | 过度调用次数 | 建议 |")
    report_lines.append("|------|--------------|------|")
    for tool, count in inefficient_tools.items():
        suggestion = "限制探索范围，使用更精确的路径/模式" if tool in ["Glob", "Grep"] else "合并读取请求，减少碎片化读取"
        report_lines.append(f"| {tool} | {count} | {suggestion} |")
    report_lines.append("")

    # 成功模式
    report_lines.append("## 二、成功模式")
    report_lines.append("")
    report_lines.append("### 2.1 成功事件类型分布")
    success_types = defaultdict(int)
    for s in results["session_stats"]:
        for marker in s["success_markers"]:
            success_types[marker["type"]] += 1
    for stype, count in sorted(success_types.items(), key=lambda x: x[1], reverse=True):
        report_lines.append(f"- **{stype}**: {count}次")
    report_lines.append("")

    report_lines.append("### 2.2 高效协作特征")
    parallel_count = sum(s.get("efficient_pattern_parallel", 0) for s in results["session_stats"])
    report_lines.append(f"- **并行工具调用**: {parallel_count}次 (多工具同时执行，减少轮次)")
    report_lines.append(f"- **Skill使用**: {total_skill_calls}次 (遵循既定流程)")
    report_lines.append("")

    # 失败模式
    report_lines.append("## 三、失败教训")
    report_lines.append("")
    report_lines.append("### 3.1 失败事件类型分布")
    failure_types = defaultdict(int)
    for s in results["session_stats"]:
        for err in s["error_events"]:
            failure_types[err["type"]] += 1
    for ftype, count in sorted(failure_types.items(), key=lambda x: x[1], reverse=True):
        report_lines.append(f"- **{ftype}**: {count}次")
    report_lines.append("")

    avg_request_len = sum(s["avg_request_length"] for s in results["session_stats"] if s["avg_request_length"] > 0) / max(1, len([s for s in results["session_stats"] if s["avg_request_length"] > 0]))
    report_lines.append("### 3.2 用户指令问题")
    report_lines.append(f"- **平均请求长度**: {avg_request_len:.0f}字符")
    if avg_request_len < 100:
        report_lines.append("  - ⚠️ 指令过短，缺少必要上下文")
    report_lines.append("")

    # 规范建议
    report_lines.append("## 四、规范建议")
    report_lines.append("")
    report_lines.append("### 4.1 用户端规范")
    report_lines.append("")
    report_lines.append("**DO (应该做的):**")
    report_lines.append("- ✅ 提供具体文件路径 (`src/auth/login.ts`)")
    report_lines.append("- ✅ 明确功能边界 (`添加JWT验证，不含登录UI`)")
    report_lines.append("- ✅ 说明验收标准 (`需通过 tests/auth.test.ts`)")
    report_lines.append("- ✅ 请求长度 >100字符 (提供足够上下文)")
    report_lines.append("")
    report_lines.append("**DON'T (避免做的):**")
    report_lines.append("- ❌ 模糊指令 (`帮我看看这个代码`)")
    report_lines.append("- ❌ 无边界 (`优化一下`)")
    report_lines.append("- ❌ 无验收标准 (`改好就行`)")
    report_lines.append("")

    report_lines.append("### 4.2 Claude端规范")
    report_lines.append("")
    report_lines.append("**工具调用原则:**")
    report_lines.append("- Glob/Grep 调用 <10次/任务 (使用精确路径)")
    report_lines.append("- 并行调用替代串行 (`Glob + Read` 同时执行)")
    report_lines.append("- 先 Skill 再探索 (遵循既定流程)")
    report_lines.append("")
    report_lines.append("**错误处理:**")
    report_lines.append("- 工具超时 >10秒需重评估策略")
    report_lines.append("- 错误发生后先分析根因再行动")
    report_lines.append("")

    report_lines.append("### 4.3 项目配置规范")
    report_lines.append("```markdown")
    report_lines.append("# CLAUDE.md 建议")
    report_lines.append("")
    report_lines.append("## 工具使用约束")
    report_lines.append("- Glob: 使用精确路径，避免 `**/*` 大范围搜索")
    report_lines.append("- Read: 优先读取关键文件，合并请求")
    report_lines.append("")
    report_lines.append("## Skill触发")
    report_lines.append("- 实现任务 → 先调用 brainstorming skill")
    report_lines.append("- Bug修复 → 先调用 debugging skill")
    report_lines.append("```")
    report_lines.append("")

    return "\n".join(report_lines)

# 执行分析
print("开始扫描会话...")
results = scan_all_sessions_for_patterns()
print(f"扫描完成: {len(results['session_stats'])}个会话")

# 生成报告
report = generate_report(results)

# 输出到文件
output_path = Path("d:/Works/SecDev/kdev-agents/docs/framework/01-design/2026-05-08-会话分析报告.md")
output_path.write_text(report, encoding='utf-8')
print(f"报告已保存: {output_path}")