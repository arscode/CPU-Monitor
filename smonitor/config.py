"""Application constants, themes and user-tunable settings."""

REFRESH_MS = 1500            # refresh interval (ms)
MAX_PROCS_HINT = 500         # processes shown in the table (realistic cap)
HIGHLIGHT_MB = 256           # processes above this RSS (MB) are highlighted
OPACITY = 1.0                # overall window opacity (1.0 = fully solid)
WINDOW_W, WINDOW_H = 540, 640

THERMAL_TYPES = ("x86_pkg_temp", "coretemp", "k10temp", "cpu_thermal", "acpitz")

THEMES = {
    "light": {
        "window":    "rgba(247,248,251,253)",
        "border":    "rgba(255,255,255,255)",
        "frame":     "rgba(24,25,31,26)",
        "text":      "#1e2229",
        "muted":     "#6a7280",
        "metric_bg": "rgba(23,26,32,42)",
        "accent":    "#3b82f6",
        "bar_bg":    "rgba(23,26,32,30)",
        "ok":        "#0e9f6e",
        "warn":      "#d97706",
        "hot":       "#dc2626",
        "highlight": "rgba(220,38,38,72)",
        "grid":      "rgba(23,26,32,26)",
        "header":    "rgba(23,26,32,22)",
        "scroll":    "rgba(23,26,32,110)",
    },
    "dark": {
        "window":    "rgba(17,19,24,253)",
        "border":    "rgba(255,255,255,34)",
        "frame":     "rgba(255,255,255,18)",
        "text":      "#e6e9ef",
        "muted":     "#8a93a3",
        "metric_bg": "rgba(255,255,255,26)",
        "accent":    "#60a5fa",
        "bar_bg":    "rgba(255,255,255,26)",
        "ok":        "#34d399",
        "warn":      "#fbbf24",
        "hot":       "#f87171",
        "highlight": "rgba(248,113,113,96)",
        "grid":      "rgba(255,255,255,24)",
        "header":    "rgba(255,255,255,20)",
        "scroll":    "rgba(255,255,255,160)",
    },
}

MODE_LABELS = {"system": "Auto", "light": "Light", "dark": "Dark"}