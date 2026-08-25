Name:           plasma-osd-position
Version:        0.1.0
Release:        1%{?dist}
Summary:        Position der Plasma-Bildschirmanzeige (OSD) grafisch einstellen
BuildArch:      noarch
License:        MIT
URL:            https://github.com/OWNER/plasma-osd-position
Source0:        %{name}-%{version}.tar.gz
Requires:       python3 >= 3.9
Requires:       python3-pyqt6
Requires:       kf6-kconfig
Requires:       qt6-qttools

%description
Verschiebt das Lautstaerke- und Helligkeits-OSD von KDE Plasma ueber eine
KWin-Fensterregel, die auf den Fenstertyp "On-Screen Display" matcht und
Position sowie Anfangsplatzierung erzwingt.

%prep
%setup -q

%install
install -d %{buildroot}%{_bindir}
install -d %{buildroot}%{_datadir}/plasma-osd-position/plasma_osd_position
install -d %{buildroot}%{_datadir}/applications
install -m 0644 src/plasma_osd_position/*.py %{buildroot}%{_datadir}/plasma-osd-position/plasma_osd_position/
install -m 0755 data/plasma-osd-position %{buildroot}%{_bindir}/plasma-osd-position
install -m 0644 data/org.kde.plasma-osd-position.desktop %{buildroot}%{_datadir}/applications/

%files
%license LICENSE
%doc README.md
%{_bindir}/plasma-osd-position
%{_datadir}/plasma-osd-position
%{_datadir}/applications/org.kde.plasma-osd-position.desktop

%changelog
* Tue Aug 25 2026 Tim <tim@example.invalid> - 0.1.0-1
- Erste Version
