#!/usr/bin/env bash

set -e

# ============================================================
# LaserPrep Production Installer
# ============================================================

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_NAME="LaserPrep"
SOURCE_EXECUTABLE="$SCRIPT_DIR/dist/$PROJECT_NAME"
SOURCE_ICON="$SCRIPT_DIR/rocket.png"

INSTALL_DIR="/opt/$PROJECT_NAME"
INSTALL_EXECUTABLE="$INSTALL_DIR/$PROJECT_NAME"
INSTALL_ICON="$INSTALL_DIR/rocket.png"

ATN_USER="ATN"
ATN_HOME="/home/$ATN_USER"
ATN_DESKTOP="$ATN_HOME/Desktop"
DESKTOP_FILE="$ATN_DESKTOP/$PROJECT_NAME.desktop"

echo
echo "============================================"
echo "        Installing $PROJECT_NAME"
echo "============================================"
echo

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This installer must be run with sudo."
    echo
    echo "Run:"
    echo "    sudo ./install_app.sh"
    echo
    exit 1
fi

if [ ! -f "$SOURCE_EXECUTABLE" ]; then
    echo "ERROR: Built executable not found:"
    echo "       $SOURCE_EXECUTABLE"
    echo
    echo "Build LaserPrep first with:"
    echo "    ./build_app.sh"
    echo
    exit 1
fi

if [ ! -f "$SOURCE_ICON" ]; then
    echo "ERROR: Icon file not found:"
    echo "       $SOURCE_ICON"
    exit 1
fi

if ! id "$ATN_USER" >/dev/null 2>&1; then
    echo "ERROR: User account '$ATN_USER' does not exist."
    echo
    echo "Create the account first with:"
    echo "    sudo adduser $ATN_USER"
    echo
    exit 1
fi

if [ ! -d "$ATN_HOME" ]; then
    echo "ERROR: ATN home directory not found:"
    echo "       $ATN_HOME"
    exit 1
fi

echo "Installing application to:"
echo "  $INSTALL_DIR"
echo

mkdir -p "$INSTALL_DIR"

install -m 755 "$SOURCE_EXECUTABLE" "$INSTALL_EXECUTABLE"
install -m 644 "$SOURCE_ICON" "$INSTALL_ICON"

chown -R root:root "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"
chmod 755 "$INSTALL_EXECUTABLE"
chmod 644 "$INSTALL_ICON"

echo "Creating ATN desktop launcher..."

mkdir -p "$ATN_DESKTOP"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$PROJECT_NAME
Comment=PDF to laser preparation
Exec=x-terminal-emulator -e bash -c '$INSTALL_EXECUTABLE; echo; echo "LaserPrep has finished."; echo; read -p "Press Enter to close..."'
Icon=$INSTALL_ICON
Terminal=false
Categories=Utility;
Path=$INSTALL_DIR
StartupNotify=true
EOF

chown "$ATN_USER:$ATN_USER" "$DESKTOP_FILE"
chmod 755 "$DESKTOP_FILE"

if command -v gio >/dev/null 2>&1; then
    sudo -u "$ATN_USER" gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true
fi

echo
echo "============================================"
echo "          Installation complete"
echo "============================================"
echo
echo "Application:"
echo "  $INSTALL_EXECUTABLE"
echo
echo "ATN desktop launcher:"
echo "  $DESKTOP_FILE"
echo
echo "The production application is owned by root."
echo "The ATN account can run it but cannot modify it."
echo
