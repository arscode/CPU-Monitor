"""The main monitor window: metrics, chips, processes and core tabs."""

import psutil

from . import sysinfo
from .config import (HIGHLIGHT_MB, MAX_PROCS_HINT, MODE_LABELS, OPACITY,
                     REFRESH_MS, THEMES, WINDOW_H, WINDOW_W)
from .qtcompat import QtCore, QtGui, QtWidgets
from .widgets import CoreView, ResizeGrip, Sparkline


class Monitor(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.mode = "system"
        self.theme_name = "light"
        self.theme = dict(THEMES["light"])
        self._drag = None
        self._procs = {}          # pid -> psutil.Process (for cpu_percent deltas)

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setWindowTitle("Sleek Monitor")

        self._build_ui()
        self.apply_theme()
        self._refresh()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(REFRESH_MS)
        self.setWindowOpacity(OPACITY)
        self.setMinimumSize(460, 560)
        self.resize(WINDOW_W, WINDOW_H)

    # ------------------------------------------------------------------ UI --
    def _build_ui(self):
        panel = QtWidgets.QWidget(self)
        panel.setObjectName("panel")
        panel.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        panel.setGeometry(0, 0, WINDOW_W, WINDOW_H)
        self.panel = panel

        outer = QtWidgets.QVBoxLayout(panel)
        outer.setContentsMargins(14, 10, 14, 14)
        outer.setSpacing(10)

        outer.addWidget(self._build_header())

        self.spark = Sparkline(self)
        outer.addWidget(self.spark)

        outer.addLayout(self._build_metrics())

        self.chips = QtWidgets.QLabel(panel)
        self.chips.setObjectName("subtitle")
        self.chips.setWordWrap(True)
        outer.addWidget(self.chips)

        outer.addWidget(self._build_tabs(), 1)

        self.hint = QtWidgets.QLabel(panel)
        self.hint.setObjectName("subtitle")
        outer.addWidget(self.hint)

        self._make_grips()

    def _build_tabs(self):
        self.tabs = QtWidgets.QTabWidget(self.panel)
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_table(), "Processes")
        self.core_view = CoreView(self)
        self.tabs.addTab(self.core_view, "Cores")
        return self.tabs

    def _make_grips(self):
        stick = QtCore.Qt.SizeVerCursor
        horiz = QtCore.Qt.SizeHorCursor
        diag1 = QtCore.Qt.SizeFDiagCursor
        diag2 = QtCore.Qt.SizeBDiagCursor
        e, w, n, s = (ResizeGrip.EDGE_RIGHT, ResizeGrip.EDGE_LEFT,
                      ResizeGrip.EDGE_TOP, ResizeGrip.EDGE_BOTTOM)
        specs = [
            (n, stick), (s, stick), (w, horiz), (e, horiz),
            (n, w, diag2), (n, e, diag1), (s, w, diag1), (s, e, diag2),
        ]
        self._grip_widgets = []
        for *edges, cursor in specs:
            self._grip_widgets.append(ResizeGrip(self, edges, cursor))
        self._place_grips()

    def _place_grips(self):
        T = 14
        w, h = self.width(), self.height()
        n, s, w_, e_ = (ResizeGrip.EDGE_TOP, ResizeGrip.EDGE_BOTTOM,
                        ResizeGrip.EDGE_LEFT, ResizeGrip.EDGE_RIGHT)
        spot = {
            frozenset((n,)): (T, 0, w - 2 * T, T),
            frozenset((s,)): (T, h - T, w - 2 * T, T),
            frozenset((w_,)): (0, T, T, h - 2 * T),
            frozenset((e_,)): (w - T, T, T, h - 2 * T),
            frozenset((n, w_)): (0, 0, T, T),
            frozenset((n, e_)): (w - T, 0, T, T),
            frozenset((s, w_)): (0, h - T, T, T),
            frozenset((s, e_)): (w - T, h - T, T, T),
        }
        for g in self._grip_widgets:
            key = frozenset(g.edges)
            x, y, gw, gh = spot[key]
            g.setGeometry(x, y, gw, gh)
            g.raise_()

    def resizeEvent(self, e):
        self.panel.setGeometry(self.rect())
        self._place_grips()
        super().resizeEvent(e)

    def _build_header(self):
        header = QtWidgets.QWidget(self.panel)
        header.setObjectName("header")
        header.setFixedHeight(28)
        lay = QtWidgets.QHBoxLayout(header)
        lay.setContentsMargins(2, 0, 2, 0)
        lay.setSpacing(8)

        dot = QtWidgets.QLabel("●", header)
        dot.setObjectName("title")
        dot.setStyleSheet("color: " + THEMES["dark"]["accent"] + ";")
        lay.addWidget(dot)

        title = QtWidgets.QLabel("System Monitor", header)
        title.setObjectName("title")
        lay.addWidget(title)

        self.subtitle = QtWidgets.QLabel(header)
        self.subtitle.setObjectName("subtitle")
        lay.addWidget(self.subtitle)
        lay.addStretch(1)

        self.btn_mode = QtWidgets.QToolButton(header)
        self.btn_mode.setToolTip("Theme: Auto / Light / Dark")
        self.btn_mode.clicked.connect(self.cycle_mode)
        lay.addWidget(self.btn_mode)

        self.btn_pin = QtWidgets.QToolButton(header)
        self.btn_pin.setText("📌")
        self.btn_pin.setCheckable(True)
        self.btn_pin.setChecked(True)
        self.btn_pin.setToolTip("Keep on top")
        self.btn_pin.clicked.connect(self._toggle_pin)
        lay.addWidget(self.btn_pin)

        self.btn_min = QtWidgets.QToolButton(header)
        self.btn_min.setText("–")
        self.btn_min.setToolTip("Minimize")
        self.btn_min.clicked.connect(self.showMinimized)
        lay.addWidget(self.btn_min)

        self.btn_max = QtWidgets.QToolButton(header)
        self.btn_max.setText("□")
        self.btn_max.setToolTip("Maximize")
        self.btn_max.clicked.connect(self._toggle_max)
        lay.addWidget(self.btn_max)

        self.btn_close = QtWidgets.QToolButton(header)
        self.btn_close.setText("✕")
        self.btn_close.setObjectName("title")
        self.btn_close.setToolTip("Close")
        self.btn_close.clicked.connect(self.close)
        lay.addWidget(self.btn_close)

        header.mousePressEvent = self._header_press
        header.mouseMoveEvent = self._header_move
        header.mouseReleaseEvent = lambda e: setattr(self, "_drag", None)
        return header

    def _build_metrics(self):
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(10)
        self.cpu_tile = self._make_tile("CPU")
        self.ram_tile = self._make_tile("MEMORY")
        self.temp_tile = self._make_tile("TEMP")
        self.thr_tile = self._make_tile("THROTTLE")
        for tile in (self.cpu_tile, self.ram_tile, self.temp_tile, self.thr_tile):
            row.addWidget(tile[0], 1)
        return row

    def _make_tile(self, name):
        frame = QtWidgets.QFrame(self.panel)
        frame.setObjectName("tile")
        lay = QtWidgets.QVBoxLayout(frame)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(3)

        title = QtWidgets.QLabel(name, frame)
        title.setObjectName("tile_title")
        lay.addWidget(title)

        value = QtWidgets.QLabel("--", frame)
        value.setObjectName("tile_value")
        value.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        lay.addWidget(value)

        sub = QtWidgets.QLabel("", frame)
        sub.setObjectName("tile_sub")
        lay.addWidget(sub)

        bar = QtWidgets.QProgressBar(frame)
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(7)
        bar.hide()
        lay.addWidget(bar)
        lay.addStretch(0)

        return frame, value, sub, bar

    def _build_table(self):
        self.table = QtWidgets.QTableWidget(self.panel)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Process", "PID", "CPU %", "RAM MB", "Threads"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        hh.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        hh.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        hh.setSectionResizeMode(4, QtWidgets.QHeaderView.Fixed)
        self.table.setColumnWidth(1, 58)
        self.table.setColumnWidth(2, 62)
        self.table.setColumnWidth(3, 78)
        self.table.setColumnWidth(4, 68)
        return self.table

    # -------------------------------------------------------------- themes --
    def _qss(self):
        t = self.theme
        return f"""
        #panel {{
            background: {t['window']};
            border: 1px solid {t['border']};
            border-radius: 18px;
        }}
        #header {{ background: transparent; }}
        #spark   {{ background: transparent; }}
        QLabel#title    {{ color: {t['text']}; font-size: 13px; font-weight: 600; }}
        QLabel#subtitle {{ color: {t['muted']}; font-size: 10px; }}
        QFrame#tile {{
            background: {t['metric_bg']};
            border: 1px solid {t['frame']};
            border-radius: 12px;
        }}
        QLabel#tile_title {{ color: {t['muted']}; font-size: 9px; font-weight: 600; }}
        QLabel#tile_value {{ color: {t['text']}; font-size: 20px; font-weight: 600; }}
        QLabel#tile_sub   {{ color: {t['muted']}; font-size: 9px; }}
        QProgressBar {{
            background: {t['bar_bg']};
            border: none; border-radius: 3px;
        }}
        QProgressBar::chunk {{ background: {t['accent']}; border-radius: 3px; }}
        QTableWidget {{
            background: transparent;
            border: 1px solid {t['grid']};
            border-radius: 12px;
            gridline-color: {t['grid']};
            color: {t['text']};
            font-size: 11px;
        }}
        QTableWidget::item {{ padding: 3px 6px; }}
        QHeaderView::section {{
            background: {t['header']};
            color: {t['muted']};
            border: none;
            padding: 5px 6px;
            font-size: 9px; font-weight: 600;
        }}
        QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
        QScrollBar::handle:vertical {{ background: {t['scroll']}; border-radius: 4px; min-height: 24px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QToolButton {{
            background: {t['metric_bg']};
            color: {t['muted']};
            border: 1px solid {t['frame']};
            border-radius: 7px;
            padding: 3px 7px;
            font-size: 10px;
        }}
        QToolButton:hover {{ color: {t['text']}; }}
        QToolButton:checked {{ color: {t['accent']}; border-color: {t['accent']}; }}
        QTabWidget::pane {{ border: none; background: transparent; }}
        QTabBar {{ background: transparent; }}
        QTabBar::tab {{
            background: transparent;
            color: {t['muted']};
            padding: 5px 16px;
            font-size: 11px; font-weight: 600;
            border-bottom: 2px solid transparent;
        }}
        QTabBar::tab:selected {{ color: {t['text']}; border-bottom: 2px solid {t['accent']}; }}
        QTabBar::tab:hover {{ color: {t['text']}; }}
        """

    def apply_theme(self):
        self.panel.setStyleSheet(self._qss())
        self.btn_mode.setText(MODE_LABELS[self.mode])

    def set_theme(self, name):
        self.theme = dict(THEMES[name])
        self.theme_name = name
        self.apply_theme()

    def cycle_mode(self):
        order = ("system", "light", "dark")
        self.mode = order[(order.index(self.mode) + 1) % len(order)]
        self.apply_theme()
        if self.mode == "system":
            self.set_theme(sysinfo.detect_system_theme())
        else:
            self.set_theme(self.mode)

    # ----------------------------------------------------------- window drag
    def _header_press(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()

    def _header_move(self, e):
        if self._drag is not None and e.buttons() & QtCore.Qt.LeftButton:
            self.move(e.globalPos() - self._drag)
            e.accept()

    def _toggle_pin(self, checked):
        flags = self.windowFlags()
        if checked:
            flags |= QtCore.Qt.WindowStaysOnTopHint
        else:
            flags &= ~QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_max.setText("□")
            self.btn_max.setToolTip("Maximize")
        else:
            self.showMaximized()
            self.btn_max.setText("❐")
            self.btn_max.setToolTip("Restore")

    # ------------------------------------------------------------- refresh --
    def _refresh(self):
        if self.mode == "system":
            want = "dark" if sysinfo.detect_system_theme() == "dark" else "light"
            if want != self.theme_name:
                self.set_theme(want)

        cpu = psutil.cpu_percent(None)
        vm = psutil.virtual_memory()
        temp, tzone = sysinfo.read_temperature()
        core_thr, pkg_thr = sysinfo.read_throttle()
        cur, fmax, gov = sysinfo.read_freqs()
        load1, nthreads, cores = sysinfo.collect_threads()

        self.spark.add(cpu)

        self._set_tile_values(cpu, vm, temp, tzone,
                              core_thr, pkg_thr, cur, fmax, gov)

        core_count = cores if cores else (psutil.cpu_count(logical=True) or 0)
        self.subtitle.setText(f"Load {load1:.2f}  •  {nthreads} threads  •  {core_count} cores")
        self._refresh_chips()
        self._refresh_core_view()
        self._refresh_processes()

    def _refresh_chips(self):
        parts = []
        for dev, deg in sorted(sysinfo.read_nvme_temps().items()):
            parts.append(f"{dev} {deg:.0f}°C")
        pch, _ = sysinfo.read_pch_temp()
        if pch is not None:
            parts.append(f"PCH {pch:.0f}°C")
        ram, _ = sysinfo.read_ram_temp()
        if ram is not None:
            parts.append(f"RAM {ram:.0f}°C")
        if not parts:
            self.chips.setText("SSD / PCH / RAM temps: not exposed on this system")
        else:
            self.chips.setText("  •  ".join(parts))

    def _refresh_core_view(self):
        core_map = sysinfo.collect_core_map()
        core_temps = sysinfo.read_core_temps()
        rows = []
        for core in sorted(core_map):
            threads = core_map[core]
            names, seen = [], set()
            for pid, tid, name in threads:
                if name not in seen:
                    seen.add(name)
                    names.append(name)
            rows.append({
                "idx": core,
                "count": len(threads),
                "names": names[:4],
                "unique": len(names),
                "temp": core_temps.get(core),
            })
        maxc = max([r["count"] for r in rows], default=1)
        self.core_view.set_data(rows, maxc)

    # ----------------------------------------------------------- tile values
    def _set_tile_values(self, cpu, vm, temp, tzone,
                         core_thr, pkg_thr, cur, fmax, gov):
        t = self.theme

        # CPU
        _, cpu_v, cpu_s, cpu_b = self.cpu_tile
        cpu_v.setText(f"{cpu:.0f}%")
        cpu_s.setText(f"{cur / 1e6:.2f} GHz" if cur else "freq n/a")
        cpu_b.setValue(int(cpu))
        cpu_b.show()

        # RAM
        _, ram_v, ram_s, ram_b = self.ram_tile
        used = vm.used / (1024 ** 3)
        total = vm.total / (1024 ** 3)
        ram_v.setText(f"{vm.percent:.0f}%")
        ram_s.setText(f"{used:.1f} / {total:.0f} GB")
        ram_b.setValue(int(vm.percent))
        ram_b.show()

        # Temperature
        _, temp_v, temp_s, _ = self.temp_tile
        if temp is not None:
            temp_v.setText(f"{temp:.0f} °C")
            color = t["ok"] if temp < 70 else (t["warn"] if temp < 85 else t["hot"])
            temp_v.setStyleSheet(f"color: {color};")
            temp_s.setText(tzone)
        else:
            temp_v.setText("n/a")
            temp_v.setStyleSheet("")
            temp_s.setText("no sensor")

        # Throttle
        _, thr_v, thr_s, thr_b = self.thr_tile
        thr_b.hide()
        if core_thr or pkg_thr:
            thr_v.setText("THROTTLED")
            thr_v.setStyleSheet(f"color: {t['hot']};")
            thr_s.setText(f"core {core_thr} · pkg {pkg_thr} events")
        elif cur and fmax:
            ratio = cur / fmax
            if ratio >= 0.95:
                thr_v.setText("OK")
                thr_v.setStyleSheet(f"color: {t['ok']};")
                thr_s.setText(f"{cur / 1e6:.1f} / {fmax / 1e6:.1f} GHz · {gov or '?'}")
            else:
                thr_v.setText(f"{ratio * 100:.0f}%")
                thr_v.setStyleSheet(f"color: {t['warn']};")
                thr_s.setText(f"low freq · {gov or '?'}")
        else:
            thr_v.setText("n/a")
            thr_v.setStyleSheet("")
            thr_s.setText("no cpufreq")

    # ---------------------------------------------------------- process table
    def _refresh_processes(self):
        t = self.theme
        seen = set()
        rows = []
        for p in psutil.process_iter():
            pid = p.pid
            seen.add(pid)
            proc = self._procs.get(pid)
            if proc is None or proc.pid != pid:
                try:
                    proc = psutil.Process(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                self._procs[pid] = proc
            try:
                name = proc.name() or "?"
                cpus = proc.cpu_percent(None)
                rss = proc.memory_info().rss / (1024 * 1024)
                thr = proc.num_threads()
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            rows.append((rss, pid, name, cpus, thr))

        for pid in set(self._procs) - seen:
            self._procs.pop(pid, None)

        rows.sort(reverse=True, key=lambda r: r[0])
        if len(rows) > MAX_PROCS_HINT:
            rows = rows[:MAX_PROCS_HINT]

        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(rows))
        high = 0
        for i, (rss, pid, name, cpus, thr) in enumerate(rows):
            if len(name) > 28:
                name = name[:27] + "…"
            cells = (name, str(pid), f"{cpus:4.1f}", f"{rss:6.0f}", str(thr))
            is_high = rss >= HIGHLIGHT_MB
            if is_high:
                high += 1
            for col, text in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(text)
                if col > 0:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                fg = QtGui.QColor(t["hot"]) if is_high else QtGui.QColor(t["text"])
                item.setForeground(fg)
                if is_high:
                    item.setBackground(QtGui.QColor(t["highlight"]))
                self.table.setItem(i, col, item)
        self.table.setUpdatesEnabled(True)
        self.table.viewport().update()

        self.hint.setText(
            f"{high} app{'s' if high != 1 else ''} above {HIGHLIGHT_MB} MB "
            f"highlighted · refreshed every {REFRESH_MS // 1000}s")