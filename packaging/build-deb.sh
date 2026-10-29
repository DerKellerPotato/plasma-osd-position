#!/usr/bin/env bash
# Baut ein architekturunabhängiges .deb (Debian/Ubuntu/Linux Mint).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP '(?<=__version__ = ")[^"]+' "$ROOT/src/plasma_osd_position/__init__.py")"
OUT="${1:-$ROOT/dist}"
BUILD="$(mktemp -d)"
chmod 0755 "$BUILD"
trap 'rm -rf "$BUILD"' EXIT

"$ROOT/packaging/install.sh" "$BUILD" /usr
install -d "$BUILD/DEBIAN" "$BUILD/usr/share/doc/plasma-osd-position"
install -m 0644 "$ROOT/LICENSE" "$BUILD/usr/share/doc/plasma-osd-position/copyright"

cat > "$BUILD/DEBIAN/control" <<CONTROL
Package: plasma-osd-position
Version: $VERSION
Section: kde
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-pyqt6
Recommends: libkf6config-bin | libkf5config-bin
Maintainer: DerKellerPotato <noreply@github.com>
Homepage: https://github.com/DerKellerPotato/plasma-osd-position
Description: Position der Plasma-Bildschirmanzeige (OSD) grafisch einstellen
 Verschiebt das Lautstaerke- und Helligkeits-OSD von KDE Plasma ueber eine
 KWin-Fensterregel, die auf den Fenstertyp "On-Screen Display" matcht und
 Position sowie Anfangsplatzierung erzwingt.
CONTROL

dpkg-deb --root-owner-group --build "$BUILD" "$OUT/plasma-osd-position_${VERSION}_all.deb" >/dev/null
echo "$OUT/plasma-osd-position_${VERSION}_all.deb"
