# plasma-osd-position

Kleine Qt-Anwendung, um die Position des Lautstärke- und Helligkeits-OSD von
KDE Plasma grafisch festzulegen.

Plasma bietet dafür keine eigene Einstellung – das OSD wird von KWin selbst
gezeichnet. Der einzige unterstützte Weg ist eine Fensterregel, die auf den
Fenstertyp *On-Screen Display* matcht und sowohl **Position** als auch
**Anfangsplatzierung** erzwingt. Genau diese Regel legt das Programm an.

## Funktionen

- Abstand zum unteren Bildschirmrand plus horizontale Ausrichtung (mittig/links/rechts)
- Multi-Monitor: Zielbildschirm auswählbar, X/Y werden in globalen Koordinaten berechnet
- Vorschau aller Bildschirme in ihrer tatsächlichen Anordnung
- Feinjustierung über Versatz X/Y und die angenommene OSD-Größe
- Regel anwenden, testen (`org.kde.osdService`) und wieder entfernen
- KWin lädt die Konfiguration direkt neu (`qdbus org.kde.KWin /KWin reconfigure`)

## Was genau geschrieben wird

In `~/.config/kwinrulesrc` entsteht eine Gruppe mit eigener UUID:

```ini
[<uuid>]
Description=OSD-Position (plasma-osd-position)
types=65536        # NET::OnScreenDisplayMask == 1 << 16
position=X,Y       # KConfig serialisiert QPoint als "x,y"
positionrule=2     # KWin Rules::Force
placement=0        # KWin Placement::NoPlacement
placementrule=2    # KWin Rules::Force
```

Zusätzlich werden `count` und `rules` in der Gruppe `[General]` gepflegt.
Ohne das erzwungene `placement=0` überschreibt KWin die Koordinaten mit seiner
eigenen Platzierung – deshalb setzt das Programm beide Werte gemeinsam.

Geschrieben wird über `kwriteconfig6` (Fallback `kwriteconfig5`), damit
KConfig-Semantik und Dateiformat erhalten bleiben.

## Installation

Debian / Ubuntu / Linux Mint:

```bash
sudo apt install ./plasma-osd-position_0.1.0_all.deb
```

Fedora / openSUSE:

```bash
sudo dnf install ./plasma-osd-position-0.1.0-1.noarch.rpm
```

Ohne Paket direkt aus dem Quellbaum:

```bash
python3 src/plasma_osd_position/__main__.py
```

Laufzeitabhängigkeiten: `python3`, PyQt6 (`python3-pyqt6`), `kwriteconfig6`
aus KConfig sowie `qdbus6` für Reload und Test-OSD.

## Pakete selbst bauen

```bash
mkdir -p dist
./packaging/build-deb.sh    # braucht dpkg-deb
./packaging/build-rpm.sh    # braucht rpmbuild
```

Der GitHub-Actions-Workflow `.github/workflows/build.yml` baut beide Pakete bei
jedem `v*`-Tag und hängt sie an das Release.

## Ausrollen über Ansible

Die Regel ist reine Benutzerkonfiguration. Für eine einheitliche Position auf
allen Arbeitsplätzen reicht es, die Regel einmal lokal zu setzen und den
Abschnitt aus `~/.config/kwinrulesrc` per `community.general.ini_file` (oder als
Template) auf die Zielrechner zu bringen – die UUID kann dabei identisch
bleiben. Danach je Benutzersitzung:

```bash
qdbus6 org.kde.KWin /KWin reconfigure
```

## Bekannte Grenzen

- **Eine Regel = eine absolute Position.** KWin kennt keine bildschirmrelative
  Angabe, deshalb erscheint das OSD nach dem Anwenden immer auf dem gewählten
  Monitor und folgt nicht mehr dem aktiven. Ein einheitlicher unterer Abstand
  über mehrere Bildschirme hinweg ist damit nicht ausdrückbar.
- Die Regel setzt die **linke obere Ecke** des Fensters. Für den unteren Rand
  wird deshalb die OSD-Höhe benötigt; die Vorgabewerte sind eine Schätzung und
  im Dialog anpassbar.
- Bei fraktionaler Skalierung können die logischen Qt-Koordinaten von den
  Koordinaten abweichen, die KWin für die Regel verwendet – dann X/Y manuell
  nachziehen.
- Getestet gegen Plasma 6. Ältere Plasma-5-Versionen speichern `placement`
  teilweise noch als Zeichenkette.

## Lizenz

MIT
