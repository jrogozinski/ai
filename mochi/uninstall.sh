#!/usr/bin/env bash
# Removes Mochi from the app menu. Pass --forget to also delete Mochi's memories (save file).
rm -f "$HOME/.local/share/applications/mochi.desktop" \
      "$HOME/.local/share/icons/hicolor/scalable/apps/mochi.svg" \
      "$HOME/.local/share/mochi/mochi.py"
if [ "$1" = "--forget" ]; then
    rm -rf "$HOME/.local/share/mochi"
    echo "Mochi uninstalled and forgotten. Goodbye, little blob. :("
else
    echo "Mochi uninstalled (save file kept in ~/.local/share/mochi)."
fi
