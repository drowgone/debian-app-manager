#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/debian-app-manager.desktop"

mkdir -p "$DESKTOP_DIR"

cat << DESKTOP_ENTRY > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=Debian App Manager
Comment=Debian uchun tashqi dasturlarni boshqarish vositasi
Exec="$PROJECT_DIR/venv/bin/python" "$PROJECT_DIR/main.py"
Icon=system-software-install
Terminal=false
Categories=System;Utility;
Keywords=apt;snap;flatpak;app;manager;
DESKTOP_ENTRY

chmod +x "$DESKTOP_FILE"
update-desktop-database "$DESKTOP_DIR"

# GNOME Shell keshini yangilash uchrn
touch "$DESKTOP_DIR"
