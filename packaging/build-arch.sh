#!/usr/bin/env bash
# Baut ein .pkg.tar.zst (Arch Linux, Manjaro, EndeavourOS, CachyOS).
# makepkg darf nicht als root laufen - im Container also als normaler Benutzer.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP '(?<=__version__ = ")[^"]+' "$ROOT/src/plasma_osd_position/__init__.py")"
OUT="${1:-$ROOT/dist}"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT

sed "s/^pkgver=.*/pkgver=$VERSION/" "$ROOT/packaging/arch/PKGBUILD" > "$BUILD/PKGBUILD"
ln -s "$ROOT" "$BUILD/repo"
mkdir -p "$OUT"
(cd "$BUILD" && PKGDEST="$OUT" makepkg --nodeps --noconfirm --force >/dev/null)
find "$OUT" -name "plasma-osd-position-$VERSION-*.pkg.tar.zst"
