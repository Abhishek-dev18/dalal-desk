#!/usr/bin/env python3
"""Dalal Desk entry point. Run from the folder where your config.json and trader/ live:

    python3 /path/to/dalal-desk/dd.py doctor
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dalal.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
