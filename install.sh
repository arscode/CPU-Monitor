#!/usr/bin/env bash
# Install the Sleek Monitor app into ~/.sleek-monitor with its own venv,
# add a `cpu-monitor` command, a desktop entry and an icon.
# The source files in the current (original) directory are left untouched.
set -e

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.sleek-monitor"

echo ">> Creating install directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

echo ">> Copying the app across..."
cp -f "$SRC_DIR/system_monitor.py" "$SRC_DIR/requirements.txt" "$SRC_DIR/README.md" "$SRC_DIR/run.sh" "$INSTALL_DIR/"
cp -r "$SRC_DIR/smonitor" "$INSTALL_DIR/"
cp -r "$SRC_DIR/assets" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/run.sh"

echo ">> Creating virtualenv (.venv)..."
if ! python3 -m venv "$INSTALL_DIR/.venv" 2>/dev/null; then
    echo "   venv creation failed. hint: python3-venv is usually required ->"
    echo "   sudo apt-get install python3-venv"
    echo "   then re-run: bash install.sh"
    exit 1
fi

echo ">> Activating venv and installing dependencies..."
# shellcheck disable=SC1091
source "$INSTALL_DIR/.venv/bin/activate"
python -m pip install --upgrade pip setuptools
python -m pip install -r "$INSTALL_DIR/requirements.txt"

echo ">> Making sure shared Qt system libraries are present..."
if ! ldconfig -p | grep -q "libGL.so.1"; then
    echo "   libGL not found -> installing libgl1/libegl1 (needs sudo)..."
    sudo apt-get update
    sudo apt-get install -y libgl1 libegl1 libxkbcommon-x11-0 libdbus-1-3
fi

# --------------------------------------------------------------------------- #
# cpu-monitor command in ~/.local/bin
# --------------------------------------------------------------------------- #
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
ln -sf "$INSTALL_DIR/run.sh" "$BIN_DIR/cpu-monitor"
chmod +x "$BIN_DIR/cpu-monitor"
if ! printf '%s' "$PATH" | tr ':' '\n' | grep -qx "$BIN_DIR"; then
    echo "NOTE: $BIN_DIR is not on your PATH. Add to ~/.profile:"
    echo "      export PATH=\"$HOME/.local/bin:\$PATH\""
fi

# --------------------------------------------------------------------------- #
# desktop entry + icon (for the GNOME Activities / dock / favourites)
# --------------------------------------------------------------------------- #
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
APP_DIR="$HOME/.local/share/applications"
mkdir -p "$ICON_DIR" "$APP_DIR"
cp -f "$SRC_DIR/assets/cpu-monitor.svg" "$ICON_DIR/cpu-monitor.svg"

cat > "$APP_DIR/cpu-monitor.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=CPU Monitor
Comment=Sleek system monitor panel
Exec=$INSTALL_DIR/run.sh
Icon=cpu-monitor
Terminal=false
Categories=System;Monitor;Utility;
StartupNotify=true
StartupWMClass=cpu-monitor
EOF
chmod +x "$APP_DIR/cpu-monitor.desktop"

update-desktop-database "$APP_DIR" 2>/dev/null || true
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo ""
echo "Done. You can now launch it as:"
echo "    cpu-monitor"
echo "or from the app grid: open Activities, search \"CPU Monitor\", then"
echo "right-click its icon -> \"Add to Favorites\" to pin it to the dock."
echo ""
echo "Uninstall (keeps your source files):"
echo "    bash $SRC_DIR/uninstall.sh"
echo ""
echo "Tip: for the most accurate CPU temperatures install lm-sensors too:"
echo "    sudo apt-get install lm-sensors && sudo sensors-detect"