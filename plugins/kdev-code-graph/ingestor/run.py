#!/usr/bin/env python3
"""Zero-install entry point for kdev-ingestor.

Adds the parent directory to sys.path so `kdev_ingestor` can be imported
without `pip install`. Use this when calling from Claude Code skills or
ad-hoc shell scripts where setting up a venv is overkill.

Usage:
    python3 run.py inject --rules-dir <dir> --graph <path>
    python3 run.py list-tags --graph <path>
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add this script's directory to sys.path so `kdev_ingestor` resolves.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from kdev_ingestor.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
