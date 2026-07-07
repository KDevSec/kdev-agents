"""status_schema.py 单测：4 枚举判定 + 非枚举 warn。"""
from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "hooks" / "lib" / "status_schema.py"
_spec = importlib.util.spec_from_file_location("status_schema", _PATH)
assert _spec and _spec.loader
status_schema = importlib.util.module_from_spec(_spec)
sys.modules["status_schema"] = status_schema
_spec.loader.exec_module(status_schema)


class TestIsKnownStatus(unittest.TestCase):
    def test_four_enums_known(self):
        for s in ("open", "scored", "voided-faded", "voided-r-001", "voided-r-42"):
            self.assertTrue(status_schema.is_known_status(s), s)

    def test_repair_states_unknown(self):
        for s in ("fixed", "mitigated", "处置中", "prototype-validated", "设计共识"):
            self.assertFalse(status_schema.is_known_status(s), s)

    def test_empty_is_not_known(self):
        self.assertFalse(status_schema.is_known_status(""))
        self.assertFalse(status_schema.is_known_status(None))


class TestIsVoidedStatus(unittest.TestCase):
    def test_voided_forms(self):
        self.assertTrue(status_schema.is_voided_status("voided-faded"))
        self.assertTrue(status_schema.is_voided_status("voided-r-003"))

    def test_non_voided(self):
        for s in ("open", "scored", "fixed", "", None, "voided-r-nnn"):
            self.assertFalse(status_schema.is_voided_status(s), s)


class TestWarnUnknownStatus(unittest.TestCase):
    def test_warns_on_unknown(self):
        buf = io.StringIO()
        warned = status_schema.warn_unknown_status("fixed", entry_id="G-005", stream=buf)
        self.assertTrue(warned)
        out = buf.getvalue()
        self.assertIn("G-005", out)
        self.assertIn("fixed", out)
        self.assertIn("非枚举", out)

    def test_silent_on_known(self):
        buf = io.StringIO()
        warned = status_schema.warn_unknown_status("scored", entry_id="G-001", stream=buf)
        self.assertFalse(warned)
        self.assertEqual(buf.getvalue(), "")

    def test_silent_on_empty(self):
        buf = io.StringIO()
        self.assertFalse(status_schema.warn_unknown_status("", entry_id="X", stream=buf))
        self.assertEqual(buf.getvalue(), "")


class TestFallbackAndSupersededStatus(unittest.TestCase):
    """兜底方案新档：auto-fallback（待升格活态）+ voided-superseded（升格后销账）。"""

    def test_auto_fallback_known_but_not_voided(self):
        self.assertTrue(status_schema.is_known_status("auto-fallback"))
        self.assertFalse(status_schema.is_voided_status("auto-fallback"))  # 活态待升格，非销账

    def test_voided_superseded_known_and_voided(self):
        self.assertTrue(status_schema.is_known_status("voided-superseded"))
        self.assertTrue(status_schema.is_voided_status("voided-superseded"))

    def test_is_fallback_status(self):
        self.assertTrue(status_schema.is_fallback_status("auto-fallback"))
        for s in ("open", "scored", "voided-faded", "voided-superseded", "", None):
            self.assertFalse(status_schema.is_fallback_status(s), s)

    def test_new_enums_dont_warn(self):
        buf = io.StringIO()
        self.assertFalse(status_schema.warn_unknown_status("auto-fallback", stream=buf))
        self.assertFalse(status_schema.warn_unknown_status("voided-superseded", stream=buf))
        self.assertEqual(buf.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
