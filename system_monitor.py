#!/usr/bin/env python3
"""Launcher for the Sleek Monitor package."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smonitor.main import main  # noqa: E402

if __name__ == "__main__":
    main()