#!/usr/bin/env bash
# Legt das private Repository an und pusht diesen Ordner.
# Voraussetzung: gh CLI ist installiert und angemeldet (gh auth login).
set -euo pipefail
REPO="${1:-plasma-osd-position}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

[ -d .git ] || { git init -b main; git add -A; git commit -m "Erste Version"; }

gh repo create "$REPO" --private --source=. --remote=origin --push
gh release create v0.1.0 dist/* --title "v0.1.0" --notes "Erste Version" || \
  echo "Hinweis: dist/ ist leer - erst packaging/build-deb.sh und packaging/build-rpm.sh ausführen."
