"""Qt-Oberfläche für plasma-osd-position."""

from __future__ import annotations

import sys
from typing import List, Optional, Tuple

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPen, QScreen
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import kwinrules

DEFAULT_OSD_WIDTH = 340
DEFAULT_OSD_HEIGHT = 74

ALIGNMENTS = [("Mittig", 0.5), ("Links", 0.0), ("Rechts", 1.0)]


def screens() -> List[QScreen]:
    return QGuiApplication.screens()


def virtual_geometry() -> QRect:
    total = QRect()
    for screen in screens():
        total = total.united(screen.geometry())
    return total if total.isValid() else QRect(0, 0, 1920, 1080)


class PreviewWidget(QWidget):
    """Zeichnet alle Bildschirme in ihrer tatsächlichen Anordnung."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(170)
        self._target_index = 0
        self._osd = QRect(0, 0, DEFAULT_OSD_WIDTH, DEFAULT_OSD_HEIGHT)

    def update_geometry(self, target_index: int, osd: QRect) -> None:
        self._target_index = target_index
        self._osd = osd
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt-Namensschema)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()

        total = virtual_geometry()
        margin = 12
        scale = min(
            (self.width() - 2 * margin) / total.width(),
            (self.height() - 2 * margin) / total.height(),
        )
        off_x = (self.width() - total.width() * scale) / 2
        off_y = (self.height() - total.height() * scale) / 2

        def to_view(rect: QRect) -> QRect:
            return QRect(
                int(off_x + (rect.x() - total.x()) * scale),
                int(off_y + (rect.y() - total.y()) * scale),
                max(3, int(rect.width() * scale)),
                max(3, int(rect.height() * scale)),
            )

        for index, screen in enumerate(screens()):
            view = to_view(screen.geometry())
            is_target = index == self._target_index
            painter.setPen(QPen(palette.highlight().color() if is_target else palette.mid().color(), 1))
            painter.setBrush(palette.base() if is_target else palette.window())
            painter.drawRoundedRect(view, 4, 4)
            painter.setPen(palette.text().color() if is_target else palette.mid().color())
            painter.drawText(view, Qt.AlignmentFlag.AlignCenter, screen.name())

        accent = palette.highlight().color()
        painter.setPen(QPen(accent, 1))
        painter.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 150))
        painter.drawRoundedRect(to_view(self._osd), 3, 3)
        painter.end()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OSD-Position")
        self.setWindowIcon(QIcon.fromTheme("preferences-desktop-display"))

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setSpacing(12)

        intro = QLabel(
            "Legt fest, wo das Lautstärke- und Helligkeits-OSD von Plasma erscheint – "
            "über eine KWin-Fensterregel (Fenstertyp „On-Screen Display“).\n\n"
            "Achtung: Die Regel setzt eine absolute Position. Das OSD erscheint danach "
            "immer auf dem gewählten Bildschirm und folgt nicht mehr dem aktiven."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(self._build_position_box())
        layout.addWidget(self._build_advanced_box())

        preview_box = QGroupBox("Vorschau (alle Bildschirme)")
        preview_layout = QVBoxLayout(preview_box)
        self.preview = PreviewWidget()
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
        self._describe_existing()
        self._recalculate()

    # --- Aufbau ------------------------------------------------------------
    def _build_position_box(self) -> QGroupBox:
        box = QGroupBox("Position")
        form = QFormLayout(box)

        self.screen_combo = QComboBox()
        primary = QGuiApplication.primaryScreen()
        for index, screen in enumerate(screens()):
            geo = screen.geometry()
            label = f"{screen.name()} – {geo.width()}×{geo.height()} @ {geo.x()},{geo.y()}"
            if screen is primary:
                label += "  (primär)"
            self.screen_combo.addItem(label)
            if screen is primary:
                self.screen_combo.setCurrentIndex(index)
        self.screen_combo.currentIndexChanged.connect(self._recalculate)
        form.addRow("Bildschirm:", self.screen_combo)

        self.bottom_spin = QSpinBox()
        self.bottom_spin.setRange(0, 4000)
        self.bottom_spin.setValue(120)
        self.bottom_spin.setSuffix(" px")
        self.bottom_spin.valueChanged.connect(self._recalculate)
        form.addRow("Abstand zum unteren Rand:", self.bottom_spin)

        self.align_combo = QComboBox()
        for label, _ in ALIGNMENTS:
            self.align_combo.addItem(label)
        self.align_combo.currentIndexChanged.connect(self._on_alignment_changed)
        form.addRow("Horizontal:", self.align_combo)

        self.side_spin = QSpinBox()
        self.side_spin.setRange(0, 4000)
        self.side_spin.setValue(40)
        self.side_spin.setSuffix(" px")
        self.side_spin.setEnabled(False)
        self.side_spin.valueChanged.connect(self._recalculate)
        form.addRow("Seitlicher Abstand:", self.side_spin)

        self.result_label = QLabel()
        form.addRow("Ergebnis:", self.result_label)
        return box

    def _build_advanced_box(self) -> QGroupBox:
        box = QGroupBox("Feinjustierung")
        layout = QHBoxLayout(box)

        left = QFormLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(40, 2000)
        self.width_spin.setValue(DEFAULT_OSD_WIDTH)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(20, 1000)
        self.height_spin.setValue(DEFAULT_OSD_HEIGHT)
        for spin in (self.width_spin, self.height_spin):
            spin.setSuffix(" px")
            spin.valueChanged.connect(self._recalculate)
        left.addRow("OSD-Breite:", self.width_spin)
        left.addRow("OSD-Höhe:", self.height_spin)

        right = QFormLayout()
        self.offset_x_spin = QSpinBox()
        self.offset_x_spin.setRange(-4000, 4000)
        self.offset_y_spin = QSpinBox()
        self.offset_y_spin.setRange(-4000, 4000)
        for spin in (self.offset_x_spin, self.offset_y_spin):
            spin.setSuffix(" px")
            spin.valueChanged.connect(self._recalculate)
        right.addRow("Versatz X:", self.offset_x_spin)
        right.addRow("Versatz Y:", self.offset_y_spin)

        layout.addLayout(left)
        layout.addLayout(right)
        return box

    # --- Logik -------------------------------------------------------------
    def _current_screen(self) -> QScreen:
        available = screens()
        index = max(0, min(self.screen_combo.currentIndex(), len(available) - 1))
        return available[index]

    def _on_alignment_changed(self) -> None:
        self.side_spin.setEnabled(self.align_combo.currentIndex() != 0)
        self._recalculate()

    def _target_rect(self) -> QRect:
        geo = self._current_screen().geometry()
        width = self.width_spin.value()
        height = self.height_spin.value()
        factor = ALIGNMENTS[self.align_combo.currentIndex()][1]

        if factor == 0.5:
            x = geo.x() + (geo.width() - width) // 2
        elif factor == 0.0:
            x = geo.x() + self.side_spin.value()
        else:
            x = geo.x() + geo.width() - width - self.side_spin.value()

        y = geo.y() + geo.height() - height - self.bottom_spin.value()
        return QRect(
            x + self.offset_x_spin.value(),
            y + self.offset_y_spin.value(),
            width,
            height,
        )

    def _recalculate(self) -> None:
        rect = self._target_rect()
        self.result_label.setText(f"X = {rect.x()}, Y = {rect.y()} (global)")
        self.preview.update_geometry(self.screen_combo.currentIndex(), rect)

    def _describe_existing(self) -> None:
        position: Optional[Tuple[int, int]] = kwinrules.current_position()
        self.status.setText(
            f"Bestehende Regel: Position {position[0]},{position[1]}."
            if position
            else "Noch keine Regel vorhanden."
        )

    # --- Aktionen ----------------------------------------------------------
    def on_apply(self) -> None:
        rect = self._target_rect()
        try:
            kwinrules.apply_position(rect.x(), rect.y())
        except kwinrules.KWinRuleError as error:
            QMessageBox.critical(self, "Fehler", str(error))
            return
        reloaded = kwinrules.reconfigure()
        suffix = (
            "KWin hat die Konfiguration neu eingelesen."
            if reloaded
            else "Bitte neu anmelden – qdbus wurde nicht gefunden."
        )
        self.status.setText(f"Regel gespeichert ({rect.x()},{rect.y()}). {suffix}")

    def on_remove(self) -> None:
        try:
            removed = kwinrules.remove_rule()
        except kwinrules.KWinRuleError as error:
            QMessageBox.critical(self, "Fehler", str(error))
            return
        kwinrules.reconfigure()
        self.status.setText(
            "Regel entfernt – das OSD folgt wieder dem aktiven Bildschirm."
            if removed
            else "Es war keine Regel dieses Programms vorhanden."
        )

    def on_test(self) -> None:
        if not kwinrules.show_test_osd("OSD-Position"):
            self.status.setText(
                "Test-OSD konnte nicht ausgelöst werden – alternativ einfach eine "
                "Lautstärketaste drücken."
            )


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("plasma-osd-position")
    app.setApplicationDisplayName("OSD-Position")
    app.setDesktopFileName("org.kde.plasma-osd-position")
    window = MainWindow()
    window.resize(620, 680)
    window.show()
    return app.exec()
