import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]              # 仓根
PLUGIN = Path(__file__).resolve().parents[1]            # plugins/kdev-team


def test_plugin_json_valid():
    d = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    assert d["name"] == "kdev-team"
    assert d["version"]
    assert d["description"]


def test_registered_in_marketplace():
    mk = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    entry = [p for p in mk["plugins"] if p["name"] == "kdev-team"]
    assert len(entry) == 1
    assert entry[0]["source"] == "./plugins/kdev-team"
