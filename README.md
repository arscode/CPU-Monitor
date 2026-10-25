# cpu-monitor

A sleek, semi-transparent system monitor panel for Ubuntu/Linux. Frameless +
rounded, with Auto/Light/Dark themes (Auto follows the GNOME system theme).

## Features

- **CPU usage** with live history sparkline
- **RAM usage** (used / total + percent bar)
- **CPU temperature** from the kernel thermal zones (colour coded), plus
  **SSD / PCH / RAM chip temps** when the kernel exposes them (read-only)
- **Throttling** — core/package throttle event counters plus the
  current-vs-max frequency ratio (with governor name)
- **Active threads** across all running processes + load average + core count
- **Cores tab** — per-core bar chart of thread placement, colour-coded by the
  core's own temperature, showing which processes run on each core
- **Process table** lists **all** processes sorted by RAM (scrollable),
  with hoggers above the threshold tinted red

## Requirements

- **Ubuntu 20.04 LTS or newer** (Debian 11+ also works; this is a Linux app).
- **GNOME/GTK desktop** is assumed for the Auto theme; on other desktops just
  use the Light/Dark toggle.
- Works best under **X11**; frameless-window behaviour (pin-to-top, edge
  resize grips) is less predictable under Wayland.

Preview / grab the source first:

```bash
git clone https://github.com/arscode/cpu_monitor.git
cd cpu_monitor
# ...or a plain download: GitHub green "Code" button → Download ZIP
```

`sudo apt-get install python3-pip python3-venv` is needed on Ubuntu 20.04
(the default Python there is 3.8) — newer releases already have them.

**Python version support:** the installer pins PySide2 ≥5.15 for Python
3.8–3.9 and switches **automatically to PySide6 ≥6.2** on Python 3.10+
(environment markers in `requirements.txt`; `smonitor/qtcompat.py` imports
whichever is present).

## Install

```bash
bash install.sh
```

Two things to expect:

- If the shared Qt libraries (`libGL`) are missing, the installer will
  **prompt for your sudo password** and install `libgl1 libegl1
  libxkbcommon-x11-0 libdbus-1-3` via apt. That's its only sudo use.
- It copies the app into a dedicated directory **`~/.sleek-monitor`**, creates
  a virtualenv there and installs PySide2/PySide6 + psutil into it. Your
  source files stay where they are.

## Run

```bash
cpu-monitor      # command installed to ~/.local/bin by install.sh
```

If the shell says `command not found`, `~/.local/bin` is not on your PATH —
add it to `~/.profile` and re-open the terminal:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Alternatively launch `~/.sleek-monitor/run.sh` directly, or pin it from the
app grid: open **Activities**, search "CPU Monitor", right-click →
**Add to Favorites**.

## Run from source (without installing)

`run.sh` always points at the installed copy. To run straight from this
directory instead:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python system_monitor.py
```

## Uninstall

```bash
bash uninstall.sh
```

This removes the installed copy + venv at `~/.sleek-monitor`, the
`cpu-monitor` command, the desktop entry and the icon. Your source files
(`system_monitor.py`, README, ...) are **kept**. It also prints
the command to remove the apt-installed Qt libs (`libgl1`, `libegl1`, ...),
which are left installed by default in case other Qt apps use them.

## Themes

Click the **Auto / Light / Dark** button to cycle. `Auto` reads
`org.gnome.desktop.interface color-scheme` (and falls back to `gtk-theme`),
so it tracks the GNOME dark-mode toggle automatically.

## Details

- Header shows minimize (–) / maximize (□) / close (✕) buttons next to the
  theme and pin controls. Drag the header to move it; drag any edge or corner
  to resize (min 460×560). It stays on top by default; 📌 pins/unpins it.
- The table lists **all processes** (up to `MAX_PROCS_HINT` rows, default
  500) sorted by RAM (scroll to browse); rows above the highlight threshold
  are tinted red. The **Cores** tab shows a
  bar chart of how many threads land on each core (bar colour = that core's
  coretemp reading) plus the process names running there.
- Highlight threshold is `HIGHLIGHT_MB` (default 256 MB) and the refresh
  interval is `REFRESH_MS` (default 1500 ms), both near the top of
  `smonitor/config.py`.
- Temperature threshold colours: green < 70 °C, amber 70–85 °C, red 85 °C
  and above.
- Throttling is read from `/sys/devices/system/cpu/cpu*/thermal_throttle`
  counters. On hardware/kernels that expose them you'll see the exact count;
  otherwise the current-vs-max frequency ratio is used as a live estimate.

## Project layout

The code is split into small modules so each concern is easy to find, debug
and test in isolation:

```
system_monitor.py      launcher (thin entry point)
smonitor/
  config.py            constants, themes, tunables (HIGHLIGHT_MB, REFRESH_MS...)
  qtcompat.py          PySide2/PySide6 import shim
  sysinfo.py           read-only system data (temps, throttle, freqs, cores)
  widgets.py           Sparkline, CoreView, ResizeGrip
  monitor.py           the main window (layout, themes, refresh, table)
  main.py              QApplication bootstrap + icon lookup
assets/cpu-monitor.svg launcher icon
```

Everything HW-related lives in `sysinfo.py`; the UI is split between
`widgets.py` (reusable painting widgets) and `monitor.py` (composition +
behaviour). Run it from source as shown in **Run from source** above.

## Troubleshooting

- **No temperature shown** → add a thermal sensor type to `THERMAL_TYPES` if
  yours differs (see `/sys/class/thermal/thermal_zone*/type`), or
  `sudo apt-get install lm-sensors` and re-check.
- **`pip install PySide2` fails** → you're on Python ≥ 3.10 (PySide2 wheels
  stop at 3.9). `install.sh` handles this automatically; for source runs the
  environment markers in `requirements.txt` select PySide6 for you — no
  action needed.
- **Qt platform plugin error** → `sudo apt-get install libxcb-xinerama0`
  or run with `QT_QPA_PLATFORM=offscreen` for a quick smoke test.

## License

[GNU GPL-3.0-or-later](LICENSE) © 2026 Arunabha Saha