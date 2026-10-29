#!/usr/bin/env bash
# Installiert die Anwendung unter <PREFIX> in <DESTDIR> (gemeinsam für
# deb, rpm, Arch, Flatpak und AppImage).
#   packaging/install.sh <DESTDIR> [PREFIX=/usr]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DESTDIR="${1:?DESTDIR fehlt}"
PREFIX="${2:-/usr}"
SHARE="$DESTDIR$PREFIX/share"

install -d "$DESTDIR$PREFIX/bin" \
           "$SHARE/plasma-osd-position/plasma_osd_position" \
           "$SHARE/applications" \
           "$SHARE/metainfo" \
           "$SHARE/icons/hicolor/scalable/apps"

install -m 0644 "$ROOT"/src/plasma_osd_position/*.py "$SHARE/plasma-osd-position/plasma_osd_position/"
sed "s|/usr/share/|$PREFIX/share/|" "$ROOT/data/plasma-osd-position" > "$DESTDIR$PREFIX/bin/plasma-osd-position"
chmod 0755 "$DESTDIR$PREFIX/bin/plasma-osd-position"
install -m 0644 "$ROOT/data/org.kde.plasma-osd-position.desktop" "$SHARE/applications/"
install -m 0644 "$ROOT/data/org.kde.plasma-osd-position.metainfo.xml" "$SHARE/metainfo/"
install -m 0644 "$ROOT/data/plasma-osd-position.svg" "$SHARE/icons/hicolor/scalable/apps/"
