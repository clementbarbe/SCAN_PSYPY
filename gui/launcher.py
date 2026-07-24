"""
Minimal experiment menu — sober design.
Reopens after each run.
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QSpinBox, QComboBox,
    QCheckBox, QGroupBox, QTabWidget, QPushButton, QMessageBox,
)

from config.settings import ExperimentSettings
from gui.styles import STYLESHEET
from gui.task_panels import get_registered_panels


class ExperimentMenu(QMainWindow):

    def __init__(self, last_config: dict | None = None):
        super().__init__()
        self.setWindowTitle("Configuration Experimentale")
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(800)
        self.final_config = None
        self._last = last_config or {}
        self._build()

    def _build(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._build_config(root)
        self._build_tabs(root)

    def _build_config(self, parent):
        group = QGroupBox("Configuration")
        g = QGridLayout(group)
        g.setSpacing(6)
        g.setContentsMargins(12, 16, 12, 12)

        # Row 0
        g.addWidget(QLabel("Participant :"), 0, 0)
        self.txt_nom = QLineEdit()
        self.txt_nom.setPlaceholderText("ID")
        self.txt_nom.setFixedWidth(130)
        self.txt_nom.setText(self._last.get('pid', ''))
        g.addWidget(self.txt_nom, 0, 1)

        g.addWidget(QLabel("Session :"), 0, 2)
        self.spin_ses = QSpinBox()
        self.spin_ses.setRange(1, 20)
        self.spin_ses.setValue(self._last.get('session', 1))
        self.spin_ses.setFixedWidth(100)
        g.addWidget(self.spin_ses, 0, 3)

        g.addWidget(QLabel("Ecran :"), 0, 4)
        self.spin_scr = QSpinBox()
        n_screens = max(1, len(QApplication.screens()))
        self.spin_scr.setRange(0, n_screens - 1)
        self.spin_scr.setValue(self._last.get('screen', 0))
        self.spin_scr.setFixedWidth(100)
        g.addWidget(self.spin_scr, 0, 5)

        g.addWidget(QLabel("Mode :"), 0, 6)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["PC", "fMRI"])
        self.combo_mode.setCurrentText(self._last.get('mode', 'PC'))
        self.combo_mode.setFixedWidth(100)
        g.addWidget(self.combo_mode, 0, 7)

        # Row 1: checkboxes
        row1 = QHBoxLayout()
        row1.setSpacing(16)
        self.chk_save = QCheckBox("Save")
        self.chk_save.setChecked(self._last.get('save', True))
        row1.addWidget(self.chk_save)

        self.chk_parport = QCheckBox("Port parallele")
        self.chk_parport.setChecked(self._last.get('parport', False))
        row1.addWidget(self.chk_parport)

        self.chk_et = QCheckBox("Eye-tracker")
        self.chk_et.setChecked(self._last.get('et', False))
        row1.addWidget(self.chk_et)

        self.btn_reset = QPushButton("Force Reset")
        self.btn_reset.setObjectName("resetBtn")
        self.btn_reset.setFixedWidth(85)
        self.btn_reset.clicked.connect(self._reset_et)
        row1.addWidget(self.btn_reset)

        row1.addStretch()
        g.addLayout(row1, 1, 0, 1, 8)

        parent.addWidget(group)

    def _build_tabs(self, parent):
        self.tabs = QTabWidget()
        panels = get_registered_panels()
        for name, cls in panels.items():
            self.tabs.addTab(cls(self), name)

        # Restore last active tab
        last_tab = self._last.get('tab_index', 0)
        if 0 <= last_tab < self.tabs.count():
            self.tabs.setCurrentIndex(last_tab)

        parent.addWidget(self.tabs)

    # ── Validation ───────────────────────────────────────────────────

    def _get_current_state(self) -> dict:
        """Capture current GUI state for persistence across reopens."""
        return {
            'pid': self.txt_nom.text().strip(),
            'session': self.spin_ses.value(),
            'screen': self.spin_scr.value(),
            'mode': self.combo_mode.currentText(),
            'save': self.chk_save.isChecked(),
            'parport': self.chk_parport.isChecked(),
            'et': self.chk_et.isChecked(),
            'tab_index': self.tabs.currentIndex(),
        }

    def validate(self) -> ExperimentSettings | None:
        nom = self.txt_nom.text().strip()
        if not nom:
            QMessageBox.warning(self, "Erreur", "Nom du participant requis.")
            return None
        safe = ''.join(c for c in nom if c.isalnum() or c in '-_')
        if not safe:
            QMessageBox.warning(self, "Erreur", "Nom invalide.")
            return None
        mode = self.combo_mode.currentText().lower()
        return ExperimentSettings(
            participant_id=safe,
            session=f"{self.spin_ses.value():02d}",
            mode=mode,
            fullscreen=(mode == 'fmri'),
            screen_index=self.spin_scr.value(),
            eyetracker_enabled=self.chk_et.isChecked(),
            trigger_output_enabled=self.chk_parport.isChecked(),
            save_data=self.chk_save.isChecked(),
        )

    def run_experiment(self, task_params: dict):
        settings = self.validate()
        if settings is None:
            return

        self.final_config = {
            'settings': settings,
            'task_name': task_params['task_name'],
            'design_id': task_params.get('design_id', 1),
            'extra_params': task_params.get('extra_params', {}),
            '_gui_state': self._get_current_state(),
        }

        self.close()
        app = QApplication.instance()
        if app:
            app.quit()

    def get_config(self) -> dict | None:
        return self.final_config

    def _reset_et(self):
        reply = QMessageBox.question(
            self, "Force Reset",
            "Reinitialiser l'eye-tracker ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from hardware.eyetracker import EyeTracker
        ok, msg = EyeTracker.force_reset()
        if ok:
            QMessageBox.information(self, "Eye Tracker", msg)
        else:
            QMessageBox.warning(self, "Eye Tracker", msg)


def show_menu(last_state: dict | None = None) -> dict | None:
    """
    Show menu, block until closed.
    Pass last_state to restore fields from previous run.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    menu = ExperimentMenu(last_config=last_state)
    menu.show()
    app.exec()
    return menu.get_config()