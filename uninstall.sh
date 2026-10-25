#!/usr/bin/env bash
# Uninstall the Sleek Monitor app: removes ~/.sleek-monitor (app copy + venv).
# Your source files in this directory are KEPT.
set -e

INSTALL_DIR="$HOME/.sleek-monitor"

if [ -d "$INSTALL_DIR" ]; then
    echo ">> Removing installed app + venv ($INSTALL_DIR)..."
    rm -rf "$INSTALL_DIR"
else
    echo ">> No install directory found at $INSTALL_DIR, skipping."
fi

echo ">> Removing command, desktop entry and icon..."
rm -f "$HOME/.local/bin/cpu-monitor"
rm -f "$HOME/.local/share/applications/cpu-monitor.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/cpu-monitor.svg"

echo ""
echo "Done. Your source files (system_monitor.py, README.md, ...) are untouched."
echo "Re-install any time with: bash install.sh"
echo ""
echo "Note: sudo-installed apt libs (libgl1, libegl1, libxkbcommon-x11-0, libdbus-1-3) were NOT removed —"
echo "they may be used by other Qt apps. Remove them manually if you're sure:"
echo "    sudo apt-get remove libgl1 libegl1 libxkbcommon-x11-0 libdbus-1-3"