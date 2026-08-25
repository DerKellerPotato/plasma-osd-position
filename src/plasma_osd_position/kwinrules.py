"""Lesen, Schreiben und Entfernen der KWin-Fensterregel für die OSD-Position.

Hintergrund: Das Lautstärke-/Helligkeits-OSD von Plasma wird von KWin selbst
gezeichnet und hat keine eigene Einstellung. Über eine Fensterregel, die auf den
Fenstertyp "On-Screen Display" matcht und Position + Anfangsplatzierung
erzwingt, lässt es sich trotzdem verschieben.

Geschriebene Schlüssel in ~/.config/kwinrulesrc:

    [<uuid>]
    Description=...
    types=65536        # NET::OnScreenDisplayMask == 1 << 16
    position=X,Y       # KConfig serialisiert QPoint als "x,y"
    positionrule=2     # KWin Rules::Force
    placement=0        # KWin Placement::NoPlacement
    placementrule=2    # KWin Rules::Force

    [General]
    count=<n>
    rules=<uuid>,<uuid>,...
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid as _uuid
from typing import Dict, List, Optional, Tuple

# --- KWin-Konstanten (siehe netwm_def.h / kwin/src/rules.h) ------------------
OSD_TYPE_MASK = 1 << 16  # NET::OnScreenDisplayMask
RULE_FORCE = 2  # Rules:: Unused=0, DontAffect=1, Force=2, Apply=3, ...
PLACEMENT_NONE = 0  # Placement::NoPlacement

RULE_DESCRIPTION = "OSD-Position (plasma-osd-position)"
CONFIG_NAME = "kwinrulesrc"


class KWinRuleError(RuntimeError):
    """Fehler beim Lesen oder Schreiben der Fensterregel."""


# --- Hilfsfunktionen --------------------------------------------------------
def config_path() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, CONFIG_NAME)


def _first_binary(*names: str) -> Optional[str]:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def kwriteconfig_bin() -> Optional[str]:
    return _first_binary("kwriteconfig6", "kwriteconfig5")


def qdbus_bin() -> Optional[str]:
    return _first_binary("qdbus6", "qdbus-qt6", "qdbus", "qdbus-qt5")


def _read_lines() -> List[str]:
    path = config_path()
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read().splitlines()


def _parse() -> Dict[str, Dict[str, str]]:
    """Sehr einfacher INI-Parser. Bewusst zeilenbasiert, damit die Datei beim
    Lesen nicht umformatiert wird - geschrieben wird über kwriteconfig."""
    groups: Dict[str, Dict[str, str]] = {}
    current = ""
    for raw in _read_lines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            groups.setdefault(current, {})
        elif "=" in line and current:
            key, _, value = line.partition("=")
            groups[current][key.strip()] = value.strip()
    return groups


# --- Öffentliche API --------------------------------------------------------
def find_rule() -> Optional[Tuple[str, Dict[str, str]]]:
    """Gibt (UUID, Schlüssel) der von diesem Programm verwalteten Regel zurück."""
    for group, entries in _parse().items():
        if group in ("General", "$Version"):
            continue
        if entries.get("Description") == RULE_DESCRIPTION:
            return group, entries
    return None


def current_position() -> Optional[Tuple[int, int]]:
    found = find_rule()
    if not found:
        return None
    raw = found[1].get("position", "")
    try:
        x_str, _, y_str = raw.partition(",")
        return int(x_str), int(y_str)
    except ValueError:
        return None


def _write_key(group: str, key: str, value: str) -> None:
    binary = kwriteconfig_bin()
    if not binary:
        raise KWinRuleError(
            "Weder kwriteconfig6 noch kwriteconfig5 gefunden - "
            "läuft hier wirklich eine KDE-Plasma-Sitzung?"
        )
    result = subprocess.run(
        [binary, "--file", CONFIG_NAME, "--group", group, "--key", key, value],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise KWinRuleError(
            f"kwriteconfig ist fehlgeschlagen ({key}): {result.stderr.strip()}"
        )


def apply_position(x: int, y: int) -> str:
    """Legt die Regel an bzw. aktualisiert sie. Gibt die UUID zurück."""
    found = find_rule()
    rule_uuid = found[0] if found else str(_uuid.uuid4())

    _write_key(rule_uuid, "Description", RULE_DESCRIPTION)
    _write_key(rule_uuid, "types", str(OSD_TYPE_MASK))
    _write_key(rule_uuid, "position", f"{x},{y}")
    _write_key(rule_uuid, "positionrule", str(RULE_FORCE))
    _write_key(rule_uuid, "placement", str(PLACEMENT_NONE))
    _write_key(rule_uuid, "placementrule", str(RULE_FORCE))

    if not found:
        general = _parse().get("General", {})
        existing = [r for r in general.get("rules", "").split(",") if r]
        if rule_uuid not in existing:
            existing.append(rule_uuid)
        _write_key("General", "rules", ",".join(existing))
        _write_key("General", "count", str(len(existing)))

    return rule_uuid


def remove_rule() -> bool:
    """Entfernt die Regel wieder. True, wenn tatsächlich etwas entfernt wurde."""
    found = find_rule()
    if not found:
        return False
    rule_uuid = found[0]

    # Gruppe zeilenbasiert herausschneiden, alles andere unverändert lassen.
    lines = _read_lines()
    output: List[str] = []
    skipping = False
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            skipping = stripped[1:-1] == rule_uuid
        if not skipping:
            output.append(raw)

    path = config_path()
    tmp = path + ".plasma-osd-position.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write("\n".join(output).rstrip("\n") + "\n")
    os.replace(tmp, path)

    general = _parse().get("General", {})
    remaining = [r for r in general.get("rules", "").split(",") if r and r != rule_uuid]
    _write_key("General", "rules", ",".join(remaining))
    _write_key("General", "count", str(len(remaining)))
    return True


def reconfigure() -> bool:
    """KWin die Konfiguration neu einlesen lassen."""
    binary = qdbus_bin()
    if not binary:
        return False
    result = subprocess.run(
        [binary, "org.kde.KWin", "/KWin", "reconfigure"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def show_test_osd(text: str = "Test") -> bool:
    """Zeigt über plasmashell ein OSD an, um die Position zu prüfen."""
    binary = qdbus_bin()
    if not binary:
        return False
    result = subprocess.run(
        [
            binary,
            "org.kde.plasmashell",
            "/org/kde/osdService",
            "org.kde.osdService.showText",
            "audio-volume-medium",
            text,
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
