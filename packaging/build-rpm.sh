#!/usr/bin/env bash
# Baut ein noarch .rpm (Fedora/openSUSE).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP '(?<=__version__ = ")[^"]+' "$ROOT/src/plasma_osd_position/__init__.py")"
OUT="${1:-$ROOT/dist}"
TOP="$(mktemp -d)"
trap 'rm -rf "$TOP"' EXIT

mkdir -p "$TOP"/{SOURCES,SPECS,BUILD,RPMS,SRPMS} "$TOP/pkg/plasma-osd-position-$VERSION"
cp -r "$ROOT"/{src,data,README.md,LICENSE} "$TOP/pkg/plasma-osd-position-$VERSION/"
tar -czf "$TOP/SOURCES/plasma-osd-position-$VERSION.tar.gz" -C "$TOP/pkg" "plasma-osd-position-$VERSION"
cp "$ROOT/packaging/plasma-osd-position.spec" "$TOP/SPECS/"

rpmbuild --define "_topdir $TOP" -bb "$TOP/SPECS/plasma-osd-position.spec" >/dev/null
mkdir -p "$OUT"
find "$TOP/RPMS" -name '*.rpm' -exec cp {} "$OUT/" \;
find "$OUT" -name "plasma-osd-position-$VERSION*.rpm"
