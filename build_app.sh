#!/usr/bin/env bash

set -e

# ============================================================
# LaserPrep Application Builder
# ============================================================

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROJECT_NAME="LaserPrep"
PYTHON="$SCRIPT_DIR/.venv/bin/python"
PYINSTALLER="$SCRIPT_DIR/.venv/bin/pyinstaller"
EXECUTABLE="$SCRIPT_DIR/dist/$PROJECT_NAME"
ICON="$SCRIPT_DIR/rocket.png"
DESKTOP_DIR="$HOME/Desktop"
DESKTOP_FILE="$DESKTOP_DIR/$PROJECT_NAME.desktop"

echo
echo "============================================"
echo "            Building $PROJECT_NAME"
echo "============================================"
echo

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: Python virtual environment not found:"
    echo "       $PYTHON"
    exit 1
fi

if [ ! -x "$PYINSTALLER" ]; then
    echo "ERROR: PyInstaller is not installed in .venv."
    echo
    echo "Install it with:"
    echo "    $PYTHON -m pip install pyinstaller"
    exit 1
fi

if [ ! -f "$ICON" ]; then
    echo "ERROR: Icon file not found:"
    echo "       $ICON"
    echo
    echo "Expected rocket.png in the project directory."
    exit 1
fi

echo "Running PyInstaller..."
echo

"$PYINSTALLER"     --onefile     --name "$PROJECT_NAME"     --icon="$ICON"     main.py

echo

if [ ! -f "$EXECUTABLE" ]; then
    echo "ERROR: Expected executable was not created:"
    echo "       $EXECUTABLE"
    exit 1
fi

chmod +x "$EXECUTABLE"

mkdir -p "$DESKTOP_DIR"

echo "Creating desktop launcher..."

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$PROJECT_NAME
Comment=PDF to laser preparation
Exec=x-terminal-emulator -e bash -c '$EXECUTABLE; echo; echo "LaserPrep has finished."; echo; read -p "Press Enter to close..."'
Icon=$ICON
Terminal=false
Categories=Utility;
Path=$SCRIPT_DIR
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"

if command -v gio >/dev/null 2>&1; then
    gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true
fi

echo
echo "============================================"
echo "             Build complete"
echo "============================================"
echo
echo "Executable:"
echo "  $EXECUTABLE"
echo
echo "Desktop launcher:"
echo "  $DESKTOP_FILE"
echo
echo "You can now launch $PROJECT_NAME from your desktop."
echo
