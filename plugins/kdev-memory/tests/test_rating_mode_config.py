"""memory_config 评分模式 + brief verbosity reader 单测（P-C0.5 / P-C1a）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "hooks" / "lib" / "memory_config.py"
_spec = importlib.util.spec_from_file_location("memory_config", _PATH)
assert _spec and _spec.loader
memory_config = importlib.util.module_from_spec(_spec)
sys.modules["memory_config"] = memory_config
_spec.loader.exec_module(memory_config)


def _write_config(tmp_path: Path, text: str) -> Path:
    kdev = tmp_path / ".kdev" / "memory"
    kdev.mkdir(parents=True, exist_ok=True)
    (kdev / "config.yaml").write_text(text, encoding="utf-8")
    return kdev


def test_rating_mode_default_when_no_config(tmp_path):
    kdev = tmp_path / ".kdev" / "memory"
    kdev.mkdir(parents=True)
    assert memory_config.read_rating_mode(kdev) == "user-opt-in"


def test_rating_mode_flat_dot_key(tmp_path):
    kdev = _write_config(tmp_path, "rating.mode: model-only\n")
    assert memory_config.read_rating_mode(kdev) == "model-only"


def test_rating_mode_nested_form(tmp_path):
    kdev = _write_config(tmp_path, "rating:\n  mode: user-required\n")
    assert memory_config.read_rating_mode(kdev) == "user-required"


def test_rating_mode_underscore_form(tmp_path):
    kdev = _write_config(tmp_path, "rating_mode: model-only\n")
    assert memory_config.read_rating_mode(kdev) == "model-only"


def test_rating_mode_invalid_falls_back_to_default(tmp_path):
    kdev = _write_config(tmp_path, "rating.mode: bogus\n")
    assert memory_config.read_rating_mode(kdev) == "user-opt-in"


def test_rating_mode_configured_true_false(tmp_path):
    kdev_no = tmp_path / "a" / ".kdev" / "memory"
    kdev_no.mkdir(parents=True)
    (kdev_no / "config.yaml").write_text("record_mode: hybrid\n", encoding="utf-8")
    assert memory_config.rating_mode_configured(kdev_no) is False

    kdev_yes = _write_config(tmp_path, "rating.mode: model-only\n")
    assert memory_config.rating_mode_configured(kdev_yes) is True


def test_brief_verbosity_default_and_values(tmp_path):
    kdev = tmp_path / ".kdev" / "memory"
    kdev.mkdir(parents=True)
    assert memory_config.read_brief_verbosity(kdev) == "normal"

    kdev2 = _write_config(tmp_path, "brief.verbosity: compact\n")
    assert memory_config.read_brief_verbosity(kdev2) == "compact"

    kdev3 = _write_config(tmp_path, "brief.verbosity: verbose\n")
    assert memory_config.read_brief_verbosity(kdev3) == "verbose"


def test_brief_verbosity_invalid_falls_back(tmp_path):
    kdev = _write_config(tmp_path, "brief.verbosity: loud\n")
    assert memory_config.read_brief_verbosity(kdev) == "normal"
