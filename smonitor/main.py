"""Entry point: builds the QApplication, finds the icon and shows the window."""

import os
import sys

from .monitor import Monitor
from .qtcompat import QtGui, QtWidgets


def _find_icon():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = (
        os.path.join(here, "assets", "cpu-monitor.svg"),
        os.path.join(here, "cpu-monitor.svg"),
        os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps/cpu-monitor.svg"),
    )
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("cpu-monitor")
    app.setApplicationDisplayName("CPU Monitor")
    icon_path = _find_icon()
    if icon_path:
        app.setWindowIcon(QtGui.QIcon(icon_path))
    monitor = Monitor()
    if icon_path:
        monitor.setWindowIcon(QtGui.QIcon(icon_path))
    monitor.show()
    sys.exit(app.exec_())