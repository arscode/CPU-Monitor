"""Reusable Qt widgets: Sparkline, CoreView (core chart) and ResizeGrip."""

from collections import deque

from .qtcompat import QtCore, QtGui, QtWidgets


class Sparkline(QtWidgets.QWidget):
    """Compact CPU-history line with a soft gradient fill."""

    def __init__(self, monitor):
        super().__init__(monitor.panel)
        self.monitor = monitor
        self.data = deque(maxlen=90)
        self.setObjectName("spark")
        self.setFixedHeight(50)
        self.setMinimumWidth(120)

    def add(self, value):
        self.data.append(value)
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        t = self.monitor.theme
        w, h = self.width(), self.height()

        p.setPen(QtGui.QPen(QtGui.QColor(t["metric_bg"]), 1))
        p.setBrush(QtGui.QColor(t["metric_bg"]))
        p.drawRoundedRect(QtCore.QRectF(1, 1, w - 2, h - 2), 10, 10)

        if len(self.data) < 2:
            p.setPen(QtGui.QColor(t["muted"]))
            p.drawText(self.rect(), QtCore.Qt.AlignCenter, "No data yet")
            return

        pad = 6.0
        mx, mn = max(self.data), min(self.data)
        span = max(mx - mn, 1.0)
        n = len(self.data)
        step = (w - 2 * pad) / (n - 1)
        pts = [QtCore.QPointF(pad + i * step,
                              h - pad - (v - mn) / span * (h - 2 * pad))
               for i, v in enumerate(self.data)]

        path = QtGui.QPainterPath(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)

        fill = QtGui.QPainterPath(path)
        fill.lineTo(QtCore.QPointF(pts[-1].x(), h - 2))
        fill.lineTo(QtCore.QPointF(pts[0].x(), h - 2))
        fill.closeSubpath()

        accent = QtGui.QColor(t["accent"])
        grad = QtGui.QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QtGui.QColor(accent.red(), accent.green(),
                                          accent.blue(), 90))
        grad.setColorAt(1.0, QtGui.QColor(accent.red(), accent.green(),
                                          accent.blue(), 10))
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(grad)
        p.drawPath(fill)

        pen = QtGui.QPen(accent, 2)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawPath(path)

        p.setRenderHint(QtGui.QPainter.Antialiasing, False)
        p.setPen(QtGui.QColor(t["grid"]))
        p.drawLine(0, h - 1, w, h - 1)


class CoreView(QtWidgets.QWidget):
    """Bar chart: threads on each CPU core, bar colour = core temperature."""

    def __init__(self, monitor):
        super().__init__(monitor.panel)
        self.monitor = monitor
        self.rows = []
        self.max_count = 1
        self.setObjectName("spark")
        self.setMinimumHeight(180)

    def set_data(self, rows, max_count):
        self.rows = rows
        self.max_count = max_count or 1
        self.update()

    def _temp_color(self, temp, t):
        if temp is None:
            return QtGui.QColor(t["accent"])
        if temp < 60:
            return QtGui.QColor(t["ok"])
        if temp < 80:
            return QtGui.QColor(t["warn"])
        return QtGui.QColor(t["hot"])

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        t = self.monitor.theme
        w, h = self.width(), self.height()

        if not self.rows:
            p.setPen(QtGui.QColor(t["muted"]))
            p.drawText(self.rect(), QtCore.Qt.AlignCenter, "Collecting thread placement…")
            return

        head = 18
        lab_w = 34
        cnt_w = 52
        pad = 10
        n = len(self.rows)
        rowh = max(22, (h - head) / n)

        p.setPen(QtGui.QColor(t["muted"]))
        p.drawText(QtCore.QRect(0, 0, w, 16), QtCore.Qt.AlignLeft,
                   "bar = threads on core · colour = core temp")

        for i, r in enumerate(self.rows):
            y0 = head + i * rowh
            bar_h = max(6, rowh - 8)

            p.setPen(QtGui.QColor(t["text"]))
            p.drawText(QtCore.QRect(2, int(y0), lab_w - 4, int(bar_h)),
                       QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
                       "C%d" % r["idx"])

            bar_x = lab_w + pad
            bar_w = w - bar_x - cnt_w - pad

            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(t["bar_bg"]))
            p.drawRoundedRect(QtCore.QRectF(bar_x, y0, bar_w, bar_h), 4, 4)

            fill_w = max(2.0, bar_w * r["count"] / self.max_count)
            col = self._temp_color(r["temp"], t)
            p.setBrush(col)
            p.drawRoundedRect(QtCore.QRectF(bar_x, y0, fill_w, bar_h), 4, 4)

            p.setPen(QtGui.QColor(t["text"]))
            p.drawText(QtCore.QRect(bar_x + bar_w + 4, int(y0), cnt_w - 4, int(bar_h)),
                       QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight, str(r["count"]))

            names_x = bar_x + bar_w + cnt_w
            names_w = w - names_x - 4
            if names_w > 40:
                p.setPen(QtGui.QColor(t["muted"]))
                text = ", ".join(r["names"])
                if len(r["names"]) < r["unique"]:
                    text += "…"
                p.drawText(QtCore.QRect(names_x, int(y0), names_w, int(bar_h)),
                           QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, text)


class ResizeGrip(QtWidgets.QWidget):
    """Invisible strip on a window edge used to resize a frameless window."""

    EDGE_LEFT, EDGE_RIGHT, EDGE_TOP, EDGE_BOTTOM = "w", "e", "n", "s"

    def __init__(self, monitor, edges, cursor, size=8):
        super().__init__(monitor)
        self.monitor = monitor
        self.edges = set(edges)
        self.setCursor(cursor)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self._start_geom = None
        self._start_global = None

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._start_geom = self.monitor.geometry()
            self._start_global = e.globalPos()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._start_geom is None:
            return
        d = e.globalPos() - self._start_global
        geom = QtCore.QRect(self._start_geom)
        if "w" in self.edges:
            geom.setLeft(geom.left() + d.x())
        if "e" in self.edges:
            geom.setRight(geom.right() + d.x())
        if "n" in self.edges:
            geom.setTop(geom.top() + d.y())
        if "s" in self.edges:
            geom.setBottom(geom.bottom() + d.y())
        if geom.width() >= self.monitor.minimumWidth() and \
           geom.height() >= self.monitor.minimumHeight():
            self.monitor.setGeometry(geom)
        e.accept()

    def mouseReleaseEvent(self, e):
        self._start_geom = None
        self._start_global = None
        e.accept()