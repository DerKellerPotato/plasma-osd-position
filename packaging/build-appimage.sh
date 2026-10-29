#!/usr/bin/env bash
# Baut ein x86_64-AppImage mit eigenem Python (python-appimage, manylinux_2_28)
# und PyQt6 aus PyPI. Läuft auf jeder Distribution mit glibc >= 2.28.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP '(?<=__version__ = ")[^"]+' "$ROOT/src/plasma_osd_position/__init__.py")"
OUT="${1:-$ROOT/dist}"
PYTHON_SERIES="${PYTHON_SERIES:-3.12}"
ARCH=x86_64
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
cd "$WORK"

# Neuestes Python-AppImage der Reihe ermitteln und entpacken.
PYTHON_URL="$(curl -fsSL "https://api.github.com/repos/niess/python-appimage/releases/tags/python$PYTHON_SERIES" \
  | grep -oP '"browser_download_url": "\K[^"]+manylinux_2_28_'"$ARCH"'\.AppImage' | head -n1)"
curl -fsSL -o python.AppImage "$PYTHON_URL"
chmod +x python.AppImage
./python.AppImage --appimage-extract >/dev/null

# Das AppDir komplett übernehmen: Python findet seine Bibliotheken (libssl,
# libffi, ...) über relative RPATHs in usr/lib.
APPDIR="$WORK/AppDir"
mv squashfs-root "$APPDIR"
rm -f "$APPDIR/AppRun" "$APPDIR/.DirIcon" "$APPDIR"/*.desktop "$APPDIR"/*.png "$APPDIR"/*.svg
rm -rf "$APPDIR/usr/share/metainfo"
install -d "$APPDIR/usr/share/metainfo"
ln -s "python$PYTHON_SERIES" "$APPDIR/opt/python"
[ -e "$APPDIR/opt/python/bin/python3" ] || ln -s "python$PYTHON_SERIES" "$APPDIR/opt/python/bin/python3"
"$APPDIR/opt/python/bin/python3" -c "import ssl"

"$APPDIR/opt/python/bin/python3" -m pip install --no-cache-dir --no-warn-script-location PyQt6 >/dev/null
# QML und Übersetzungen braucht die Widgets-Oberfläche nicht.
QT="$APPDIR/opt/python/lib/python$PYTHON_SERIES/site-packages/PyQt6/Qt6"
rm -rf "$QT/qml" "$QT/translations"

install -d "$APPDIR/opt/plasma-osd-position/plasma_osd_position"
install -m 0644 "$ROOT"/src/plasma_osd_position/*.py "$APPDIR/opt/plasma-osd-position/plasma_osd_position/"
install -m 0755 "$ROOT/packaging/appimage/AppRun" "$APPDIR/AppRun"
install -m 0644 "$ROOT/data/org.kde.plasma-osd-position.desktop" "$APPDIR/"
install -m 0644 "$ROOT/data/plasma-osd-position.svg" "$APPDIR/"
ln -s plasma-osd-position.svg "$APPDIR/.DirIcon"
install -m 0644 "$ROOT/data/org.kde.plasma-osd-position.metainfo.xml" "$APPDIR/usr/share/metainfo/"

# Selbsttest: Module müssen mit dem gebündelten Python importierbar sein.
QT_QPA_PLATFORM=offscreen "$APPDIR/opt/python/bin/python3" -s -c \
  "import sys; sys.path.insert(0, '$APPDIR/opt/plasma-osd-position'); \
   from PyQt6 import QtDBus, QtWidgets; import plasma_osd_position.gui"

curl -fsSL -o appimagetool "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
chmod +x appimagetool
TARGET="$OUT/plasma-osd-position-$VERSION-$ARCH.AppImage"
ARCH="$ARCH" APPIMAGE_EXTRACT_AND_RUN=1 ./appimagetool --no-appstream "$APPDIR" "$TARGET" >/dev/null
echo "$TARGET"
