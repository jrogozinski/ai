#!/usr/bin/env bash
# Installs Mochi for the current user and adds it to the Linux Mint app menu.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HOME/.local/share/mochi"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
MENU_DIR="$HOME/.local/share/applications"

if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Mochi needs Tkinter. Install it with:"
    echo "    sudo apt install python3-tk"
    exit 1
fi

mkdir -p "$APP_DIR" "$ICON_DIR" "$MENU_DIR"
cp "$HERE/mochi.py" "$APP_DIR/mochi.py"
cp "$HERE/mochi.svg" "$ICON_DIR/mochi.svg"

cat > "$MENU_DIR/mochi.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Mochi
GenericName=Desktop Pet
Comment=A tiny squishy blob that lives on your desktop
Exec=python3 $APP_DIR/mochi.py
Icon=mochi
Terminal=false
Categories=Game;
DESKTOP

update-desktop-database "$MENU_DIR" >/dev/null 2>&1 || true
gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

echo "Mochi installed! Find it in your menu under Games, or run:"
echo "    python3 $APP_DIR/mochi.py"
