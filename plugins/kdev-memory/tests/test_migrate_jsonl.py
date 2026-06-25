# tests/test_migrate_jsonl.py
"""test migrate_jsonl.py: 执行日志.md → 执行日志.jsonl 幂等迁移 + 冻结归档 + 零丢失兜底。

从 ieidev-team 搬来（ieidev→kdev 命名归一化）。手动 CLI 工具，不接 hook。
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import step_log, migrate_jsonl  # noqa: E402

_MD = """\
## Step 20260421-101432-ly: 丢失消息补推
triggers: ["消息补推", "SSE 断线", "gap recovery", "seq", "stream"]
日期：2026-04-21
about: feature/push

### 执行事实
- 工具调用次数：32
- 报错次数：2
- 绕路次数：1
- token 消耗感：medium
- 使用的 skill：kdev-memory, playwright
- 关键 commit：abc1234, def5678
- 涉及文件：src/x.py, src/y.py
- 关键决策：
  - 先 pub/sub 后换 stream
  - 加 seq 递增防丢
- 相关条目：G-014, Q-011, F-003

### 模型他评
- 执行质量：3/5
- 本步最值得扣分项：stream API 不熟导致 2 次报错

### 用户评分
- 完成时间：2026-04-21 17:52
- 顺畅度：4/5
- 用户评价：效果好

### 评分差异分析
- 模型 vs 用户差值：+1（弱正信号）

---

## Step 20260422-090000-ly: 推送限流
triggers: ["限流", "token bucket", "推送", "节流", "队列"]
日期：2026-04-22
about: feature/push

### 执行事实
- 工具调用次数：12
- 报错次数：0
- 绕路次数：0
- token 消耗感：light
- 相关条目：
"""


def test_lossless_line_count_and_fields(tmp_path):
    md = tmp_path / "执行日志.md"
    md.write_text(_MD, encoding="utf-8")
    res = migrate_jsonl.migrate(root=tmp_path)
    assert res["migrated"] == 2  # 行数守恒：2 个 md Step → 2 行 jsonl
    recs = step_log.read_steps(root=tmp_path)
    assert len(recs) == 2
    r0 = recs[0]
    assert r0["record_id"] == "Step 20260421-101432-ly"   # ID 逐字（冻结历史）
    assert r0["title"] == "丢失消息补推"
    assert r0["date"] == "2026-04-21"
    assert r0["about"] == "feature/push"
    assert r0["key_facts"]["tools_invoked_count"] == 32     # 字段守恒
    assert r0["key_facts"]["errors_hit"] == 2
    # 真无损：执行事实 4 数组字段不再硬编码 []，须从 md 解析（spec §10 字段守恒）
    assert r0["key_facts"]["commit_shas"] == ["abc1234", "def5678"]
    assert r0["key_facts"]["files_touched"] == ["src/x.py", "src/y.py"]
    assert r0["key_facts"]["skills_used"] == ["kdev-memory", "playwright"]
    assert r0["key_facts"]["key_decisions"] == ["先 pub/sub 后换 stream", "加 seq 递增防丢"]
    # related：G/Q/F 交叉引用指针（recall/distill 依赖，spec §10 点名）
    assert r0["key_facts"]["related"] == ["G-014", "Q-011", "F-003"]
    assert r0["model_eval"]["quality"] == 3
    assert "stream API 不熟" in r0["model_eval"]["deduction"]
    assert r0["user_rating"]["smoothness"] == 4
    assert r0["score_diff"]["delta"] == 1
    # 鲁棒性：第二条 相关条目：(空) + 无 commit/skill/files/决策 → 全 []（不崩）
    r1 = recs[1]
    assert r1["key_facts"]["related"] == []
    assert r1["key_facts"]["commit_shas"] == []
    assert r1["key_facts"]["files_touched"] == []
    assert r1["key_facts"]["skills_used"] == []
    assert r1["key_facts"]["key_decisions"] == []


def test_migrated_raw_preserved(tmp_path):
    """零丢失兜底：每条带 _migrated_raw 原文。"""
    md = tmp_path / "执行日志.md"; md.write_text(_MD, encoding="utf-8")
    migrate_jsonl.migrate(root=tmp_path)
    recs = step_log.read_steps(root=tmp_path)
    assert recs[0]["_migrated_raw"]
    assert "工具调用次数" in recs[0]["_migrated_raw"]


def test_freeze_archive(tmp_path):
    md = tmp_path / "执行日志.md"; md.write_text(_MD, encoding="utf-8")
    migrate_jsonl.migrate(root=tmp_path)
    assert not md.exists()                                  # 原 md 冻结改名
    assert (tmp_path / "执行日志.archive.md").exists()


def test_idempotent(tmp_path):
    md = tmp_path / "执行日志.md"; md.write_text(_MD, encoding="utf-8")
    migrate_jsonl.migrate(root=tmp_path)
    res2 = migrate_jsonl.migrate(root=tmp_path)             # 二次跑：无 md → 0
    assert res2["migrated"] == 0
    assert len(step_log.read_steps(root=tmp_path)) == 2     # 不翻倍


def test_migrate_no_md_returns_zero(tmp_path):
    res = migrate_jsonl.migrate(root=tmp_path)
    assert res["migrated"] == 0
    assert res["archive"] is None


_LEGACY = """\
## Step main-12: 老格式条目
日期：2026-03-01

### 执行
- 做了一些事

### 模型自评
- 顺畅度自评：4/5
- 扣分项：—

### 用户评分
- 完成时间：—
- 顺畅度：—/5
"""


def test_legacy_5section_preserves_identity(tmp_path):
    (tmp_path / "执行日志.md").write_text(_LEGACY, encoding="utf-8")
    migrate_jsonl.migrate(root=tmp_path)
    recs = step_log.read_steps(root=tmp_path)
    assert len(recs) == 1
    assert recs[0]["record_id"] == "Step main-12"      # 旧 ID 逐字（冻结历史）
    assert recs[0]["title"] == "老格式条目"
    assert recs[0]["_migrated_raw"]                     # 原文兜底在
