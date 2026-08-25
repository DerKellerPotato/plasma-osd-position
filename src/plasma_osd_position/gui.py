"""Qt-Oberfläche für plasma-osd-position."""

from __future__ import annotations

import sys
from typing import Optional, Tuple

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPen, QScreen
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import kwinrules

ANCHORS = [
    ("Oben links", 0.0, 0.0),
    ("Oben mittig", 0.5, 0.0),
    ("Oben rechts", 1.0, 0.0),
    ("Mitte links", 0.0, 0.5),
    ("Zentriert", 0.5, 0.5),
    ("Mitte rechts", 1.0, 0.5),
    ("Unten links", 0.0, 1.0),
    ("Unten mittig", 0.5, 1.0),
    ("Unten rechts", 1.0, 1.0),
]

DEFAULT_OSD_WIDTH = 340
DEFAULT_OSD_HEIGHT = 74


class PreviewWidget(QWidget):
    """Zeichnet den Bildschirm und das OSD-Rechteck maßstabsgetreu."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(190)
        self._screen = QRect(0, 0, 1920, 1080)
        self._osd = QRect(0, 0, DEFAULT_OSD_WIDTH, DEFAULT_OSD_HEIGHT)

    def update_geometry(self, screen: QRect, osd: QRect) -> None:
        self._screen = screen
        self._osd = osd
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt-Namensschema)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._screen.width() <= 0 or self._screen.height() <= 0:
            return

        margin = 12
        avail_w = self.width() - 2 * margin
        avail_h = self.height() - 2 * margin
        scale = min(avail_w / self._screen.width(), avail_h / self._screen.height())
        draw_w = self._screen.width() * scale
        draw_h = self._screen.height() * scale
        off_x = (self.width() - draw_w) / 2
        off_y = (self.height() - draw_h) / 2

        palette = self.palette()
        painter.setPen(QPen(palette.mid().color(), 1))
        painter.setBrush(palette.base())
        painter.drawRoundedRect(int(off_x), int(off_y), int(draw_w), int(draw_h), 4, 4)

        rel_x = off_x + (self._osd.x() - self._screen.x()) * scale
        rel_y = off_y + (self._osd.y() - self._screen.y()) * scale
        accent = palette.highlight().color()
        painter.setPen(QPen(accent, 1))
        painter.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 140))
        painter.drawRoundedRect(
            int(rel_x),
            int(rel_y),
            max(3, int(self._osd.width() * scale)),
            max(3, int(self._osd.height() * scale)),
            3,
            3,
        )
        painter.end()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OSD-Position")
        self.setWindowIcon(QIcon.fromTheme("preferences-desktop-display"))
        self._updating = False

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setSpacing(12)

        intro = QLabel(
            "Verschiebt das Lautstärke- und Helligkeits-OSD von Plasma über eine "
            "KWin-Fensterregel (Fenstertyp „On-Screen Display“, Position und "
            "Anfangsplatzierung erzwungen)."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(self._build_placement_box())
        layout.addWidget(self._build_size_box())

        self.preview = PreviewWidget()
        preview_box = QGroupBox("Vorschau")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.addWidget(self.preview)
        layout.addWidget(preview_box)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        buttons = QDialogButtonBox()
        self.test_button = QPushButton("Test-OSD anzeigen")
        self.remove_button = QPushButton("Regel entfernen")
        self.apply_button = QPushButton("Anwenden")
        self.apply_button.setDefault(True)
        buttons.addButton(self.test_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton(self.remove_button, QDialogButtonBox.ButtonRole.DestructiveRole)
        buttons.addButton(self.apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        layout.addWidget(buttons)

        self.test_button.clicked.connect(self.on_test)
        self.remove_button.clicked.connect(self.on_remove)
        self.apply_button.clicked.connect(self.on_apply)

        self.setCentralWidget(central)
        self._load_existing()
        self._recalculate()

    # --- Aufbau ------------------------------------------------------------
    def _build_placement_box(self) -> QGroupBox:
        box = QGroupBox("Platzierung")
        outer = QHBoxLayout(box)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(4)
        self.anchor_group = QButtonGroup(self)
        for index, (label, _, _) in enumerate(ANCHORS):
            button = QToolButton()
            button.setCheckable(True)
            button.setToolTip(label)
            button.setFixedSize(46, 34)
            self.anchor_group.addButton(button, index)
            grid.addWidget(button, index // 3, index % 3)
        self.anchor_group.button(7).setChecked(True)  # Unten mittig
        self.anchor_group.idToggled.connect(lambda *_: self._recalculate())
        outer.addWidget(grid_widget)

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        self.screen_combo = QComboBox()
        for screen in QGuiApplication.screens():
            geo = screen.geometry()
            self.screen_combo.addItem(
                f"{screen.name()} ({geo.width()}×{geo.height()} @ {geo.x()},{geo.y()})"
            )
        self.screen_combo.currentIndexChanged.connect(self._recalculate)
        form.addRow("Bildschirm:", self.screen_combo)

        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 2000)
        self.margin_spin.setValue(80)
        self.margin_spin.setSuffix(" px")
        self.margin_spin.valueChanged.connect(self._recalculate)
        form.addRow("Randabstand:", self.margin_spin)

        self.x_spin = QSpinBox()
        self.x_spin.setRange(-20000, 20000)
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-20000, 20000)
        for spin in (self.x_spin, self.y_spin):
            spin.setSuffix(" px")
            spin.valueChanged.connect(self._on_manual_edit)
        form.addRow("X (global):", self.x_spin)
        form.addRow("Y (global):", self.y_spin)

        outer.addWidget(form_widget, 1)
        return box

    def _build_size_box(self) -> QGroupBox:
        box = QGroupBox("Angenommene OSD-Größe")
        layout = QFormLayout(box)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(40, 2000)
        self.width_spin.setValue(DEFAULT_OSD_WIDTH)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(20, 1000)
        self.height_spin.setValue(DEFAULT_OSD_HEIGHT)
        for spin in (self.width_spin, self.height_spin):
            spin.setSuffix(" px")
            spin.valueChanged.connect(self._recalculate)
        layout.addRow("Breite:", self.width_spin)
        layout.addRow("Höhe:", self.height_spin)
        hint = QLabel(
            "Die Regel setzt die linke obere Ecke des Fensters. Für rechte und "
            "untere Anker wird die OSD-Größe benötigt - falls das OSD nicht exakt "
            "sitzt, hier nachjustieren oder X/Y direkt eintragen."
        )
        hint.setWordWrap(True)
        layout.addRow(hint)
        return box

    # --- Logik -------------------------------------------------------------
    def _current_screen(self) -> QScreen:
        screens = QGuiApplication.screens()
        index = max(0, min(self.screen_combo.currentIndex(), len(screens) - 1))
        return screens[index]

    def _recalculate(self) -> None:
        if self._updating:
            return
        checked = self.anchor_group.checkedId()
        if checked >= 0:
            geo = self._current_screen().geometry()
            _, fx, fy = ANCHORS[checked]
            margin = self.margin_spin.value()
            width = self.width_spin.value()
            height = self.height_spin.value()

            usable_x = geo.width() - width
            usable_y = geo.height() - height
            x = geo.x() + int(round(usable_x * fx))
            y = geo.y() + int(round(usable_y * fy))
            if fx == 0.0:
                x += margin
            elif fx == 1.0:
                x -= margin
            if fy == 0.0:
                y += margin
            elif fy == 1.0:
                y -= margin

            self._updating = True
            self.x_spin.setValue(x)
            self.y_spin.setValue(y)
            self._updating = False

        self._update_preview()

    def _on_manual_edit(self) -> None:
        if self._updating:
            return
        button = self.anchor_group.checkedButton()
        if button is not None:
            self.anchor_group.setExclusive(False)
            button.setChecked(False)
            self.anchor_group.setExclusive(True)
        self._update_preview()

    def _update_preview(self) -> None:
        geo = self._current_screen().geometry()
        osd = QRect(
            self.x_spin.value(),
            self.y_spin.value(),
            self.width_spin.value(),
            self.height_spin.value(),
        )
        self.preview.update_geometry(geo, osd)

    def _load_existing(self) -> None:
        position: Optional[Tuple[int, int]] = kwinrules.current_position()
        if position:
            self._updating = True
            self.anchor_group.setExclusive(False)
            for button in self.anchor_group.buttons():
                button.setChecked(False)
            self.anchor_group.setExclusive(True)
            self.x_spin.setValue(position[0])
            self.y_spin.setValue(position[1])
            self._updating = False
            self.status.setText(
                f"Bestehende Regel gefunden: Position {position[0]},{position[1]}."
            )
        else:
            self.status.setText("Noch keine Regel vorhanden.")

    # --- Aktionen ----------------------------------------------------------
    def on_apply(self) -> None:
        try:
            kwinrules.apply_position(self.x_spin.value(), self.y_spin.value())
        except kwinrules.KWinRuleError as error:
            QMessageBox.critical(self, "Fehler", str(error))
            return
        reloaded = kwinrules.reconfigure()
        suffix = (
            "KWin hat die Konfiguration neu eingelesen."
            if reloaded
            else "Bitte KWin neu starten oder neu anmelden - qdbus wurde nicht gefunden."
        )
        self.status.setText(
            f"Regel gespeichert ({self.x_spin.value()},{self.y_spin.value()}). {suffix}"
        )

    def on_remove(self) -> None:
        try:
            removed = kwinrules.remove_rule()
        except kwinrules.KWinRuleError as error:
            QMessageBox.critical(self, "Fehler", str(error))
            return
        kwinrules.reconfigure()
        self.status.setText(
            "Regel entfernt - das OSD erscheint wieder an der Standardposition."
            if removed
            else "Es war keine Regel dieses Programms vorhanden."
        )

    def on_test(self) -> None:
        if not kwinrules.show_test_osd("OSD-Position"):
            self.status.setText(
                "Test-OSD konnte nicht ausgelöst werden (org.kde.plasmashell "
                "nicht erreichbar). Alternativ einfach eine Lautstärketaste drücken."
            )


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("plasma-osd-position")
    app.setApplicationDisplayName("OSD-Position")
    app.setDesktopFileName("org.kde.plasma-osd-position")
    window = MainWindow()
    window.resize(620, 720)
    window.show()
    return app.exec()
