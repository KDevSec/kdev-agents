import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sessions_dir = Path("C:/Users/liyong/.claude/projects")

stats = defaultdict(lambda: {
    "sessions": [],
    "total_lines": 0,
    "user_msgs": 0,
    "assistant_msgs": 0,
    "tool_results": 0,
    "first_date": None,
    "last_date": None,
    "total_size_kb": 0
})

# 收集所有 D:\Works 相关项目
works_projects = []

for project_dir in sessions_dir.iterdir():
    if not project_dir.is_dir():
        continue
    # 筛选 D:\Works 相关项目
    if "Works" in project_dir.name or "works" in project_dir.name.lower():
        works_projects.append(project_dir.name)

        for jsonl_file in project_dir.glob("*.jsonl"):
            if "subagents" in str(jsonl_file):
                continue

            file_size = jsonl_file.stat().st_size / 1024  # KB
            stats[project_dir.name]["total_size_kb"] += file_size
            stats[project_dir.name]["sessions"].append(jsonl_file.name)

            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        stats[project_dir.name]["total_lines"] += 1
                        ts = record.get("timestamp", "")
                        if ts:
                            date_str = ts[:10]
                            if stats[project_dir.name]["first_date"] is None or date_str < stats[project_dir.name]["first_date"]:
                                stats[project_dir.name]["first_date"] = date_str
                            if stats[project_dir.name]["last_date"] is None or date_str > stats[project_dir.name]["last_date"]:
                                stats[project_dir.name]["last_date"] = date_str

                        rtype = record.get("type")
                        if rtype == "user":
                            stats[project_dir.name]["user_msgs"] += 1
                        elif rtype == "assistant":
                            stats[project_dir.name]["assistant_msgs"] += 1
                        elif "toolUseResult" in record:
                            stats[project_dir.name]["tool_results"] += 1
                    except Exception as e:
                        pass

print("=" * 80)
print("Claude Code 会话统计报告 - D:\\Works 相关项目")
print("=" * 80)
print(f"\n项目总数: {len(works_projects)}")

# 按时间排序
sorted_stats = sorted(stats.items(), key=lambda x: x[1]["last_date"] or "", reverse=True)

print("\n项目详情:")
print("-" * 80)
for proj, data in sorted_stats:
    session_count = len(data["sessions"])
    print(f"\n[{proj}]")
    print(f"   会话数: {session_count} | 文件大小: {data['total_size_kb']:.1f} KB")
    print(f"   时间范围: {data['first_date']} ~ {data['last_date']}")
    print(f"   消息统计: 用户={data['user_msgs']} | AI={data['assistant_msgs']} | 工具结果={data['tool_results']}")

# 统计按月份分布
monthly_stats = defaultdict(lambda: {"sessions": 0, "user_msgs": 0, "assistant_msgs": 0, "tool_results": 0})

for proj, data in stats.items():
    # 从会话文件名推断月份（通过读取文件内容获取准确时间）
    for session_file in data["sessions"]:
        jsonl_path = Path(sessions_dir) / proj / session_file
        session_month = None
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    ts = record.get("timestamp", "")
                    if ts:
                        session_month = ts[:7]  # YYYY-MM
                        break
                except:
                    pass
        if session_month:
            monthly_stats[session_month]["sessions"] += 1
            monthly_stats[session_month]["user_msgs"] += data["user_msgs"]
            monthly_stats[session_month]["assistant_msgs"] += data["assistant_msgs"]

print("\n\n按月份统计:")
print("-" * 80)
for month in sorted(monthly_stats.keys()):
    data = monthly_stats[month]
    print(f"[{month}] 会话={data['sessions']}")

# 找出最大和最有代表性的会话
print("\n\n大型会话 (>1MB):")
print("-" * 80)
large_sessions = []
for proj, data in stats.items():
    for session_file in data["sessions"]:
        jsonl_path = Path(sessions_dir) / proj / session_file
        size_kb = jsonl_path.stat().st_size / 1024
        if size_kb > 1000:  # > 1MB
            large_sessions.append((proj, session_file, size_kb))

for proj, file, size in sorted(large_sessions, key=lambda x: x[2], reverse=True)[:10]:
    print(f"   {proj}/{file}: {size:.1f} KB")

print("\n" + "=" * 80)
print("统计完成")