"""Shared Qt import shim (prefers PySide2, falls back to PySide6)."""

import sys

try:
    from PySide2 import QtCore, QtGui, QtWidgets
except ImportError:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError:
        sys.exit("PySide2/PySide6 missing. Run: bash install.sh")