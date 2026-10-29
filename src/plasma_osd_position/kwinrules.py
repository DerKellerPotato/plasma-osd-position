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
def in_flatpak() -> bool:
    return os.path.exists("/.flatpak-info")


def config_path() -> str:
    # Im Flatpak zeigt XDG_CONFIG_HOME auf ~/.var/app/<id>/config - KWin liest
    # aber die Datei des Hosts, die per --filesystem=xdg-config sichtbar ist.
    if in_flatpak():
        base = os.path.expanduser("~/.config")
    else:
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


def _write_lines(lines: List[str]) -> None:
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".plasma-osd-position.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip("\n") + "\n")
    os.replace(tmp, path)


def _write_key_direct(group: str, key: str, value: str) -> None:
    """Ersatz für kwriteconfig, wenn es nicht verfügbar ist (z. B. im Flatpak).
    Ändert nur die eine Zeile bzw. hängt sie an die Gruppe an; die Werte dieses
    Programms brauchen kein KConfig-Escaping."""
    lines = _read_lines()
    header = f"[{group}]"
    start = next((i for i, line in enumerate(lines) if line.strip() == header), None)
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        _write_lines(lines + [header, f"{key}={value}"])
        return

    insert_at = start + 1
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            break
        name, sep, _ = stripped.partition("=")
        if sep and name.strip() == key:
            lines[index] = f"{key}={value}"
            _write_lines(lines)
            return
        if stripped:
            insert_at = index + 1
    lines.insert(insert_at, f"{key}={value}")
    _write_lines(lines)


def _write_key(group: str, key: str, value: str) -> None:
    binary = kwriteconfig_bin()
    if not binary:
        _write_key_direct(group, key, value)
        return
    result = subprocess.run(
        [binary, "--file", config_path(), "--group", group, "--key", key, value],
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

    _write_lines(output)

    general = _parse().get("General", {})
    remaining = [r for r in general.get("rules", "").split(",") if r and r != rule_uuid]
    _write_key("General", "rules", ",".join(remaining))
    _write_key("General", "count", str(len(remaining)))
    return True


def _dbus_call(service: str, path: str, interface: str, method: str, *args: str) -> bool:
    """Ruft eine Session-Bus-Methode auf - bevorzugt über QtDBus, sonst qdbus."""
    try:
        from PyQt6.QtDBus import QDBusConnection, QDBusMessage
    except ImportError:
        binary = qdbus_bin()
        if not binary:
            return False
        result = subprocess.run(
            [binary, service, path, f"{interface}.{method}", *args],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    message = QDBusMessage.createMethodCall(service, path, interface, method)
    message.setArguments(list(args))
    reply = QDBusConnection.sessionBus().call(message)
    return reply.type() != QDBusMessage.MessageType.ErrorMessage


def reconfigure() -> bool:
    """KWin die Konfiguration neu einlesen lassen."""
    return _dbus_call("org.kde.KWin", "/KWin", "org.kde.KWin", "reconfigure")


def show_test_osd(text: str = "Test") -> bool:
    """Zeigt über plasmashell ein OSD an, um die Position zu prüfen."""
    return _dbus_call(
        "org.kde.plasmashell",
        "/org/kde/osdService",
        "org.kde.osdService",
        "showText",
        "audio-volume-medium",
        text,
    )
