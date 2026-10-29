Name:           plasma-osd-position
Version:        0.2.0
Release:        1%{?dist}
Summary:        Position der Plasma-Bildschirmanzeige (OSD) grafisch einstellen
BuildArch:      noarch
License:        MIT
URL:            https://github.com/DerKellerPotato/plasma-osd-position
Source0:        %{name}-%{version}.tar.gz
Requires:       python3 >= 3.9
# Fedora: python3-pyqt6, openSUSE: python3-PyQt6
Requires:       (python3-pyqt6 or python3-PyQt6)
# kwriteconfig ist optional - ohne schreibt das Programm die Datei selbst.
Recommends:     /usr/bin/kwriteconfig6

%description
Verschiebt das Lautstaerke- und Helligkeits-OSD von KDE Plasma ueber eine
KWin-Fensterregel, die auf den Fenstertyp "On-Screen Display" matcht und
Position sowie Anfangsplatzierung erzwingt.

%prep
%setup -q

%install
packaging/install.sh %{buildroot} %{_prefix}

%files
%license LICENSE
%doc README.md
%{_bindir}/plasma-osd-position
%{_datadir}/plasma-osd-position
%{_datadir}/applications/org.kde.plasma-osd-position.desktop
%{_datadir}/metainfo/org.kde.plasma-osd-position.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/plasma-osd-position.svg

%changelog
* Tue Aug 25 2026 Tim <tim@example.invalid> - 0.2.0-1
- Bedienung auf unteren Rand plus Ausrichtung umgestellt, Vorschau ueber alle Bildschirme

* Tue Aug 25 2026 Tim <tim@example.invalid> - 0.1.0-1
- Erste Version
